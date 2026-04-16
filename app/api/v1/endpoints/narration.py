"""
Narration endpoints — AI sky description + async TTS voice generation.
"""
import uuid

import structlog
from fastapi import APIRouter, Request

from app.core.cache import cache_key, get_cached, set_cached, check_rate_limit
from app.core.exceptions import NarrationError, RateLimitExceededError
from app.schemas.astronomy import NarrationRequest, NarrationResponse, VoiceJobResponse
from app.services.narration_service import narration_service

router = APIRouter()
logger = structlog.get_logger(__name__)

# In-memory snapshot store (use a DB in production)
_snapshot_store: dict = {}


def register_snapshot(snapshot_id: str, snapshot_data: dict):
    """Called by astronomy endpoint to store snapshot for narration lookup."""
    _snapshot_store[snapshot_id] = snapshot_data

    print("FETCHING SNAPSHOT:", snapshot_id)
@router.post("/generate", response_model=NarrationResponse, summary="Generate AI sky narration")
async def generate_narration(body: NarrationRequest, request: Request):
    """
    Generate a natural-language description of a sky snapshot.

    - Requires a `sky_snapshot_id` from the `/astronomy/sky` endpoint.
    - Uses Claude (Anthropic) if an API key is configured; falls back to template.
    - If `voice=true`, queues an async Celery job for TTS audio generation.
    """
    client_ip = request.client.host
    allowed, _ = await check_rate_limit(client_ip)
    if not allowed:
        raise RateLimitExceededError()

    ck = cache_key("narration", body.sky_snapshot_id)
    cached = await get_cached(ck)
    if cached and not body.voice:
        return NarrationResponse(**cached)

    snapshot = _snapshot_store.get(body.sky_snapshot_id)
    if not snapshot:
        raise NarrationError(
            f"Snapshot '{body.sky_snapshot_id}' not found. "
            "Call /astronomy/sky first to generate a snapshot."
        )

    from app.schemas.astronomy import MoonData, PlanetData, WeatherData
    moon = MoonData(**snapshot["moon"])
    planets = [PlanetData(**p) for p in snapshot["planets"]]
    weather = WeatherData(**snapshot["weather"]) if snapshot.get("weather") else None

    narration_text, model_used = await narration_service.generate(
        moon=moon,
        planets=planets,
        weather=weather,
        location_name=snapshot.get("location_name"),
        datetime_str=str(snapshot.get("datetime_utc")),
    )

    voice_job_id = None
    if body.voice:
        from app.tasks.worker import generate_voice_task
        job_id = str(uuid.uuid4())
        generate_voice_task.apply_async(
            args=[narration_text, job_id],
            task_id=job_id,
        )
        voice_job_id = job_id
        logger.info("voice_job_queued", job_id=job_id)

    response = NarrationResponse(
        snapshot_id=body.sky_snapshot_id,
        narration_text=narration_text,
        voice_job_id=voice_job_id,
        model_used=model_used,
    )
    
    await set_cached(ck, response.model_dump(), ttl=3600)
    return response


@router.get("/voice/{job_id}", response_model=VoiceJobResponse, summary="Poll voice job status")
async def get_voice_status(job_id: str):
    """
    Poll the status of an async TTS voice generation job.
    Returns status: pending | processing | done | failed
    and an `audio_url` when complete.
    """
    from app.tasks.worker import celery_app
    result = celery_app.AsyncResult(job_id)

    status_map = {
        "PENDING":  "pending",
        "STARTED":  "processing",
        "SUCCESS":  "done",
        "FAILURE":  "failed",
        "RETRY":    "processing",
    }
    status = status_map.get(result.state, "pending")
    audio_url = None

    if result.state == "SUCCESS" and result.result:
        # In production, replace with a signed S3/GCS URL
        audio_url = f"/audio/{job_id}.mp3"

    return VoiceJobResponse(job_id=job_id, status=status, audio_url=audio_url)
