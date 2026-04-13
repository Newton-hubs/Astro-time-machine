"""
Weather service — fetches cloud cover from OpenWeatherMap.
Implements a simple circuit breaker to avoid cascading failures.
"""
import time
from enum import Enum
from typing import Optional

import httpx
import structlog

from app.core.config import settings
from app.schemas.astronomy import WeatherData

logger = structlog.get_logger(__name__)

WEATHER_API_URL = "https://api.openweathermap.org/data/2.5/weather"
REQUEST_TIMEOUT = 5.0


class CircuitState(str, Enum):
    CLOSED = "closed"       # normal operation
    OPEN = "open"           # failing, reject requests
    HALF_OPEN = "half_open" # probe to see if service recovered


class CircuitBreaker:
    """
    Simple in-process circuit breaker.
    In production, state would live in Redis for multi-instance deployments.
    """
    FAILURE_THRESHOLD = 5
    RECOVERY_TIMEOUT = 60   # seconds

    def __init__(self):
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time: Optional[float] = None

    def record_success(self):
        self.failure_count = 0
        self.state = CircuitState.CLOSED

    def record_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.monotonic()
        if self.failure_count >= self.FAILURE_THRESHOLD:
            self.state = CircuitState.OPEN
            logger.warning("circuit_breaker_opened", service="weather")

    def allow_request(self) -> bool:
        if self.state == CircuitState.CLOSED:
            return True
        if self.state == CircuitState.OPEN:
            if time.monotonic() - (self.last_failure_time or 0) > self.RECOVERY_TIMEOUT:
                self.state = CircuitState.HALF_OPEN
                logger.info("circuit_breaker_half_open", service="weather")
                return True
            return False
        return True  # HALF_OPEN: allow one probe


weather_circuit = CircuitBreaker()


class WeatherService:
    async def get_cloud_cover(
        self,
        latitude: float,
        longitude: float,
    ) -> Optional[WeatherData]:
        """
        Fetch current cloud cover for coordinates.
        Returns None gracefully if the weather service is unavailable.
        """
        if not settings.OPENWEATHER_API_KEY:
            logger.debug("weather_api_key_missing")
            return None

        if not weather_circuit.allow_request():
            logger.warning("circuit_breaker_rejected", service="weather")
            return None

        try:
            async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
                resp = await client.get(
                    WEATHER_API_URL,
                    params={
                        "lat": latitude,
                        "lon": longitude,
                        "appid": settings.OPENWEATHER_API_KEY,
                        "units": "metric",
                    },
                )
                resp.raise_for_status()

            data = resp.json()
            cloud_cover = data.get("clouds", {}).get("all", 0)
            description = data.get("weather", [{}])[0].get("description", "unknown")

            weather_circuit.record_success()
            logger.info("weather_fetched", lat=latitude, lon=longitude, clouds=cloud_cover)

            return WeatherData(
                cloud_cover_pct=float(cloud_cover),
                description=description,
            )

        except httpx.TimeoutException:
            weather_circuit.record_failure()
            logger.warning("weather_timeout", lat=latitude, lon=longitude)
            return None
        except httpx.HTTPStatusError as exc:
            weather_circuit.record_failure()
            logger.error("weather_http_error", status=exc.response.status_code)
            return None
        except Exception as exc:
            weather_circuit.record_failure()
            logger.error("weather_unexpected_error", error=str(exc))
            return None


weather_service = WeatherService()
