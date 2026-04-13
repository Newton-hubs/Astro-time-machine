"""
Pydantic v2 schemas for all API request/response models.
"""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


# ── Requests ────────────────────────────────────────────────────────────────

class SkyQueryRequest(BaseModel):
    """Request body for sky computation."""
    latitude: float = Field(..., ge=-90, le=90, description="Observer latitude")
    longitude: float = Field(..., ge=-180, le=180, description="Observer longitude")
    datetime_utc: datetime = Field(..., description="Observation datetime in UTC (ISO 8601)")
    location_name: Optional[str] = Field(None, max_length=200, description="Human-readable place name")

    @field_validator("datetime_utc")
    @classmethod
    def validate_datetime_range(cls, v: datetime) -> datetime:
        min_dt = datetime(1800, 1, 1)
        max_dt = datetime(2100, 12, 31)
        if not (min_dt <= v.replace(tzinfo=None) <= max_dt):
            raise ValueError("Datetime must be between 1800 and 2100")
        return v

    model_config = {"json_schema_extra": {
        "example": {
            "latitude": 12.9716,
            "longitude": 77.5946,
            "datetime_utc": "2024-07-04T21:00:00",
            "location_name": "Bengaluru, India",
        }
    }}


class LocationQueryRequest(BaseModel):
    """Resolve a place name to coordinates."""
    location_name: str = Field(..., min_length=2, max_length=200)


class NarrationRequest(BaseModel):
    """Request AI narration for a sky snapshot."""
    sky_snapshot_id: str = Field(..., description="ID returned from /sky endpoint")
    voice: bool = Field(False, description="Also generate TTS audio (async job)")


# ── Sub-models ───────────────────────────────────────────────────────────────

class MoonData(BaseModel):
    phase_name: str
    illumination_pct: float = Field(..., ge=0, le=100)
    altitude_deg: float
    azimuth_deg: float
    is_above_horizon: bool
    is_cloud_obscured: bool
    age_days: float


class PlanetData(BaseModel):
    name: str
    altitude_deg: float
    azimuth_deg: float
    is_visible: bool
    magnitude: Optional[float] = None


class WeatherData(BaseModel):
    cloud_cover_pct: float = Field(..., ge=0, le=100)
    description: str
    source: str = "OpenWeatherMap"


class SkyVisualization(BaseModel):
    image_base64: str = Field(..., description="PNG sky map encoded as base64")
    width_px: int
    height_px: int


# ── Responses ────────────────────────────────────────────────────────────────

class SkySnapshotResponse(BaseModel):
    snapshot_id: str
    latitude: float
    longitude: float
    location_name: Optional[str]
    datetime_utc: datetime
    moon: MoonData
    planets: List[PlanetData]
    weather: Optional[WeatherData]
    visualization: SkyVisualization
    computed_at: datetime


class NarrationResponse(BaseModel):
    snapshot_id: str
    narration_text: str
    voice_job_id: Optional[str] = None   # populated if voice=True
    model_used: str


class VoiceJobResponse(BaseModel):
    job_id: str
    status: str                           # pending | processing | done | failed
    audio_url: Optional[str] = None


class LocationResponse(BaseModel):
    location_name: str
    latitude: float
    longitude: float
    country: Optional[str]
    timezone: Optional[str]


class HealthResponse(BaseModel):
    status: str
    redis: bool
    version: str = "1.0.0"
