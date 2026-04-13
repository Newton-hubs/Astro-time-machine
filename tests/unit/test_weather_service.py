"""
Unit tests for WeatherService and CircuitBreaker.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.weather_service import CircuitBreaker, CircuitState, WeatherService


class TestCircuitBreaker:
    def setup_method(self):
        self.cb = CircuitBreaker()

    def test_initial_state_is_closed(self):
        assert self.cb.state == CircuitState.CLOSED
        assert self.cb.allow_request() is True

    def test_opens_after_threshold_failures(self):
        for _ in range(CircuitBreaker.FAILURE_THRESHOLD):
            self.cb.record_failure()
        assert self.cb.state == CircuitState.OPEN
        assert self.cb.allow_request() is False

    def test_success_resets_to_closed(self):
        for _ in range(CircuitBreaker.FAILURE_THRESHOLD):
            self.cb.record_failure()
        assert self.cb.state == CircuitState.OPEN
        self.cb.record_success()
        assert self.cb.state == CircuitState.CLOSED
        assert self.cb.failure_count == 0

    def test_half_open_after_recovery_timeout(self):
        for _ in range(CircuitBreaker.FAILURE_THRESHOLD):
            self.cb.record_failure()
        # Simulate recovery timeout elapsed
        self.cb.last_failure_time = 0  # far in the past
        assert self.cb.allow_request() is True
        assert self.cb.state == CircuitState.HALF_OPEN


class TestWeatherService:
    @pytest.mark.asyncio
    async def test_returns_none_without_api_key(self):
        service = WeatherService()
        with patch("app.services.weather_service.settings") as mock_settings:
            mock_settings.OPENWEATHER_API_KEY = ""
            result = await service.get_cloud_cover(12.97, 77.59)
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_weather_data_on_success(self):
        service = WeatherService()
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "clouds": {"all": 40},
            "weather": [{"description": "scattered clouds"}],
        }

        with patch("app.services.weather_service.settings") as mock_settings, \
             patch("httpx.AsyncClient") as mock_client:
            mock_settings.OPENWEATHER_API_KEY = "test-key"

            mock_ctx = AsyncMock()
            mock_ctx.__aenter__ = AsyncMock(return_value=mock_ctx)
            mock_ctx.__aexit__ = AsyncMock(return_value=False)
            mock_ctx.get = AsyncMock(return_value=mock_response)
            mock_client.return_value = mock_ctx

            result = await service.get_cloud_cover(12.97, 77.59)

        assert result is not None
        assert result.cloud_cover_pct == 40.0
        assert result.description == "scattered clouds"

    @pytest.mark.asyncio
    async def test_returns_none_on_timeout(self):
        import httpx
        service = WeatherService()

        with patch("app.services.weather_service.settings") as mock_settings, \
             patch("httpx.AsyncClient") as mock_client:
            mock_settings.OPENWEATHER_API_KEY = "test-key"

            mock_ctx = AsyncMock()
            mock_ctx.__aenter__ = AsyncMock(return_value=mock_ctx)
            mock_ctx.__aexit__ = AsyncMock(return_value=False)
            mock_ctx.get = AsyncMock(side_effect=httpx.TimeoutException("timeout"))
            mock_client.return_value = mock_ctx

            result = await service.get_cloud_cover(12.97, 77.59)

        assert result is None

    @pytest.mark.asyncio
    async def test_circuit_breaker_blocks_when_open(self):
        service = WeatherService()
        from app.services.weather_service import weather_circuit, CircuitState
        original_state = weather_circuit.state

        weather_circuit.state = CircuitState.OPEN
        weather_circuit.last_failure_time = 9999999999  # far in future

        with patch("app.services.weather_service.settings") as mock_settings:
            mock_settings.OPENWEATHER_API_KEY = "test-key"
            result = await service.get_cloud_cover(12.97, 77.59)

        weather_circuit.state = original_state  # restore
        assert result is None
