
"""
Rate limiting (sliding window) and response caching via Redis.
"""
import hashlib
import json
import time
from typing import Any, Optional

import structlog
from redis.exceptions import RedisError

from app.core.config import settings
from app.db.redis_client import redis_client

logger = structlog.get_logger(__name__)


async def check_rate_limit(client_ip: str) -> tuple[bool, int]:
    """
    Sliding-window rate limiter.
    Returns (is_allowed, remaining_requests).

    WARNING: If Redis is unavailable, requests are allowed without
    rate limiting. Restore Redis for production use.
    """
    client = redis_client.client

    if client is None:
        logger.warning("rate_limit_skipped_redis_unavailable")
        return True, settings.RATE_LIMIT_REQUESTS

    key = f"rate_limit:{client_ip}"
    now = time.time()
    window_start = now - settings.RATE_LIMIT_WINDOW_SECONDS

    try:
        pipe = client.pipeline()
        pipe.zremrangebyscore(key, 0, window_start)
        pipe.zadd(key, {str(now): now})
        pipe.zcard(key)
        pipe.expire(key, settings.RATE_LIMIT_WINDOW_SECONDS)

        results = await pipe.execute()

        count = results[2]
        allowed = count <= settings.RATE_LIMIT_REQUESTS
        remaining = max(0, settings.RATE_LIMIT_REQUESTS - count)

        return allowed, remaining

    except RedisError:
        logger.exception("rate_limit_redis_error")
        # Fail open: the API works, but rate limiting is bypassed.
        return True, settings.RATE_LIMIT_REQUESTS


def cache_key(*args, **kwargs) -> str:
    """Generate a deterministic cache key from arguments."""
    raw = json.dumps(
        {"args": args, "kwargs": kwargs},
        sort_keys=True,
        default=str,
    )
    return hashlib.sha256(raw.encode()).hexdigest()


async def get_cached(key: str) -> Optional[Any]:
    """Get cached data; return None if Redis is unavailable."""
    client = redis_client.client

    if client is None:
        return None

    try:
        data = await client.get(f"cache:{key}")

        if data:
            logger.debug("cache_hit", key=key)
            return json.loads(data)

    except (RedisError, json.JSONDecodeError):
        logger.exception("cache_read_failed", key=key)

    return None


async def set_cached(
    key: str,
    value: Any,
    ttl: int = settings.CACHE_TTL_SECONDS,
) -> None:
    """Cache data; skip caching if Redis is unavailable."""
    client = redis_client.client

    if client is None:
        return

    try:
        await client.setex(
            f"cache:{key}",
            ttl,
            json.dumps(value, default=str),
        )
        logger.debug("cache_set", key=key, ttl=ttl)

    except (RedisError, TypeError, ValueError):
        logger.exception("cache_write_failed", key=key)

