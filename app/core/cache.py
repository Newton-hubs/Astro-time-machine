"""
Rate limiting (sliding window) and response caching via Redis.
"""
import hashlib
import json
import time
from typing import Any, Optional

import structlog

from app.core.config import settings
from app.db.redis_client import redis_client

logger = structlog.get_logger(__name__)


async def check_rate_limit(client_ip: str) -> tuple[bool, int]:
    """
    Sliding-window rate limiter.
    Returns (is_allowed, remaining_requests).
    """
    key = f"rate_limit:{client_ip}"
    now = time.time()
    window_start = now - settings.RATE_LIMIT_WINDOW_SECONDS

    pipe = redis_client.client.pipeline()
    pipe.zremrangebyscore(key, 0, window_start)          # remove old entries
    pipe.zadd(key, {str(now): now})                       # add current request
    pipe.zcard(key)                                       # count in window
    pipe.expire(key, settings.RATE_LIMIT_WINDOW_SECONDS)
    results = await pipe.execute()

    count = results[2]
    allowed = count <= settings.RATE_LIMIT_REQUESTS
    remaining = max(0, settings.RATE_LIMIT_REQUESTS - count)
    return allowed, remaining


def cache_key(*args, **kwargs) -> str:
    """Generate a deterministic cache key from arguments."""
    raw = json.dumps({"args": args, "kwargs": kwargs}, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode()).hexdigest()


async def get_cached(key: str) -> Optional[Any]:
    data = await redis_client.client.get(f"cache:{key}")
    if data:
        logger.debug("cache_hit", key=key)
        return json.loads(data)
    return None


async def set_cached(key: str, value: Any, ttl: int = settings.CACHE_TTL_SECONDS) -> None:
    await redis_client.client.setex(
        f"cache:{key}", ttl, json.dumps(value, default=str)
    )
    logger.debug("cache_set", key=key, ttl=ttl)
