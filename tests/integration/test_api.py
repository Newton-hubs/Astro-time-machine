"""
Integration tests for FastAPI endpoints.
Redis and external services are mocked.
"""
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.astronomy import (
    MoonData, PlanetData, SkySnapshotResponse, SkyVisualization, WeatherData
)


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


# ── Shared mock data ──────────────────────────────────────────────────────────

def make_moon():
    return MoonData(
        phase_name="Waxing Gibbous",
        illumination_pct=72.0,
        altitude_deg=42.0,
        azimuth_deg=180.0,
        is_above_horizon=True,
        is_cloud_obscured=False,
        age_days=10.5,
    )


def make_planets():
    return [
        PlanetData(name="Mars", altitude_deg=25.0, azimuth_deg=90.0, is_visible=True),
        PlanetData(name="Jupiter", altitude_deg=15.0, azimuth_deg=270.0, is_visible=True),
        PlanetData(name="Saturn", altitude_deg=-5.0, azimuth_deg=300.0, is_visible=False),
    ]


def make_snapshot():
    return SkySnapshotResponse(
        snapshot_id="test-snapshot-123",
        latitude=12.9716,
        longitude=77.5946,
        location_name="Bengaluru",
        datetime_utc=datetime(2024, 7, 4, 21, 0, 0, tzinfo=timezone.utc),
        moon=make_moon(),
        planets=make_planets(),
        weather=WeatherData(cloud_cover_pct=20.0, description="clear sky"),
        visualization=SkyVisualization(image_base64="abc123", width_px=600, height_px=600),
        computed_at=datetime.now(timezone.utc),
    )


# ── Health ────────────────────────────────────────────────────────────────────

class TestHealthEndpoint:
    @patch("app.db.redis_client.redis_client.health_check", new_callable=AsyncMock)
    def test_health_check_healthy(self, mock_ping, client):
        mock_ping.return_value = True
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert data["redis"] is True

    @patch("app.db.redis_client.redis_client.health_check", new_callable=AsyncMock)
    def test_health_check_degraded(self, mock_ping, client):
        mock_ping.return_value = False
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "degraded"


# ── Sky endpoint ──────────────────────────────────────────────────────────────

class TestSkyEndpoint:
    @patch("app.api.v1.endpoints.astronomy.check_rate_limit", new_callable=AsyncMock)
    @patch("app.api.v1.endpoints.astronomy.get_cached", new_callable=AsyncMock)
    @patch("app.api.v1.endpoints.astronomy.set_cached", new_callable=AsyncMock)
    @patch("app.api.v1.endpoints.astronomy.weather_service.get_cloud_cover", new_callable=AsyncMock)
    @patch("app.api.v1.endpoints.astronomy.astronomy_service.compute_moon")
    @patch("app.api.v1.endpoints.astronomy.astronomy_service.compute_planets")
    @patch("app.api.v1.endpoints.astronomy.visualization_service.render_sky")
    def test_sky_compute_success(
        self, mock_viz, mock_planets, mock_moon, mock_weather,
        mock_set_cache, mock_get_cache, mock_rate_limit, client
    ):
        mock_rate_limit.return_value = (True, 59)
        mock_get_cache.return_value = None
        mock_weather.return_value = WeatherData(cloud_cover_pct=20.0, description="clear sky")
        mock_moon.return_value = make_moon()
        mock_planets.return_value = make_planets()
        mock_viz.return_value = ("base64img", 600, 600)

        resp = client.post("/api/v1/astronomy/sky", json={
            "latitude": 12.9716,
            "longitude": 77.5946,
            "datetime_utc": "2024-07-04T21:00:00",
            "location_name": "Bengaluru",
        })

        assert resp.status_code == 200
        data = resp.json()
        assert "snapshot_id" in data
        assert data["moon"]["phase_name"] == "Waxing Gibbous"
        assert len(data["planets"]) == 3

    @patch("app.api.v1.endpoints.astronomy.check_rate_limit", new_callable=AsyncMock)
    @patch("app.api.v1.endpoints.astronomy.get_cached", new_callable=AsyncMock)
    def test_sky_returns_cached_result(self, mock_get_cache, mock_rate_limit, client):
        mock_rate_limit.return_value = (True, 59)
        snapshot = make_snapshot()
        mock_get_cache.return_value = snapshot.model_dump()

        resp = client.post("/api/v1/astronomy/sky", json={
            "latitude": 12.9716,
            "longitude": 77.5946,
            "datetime_utc": "2024-07-04T21:00:00",
        })

        assert resp.status_code == 200
        assert resp.json()["snapshot_id"] == "test-snapshot-123"

    @patch("app.api.v1.endpoints.astronomy.check_rate_limit", new_callable=AsyncMock)
    def test_sky_rate_limit_exceeded(self, mock_rate_limit, client):
        mock_rate_limit.return_value = (False, 0)

        resp = client.post("/api/v1/astronomy/sky", json={
            "latitude": 12.9716,
            "longitude": 77.5946,
            "datetime_utc": "2024-07-04T21:00:00",
        })
        assert resp.status_code == 429

    def test_sky_invalid_latitude(self, client):
        resp = client.post("/api/v1/astronomy/sky", json={
            "latitude": 999.0,
            "longitude": 77.0,
            "datetime_utc": "2024-07-04T21:00:00",
        })
        assert resp.status_code == 422

    def test_sky_missing_datetime(self, client):
        resp = client.post("/api/v1/astronomy/sky", json={
            "latitude": 12.0,
            "longitude": 77.0,
        })
        assert resp.status_code == 422


# ── Location endpoint ─────────────────────────────────────────────────────────

class TestLocationEndpoint:
    @patch("app.api.v1.endpoints.astronomy.check_rate_limit", new_callable=AsyncMock)
    @patch("app.api.v1.endpoints.astronomy.geocoding_service.resolve", new_callable=AsyncMock)
    def test_resolve_location_success(self, mock_resolve, mock_rate_limit, client):
        from app.schemas.astronomy import LocationResponse
        mock_rate_limit.return_value = (True, 59)
        mock_resolve.return_value = LocationResponse(
            location_name="Bengaluru, Karnataka, India",
            latitude=12.9716,
            longitude=77.5946,
            country="India",
            timezone=None,
        )

        resp = client.post("/api/v1/astronomy/location/resolve", json={
            "location_name": "Bengaluru"
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["latitude"] == 12.9716
        assert data["country"] == "India"

    @patch("app.api.v1.endpoints.astronomy.check_rate_limit", new_callable=AsyncMock)
    @patch("app.api.v1.endpoints.astronomy.geocoding_service.resolve", new_callable=AsyncMock)
    def test_resolve_location_not_found(self, mock_resolve, mock_rate_limit, client):
        from app.core.exceptions import LocationResolutionError
        mock_rate_limit.return_value = (True, 59)
        mock_resolve.side_effect = LocationResolutionError("xyzabc_nonexistent_place")

        resp = client.post("/api/v1/astronomy/location/resolve", json={
            "location_name": "xyzabc_nonexistent_place"
        })
        assert resp.status_code == 404
