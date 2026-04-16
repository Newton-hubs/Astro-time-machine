from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.exceptions import (
    AstroBaseException,
    EphemerisError,
    LocationResolutionError,
    NarrationError,
    RateLimitExceededError,
    WeatherServiceError,
    register_exception_handlers,
)


def test_exception_classes_defaults():
    base = AstroBaseException("oops", status_code=418)
    assert str(base) == "oops"
    assert base.status_code == 418
    assert "Could not resolve location" in str(LocationResolutionError("moon"))
    assert EphemerisError().status_code == 500
    assert WeatherServiceError().status_code == 503
    assert NarrationError().status_code == 503
    assert RateLimitExceededError().status_code == 429


def test_registered_exception_handlers():
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/astro")
    async def astro():
        raise NarrationError("broken")

    @app.get("/boom")
    async def boom():
        raise RuntimeError("unexpected")

    client = TestClient(app, raise_server_exceptions=False)

    astro_resp = client.get("/astro")
    assert astro_resp.status_code == 503
    assert astro_resp.json() == {"error": "broken", "type": "NarrationError"}

    boom_resp = client.get("/boom")
    assert boom_resp.status_code == 500
    assert boom_resp.json()["type"] == "InternalServerError"
