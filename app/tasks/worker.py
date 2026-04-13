"""
Celery task queue — handles async jobs (e.g. TTS audio generation).
Workers are run separately: `celery -A app.tasks.worker worker --loglevel=info`
"""
import io
import uuid

import structlog
from celery import Celery

from app.core.config import settings

logger = structlog.get_logger(__name__)

celery_app = Celery(
    "astro_tasks",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.tasks.worker"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    result_expires=3600,
    task_track_started=True,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
)


@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=10,
    name="tasks.generate_voice",
)
def generate_voice_task(self, narration_text: str, job_id: str) -> dict:
    """
    Generate TTS audio from narration text using gTTS.
    Returns a dict with the audio file path.

    In production: upload audio to S3/GCS and return a signed URL.
    """
    try:
        from gtts import gTTS

        logger.info("voice_job_started", job_id=job_id)

        tts = gTTS(text=narration_text, lang="en", slow=False)
        buf = io.BytesIO()
        tts.write_to_fp(buf)
        buf.seek(0)

        # In production: upload buf to object storage and return a presigned URL
        audio_path = f"/tmp/audio_{job_id}.mp3"
        with open(audio_path, "wb") as f:
            f.write(buf.read())

        logger.info("voice_job_completed", job_id=job_id, path=audio_path)
        return {"status": "done", "audio_path": audio_path, "job_id": job_id}

    except Exception as exc:
        logger.error("voice_job_failed", job_id=job_id, error=str(exc))
        raise self.retry(exc=exc)
