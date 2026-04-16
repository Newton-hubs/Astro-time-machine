import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core import cache


@pytest.mark.asyncio
async def test_check_rate_limit_allowed(monkeypatch):
    pipe = MagicMock()
    pipe.execute = AsyncMock(return_value=[0, 1, 2, 1])
    cache.redis_client.client = MagicMock(pipeline=MagicMock(return_value=pipe))
    monkeypatch.setattr(cache.settings, "RATE_LIMIT_WINDOW_SECONDS", 60)
    monkeypatch.setattr(cache.settings, "RATE_LIMIT_REQUESTS", 10)

    allowed, remaining = await cache.check_rate_limit("1.2.3.4")

    assert allowed is True
    assert remaining == 8
    pipe.zremrangebyscore.assert_called_once()
    pipe.zadd.assert_called_once()
    pipe.zcard.assert_called_once()
    pipe.expire.assert_called_once()


@pytest.mark.asyncio
async def test_check_rate_limit_blocked(monkeypatch):
    pipe = MagicMock()
    pipe.execute = AsyncMock(return_value=[0, 1, 15, 1])
    cache.redis_client.client = MagicMock(pipeline=MagicMock(return_value=pipe))
    monkeypatch.setattr(cache.settings, "RATE_LIMIT_WINDOW_SECONDS", 60)
    monkeypatch.setattr(cache.settings, "RATE_LIMIT_REQUESTS", 10)

    allowed, remaining = await cache.check_rate_limit("5.6.7.8")

    assert allowed is False
    assert remaining == 0


@pytest.mark.asyncio
async def test_get_cached_hit():
    key = "abc"
    payload = {"x": 1}
    redis = MagicMock()
    redis.get = AsyncMock(return_value=json.dumps(payload))
    cache.redis_client.client = redis

    result = await cache.get_cached(key)

    assert result == payload
    redis.get.assert_awaited_once_with("cache:abc")


@pytest.mark.asyncio
async def test_get_cached_miss():
    redis = MagicMock()
    redis.get = AsyncMock(return_value=None)
    cache.redis_client.client = redis

    result = await cache.get_cached("missing")

    assert result is None


@pytest.mark.asyncio
async def test_set_cached_uses_setex():
    redis = MagicMock()
    redis.setex = AsyncMock()
    cache.redis_client.client = redis

    await cache.set_cached("k1", {"ok": True}, ttl=120)

    redis.setex.assert_awaited_once()
    args = redis.setex.await_args.args
    assert args[0] == "cache:k1"
    assert args[1] == 120
    assert json.loads(args[2]) == {"ok": True}
