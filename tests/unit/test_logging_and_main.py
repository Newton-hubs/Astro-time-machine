from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core import logging as logmod
from app.core.exceptions import LocationResolutionError, RateLimitExceededError
from app.main import app, lifespan, location_handler, rate_limit_handler


def test_setup_logging_development_and_noisy_loggers(monkeypatch):
    monkeypatch.setattr(logmod.settings, "DEBUG", True)
    monkeypatch.setattr(logmod.settings, "APP_ENV", "development")
    logger_instance = MagicMock()
    get_logger = MagicMock(return_value=logger_instance)

    with patch("app.core.logging.structlog.configure") as configure, patch(
        "app.core.logging.logging.getLogger", get_logger
    ):
        logmod.setup_logging()

    configure.assert_called_once()
    assert get_logger.call_count == 3
    assert logger_instance.setLevel.call_count == 3


@pytest.mark.asyncio
async def test_lifespan_connects_and_disconnects():
    with patch("app.main.redis_client.connect", new_callable=AsyncMock) as connect, patch(
        "app.main.redis_client.disconnect", new_callable=AsyncMock
    ) as disconnect:
        async with lifespan(app):
            connect.assert_awaited_once()
            disconnect.assert_not_awaited()
        disconnect.assert_awaited_once()


@pytest.mark.asyncio
async def test_main_exception_handlers():
    r1 = await rate_limit_handler(None, RateLimitExceededError())
    assert r1.status_code == 429
    assert b"Rate limit exceeded" in r1.body

    r2 = await location_handler(None, LocationResolutionError("Atlantis"))
    assert r2.status_code == 404
    assert b"Could not resolve location" in r2.body
