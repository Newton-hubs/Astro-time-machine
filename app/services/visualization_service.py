"""
Sky visualization service — generates a circular night-sky projection as a PNG.
"""
import base64
import io
import math
from typing import List

import matplotlib
import matplotlib.pyplot as plt
import numpy as np

matplotlib.use("Agg")  # non-interactive backend — essential for server-side rendering

from app.schemas.astronomy import MoonData, PlanetData

PLANET_COLORS = {
    "Mercury": "#aaaaaa",
    "Venus":   "#fffacd",
    "Mars":    "#ff6b6b",
    "Jupiter": "#ffd700",
    "Saturn":  "#f5deb3",
    "Uranus":  "#7fffd4",
    "Neptune": "#4169e1",
}

MOON_PHASE_CHAR = {
    "New Moon":        "🌑",
    "Waxing Crescent": "🌒",
    "First Quarter":   "🌓",
    "Waxing Gibbous":  "🌔",
    "Full Moon":       "🌕",
    "Waning Gibbous":  "🌖",
    "Last Quarter":    "🌗",
    "Waning Crescent": "🌘",
}


def _alt_az_to_xy(altitude_deg: float, azimuth_deg: float) -> tuple[float, float]:
    """
    Project altitude/azimuth to 2D polar coordinates.
    Azimuth 0=N, 90=E. Center = zenith, edge = horizon.
    """
    r = 1.0 - (altitude_deg / 90.0)  # zenith at 0, horizon at 1
    theta = math.radians(azimuth_deg - 90)  # rotate so N is up
    x = r * math.cos(theta)
    y = r * math.sin(theta)
    return x, y


class VisualizationService:
    def render_sky(
        self,
        moon: MoonData,
        planets: List[PlanetData],
        size_px: int = 600,
    ) -> tuple[str, int, int]:
        """
        Returns (base64_png, width_px, height_px).
        """
        dpi = 100
        fig_size = size_px / dpi

        fig, ax = plt.subplots(figsize=(fig_size, fig_size), dpi=dpi)
        fig.patch.set_facecolor("#050a1a")
        ax.set_facecolor("#050a1a")

        # Draw horizon circle
        circle = plt.Circle((0, 0), 1.0, color="#1a2a4a", fill=True, zorder=1)
        ax.add_patch(circle)
        border = plt.Circle((0, 0), 1.0, color="#2a4a6a", fill=False, linewidth=2, zorder=2)
        ax.add_patch(border)

        # Cardinal direction labels
        for label, (lx, ly) in [("N", (0, 1.12)), ("S", (0, -1.12)),
                                  ("E", (1.12, 0)), ("W", (-1.12, 0))]:
            ax.text(lx, ly, label, color="#4a7a9a", ha="center", va="center",
                    fontsize=10, fontweight="bold", zorder=5)

        # Draw stars (random but seeded for determinism)
        rng = np.random.default_rng(42)
        for _ in range(200):
            angle = rng.uniform(0, 2 * math.pi)
            radius = rng.uniform(0, 0.98)
            sx, sy = radius * math.cos(angle), radius * math.sin(angle)
            brightness = rng.uniform(0.3, 1.0)
            size = rng.uniform(0.5, 2.5)
            ax.scatter(sx, sy, s=size, color=(brightness, brightness, brightness),
                       alpha=brightness, zorder=3)

        # Draw Moon
        if moon.is_above_horizon:
            mx, my = _alt_az_to_xy(moon.altitude_deg, moon.azimuth_deg)
            moon_alpha = 0.3 if moon.is_cloud_obscured else 1.0
            moon_size = 200 + moon.illumination_pct * 2
            ax.scatter(mx, my, s=moon_size, color="#fffde7", alpha=moon_alpha,
                       zorder=6, marker="o", edgecolors="#fff9c4", linewidths=1)
            ax.text(mx, my - 0.12, moon.phase_name, color="#fffde7",
                    ha="center", va="top", fontsize=7, alpha=moon_alpha, zorder=7)

        # Draw Planets
        for planet in planets:
            if planet.is_visible:
                px, py = _alt_az_to_xy(planet.altitude_deg, planet.azimuth_deg)
                color = PLANET_COLORS.get(planet.name, "#ffffff")
                ax.scatter(px, py, s=80, color=color, zorder=6,
                           edgecolors="white", linewidths=0.5)
                ax.text(px, py + 0.1, planet.name, color=color,
                        ha="center", va="bottom", fontsize=6, zorder=7)

        # Zenith marker
        ax.scatter(0, 0, s=15, color="#ffffff", alpha=0.4, zorder=4, marker="+")

        ax.set_xlim(-1.3, 1.3)
        ax.set_ylim(-1.3, 1.3)
        ax.set_aspect("equal")
        ax.axis("off")

        plt.tight_layout(pad=0)

        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=dpi, bbox_inches="tight",
                    facecolor=fig.get_facecolor())
        plt.close(fig)

        buf.seek(0)
        encoded = base64.b64encode(buf.read()).decode("utf-8")
        return encoded, size_px, size_px


visualization_service = VisualizationService()
