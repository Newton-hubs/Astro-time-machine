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
        self._pool = ConnectionPool.from_url(
            settings.REDIS_URL,
            max_connections=20,
            decode_responses=True,
        )
        self.client = Redis(connection_pool=self._pool)
        await self.client.ping()
        logger.info("redis_connected", url=settings.REDIS_URL)

    async def disconnect(self) -> None:
        if self.client:
            await self.client.aclose()
            logger.info("redis_disconnected")

    async def health_check(self) -> bool:
        try:
            return await self.client.ping()
        except Exception:
            return False


redis_client = RedisClient()
