import streamlit as st
from datetime import time as dt_time, date as dt_date
from moon import get_moon_data
from weather import get_cloud_cover, is_moon_hidden_by_clouds
from sky_generator import generate_sky_image
import base64
import geocoder
from ai_interpreter import generate_sky_description
from ai_voice import generate_voice_narration
import re

# ===============================
# Get User Location (IP lookup)
# ===============================
def get_user_location():
    try:
        g = geocoder.ip("me")
        if g.ok and g.latlng:
            return {
                "city": g.city or "Unknown",
                "lat": g.latlng[0],
                "lon": g.latlng[1],
            }
        return None
    except:
        return None


st.set_page_config(layout="wide", page_title="Astro Time Machine", page_icon="🌌")


# ===============================
# Global UI Styling
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
# Session State Defaults
# ===============================
if "current_sky_image" not in st.session_state:
    st.session_state.current_sky_image = None
    st.session_state.visible_planets = []
    st.session_state.moon_status_text = "—"
    st.session_state.moon_phase_label = "—"
    st.session_state.ai_summary = "Generate a sky view to see AI narration."
    st.session_state.voice_path = None


# ===============================
# Header
# ===============================
st.markdown("""
<div class="top-bar">
    <div class="top-title">ASTRO TIME MACHINE</div>
    <div>Travel through time to see the sky from anywhere on Earth</div>
</div>
""", unsafe_allow_html=True)


# ===============================
# Layout (Controls | Sky | Info)
# ===============================
col_controls, col_sky, col_info = st.columns([1.1, 1.3, 0.9])


# ======================================================
# 🎛 LEFT — Mission Control
# ======================================================
with col_controls:

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">🎛 Mission Control</div>', unsafe_allow_html=True)

    use_live_location = st.toggle("📡 Use my live location")

    if use_live_location:
        user_loc = get_user_location()

        if user_loc:
            location = user_loc["city"]
            latitude = user_loc["lat"]
            longitude = user_loc["lon"]
            st.success(f"📍 Location detected: {location}")

        else:
            st.error("⚠️ Unable to detect location — using manual mode")
            use_live_location = False

    if not use_live_location:
        location = st.selectbox("Site", ["Bangalore", "New York", "London"])

        if location == "Bangalore":
            latitude, longitude = 12.97, 77.59
        elif location == "New York":
            latitude, longitude = 40.71, -74.00
        else:
            latitude, longitude = 51.50, -0.12

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
# 🌌 CENTER — Sky Display
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

            # 🤖 AI text summary
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

            # 🎧 Voice narration
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
# 🛰 RIGHT — Info Tiles
# ======================================================
with col_info:

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

    info_tile("🌙", "Moon phase", st.session_state.moon_phase_label)
    info_tile("👁️", "Visibility", st.session_state.moon_status_text)
    info_tile("🪐", "Planets", planet_list)
    info_tile("📍", "Location", location)


# ======================================================
# 🤖 FULL-WIDTH AI INTERPRETATION (BOTTOM)
# ======================================================

def clean_ai_summary(text):
    """
    Cleans AI HTML output so raw <div> tags do not appear.
    Keeps inner text and formatting.
    """

    if not text:
        return ""

    # Remove ALL opening/closing div tags (case-insensitive)
    text = re.sub(r"</?div[^>]*>", "", text, flags=re.IGNORECASE)

    # Remove accidental code block formatting
    text = text.replace("```", "")

    # Remove leading/trailing whitespace
    text = text.strip()

    return text



# Clean AI output safely
safe_ai_text = clean_ai_summary(st.session_state.ai_summary)


# ---------- UI Card ----------
st.markdown("""
<div style="
    margin-top:14px;
    background:#0f1432;
    border:1px solid rgba(160,180,255,.35);
    border-radius:14px;
    padding:1rem 1.2rem;
">
    <div style="
        font-size:1.2rem;
        font-weight:700;
        color:#e9ecff;
        margin-bottom:6px;
    ">
        🤖 AI Sky Interpretation
    </div>

    
""", unsafe_allow_html=True)


# ---------- Insert Cleaned AI Text ----------
st.markdown(safe_ai_text, unsafe_allow_html=True)


# ---------- Close container ----------
st.markdown("</div></div>", unsafe_allow_html=True)


# 🎧 AUDIO PLAYER
if st.session_state.voice_path:
    with open(st.session_state.voice_path, "rb") as f:
        st.audio(f.read(), format="audio/mp3")