"""
Application configuration — loaded from environment variables / .env file.
"""
from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # App
    APP_ENV: str = "development"
    DEBUG: bool = False
    SECRET_KEY: str = "change-me-in-production"
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8000"]

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    CACHE_TTL_SECONDS: int = 3600          # 1 hour for astronomy data
    RATE_LIMIT_REQUESTS: int = 60
    RATE_LIMIT_WINDOW_SECONDS: int = 60

    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    # External APIs
    OPENWEATHER_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""          # used for AI sky narration

    # Astronomy
    EPHEMERIS_FILE: str = "de421.bsp"    # JPL ephemeris
    DEFAULT_TIMEZONE: str = "UTC"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
