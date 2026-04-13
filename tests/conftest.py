"""
Shared pytest configuration and fixtures.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture(autouse=True)
def mock_redis_lifespan():
    """
    Prevent real Redis connections during tests.
    Patches connect/disconnect so the FastAPI lifespan doesn't fail.
    """
    with patch("app.db.redis_client.redis_client.connect", new_callable=AsyncMock) as mock_connect, \
         patch("app.db.redis_client.redis_client.disconnect", new_callable=AsyncMock) as mock_disconnect:
        # Provide a minimal async Redis mock
        mock_redis = MagicMock()
        mock_redis.ping = AsyncMock(return_value=True)
        mock_redis.get = AsyncMock(return_value=None)
        mock_redis.setex = AsyncMock(return_value=True)
        mock_redis.zremrangebyscore = AsyncMock()
        mock_redis.zadd = AsyncMock()
        mock_redis.zcard = AsyncMock(return_value=0)
        mock_redis.expire = AsyncMock()
        mock_redis.pipeline = MagicMock(return_value=MagicMock(
            execute=AsyncMock(return_value=[None, None, 1, None])
        ))

        import app.db.redis_client as rc
        rc.redis_client.client = mock_redis
        yield
