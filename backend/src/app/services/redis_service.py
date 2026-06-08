import time

from redis.asyncio import from_url

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class RedisService:
    """
    Connects to the Redis cache cluster.
    """

    @staticmethod
    async def check_health() -> tuple[bool, float]:
        """
        Pings the Redis database and returns latency in milliseconds.
        Returns:
            A tuple of (is_connected, latency_ms)
        """
        start_time = time.perf_counter()
        try:
            # Connect and send a ping command
            client = from_url(settings.redis_url, socket_timeout=2.0)
            await client.ping()
            await client.close()
            latency_ms = (time.perf_counter() - start_time) * 1000
            return True, round(latency_ms, 2)
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return False, 0.0
