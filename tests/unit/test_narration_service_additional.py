from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.schemas.astronomy import MoonData
from app.services.narration_service import NarrationService


def _moon():
    return MoonData(
        phase_name="Full Moon",
        illumination_pct=100.0,
        altitude_deg=50.0,
        azimuth_deg=180.0,
        is_above_horizon=True,
        is_cloud_obscured=False,
        age_days=14.0,
    )


@pytest.mark.asyncio
async def test_generate_uses_claude_when_api_key_present():
    service = NarrationService()
    with patch("app.services.narration_service.settings.ANTHROPIC_API_KEY", "key"), patch.object(
        service, "_call_claude", new_callable=AsyncMock
    ) as call_claude:
        call_claude.return_value = ("generated", "claude-model")
        text, model = await service.generate(_moon(), [], None, "X", "2024-01-01")

    assert text == "generated"
    assert model == "claude-model"


@pytest.mark.asyncio
async def test_generate_falls_back_when_claude_fails():
    service = NarrationService()
    with patch("app.services.narration_service.settings.ANTHROPIC_API_KEY", "key"), patch.object(
        service, "_call_claude", new_callable=AsyncMock
    ) as call_claude:
        call_claude.side_effect = RuntimeError("api down")
        text, model = await service.generate(_moon(), [], None, "X", "2024-01-01")

    assert model == "template"
    assert isinstance(text, str)


@pytest.mark.asyncio
async def test_call_claude_success_response():
    service = NarrationService()
    response = MagicMock()
    response.raise_for_status = MagicMock()
    response.json.return_value = {"content": [{"text": "hello"}], "model": "claude-x"}
    client = MagicMock()
    client.post = AsyncMock(return_value=response)

    with patch("app.services.narration_service.httpx.AsyncClient") as client_cls:
        client_cls.return_value.__aenter__.return_value = client
        text, model = await service._call_claude("prompt")

    assert text == "hello"
    assert model == "claude-x"
