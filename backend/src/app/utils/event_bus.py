from __future__ import annotations

import json
from datetime import datetime
from uuid import uuid4

from app.core.logging import get_logger
from app.services.redis_service import RedisService

logger = get_logger(__name__)


class EventBus:
    """
    Lightweight asynchronous event publisher.
    Publishes events to Redis Pub/Sub channels and logs them.
    """

    @staticmethod
    async def publish(event_type: str, data: dict) -> None:
        event = {
            "event_id": str(uuid4()),
            "event_type": event_type,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "data": data,
        }
        event_str = json.dumps(event)
        logger.info(f"Publishing event '{event_type}': {event_str}")

        try:
            client = RedisService.get_client()
            await client.publish(event_type, event_str)
            await client.close()
        except Exception as e:
            logger.error(f"Failed to publish event to Redis: {e}")
