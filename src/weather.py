import requests
from datetime import datetime


OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"


def get_cloud_cover(latitude, longitude, date=None, time=None):
    """
    Fetches cloud cover (%) for a given location and datetime.

    Returns:
        int cloud_cover_percent (0–100)
    """

    try:
        # If datetime not provided, use current time
        if date is None or time is None:
            dt = datetime.utcnow()
        else:
            dt = datetime.combine(date, time)

        params = {
            "latitude": latitude,
            "longitude": longitude,
            "hourly": "cloudcover",
            "timezone": "auto"
        }

        response = requests.get(OPEN_METEO_URL, params=params, timeout=10)
        response.raise_for_status()

        data = response.json()

        times = data["hourly"]["time"]
        clouds = data["hourly"]["cloudcover"]

        # Find closest hour index
        target_time = dt.strftime("%Y-%m-%dT%H:00")

        if target_time in times:
            idx = times.index(target_time)
            return int(clouds[idx])

        # fallback: return last available value
        return int(clouds[-1])

    except Exception as e:
        print("Weather API failed:", e)

        # Safe fallback value
        return 20   # assume mostly clear sky


# ---------------------------------------------------------
# 🌙 Moon Visibility Check
# ---------------------------------------------------------

def is_moon_hidden_by_clouds(cloud_cover, moon_altitude):
    """
    Determines whether the moon is obscured.

    Rules:
      - If moon below horizon → not visible anyway
      - > 80% clouds → moon hidden
      - 60–80% → partially visible
      - < 60% → visible

    Returns:
        True  = moon hidden
        False = moon visible
    """

    if moon_altitude < 0:
        return True   # below horizon

    if cloud_cover >= 80:
        return True

    if 60 <= cloud_cover < 80:
        return "partial"

    return False
