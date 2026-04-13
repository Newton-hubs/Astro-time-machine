"""
AI narration service — uses Claude (Anthropic) to generate sky descriptions.
Falls back to a template-based description if the API is unavailable.
"""
from typing import Optional

import httpx
import structlog

from app.core.config import settings
from app.schemas.astronomy import MoonData, PlanetData, WeatherData

logger = structlog.get_logger(__name__)

SYSTEM_PROMPT = """You are an expert astronomer and poetic narrator. 
Given structured sky data, you write a vivid, engaging 2-3 paragraph description 
of the night sky as a knowledgeable guide would describe it to an observer.
Be scientifically accurate but accessible. Mention specific details from the data provided."""


class NarrationService:
    """
    Generates natural-language sky narration using Claude.
    Template fallback ensures the API always returns something useful.
    """

    async def generate(
        self,
        moon: MoonData,
        planets: list[PlanetData],
        weather: Optional[WeatherData],
        location_name: Optional[str],
        datetime_str: str,
    ) -> tuple[str, str]:
        """Returns (narration_text, model_used)."""

        prompt = self._build_prompt(moon, planets, weather, location_name, datetime_str)

        if settings.ANTHROPIC_API_KEY:
            try:
                return await self._call_claude(prompt)
            except Exception as exc:
                logger.warning("narration_api_failed", error=str(exc))

        # Graceful fallback
        return self._template_narration(moon, planets, weather), "template"

    async def _call_claude(self, prompt: str) -> tuple[str, str]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": settings.ANTHROPIC_API_KEY,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": "claude-3-5-haiku-20241022",
                    "max_tokens": 500,
                    "system": SYSTEM_PROMPT,
                    "messages": [{"role": "user", "content": prompt}],
                },
            )
            resp.raise_for_status()
            data = resp.json()
            text = data["content"][0]["text"]
            model = data.get("model", "claude-3-5-haiku")
            logger.info("narration_generated", model=model, chars=len(text))
            return text, model

    @staticmethod
    def _build_prompt(
        moon: MoonData,
        planets: list[PlanetData],
        weather: Optional[WeatherData],
        location_name: Optional[str],
        datetime_str: str,
    ) -> str:
        visible_planets = [p.name for p in planets if p.is_visible]
        weather_info = (
            f"Cloud cover: {weather.cloud_cover_pct}% ({weather.description})"
            if weather else "Weather data unavailable"
        )

        return f"""
Sky observation data:
- Location: {location_name or 'Unknown location'}
- Date/Time (UTC): {datetime_str}
- Moon phase: {moon.phase_name} ({moon.illumination_pct:.1f}% illuminated)
- Moon altitude: {moon.altitude_deg:.1f}° ({'above' if moon.is_above_horizon else 'below'} horizon)
- Moon cloud-obscured: {moon.is_cloud_obscured}
- Visible planets: {', '.join(visible_planets) if visible_planets else 'None'}
- {weather_info}

Please describe this night sky to an observer standing at this location.
""".strip()

    @staticmethod
    def _template_narration(
        moon: MoonData,
        planets: list[PlanetData],
        weather: Optional[WeatherData],
    ) -> str:
        moon_line = (
            f"Tonight the {moon.phase_name} hangs {'high' if moon.altitude_deg > 45 else 'low'} "
            f"in the sky, illuminated at {moon.illumination_pct:.0f}%."
            if moon.is_above_horizon
            else "The Moon has set below the horizon, leaving the sky darker."
        )

        planet_names = [p.name for p in planets if p.is_visible]
        planet_line = (
            f"Shining bright are: {', '.join(planet_names)}."
            if planet_names
            else "No planets are visible to the naked eye right now."
        )

        weather_line = (
            f"Cloud cover is {weather.cloud_cover_pct:.0f}%, "
            + ("obscuring much of the sky." if weather.cloud_cover_pct > 70 else "leaving the sky mostly clear.")
            if weather else ""
        )

        return f"{moon_line} {planet_line} {weather_line}".strip()


narration_service = NarrationService()
