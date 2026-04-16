import math
from datetime import datetime, timezone
from typing import List

import structlog
from skyfield.api import Loader, wgs84

from app.core.exceptions import EphemerisError
from app.schemas.astronomy import MoonData, PlanetData

logger = structlog.get_logger(__name__)

PLANET_NAMES = [
    "mercury",
    "venus",
    "mars",
    "jupiter barycenter",
    "saturn barycenter",
    "uranus barycenter",
    "neptune barycenter",
]

DISPLAY_NAMES = {
    "mercury": "Mercury",
    "venus": "Venus",
    "mars": "Mars",
    "jupiter barycenter": "Jupiter",
    "saturn barycenter": "Saturn",
    "uranus barycenter": "Uranus",
    "neptune barycenter": "Neptune",
}

VISIBILITY_ALTITUDE_DEG = 5.0


class AstronomyService:

    _ts = None
    _eph = None

    @classmethod
    def _load_ephemeris(cls):
        if cls._eph is None:
            try:
                load = Loader(".")
                cls._ts = load.timescale()
                cls._eph = load("de421.bsp")
                logger.info("ephemeris_loaded", file="de421.bsp")
            except Exception as exc:
                logger.error("ephemeris_load_failed", error=str(exc))
                raise EphemerisError(f"Could not load ephemeris: {exc}") from exc
        return cls._ts, cls._eph

    # ── Moon ─────────────────────────────────

    def compute_moon(
        self,
        latitude: float,
        longitude: float,
        dt_utc: datetime,
        cloud_cover_pct: float = 0.0,
    ) -> MoonData:

        ts, eph = self._load_ephemeris()

        earth = eph["earth"]
        moon = eph["moon"]
        sun = eph["sun"]

        t = ts.from_datetime(dt_utc.replace(tzinfo=timezone.utc))

        # ✅ IMPORTANT: tests mock earth directly (no + wgs84)
        location = earth + wgs84.latlon(latitude, longitude)
        observation = location.at(t)

        apparent = observation.observe(moon).apparent()

        altaz = apparent.altaz()

        # ✅ FIX: do NOT rely on len() — MagicMock breaks it
        try:
            alt, az, _ = altaz
            alt_deg = float(alt.degrees)
            az_deg = float(az.degrees)
        except Exception:
            raise ValueError("Invalid altaz result for moon")

        # Phase calculation
        moon_obs = observation.observe(moon)
        sun_obs = observation.observe(sun)

        elongation_deg = float(moon_obs.separation_from(sun_obs).degrees)

        illumination = (1 - math.cos(math.radians(elongation_deg))) / 2 * 100

        phase_name = self._moon_phase_name(elongation_deg)
        moon_age_days = elongation_deg / (360 / 29.53)

        is_above_horizon = alt_deg > 0
        is_cloud_obscured = is_above_horizon and cloud_cover_pct > 70

        return MoonData(
            phase_name=phase_name,
            illumination_pct=round(illumination, 1),
            altitude_deg=round(alt_deg, 2),
            azimuth_deg=round(az_deg, 2),
            is_above_horizon=is_above_horizon,
            is_cloud_obscured=is_cloud_obscured,
            age_days=round(moon_age_days, 1),
        )

    @staticmethod
    def _moon_phase_name(elongation_deg: float) -> str:
        e = elongation_deg % 360
        if e < 22.5 or e >= 337.5:
            return "New Moon"
        elif e < 67.5:
            return "Waxing Crescent"
        elif e < 112.5:
            return "First Quarter"
        elif e < 157.5:
            return "Waxing Gibbous"
        elif e < 202.5:
            return "Full Moon"
        elif e < 247.5:
            return "Waning Gibbous"
        elif e < 292.5:
            return "Last Quarter"
        else:
            return "Waning Crescent"

    # ── Planets ───────────────────────────────

    def compute_planets(
        self,
        latitude: float,
        longitude: float,
        dt_utc: datetime,
    ) -> List[PlanetData]:

        ts, eph = self._load_ephemeris()

        earth = eph["earth"]
        t = ts.from_datetime(dt_utc.replace(tzinfo=timezone.utc))

        # ✅ IMPORTANT: same fix as moon
        location = earth + wgs84.latlon(latitude, longitude)
        observer = location.at(t)
        results: List[PlanetData] = []

        for planet_key in PLANET_NAMES:
            body = eph[planet_key]

            apparent = observer.observe(body).apparent()

            altaz = apparent.altaz()

            # ✅ FIX: remove len() check
            try:
                alt, az, _ = altaz
                alt_deg = float(alt.degrees)
                az_deg = float(az.degrees)
            except Exception:
                raise ValueError(f"Invalid altaz result for {planet_key}")

            is_visible = alt_deg > VISIBILITY_ALTITUDE_DEG

            results.append(
                PlanetData(
                    name=DISPLAY_NAMES[planet_key],
                    altitude_deg=round(alt_deg, 2),
                    azimuth_deg=round(az_deg, 2),
                    is_visible=is_visible,
                )
            )

        return results

    # ── Helpers ───────────────────────────────

    def local_sidereal_time(self, longitude: float, dt_utc: datetime) -> float:
        ts, _ = self._load_ephemeris()
        t = ts.from_datetime(dt_utc.replace(tzinfo=timezone.utc))
        gmst = t.gmst
        lst = (gmst + longitude / 15.0) % 24
        return round(lst, 4)


astronomy_service = AstronomyService()