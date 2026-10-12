from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.db.redis_client import RedisClient


@pytest.mark.asyncio
async def test_connect_success():
    client = RedisClient()
    mock_pool = MagicMock()
    mock_redis = MagicMock()
    mock_redis.ping = AsyncMock(return_value=True)

    with patch("app.db.redis_client.ConnectionPool.from_url", return_value=mock_pool), patch(
        "app.db.redis_client.Redis", return_value=mock_redis
    ):
        await client.connect()

    assert client._pool is mock_pool
    assert client.client is mock_redis
    mock_redis.ping.assert_awaited_once()


@pytest.mark.asyncio
async def test_connect_failure_sets_client_none():
    client = RedisClient()
    mock_redis = MagicMock()
    mock_redis.ping = AsyncMock(side_effect=RuntimeError("boom"))

    with patch("app.db.redis_client.ConnectionPool.from_url", return_value=MagicMock()), patch(
        "app.db.redis_client.Redis", return_value=mock_redis
    ):
        await client.connect()

    assert client.client is None


@pytest.mark.asyncio
async def test_disconnect_calls_aclose():
    client = RedisClient()
    mock_redis = MagicMock()
    mock_redis.aclose = AsyncMock()
    client.client = mock_redis

    await client.disconnect()

    mock_redis.aclose.assert_awaited_once()


@pytest.mark.asyncio
async def test_health_check_true_and_false():
    client = RedisClient()
    mock_redis = MagicMock()
    mock_redis.ping = AsyncMock(return_value=True)
    client.client = mock_redis

    assert await client.health_check() is True

    mock_redis.ping = AsyncMock(side_effect=RuntimeError("down"))
    assert await client.health_check() is False
