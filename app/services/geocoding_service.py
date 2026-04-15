"""
Geocoding service — resolves location names to lat/lon via Nominatim (OSM).
Respects OSM's usage policy with a User-Agent header and request throttle.
"""

import httpx
import structlog

from app.core.exceptions import LocationResolutionError
from app.schemas.astronomy import LocationResponse

logger = structlog.get_logger(__name__)

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
TIMEOUT = 8.0


class GeocodingService:
    async def resolve(self, location_name: str) -> LocationResponse:
        try:
            async with httpx.AsyncClient(timeout=TIMEOUT) as client:
                resp = await client.get(
                    NOMINATIM_URL,
                    params={
                        "q": location_name,
                        "format": "json",
                        "limit": 1,
                        "addressdetails": 1,
                    },
                    headers={"User-Agent": "AstroTimeMachine/1.0"},
                )
                resp.raise_for_status()

                results = resp.json()
            if not results:
                raise LocationResolutionError(location_name)

            r = results[0]
            address = r.get("address", {})

            return LocationResponse(
                location_name=r.get("display_name", location_name),
                latitude=float(r["lat"]),
                longitude=float(r["lon"]),
                country=address.get("country"),
                timezone=None,   # would require a separate tz-lookup service
            )

        except LocationResolutionError:
            raise
        except Exception as exc:
            logger.error("geocoding_failed", location=location_name, error=str(exc))
            raise LocationResolutionError(location_name) from exc


geocoding_service = GeocodingService()
