# 🌌 Astro Time Machine

Astro Time Machine is an interactive astronomy experience that lets users
travel through time and see how the sky looked — or will look —
from any location on Earth.

The app visualizes the night sky using real astronomical data, computes
Moon phase & visibility, estimates cloud conditions, detects visible planets,
and generates an AI-powered narration describing the sky.

It also supports optional AI **voice narration**, turning the sky story
into an immersive audio experience.

---

## ✨ Features

### 🛰 Real Astronomical Calculations
- Accurate Moon phase & illumination
- Moon altitude, azimuth & horizon visibility
- Separation-based astronomical phase model
- Planet visibility detection
- Time & location based sky computation

---

### 🌥 Weather Awareness
- Fetches cloud cover for the observation site
- Detects whether the Moon is **cloud-obscured**
- Adjusts AI narration accordingly

---

### 🌌 Sky Visualization
- Generates circular night-sky projection
- Highlights Moon & visible planets
- Supports different Moon phase brightness
- Horizon awareness (below / above)

---

### 🤖 AI Sky Interpretation
The app generates a natural-language explanation including:

- How the night sky looks
- Moon phase & visibility condition
- Brightness & position in the sky
- Which planets are visible
- Whether clouds affect viewing
- Description adapted to time & location

Optional:
- 🎧 AI **voice narration** of the explanation

---

## 🧠 Tech Stack

- **Python**
- **Streamlit** — UI & app framework
- **Skyfield** — astronomical calculations
- **Pillow / Matplotlib** — sky visualization
- **Geocoder** — location lookup
- **Weather API (cloud cover)** — observational realism
- **AI text interpretation module**
- **AI text-to-speech (voice narration)**

---

## 🚀 Running the Project

### 1️⃣ Install dependencies

```bash
pip install -r requirements.txt
