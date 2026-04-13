"""
Unit tests for Pydantic schemas and cache key generation.
"""
from datetime import datetime

import pytest
from pydantic import ValidationError

from app.schemas.astronomy import (
    MoonData,
    SkyQueryRequest,
    WeatherData,
)
from app.core.cache import cache_key


class TestSkyQueryRequest:
    def test_valid_request(self):
        req = SkyQueryRequest(
            latitude=12.9716,
            longitude=77.5946,
            datetime_utc=datetime(2024, 7, 4, 21, 0, 0),
            location_name="Bengaluru",
        )
        assert req.latitude == 12.9716
        assert req.location_name == "Bengaluru"

    def test_invalid_latitude_too_high(self):
        with pytest.raises(ValidationError):
            SkyQueryRequest(
                latitude=91.0,
                longitude=77.0,
                datetime_utc=datetime(2024, 7, 4, 21, 0, 0),
            )

    def test_invalid_latitude_too_low(self):
        with pytest.raises(ValidationError):
            SkyQueryRequest(
                latitude=-91.0,
                longitude=77.0,
                datetime_utc=datetime(2024, 7, 4, 21, 0, 0),
            )

    def test_invalid_longitude(self):
        with pytest.raises(ValidationError):
            SkyQueryRequest(
                latitude=12.0,
                longitude=200.0,
                datetime_utc=datetime(2024, 7, 4, 21, 0, 0),
            )

    def test_datetime_out_of_range(self):
        with pytest.raises(ValidationError):
            SkyQueryRequest(
                latitude=12.0,
                longitude=77.0,
                datetime_utc=datetime(1700, 1, 1),
            )

    def test_datetime_future_allowed(self):
        req = SkyQueryRequest(
            latitude=12.0,
            longitude=77.0,
            datetime_utc=datetime(2099, 12, 31),
        )
        assert req.datetime_utc.year == 2099

    def test_location_name_optional(self):
        req = SkyQueryRequest(
            latitude=0.0,
            longitude=0.0,
            datetime_utc=datetime(2024, 1, 1),
        )
        assert req.location_name is None


class TestMoonData:
    def test_illumination_bounds(self):
        with pytest.raises(ValidationError):
            MoonData(
                phase_name="Full Moon",
                illumination_pct=110.0,  # > 100
                altitude_deg=45.0,
                azimuth_deg=180.0,
                is_above_horizon=True,
                is_cloud_obscured=False,
                age_days=14.5,
            )

    def test_valid_moon_data(self):
        moon = MoonData(
            phase_name="Waxing Gibbous",
            illumination_pct=75.3,
            altitude_deg=30.0,
            azimuth_deg=220.0,
            is_above_horizon=True,
            is_cloud_obscured=False,
            age_days=10.2,
        )
        assert moon.phase_name == "Waxing Gibbous"
        assert moon.illumination_pct == 75.3


class TestWeatherData:
    def test_cloud_cover_bounds(self):
        with pytest.raises(ValidationError):
            WeatherData(cloud_cover_pct=110.0, description="too cloudy")

    def test_valid_weather(self):
        w = WeatherData(cloud_cover_pct=40.0, description="scattered clouds")
        assert w.source == "OpenWeatherMap"


class TestCacheKey:
    def test_same_args_produce_same_key(self):
        k1 = cache_key("sky", 12.97, 77.59, "2024-07-04T21:00:00")
        k2 = cache_key("sky", 12.97, 77.59, "2024-07-04T21:00:00")
        assert k1 == k2

    def test_different_args_produce_different_keys(self):
        k1 = cache_key("sky", 12.97, 77.59, "2024-07-04T21:00:00")
        k2 = cache_key("sky", 13.00, 77.59, "2024-07-04T21:00:00")
        assert k1 != k2

    def test_key_is_string(self):
        k = cache_key("test", 1, 2, 3)
        assert isinstance(k, str)
        assert len(k) == 64  # SHA-256 hex digest
