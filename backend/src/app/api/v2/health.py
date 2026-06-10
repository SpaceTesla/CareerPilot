from datetime import UTC, datetime

from fastapi import APIRouter, Response, status

from app.schemas.health import HealthResponse, ServiceHealthDetail
from app.services.database_service import DatabaseService
from app.services.qdrant_service import QdrantService
from app.services.redis_service import RedisService
from app.services.neo4j_service import Neo4jService

router = APIRouter(prefix="/health", tags=["health"])


@router.get(
    "",
    response_model=HealthResponse,
    responses={
        200: {"model": HealthResponse},
        503: {"model": HealthResponse},
    },
)
async def health_check(response: Response):
    """
    Checks the health of the application and all critical backing
    services (Database, Redis, Qdrant, Neo4j).
    """

    db_connected, db_latency = await DatabaseService.check_health()
    redis_connected, redis_latency = await RedisService.check_health()
    qdrant_connected, qdrant_latency = await QdrantService.check_health()
    neo4j_connected, neo4j_latency = await Neo4jService.check_health()

    services = {
        "database": ServiceHealthDetail(
            status="connected" if db_connected else "disconnected",
            latency_ms=db_latency if db_connected else None,
            error=None if db_connected else "Connection error",
        ),
        "redis": ServiceHealthDetail(
            status="connected" if redis_connected else "disconnected",
            latency_ms=redis_latency if redis_connected else None,
            error=None if redis_connected else "Connection error",
        ),
        "qdrant": ServiceHealthDetail(
            status="connected" if qdrant_connected else "disconnected",
            latency_ms=qdrant_latency if qdrant_connected else None,
            error=None if qdrant_connected else "Connection error",
        ),
        "neo4j": ServiceHealthDetail(
            status="connected" if neo4j_connected else "disconnected",
            latency_ms=neo4j_latency if neo4j_connected else None,
            error=None if neo4j_connected else "Connection error",
        ),
    }

    # System is healthy only if all services are connected
    is_healthy = db_connected and redis_connected and qdrant_connected and neo4j_connected
    status_str = "healthy" if is_healthy else "unhealthy"

    if not is_healthy:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return HealthResponse(
        status=status_str,
        version="2.0.0",
        timestamp=datetime.now(UTC),
        services=services,
    )
