# 🌌 Astro Time Machine

A production-grade REST API that lets you travel through time and explore the night sky
from any location on Earth. Built as a showcase of backend engineering best practices.

[![CI](https://github.com/Newton-hubs/Astro-time-machine/actions/workflows/ci.yml/badge.svg)](https://github.com/Newton-hubs/Astro-time-machine/actions)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-green.svg)](https://fastapi.tiangolo.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## ✨ Features

- **Real astronomical calculations** — Moon phase, illumination, altitude/azimuth, planet visibility via Skyfield + JPL DE421 ephemeris
- **Weather integration** — Live cloud cover from OpenWeatherMap with graceful degradation
- **Sky visualization** — Server-rendered circular sky projection (PNG) as base64
- **AI narration** — Natural language sky descriptions via Claude (Anthropic); template fallback when unavailable
- **Async voice generation** — TTS audio via Celery + gTTS, polled via job ID
- **Redis caching** — 1-hour cache on sky snapshots; sliding-window rate limiter
- **Circuit breaker** — Weather service failures don't cascade to the main API
- **Structured logging** — JSON logs via structlog; request-scoped context
- **Docker-first** — Multi-stage Dockerfile + Docker Compose with Redis, Celery worker, and Flower

---

## 🏗 Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    FastAPI Application                   │
│                                                          │
│  POST /api/v1/astronomy/sky                              │
│    ├── Rate Limiter (Redis sliding window)               │
│    ├── Cache check (Redis)                               │
│    ├── AstronomyService (Skyfield / DE421)               │
│    ├── WeatherService (OpenWeatherMap + circuit breaker) │
│    ├── VisualizationService (Matplotlib → base64 PNG)    │
│    └── Cache write → Response                            │
│                                                          │
│  POST /api/v1/narration/generate                         │
│    ├── NarrationService (Claude API / template fallback) │
│    └── Celery task dispatch → job_id (if voice=true)     │
│                                                          │
│  GET  /api/v1/narration/voice/{job_id}   (job polling)   │
└────────────────────┬────────────────────────────────────┘
                     │
          ┌──────────▼──────────┐
          │    Redis             │
          │  • Cache store       │
          │  • Rate limit store  │
          │  • Celery broker     │
          └──────────┬──────────┘
                     │
          ┌──────────▼──────────┐
          │  Celery Worker       │
          │  • TTS generation    │
          │  • gTTS → MP3        │
          └─────────────────────┘
```

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Docker & Docker Compose
- `de421.bsp` (JPL ephemeris, ~17 MB) — download with:
  ```bash
  python -c "from skyfield.api import Loader; Loader('.').open('de421.bsp')"
  ```

### Run with Docker Compose

```bash
cp .env.example .env
# Edit .env — add your OPENWEATHER_API_KEY and ANTHROPIC_API_KEY

docker compose up --build
```

API docs: http://localhost:8000/docs  
Celery dashboard: http://localhost:5555

### Run locally

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env  # edit as needed

# Start Redis
docker run -d -p 6379:6379 redis:7-alpine

# Start API
uvicorn app.main:app --reload --port 8000

# Start Celery worker (separate terminal)
celery -A app.tasks.worker celery_app worker --loglevel=info
```

---

## 📡 API Reference

### `POST /api/v1/astronomy/sky`

Compute a complete sky snapshot.

**Request:**
```json
{
  "latitude": 12.9716,
  "longitude": 77.5946,
  "datetime_utc": "2024-07-04T21:00:00",
  "location_name": "Bengaluru, India"
}
```

**Response:**
```json
{
  "snapshot_id": "uuid-...",
  "moon": {
    "phase_name": "Waxing Gibbous",
    "illumination_pct": 72.3,
    "altitude_deg": 42.1,
    "is_above_horizon": true,
    "is_cloud_obscured": false
  },
  "planets": [
    { "name": "Mars", "altitude_deg": 25.0, "is_visible": true },
    ...
  ],
  "weather": { "cloud_cover_pct": 20.0, "description": "clear sky" },
  "visualization": { "image_base64": "...", "width_px": 600, "height_px": 600 }
}
```

### `POST /api/v1/astronomy/location/resolve`

Resolve a place name to coordinates.

```json
{ "location_name": "Mysuru, Karnataka" }
```

### `POST /api/v1/narration/generate`

Generate an AI sky narration for a snapshot.

```json
{ "sky_snapshot_id": "uuid-...", "voice": true }
```

### `GET /api/v1/narration/voice/{job_id}`

Poll TTS voice job status.

### `GET /api/v1/health`

Liveness/readiness probe.

---

## 🧪 Testing

```bash
pytest                          # all tests
pytest tests/unit/              # unit tests only
pytest tests/integration/       # integration tests only
pytest --cov=app --cov-report=html  # with coverage report
```

Test coverage target: **≥ 75%**

---

## 🛠 Backend Engineering Highlights

| Concern | Approach |
|---|---|
| Async I/O | FastAPI + async/await throughout |
| Caching | Redis with SHA-256 cache keys, configurable TTL |
| Rate limiting | Sliding-window counter in Redis (per IP) |
| Resilience | Circuit breaker on weather service |
| Task queue | Celery + Redis broker for async TTS jobs |
| Validation | Pydantic v2 with field-level constraints |
| Config | `pydantic-settings` + `.env` file |
| Logging | Structured JSON logs via structlog |
| Containerisation | Multi-stage Docker build; non-root user |
| CI/CD | GitHub Actions — lint, type-check, test, docker build |

---

## 📁 Project Structure

```
astro-time-machine/
├── app/
│   ├── main.py                   # FastAPI app + lifespan
│   ├── api/v1/endpoints/
│   │   ├── astronomy.py          # Sky + location endpoints
│   │   ├── narration.py          # AI narration + voice endpoints
│   │   └── health.py             # Health check
│   ├── core/
│   │   ├── config.py             # Settings (pydantic-settings)
│   │   ├── cache.py              # Redis cache + rate limiter
│   │   ├── exceptions.py         # Custom exceptions + handlers
│   │   └── logging.py            # structlog setup
│   ├── db/
│   │   └── redis_client.py       # Async Redis client (connection pool)
│   ├── schemas/
│   │   └── astronomy.py          # Pydantic v2 request/response models
│   ├── services/
│   │   ├── astronomy_service.py  # Skyfield computations
│   │   ├── weather_service.py    # OpenWeatherMap + circuit breaker
│   │   ├── visualization_service.py  # Matplotlib sky renderer
│   │   ├── narration_service.py  # Claude AI + template fallback
│   │   └── geocoding_service.py  # OSM Nominatim geocoding
│   └── tasks/
│       └── worker.py             # Celery tasks (TTS voice generation)
├── tests/
│   ├── conftest.py               # Shared fixtures
│   ├── unit/
│   │   ├── test_astronomy_service.py
│   │   ├── test_weather_service.py
│   │   └── test_schemas.py
│   └── integration/
│       └── test_api.py
├── .github/workflows/ci.yml      # GitHub Actions CI pipeline
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── pytest.ini
└── .env.example
```

---

## 📜 License

MIT
