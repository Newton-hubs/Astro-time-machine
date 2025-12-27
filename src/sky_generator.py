import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from datetime import datetime, timezone

from skyfield.api import load, wgs84, Star

# ==========================
# Skyfield setup
# ==========================
eph = load("de421.bsp")
ts = load.timescale()

# ==========================
# Planet keys
# ==========================
PLANETS = {
    "Jupiter": "jupiter barycenter",
    "Saturn": "saturn barycenter",
    "Mars": "mars",
    "Venus": "venus",
}

# ==========================
# Minimal constellation set
# (we can expand later)
# ==========================
CONSTELLATIONS = {
    "Orion": [
        ("Betelgeuse", 88.79, 7.40),
        ("Bellatrix", 81.28, 6.34),
        ("Alnitak", 85.18, -1.94),
        ("Alnilam", 84.05, -1.20),
        ("Mintaka", 83.00, -0.29),
        ("Saiph", 86.93, -9.66),
        ("Rigel", 78.63, -8.20),
    ],
    "Cassiopeia": [
        ("Schedar", 10.12, 56.53),
        ("Caph", 2.29, 59.14),
        ("Ruchbah", 10.12, 60.23),
        ("Tsih", 14.17, 60.71),
        ("Segin", 28.59, 63.67),
    ],
    "Ursa Major": [
        ("Dubhe", 165.46, 61.75),
        ("Merak", 165.93, 56.38),
        ("Phecda", 178.45, 53.69),
        ("Megrez", 183.85, 57.03),
        ("Alioth", 193.50, 55.95),
        ("Mizar", 200.98, 54.92),
        ("Alkaid", 206.88, 49.31),
    ],
}


# ==========================
# Projection helper
# ==========================
def project_star_to_sky(az_deg, alt_deg):
    r = (90 - alt_deg) / 90 * 0.38
    theta = np.radians(az_deg)

    x = 0.5 + r * np.sin(theta)
    y = 0.5 + r * np.cos(theta)

    return x, y


# ==========================
# Convert RA/Dec → Alt/Az
# ==========================
def get_star_altaz(ra_deg, dec_deg, t, observer):
    star = Star(ra_hours=ra_deg / 15, dec_degrees=dec_deg)
    astrometric = observer.at(t).observe(star).apparent()
    alt, az, _ = astrometric.altaz()
    return alt.degrees, az.degrees


# ==========================
# Draw constellation lines
# ==========================
def draw_constellations(ax, t, observer):

    for name, stars in CONSTELLATIONS.items():

        pts = []

        for (_, ra, dec) in stars:

            alt, az = get_star_altaz(ra, dec, t, observer)

            # only draw if above horizon
            if alt <= 0:
                continue

            x, y = project_star_to_sky(az, alt)
            pts.append((x, y))

        if len(pts) < 2:
            continue

        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]

        ax.plot(
            xs, ys,
            linewidth=1.4,
            color="#8fa4ff",
            alpha=0.65
        )


# ==========================
# MAIN SKY RENDER
# ==========================
def generate_sky_image(
    date,
    time,
    latitude,
    longitude,
    cloud_cover=0,
    moon_phase=None,
    moon_altitude=None,
    moon_azimuth=None,
    show_constellations=True,
    filename="sky.png"
):

    output_dir = Path("assets/output")
    output_dir.mkdir(parents=True, exist_ok=True)

    dt = datetime.combine(date, time).replace(tzinfo=timezone.utc)
    t = ts.from_datetime(dt)

    observer = eph["earth"] + wgs84.latlon(latitude, longitude)

    fig, ax = plt.subplots(figsize=(6, 6))
    fig.patch.set_facecolor("#02030c")

    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    # ---------------- depth glow ----------------
    for r in np.linspace(1.2, 0.2, 60):
            ax.add_patch(plt.Circle(
                (0.5, 0.5),
                radius=r,
                color="#02030c",
                alpha=0.12
            ))

    # ---------------- stars ----------------
    star_visibility = max(0.35, 1 - cloud_cover / 120)

    ax.scatter(
        np.random.rand(500),
        np.random.rand(500),
        s=np.random.uniform(10, 60, 500),
        c=np.random.choice(
            ["#ffffff", "#dbe9ff", "#ffe7c7"],
            size=500,
            p=[0.6, 0.25, 0.15]
        ),
        alpha=0.9 * star_visibility
    )

    visible_planets = []

    # ---------------- planets ----------------
    for name, key in PLANETS.items():

        planet = eph[key]
        astrometric = observer.at(t).observe(planet).apparent()
        alt, az, _ = astrometric.altaz()

        if alt.degrees <= 0:
            continue

        visible_planets.append(name)

        px = 0.5 + np.sin(np.radians(az.degrees)) * 0.35
        py = 0.5 + np.cos(np.radians(az.degrees)) * 0.35

        ax.scatter(px, py, s=900, color="#ffde9c", alpha=0.35)
        ax.scatter(px, py, s=280, color="#ffd27d", alpha=1.0)

        ax.text(px, py - 0.06, name,
                color="white",
                ha="center",
                fontsize=11)

    # ---------------- constellations ----------------
    if show_constellations:
        draw_constellations(ax, t, observer)

    # ---------------- moon ----------------
    if (
        moon_altitude is not None
        and moon_azimuth is not None
        and moon_altitude > 0
    ):
        mx = 0.5 + np.sin(np.radians(moon_azimuth)) * 0.32
        my = 0.5 + np.cos(np.radians(moon_azimuth)) * 0.32

        moon_r = 0.05

        ax.scatter(mx, my, s=1800, color="white", alpha=0.12)
        ax.scatter(mx, my, s=650, color="white", alpha=0.95)

        if moon_phase is not None:
            offset = (0.5 - moon_phase) * (moon_r * 2)
            shadow = plt.Circle((mx + offset, my), moon_r, color="#02030c")
            ax.add_patch(shadow)

        ax.text(mx, my - 0.08, "Moon",
                color="white",
                ha="center",
                fontsize=11)

    # ---------------- save ----------------
    filepath = output_dir / filename

    plt.savefig(
        filepath,
        dpi=240,
        pad_inches=0,
        facecolor=fig.get_facecolor()
    )

    plt.close()

    return filepath, visible_planets
