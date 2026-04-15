import pytest
from unittest.mock import AsyncMock, patch

from app.services.visualization_service import VisualizationService
from app.services.narration_service import NarrationService
from app.services.geocoding_service import GeocodingService

from app.schemas.astronomy import MoonData, WeatherData


# ---------------------------
# 🌍 GeocodingService (ASYNC)
# ---------------------------
@pytest.mark.asyncio
@patch("app.services.geocoding_service.httpx.AsyncClient")
async def test_geocoding(mock_client):
    mock_response = AsyncMock()
    mock_response.json.return_value = [{
        "lat": "12.97",
        "lon": "77.59",
        "display_name": "Bangalore",
        "address": {"country": "India"},
    }]
    mock_response.raise_for_status = lambda: None

    mock_ctx = AsyncMock()
    mock_ctx.__aenter__.return_value = mock_ctx
    mock_ctx.get = AsyncMock(return_value=mock_response)
    mock_client.return_value = mock_ctx

    service = GeocodingService()
    result = await service.resolve("Bangalore")

    assert result.latitude == 12.97
    assert result.longitude == 77.59


# ---------------------------
# 🌌 VisualizationService
# ---------------------------
def test_visualization_basic():
    service = VisualizationService()

    moon = MoonData(
        phase_name="Full Moon",
        illumination_pct=100,
        altitude_deg=45,
        azimuth_deg=180,
        is_above_horizon=True,
        is_cloud_obscured=False,
        age_days=14,
    )

    planets = []

    encoded, w, h = service.render_sky(moon, planets)

    assert isinstance(encoded, str)
    assert w == 600
    assert h == 600


def test_visualization_empty_planets():
    service = VisualizationService()

    moon = MoonData(
        phase_name="New Moon",
        illumination_pct=0,
        altitude_deg=-10,
        azimuth_deg=0,
        is_above_horizon=False,
        is_cloud_obscured=False,
        age_days=0,
    )

    encoded, _, _ = service.render_sky(moon, [])

    assert encoded is not None


# ---------------------------
# 🧠 NarrationService (ASYNC)
# ---------------------------
@pytest.mark.asyncio
async def test_narration_template_fallback():
    service = NarrationService()

    moon = MoonData(
        phase_name="Full Moon",
        illumination_pct=100,
        altitude_deg=50,
        azimuth_deg=180,
        is_above_horizon=True,
        is_cloud_obscured=False,
        age_days=14,
    )

    weather = WeatherData(
        cloud_cover_pct=20,
        description="clear sky",
    )

    # Force fallback (no API key)
    with patch("app.services.narration_service.settings") as mock_settings:
        mock_settings.ANTHROPIC_API_KEY = ""

        text, model = await service.generate(
            moon=moon,
            planets=[],
            weather=weather,
            location_name="Bangalore",
            datetime_str="2024-07-04 21:00",
        )

    assert isinstance(text, str)
    assert model == "template"


@pytest.mark.asyncio
async def test_narration_with_no_weather():
    service = NarrationService()

    moon = MoonData(
        phase_name="New Moon",
        illumination_pct=0,
        altitude_deg=-5,
        azimuth_deg=0,
        is_above_horizon=False,
        is_cloud_obscured=False,
        age_days=0,
    )

    with patch("app.services.narration_service.settings") as mock_settings:
        mock_settings.ANTHROPIC_API_KEY = ""

        text, model = await service.generate(
            moon=moon,
            planets=[],
            weather=None,
            location_name=None,
            datetime_str="",
        )

    assert "Moon" in text or "sky" in text