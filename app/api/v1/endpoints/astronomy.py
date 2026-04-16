"""
Astronomy endpoints — core sky computation API.
"""
import uuid
from datetime import datetime, timezone

import structlog
from fastapi import APIRouter, Request

from app.core.cache import cache_key, get_cached, set_cached
from app.core.exceptions import RateLimitExceededError
from app.core.cache import check_rate_limit
from app.schemas.astronomy import (
    LocationQueryRequest,
    LocationResponse,
    SkyQueryRequest,
    SkySnapshotResponse,
    SkyVisualization,
)
from app.services.astronomy_service import astronomy_service
from app.services.geocoding_service import geocoding_service
from app.services.visualization_service import visualization_service
from app.services.weather_service import weather_service


router = APIRouter()
logger = structlog.get_logger(__name__)


async def get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    return forwarded.split(",")[0].strip() if forwarded else request.client.host


@router.post("/sky", response_model=SkySnapshotResponse, summary="Compute night sky snapshot")
async def compute_sky(
    body: SkyQueryRequest,
    request: Request,
):
    """
    Compute a complete sky snapshot for a given location and datetime.

    - Returns moon phase, illumination, altitude, and azimuth.
    - Returns visibility for all major planets.
    - Fetches cloud cover from OpenWeatherMap (if API key configured).
    - Generates a circular sky map image (base64 PNG).
    - Results are cached in Redis for 1 hour.
    """
    client_ip = await get_client_ip(request)

    # Rate limiting
    allowed, remaining = await check_rate_limit(client_ip)
    if not allowed:
        raise RateLimitExceededError()

    # Cache lookup
    ck = cache_key(
        "sky",
        body.latitude,
        body.longitude,
        body.datetime_utc.isoformat(),
    )
    cached = await get_cached(ck)
    if cached:
        return SkySnapshotResponse(**cached)

    logger.info(
        "sky_compute",
        lat=body.latitude,
        lon=body.longitude,
        dt=body.datetime_utc.isoformat(),
    )

    # Parallel-ish: weather doesn't block astronomy
    print("STEP 1: rate limit passed")

    weather = await weather_service.get_cloud_cover(body.latitude, body.longitude)
    print("STEP 2: weather done")

    cloud_cover = weather.cloud_cover_pct if weather else 0.0

    moon = astronomy_service.compute_moon(
        body.latitude, body.longitude, body.datetime_utc, cloud_cover
    )
    print("STEP 3: moon done")

    planets = astronomy_service.compute_planets(
        body.latitude, body.longitude, body.datetime_utc
    )
    print("STEP 4: planets done")

    img_b64, w, h = visualization_service.render_sky(moon, planets)
    print("STEP 5: visualization done")

    snapshot = SkySnapshotResponse(
        snapshot_id=str(uuid.uuid4()),
        latitude=body.latitude,
        longitude=body.longitude,
        location_name=body.location_name,
        datetime_utc=body.datetime_utc,
        moon=moon,
        planets=planets,
        weather=weather,
        visualization=SkyVisualization(image_base64=img_b64, width_px=w, height_px=h),
        computed_at=datetime.now(timezone.utc),
    )

    await set_cached(ck, snapshot.model_dump())
    print("SAVING SNAPSHOT:", snapshot.snapshot_id)

    # ADD THESE TWO LINES RIGHT HERE ↓
    from app.api.v1.endpoints.narration import register_snapshot
    register_snapshot(snapshot.snapshot_id, snapshot.model_dump())
    
    return snapshot


@router.post("/location/resolve", response_model=LocationResponse, summary="Resolve location name to coordinates")
async def resolve_location(body: LocationQueryRequest, request: Request):
    """
    Convert a human-readable place name to latitude/longitude using OSM Nominatim.
    """
    client_ip = await get_client_ip(request)
    allowed, _ = await check_rate_limit(client_ip)
    if not allowed:
        raise RateLimitExceededError()

    return await geocoding_service.resolve(body.location_name)
