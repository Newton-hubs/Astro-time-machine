from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.api.v1.endpoints import narration
from app.core.exceptions import NarrationError
from app.schemas.astronomy import (
    MoonData,
    NarrationRequest,
    NarrationResponse,
    PlanetData,
    WeatherData,
)


def _request(host: str = "127.0.0.1"):
    return SimpleNamespace(client=SimpleNamespace(host=host))


def _snapshot_dict():
    moon = MoonData(
        phase_name="Full Moon",
        illumination_pct=99.0,
        altitude_deg=30.0,
        azimuth_deg=120.0,
        is_above_horizon=True,
        is_cloud_obscured=False,
        age_days=14.1,
    )
    return {
        "moon": moon.model_dump(),
        "planets": [
            PlanetData(name="Mars", altitude_deg=10, azimuth_deg=90, is_visible=True).model_dump()
        ],
        "weather": WeatherData(cloud_cover_pct=10, description="clear").model_dump(),
        "location_name": "Bengaluru",
        "datetime_utc": "2024-07-04T21:00:00+00:00",
    }


@pytest.mark.asyncio
async def test_register_snapshot_and_generate_from_cache():
    narration._snapshot_store.clear()
    cached = NarrationResponse(
        snapshot_id="s1", narration_text="cached text", voice_job_id=None, model_used="template"
    ).model_dump()

    with patch("app.api.v1.endpoints.narration.check_rate_limit", new_callable=AsyncMock) as rate, patch(
        "app.api.v1.endpoints.narration.get_cached", new_callable=AsyncMock
    ) as get_cached:
        rate.return_value = (True, 1)
        get_cached.return_value = cached

        resp = await narration.generate_narration(
            NarrationRequest(sky_snapshot_id="s1", voice=False), _request()
        )

    assert resp.narration_text == "cached text"
    narration.register_snapshot("s1", {"a": 1})
    assert narration._snapshot_store["s1"] == {"a": 1}


@pytest.mark.asyncio
async def test_generate_narration_missing_snapshot_raises():
    narration._snapshot_store.clear()
    with patch("app.api.v1.endpoints.narration.check_rate_limit", new_callable=AsyncMock) as rate, patch(
        "app.api.v1.endpoints.narration.get_cached", new_callable=AsyncMock
    ) as get_cached:
        rate.return_value = (True, 1)
        get_cached.return_value = None
        with pytest.raises(NarrationError):
            await narration.generate_narration(
                NarrationRequest(sky_snapshot_id="missing", voice=False), _request()
            )


@pytest.mark.asyncio
async def test_generate_narration_voice_job_path():
    narration._snapshot_store.clear()
    narration._snapshot_store["snap-1"] = _snapshot_dict()

    with patch("app.api.v1.endpoints.narration.check_rate_limit", new_callable=AsyncMock) as rate, patch(
        "app.api.v1.endpoints.narration.get_cached", new_callable=AsyncMock
    ) as get_cached, patch(
        "app.api.v1.endpoints.narration.narration_service.generate", new_callable=AsyncMock
    ) as generate, patch(
        "app.api.v1.endpoints.narration.set_cached", new_callable=AsyncMock
    ) as set_cached, patch(
        "app.api.v1.endpoints.narration.uuid.uuid4", return_value="job-123"
    ), patch(
        "app.tasks.worker.generate_voice_task.apply_async"
    ) as apply_async:
        rate.return_value = (True, 1)
        get_cached.return_value = None
        generate.return_value = ("hello sky", "template")

        resp = await narration.generate_narration(
            NarrationRequest(sky_snapshot_id="snap-1", voice=True), _request()
        )

    assert resp.voice_job_id == "job-123"
    apply_async.assert_called_once()
    set_cached.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_voice_status_maps_states():
    success_result = MagicMock(state="SUCCESS", result={"ok": True})
    pending_result = MagicMock(state="WHATEVER", result=None)

    with patch("app.tasks.worker.celery_app.AsyncResult", return_value=success_result):
        done = await narration.get_voice_status("j1")
        assert done.status == "done"
        assert done.audio_url == "/audio/j1.mp3"

    with patch("app.tasks.worker.celery_app.AsyncResult", return_value=pending_result):
        pending = await narration.get_voice_status("j2")
        assert pending.status == "pending"
        assert pending.audio_url is None
