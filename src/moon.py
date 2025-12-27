from skyfield.api import load, wgs84
from datetime import datetime, timezone
import math

eph = load('de421.bsp')
ts = load.timescale()


def get_moon_data(date, time, latitude, longitude):

    dt = datetime.combine(date, time).replace(tzinfo=timezone.utc)
    t = ts.from_datetime(dt)

    observer = wgs84.latlon(latitude, longitude)

    earth = eph["earth"]
    moon  = eph["moon"]
    sun   = eph["sun"]

    # ------------------------------------------------
    # 1) GEOCENTRIC VECTORS (for phase angle)
    # ------------------------------------------------
    moon_geo = earth.at(t).observe(moon)
    sun_geo  = earth.at(t).observe(sun)

    m_vec = moon_geo.position.km
    s_vec = sun_geo.position.km

    # dot-product angle formula
    dot = (m_vec * s_vec).sum()
    m_mag = math.sqrt((m_vec * m_vec).sum())
    s_mag = math.sqrt((s_vec * s_vec).sum())

    # angle between vectors (degrees)
    phase_angle = math.degrees(math.acos(dot / (m_mag * s_mag)))

    # illumination fraction
    illuminated = (1 + math.cos(math.radians(phase_angle))) / 2 * 100

    # ------------------------------------------------
    # 2) TOPOCENTRIC ALT-AZ (observer-based)
    # ------------------------------------------------
    moon_topo = (earth + observer).at(t).observe(moon).apparent()
    alt, az, _ = moon_topo.altaz()

    # ------------------------------------------------
    # 3) Phase name
    # ------------------------------------------------
    if illuminated < 5:
        phase_name = "New Moon"
    elif illuminated < 35:
        phase_name = "Crescent"
    elif illuminated < 65:
        phase_name = "First Quarter / Half Moon"
    elif illuminated < 95:
        phase_name = "Gibbous"
    else:
        phase_name = "Full Moon"

    return {
        "phase_name": phase_name,
        "illumination": round(illuminated, 1),
        "altitude": round(alt.degrees, 2),
        "azimuth": round(az.degrees, 2),
        "datetime_utc": dt,
    }
