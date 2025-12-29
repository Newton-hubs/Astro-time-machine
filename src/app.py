import streamlit as st
from datetime import time as dt_time, date as dt_date
from moon import get_moon_data
from weather import get_cloud_cover, is_moon_hidden_by_clouds
from sky_generator import generate_sky_image
import base64
from ai_interpreter import generate_sky_description
from ai_voice import generate_voice_narration
import re
import requests
from geopy.geocoders import Nominatim
import streamlit.components.v1 as components


# ===============================
# Geocoder (City Search)
# ===============================
geolocator = Nominatim(user_agent="astro_time_machine_app")

def lookup_city_coordinates(city_name: str):
    try:
        location = geolocator.geocode(city_name)
        if location:
            return {
                "city": location.address.split(",")[0],
                "lat": location.latitude,
                "lon": location.longitude
            }
    except:
        pass
    return None


# ===============================
# Safe IP Location Detection
# ===============================
def get_user_location():
    try:
        r = requests.get("https://ipapi.co/json/", timeout=5)
        if r.status_code == 200:
            d = r.json()
            lat = d.get("latitude")
            lon = d.get("longitude")
            if lat and lon:
                return {
                    "city": d.get("city", "Unknown"),
                    "lat": lat,
                    "lon": lon,
                }
    except:
        pass
    return None


# ===============================
# Browser GPS Detection
# ===============================
def get_browser_location():
    """
    Requests browser GPS and returns 'lat,lon' string via hidden input binding.
    """
    # hidden text input to receive data from JS
    st.text_input("", key="gps_coords", label_visibility="collapsed")

    components.html("""
    <script>
    navigator.geolocation.getCurrentPosition(
        function(pos) {
            const value = pos.coords.latitude + "," + pos.coords.longitude;

            // find the hidden Streamlit input
            const input = window.parent.document.querySelector(
                'input[id="gps_coords"]'
            );

            if (input) {
                input.value = value;

                // notify Streamlit of the change
                const event = new Event('input', { bubbles: true });
                input.dispatchEvent(event);
            }
        }
    );
    </script>
    """, height=0)

    return st.session_state.get("gps_coords", None)

# ===============================
# Page Config
# ===============================
st.set_page_config(layout="wide", page_title="Astro Time Machine", page_icon="🌌")


# ===============================
# UI Styling (unchanged)
# ===============================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap'); 
@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@500;700&display=swap');
header[data-testid="stHeader"] { display:none; }
[data-testid="stToolbar"] { display:none; }

html, body, #root {
    margin:0 !important;
    padding:0 !important;
}

body { background:#020410; color:#e3e7ff; }

main.block-container {
    margin-top:0 !important;
    padding-top:0 !important;
    padding-bottom:0.5rem !important;
    max-width:1400px;
}

/* Remove top blank margin injected by Streamlit */ 
section[data-testid="stSidebar"], 
div.block-container { 
            padding-top: 0rem !important; 
            margin-top: 0rem !important; } 
            /* Prevent browser default spacing */ 
            #root > div:nth-child(1) { 
            # padding-top: 0 !important; 
            # margin-top: 0 !important; 
            }
/* Top bar */
.top-bar {
    display:flex;
    justify-content:space-between;
    align-items:center;
    padding:0.4rem 1.5rem;
    background:#050814;
    border-bottom:1px solid rgba(255,255,255,0.06);
    margin-bottom:0.7rem;
}

.top-title {
    font-family:'Orbitron', monospace;
    letter-spacing:.12em;
    color:#8fa4ff;
    text-transform:uppercase;
}

/* Cards */
.card {
    background:#060a1e;
    border-radius:14px;
    padding:.9rem 1rem;
    border:1px solid rgba(160,180,255,0.18);
}

.section-title { font-weight:600; color:#f4f5ff; }

/* Info tiles */
.info-tile {
    background:#11182f;
    border-radius:14px;
    padding:.7rem .8rem;
    border:1px solid rgba(140,160,255,0.25);
    margin-bottom:.6rem;
}

/* Sky preview */
.sky-circle {
    width:min(430px,60vh);
    height:min(430px,60vh);
    border-radius:50%;
    border:2px solid rgba(120,170,255,.7);
    box-shadow:0 0 40px rgba(25,80,200,.6),
               0 0 120px rgba(25,80,200,.4);
    display:flex;
    align-items:center;
    justify-content:center;
    overflow:hidden;
    background:radial-gradient(circle at 50% 35%, #050919 0%, #02030a 70%);
}

.sky-circle img {
    width:108%;
    height:108%;
    object-fit:cover;
    object-position:center 45%;
}

</style>
""", unsafe_allow_html=True)


# ===============================
# Session Defaults
# ===============================
if "current_sky_image" not in st.session_state:
    st.session_state.current_sky_image = None
    st.session_state.visible_planets = []
    st.session_state.moon_status_text = "—"
    st.session_state.moon_phase_label = "—"
    st.session_state.ai_summary = "Generate a sky view to see AI narration."
    st.session_state.voice_path = None


# ===============================
# Header Bar
# ===============================
st.markdown("""
<div class="top-bar">
    <div class="top-title">ASTRO TIME MACHINE</div>
    <div>Travel through time to see the sky from anywhere on Earth</div>
</div>
""", unsafe_allow_html=True)


# ===============================
# Layout
# ===============================
col_controls, col_sky, col_info = st.columns([1.1, 1.3, 0.9])


# ======================================================
# 🎛 LEFT — MISSION CONTROL
# ======================================================
with col_controls:

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">🎛 Mission Control</div>', unsafe_allow_html=True)

    # -------------------------------------------------
    # LOCATION SYSTEM (GPS + IP + CITY SEARCH + MANUAL)
    # -------------------------------------------------
    use_live_location = st.toggle("📡 Use my live location (GPS / IP)")

    location = "Unknown"
    latitude = 12.97
    longitude = 77.59

    # ---------- AUTO MODE ----------
    if use_live_location:

        gps_clicked = st.button("📍 Detect using GPS")

        got_location = False

        # Try GPS first
        if gps_clicked:
            coords = get_browser_location()
            if coords:
                try:
                    lat, lon = map(float, coords.split(","))
                    latitude, longitude = lat, lon
                    location = "My Location"
                    got_location = True
                    st.success("✔ GPS location detected")
                except:
                    st.error("⚠ Unable to read GPS values")

        # Fallback to IP lookup
        if not got_location:
            ip_loc = get_user_location()

            if ip_loc:
                location = ip_loc["city"]
                latitude = ip_loc["lat"]
                longitude = ip_loc["lon"]
                st.success(f"📍 Location detected: {location}")
            else:
                st.info("🌐 Auto-location unavailable — switched to manual mode")
                use_live_location = False


    # ---------- MANUAL MODE ----------
    if not use_live_location:

        location_mode = st.radio(
            "Choose location method",
            ["Select a city", "Search a city", "Custom coordinates"]
        )

        # Preset cities
        if location_mode == "Select a city":
            location = st.selectbox("City", ["Bangalore", "New York", "London"])

            if location == "Bangalore":
                latitude, longitude = 12.97, 77.59
            elif location == "New York":
                latitude, longitude = 40.71, -74.00
            else:
                latitude, longitude = 51.50, -0.12

        # City search (no coordinates needed)
        elif location_mode == "Search a city":
            city_input = st.text_input("Enter city name")

            if city_input:
                city_result = lookup_city_coordinates(city_input)

                if city_result:
                    location = city_result["city"]
                    latitude = city_result["lat"]
                    longitude = city_result["lon"]
                    st.success(f"📍 Found: {location}")
                else:
                    st.error("❌ City not found — try another name")

        # Manual expert mode
        else:
            location = "Custom Location"
            latitude = st.number_input("Latitude", value=12.97, format="%.6f")
            longitude = st.number_input("Longitude", value=77.59, format="%.6f")


    # ---------- DATE & TIME ----------
    c1, c2 = st.columns(2)

    with c1:
        selected_date = st.date_input(
            "Date",
            dt_date.today(),
            min_value=dt_date(1900, 1, 1),
            max_value=dt_date(2100, 12, 31)
        )

    with c2:
        selected_time = st.time_input("Time", dt_time(21, 0))

    generate = st.button("🚀 Generate sky")

    st.markdown("</div>", unsafe_allow_html=True)


# ======================================================
# 🌌 CENTER — SKY DISPLAY
# ======================================================
with col_sky:

    st.markdown('<div class="card" style="display:flex;justify-content:center;">',
                unsafe_allow_html=True)

    if generate:

        with st.spinner("Computing celestial positions…"):

            moon = get_moon_data(
                date=selected_date,
                time=selected_time,
                latitude=latitude,
                longitude=longitude,
            )

            st.session_state.moon_phase_label = moon["phase_name"]
            moon_alt = moon["altitude"]
            moon_az = moon["azimuth"]
            moon_brightness = moon["illumination"]

            cloud_cover = get_cloud_cover(latitude, longitude)

            moon_cloud_hidden = is_moon_hidden_by_clouds(
                cloud_cover=cloud_cover,
                moon_altitude=moon_alt,
            )

            if moon_alt < 0:
                st.session_state.moon_status_text = "Below horizon"
            elif moon_cloud_hidden:
                st.session_state.moon_status_text = "Cloud obscured"
            else:
                st.session_state.moon_status_text = "Visible"

            image_path, st.session_state.visible_planets = generate_sky_image(
                date=selected_date,
                time=selected_time,
                latitude=latitude,
                longitude=longitude,
                cloud_cover=cloud_cover,
                moon_phase=moon_brightness / 100,
                moon_altitude=moon_alt,
                moon_azimuth=moon_az,
            )

            st.session_state.current_sky_image = str(image_path)

            st.session_state.ai_summary = generate_sky_description(
                location=location,
                date=selected_date,
                time=selected_time,
                moon_phase=moon["phase_name"],
                moon_visibility=st.session_state.moon_status_text,
                moon_brightness=moon["illumination"],
                visible_planets=st.session_state.visible_planets,
                cloud_cover=cloud_cover,
            )

            st.session_state.voice_path = generate_voice_narration(
                st.session_state.ai_summary
            )

    # render sky image
    if st.session_state.current_sky_image:
        with open(st.session_state.current_sky_image, "rb") as f:
            encoded = base64.b64encode(f.read()).decode()

        st.markdown(f"""
        <div class="sky-circle">
            <img src="data:image/png;base64,{encoded}">
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="sky-circle">
            <div style="color:#8fa4ff;text-align:center;">
                Choose a site, date & time<br>then click “Generate sky”
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)


# ======================================================
# 🛰 RIGHT — INFO TILES (unchanged)
# ======================================================
def info_tile(emoji, label, value):
    st.markdown(f"""
    <div class="info-tile">
        <div style="font-size:1.4rem">{emoji}</div>
        <div style="color:#9ca6d8;font-size:.8rem">{label}</div>
        <div style="font-size:.95rem;font-weight:600;color:#e8ecff">
            {value}
        </div>
    </div>
    """, unsafe_allow_html=True)

planet_list = ", ".join(st.session_state.visible_planets) or "None"

with col_info:
    info_tile("🌙", "Moon phase", st.session_state.moon_phase_label)
    info_tile("👁️", "Visibility", st.session_state.moon_status_text)
    info_tile("🪐", "Planets", planet_list)
    info_tile("📍", "Location", location)


# ======================================================
# 🤖 AI INTERPRETATION (unchanged)
# ======================================================
def clean_ai_summary(text):
    if not text:
        return ""
    text = re.sub(r"</?div[^>]*>", "", text, flags=re.IGNORECASE)
    text = text.replace("```", "")
    return text.strip()

safe_ai_text = clean_ai_summary(st.session_state.ai_summary)

st.markdown("""
<div style="
    margin-top:14px;
    background:#0f1432;
    border:1px solid rgba(160,180,255,.35);
    border-radius:14px;
    padding:1rem 1.2rem;
">
    <div style="font-size:1.2rem;font-weight:700;color:#e9ecff;margin-bottom:6px;">
        🤖 AI Sky Interpretation
    </div>
""", unsafe_allow_html=True)

st.markdown(safe_ai_text, unsafe_allow_html=True)
st.markdown("</div></div>", unsafe_allow_html=True)


# 🎧 AUDIO PLAYER
if st.session_state.voice_path:
    with open(st.session_state.voice_path, "rb") as f:
        st.audio(f.read(), format="audio/mp3")
