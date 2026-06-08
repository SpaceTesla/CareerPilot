import time

import httpx

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class QdrantService:
    """
    Connects to the Qdrant vector store.
    """

    @staticmethod
    async def check_health() -> tuple[bool, float]:
        """
        Pings the Qdrant REST API health endpoint and
        returns latency in milliseconds.
        Returns:
            A tuple of (is_connected, latency_ms)
        """
        start_time = time.perf_counter()
        try:
            url = f"{settings.qdrant_url.rstrip('/')}/health"
            async with httpx.AsyncClient(timeout=2.0) as client:
                response = await client.get(url)
                if response.status_code == 200:
                    latency_ms = (time.perf_counter() - start_time) * 1000
                    return True, round(latency_ms, 2)
                else:
                    logger.error(
                        "Qdrant health check returned status code: "
                        f"{response.status_code}"
                    )
                    return False, 0.0

        except Exception as e:
            logger.error(f"Qdrant health check failed: {e}")
            return False, 0.0
