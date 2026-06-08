from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.core.config import Settings
from app.main import app
from app.services.database_service import DatabaseService
from app.services.qdrant_service import QdrantService
from app.services.redis_service import RedisService


# 1. Settings validation tests
def test_settings_validation_missing_keys():
    # Required keys missing
    with pytest.raises(ValidationError):
        Settings(google_api_key="", tavily_api_key="")


def test_settings_validation_invalid_google_key():
    # Key does not match pattern/length
    with pytest.raises(ValidationError):
        Settings(google_api_key="short", tavily_api_key="tvly-dev-test")


def test_settings_valid():
    settings = Settings(
        google_api_key="DUMMY_GOOGLE_API_KEY_FOR_TESTS",
        tavily_api_key="DUMMY_TAVILY_API_KEY_FOR_TESTS",
        database_url="postgresql+psycopg2://postgres:postgres@localhost:5432/careerpilot",
    )
    assert settings.app_name == "CareerPilot"
    assert (
        settings.async_database_url
        == "postgresql+asyncpg://postgres:postgres@localhost:5432/careerpilot"
    )



# 2. DatabaseService health check tests
@pytest.mark.asyncio
@patch("app.services.database_service.AsyncSessionLocal")
async def test_database_service_health_healthy(mock_session_maker):
    mock_session = AsyncMock()
    mock_session_maker.return_value.__aenter__.return_value = mock_session

    is_connected, latency = await DatabaseService.check_health()
    assert is_connected is True
    assert latency >= 0.0
    mock_session.execute.assert_called_once()


@pytest.mark.asyncio
@patch("app.services.database_service.AsyncSessionLocal")
async def test_database_service_health_unhealthy(mock_session_maker):
    mock_session = AsyncMock()
    mock_session.execute.side_effect = Exception("Connection error")
    mock_session_maker.return_value.__aenter__.return_value = mock_session

    is_connected, latency = await DatabaseService.check_health()
    assert is_connected is False
    assert latency == 0.0


# 3. RedisService health check tests
@pytest.mark.asyncio
@patch("app.services.redis_service.from_url")
async def test_redis_service_health_healthy(mock_from_url):
    mock_client = AsyncMock()
    mock_from_url.return_value = mock_client

    is_connected, latency = await RedisService.check_health()
    assert is_connected is True
    assert latency >= 0.0
    mock_client.ping.assert_called_once()
    mock_client.close.assert_called_once()


@pytest.mark.asyncio
@patch("app.services.redis_service.from_url")
async def test_redis_service_health_unhealthy(mock_from_url):
    mock_from_url.side_effect = Exception("Redis unreachable")

    is_connected, latency = await RedisService.check_health()
    assert is_connected is False
    assert latency == 0.0


# 4. QdrantService health check tests
@pytest.mark.asyncio
@patch("httpx.AsyncClient.get")
async def test_qdrant_service_health_healthy(mock_get):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_get.return_value = mock_response

    is_connected, latency = await QdrantService.check_health()
    assert is_connected is True
    assert latency >= 0.0


@pytest.mark.asyncio
@patch("httpx.AsyncClient.get")
async def test_qdrant_service_health_unhealthy(mock_get):
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_get.return_value = mock_response

    is_connected, latency = await QdrantService.check_health()
    assert is_connected is False
    assert latency == 0.0


# 5. Integration health check endpoint tests
client = TestClient(app)


@patch(
    "app.services.database_service.DatabaseService.check_health",
    new_callable=AsyncMock,
)
@patch("app.services.redis_service.RedisService.check_health", new_callable=AsyncMock)
@patch("app.services.qdrant_service.QdrantService.check_health", new_callable=AsyncMock)
def test_api_health_endpoint_healthy(mock_qdrant, mock_redis, mock_db):
    mock_db.return_value = (True, 1.2)
    mock_redis.return_value = (True, 0.8)
    mock_qdrant.return_value = (True, 2.5)

    response = client.get("/api/v2/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["version"] == "2.0.0"
    assert data["services"]["database"]["status"] == "connected"
    assert data["services"]["database"]["latency_ms"] == 1.2
    assert data["services"]["redis"]["status"] == "connected"
    assert data["services"]["redis"]["latency_ms"] == 0.8
    assert data["services"]["qdrant"]["status"] == "connected"
    assert data["services"]["qdrant"]["latency_ms"] == 2.5


@patch(
    "app.services.database_service.DatabaseService.check_health",
    new_callable=AsyncMock,
)
@patch("app.services.redis_service.RedisService.check_health", new_callable=AsyncMock)
@patch("app.services.qdrant_service.QdrantService.check_health", new_callable=AsyncMock)
def test_api_health_endpoint_degraded(mock_qdrant, mock_redis, mock_db):
    mock_db.return_value = (False, 0.0)  # Database disconnected
    mock_redis.return_value = (True, 0.8)
    mock_qdrant.return_value = (True, 2.5)

    response = client.get("/api/v2/health")
    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "unhealthy"
    assert data["services"]["database"]["status"] == "disconnected"
    assert data["services"]["database"]["latency_ms"] is None
    assert data["services"]["database"]["error"] is not None
    assert data["services"]["redis"]["status"] == "connected"
    assert data["services"]["qdrant"]["status"] == "connected"
