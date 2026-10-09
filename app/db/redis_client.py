```python
"""
Async Redis client with connection pooling.
"""
import structlog
from redis.asyncio import ConnectionPool, Redis

from app.core.config import settings

logger = structlog.get_logger(__name__)


class RedisClient:
    def __init__(self):
        self.client: Redis | None = None
        self._pool: ConnectionPool | None = None

    async def connect(self) -> None:
        try:
            self._pool = ConnectionPool.from_url(
                settings.REDIS_URL,
                max_connections=20,
                decode_responses=True,
            )

            client = Redis(connection_pool=self._pool)
            await client.ping()

            self.client = client
            logger.info("redis_connected")

        except Exception:
            logger.exception("redis_connection_failed")
            self.client = None

            if self._pool is not None:
                await self._pool.aclose()
                self._pool = None

    async def disconnect(self) -> None:
        if self.client is not None:
            await self.client.aclose()
            self.client = None
            self._pool = None
            logger.info("redis_disconnected")

    async def health_check(self) -> bool:
        if self.client is None:
            return False

        try:
            return bool(await self.client.ping())
        except Exception:
            logger.exception("redis_health_check_failed")
            return False


redis_client = RedisClient()
