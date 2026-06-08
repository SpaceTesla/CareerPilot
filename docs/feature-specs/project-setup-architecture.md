# Feature Specification: Project Setup & Architecture

## 1. Purpose
This feature establishes the monorepo structure, developer environment, and boilerplate code foundation for CareerPilot. It configures the FastAPI skeleton, PostgreSQL connection layer (using SQLAlchemy and asyncpg), Alembic migrations, Docker Compose developer setup, JSON logging, and foundational package layout. This is the root package initialization that supports all epics, ensuring a uniform path for API versioning (`/api/v2`) and health checks.

For more high-level design details, see [careerpilot_v2.md](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/careerpilot_v2.md) and the project backlog in [backlog.md](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/backlog.md).

## 2. User Value
While invisible to end-users, this foundation accelerates developer velocity and guarantees the stability, performance, and scalability of the platform. A structured monorepo and Docker setup ensure that the development, staging, and production environments are identical, reducing "works on my machine" bugs. This is the bedrock on which the Career Intelligence Compounding Loop is built.

## 3. Requirements
- **Monorepo Layout**: Configure folder paths for backend services (`src/`), database migrations (`migrations/`), deployment configs (`docker/`), and shared libraries.
- **FastAPI Skeleton**: Instantiate the main FastAPI app with standardized middlewares (CORS, trusted hosts, request ID generation).
- **PostgreSQL Connection Layer**: Set up SQLAlchemy (v2.0+) using asyncpg for async database operations. Configure connection pooling (pool size = 20, max overflow = 10, pool pre-ping = True).
- **Alembic Migration Infrastructure**: Initialize Alembic, configure `env.py` to auto-detect models, and support running migrations inside the Docker container.
- **Docker Development Environment**: Set up `Dockerfile.dev` and `docker-compose.yml` to spin up PostgreSQL, Redis, Qdrant, and the FastAPI app in watch mode.
- **Environment Management**: Implement Pydantic `BaseSettings` for strictly validated configurations with environment variable overrides.
- **API Versioning**: Configure route prefixing for version 2 (`/api/v2`).
- **Structured Logging**: Configure the standard library logging to use JSON formatting for all application-level logs.
- **Health Check Endpoint**: Implement a liveness and readiness check that ping PostgreSQL, Redis, and Qdrant.

## 4. Database Changes
No functional database tables are created in this setup. However, the system reserves the standard Alembic migration version table:
- **`alembic_version`**:
  - `version_num`: `VARCHAR(32)` (Primary Key, Not Null) - Stores the current migration version hash.

## 5. API Endpoints
### `GET /api/v2/health`
Checks the health of the application and all critical backing services (Database, Redis, Qdrant).

**Request Headers**: None required.
**Query Parameters**: None.
**Response Body (200 OK)**:
```json
{
  "status": "healthy",
  "version": "2.0.0",
  "timestamp": "2026-06-09T02:04:18Z",
  "services": {
    "database": {
      "status": "connected",
      "latency_ms": 1.2
    },
    "redis": {
      "status": "connected",
      "latency_ms": 0.8
    },
    "qdrant": {
      "status": "connected",
      "latency_ms": 2.5
    }
  }
}
```

**Response Body (503 Service Unavailable)**:
```json
{
  "status": "unhealthy",
  "version": "2.0.0",
  "timestamp": "2026-06-09T02:04:18Z",
  "services": {
    "database": {
      "status": "disconnected",
      "error": "Connection timeout"
    },
    "redis": {
      "status": "connected",
      "latency_ms": 0.8
    },
    "qdrant": {
      "status": "connected",
      "latency_ms": 2.5
    }
  }
}
```

## 6. Domain Models
### Pydantic Schemas

#### `ServiceHealthDetail`
```python
from pydantic import BaseModel
from typing import Optional

class ServiceHealthDetail(BaseModel):
    status: str  # "connected", "disconnected"
    latency_ms: Optional[float] = None
    error: Optional[str] = None
```

#### `HealthResponse`
```python
from pydantic import BaseModel
from datetime import datetime
from typing import Dict

class HealthResponse(BaseModel):
    status: str  # "healthy", "unhealthy"
    version: str
    timestamp: datetime
    services: Dict[str, ServiceHealthDetail]
```

## 7. Services
### `DatabaseService`
- **Responsibilities**: Manages the life cycle of the async database engine and sessions.
- **Methods**:
  - `get_session() -> AsyncGenerator[AsyncSession, None]`: Dependency injection provider yielding an async SQLAlchemy session.
  - `check_health() -> tuple[bool, float]`: Executes a raw query `SELECT 1` to measure database connectivity and latency in milliseconds.

### `RedisService`
- **Responsibilities**: Connects to the Redis cache cluster.
- **Methods**:
  - `check_health() -> tuple[bool, float]`: Pings the Redis database and returns latency.

### `QdrantService`
- **Responsibilities**: Connects to the Qdrant vector store.
- **Methods**:
  - `check_health() -> tuple[bool, float]`: Pings the Qdrant REST API health endpoint and returns latency.

## 8. Events
No events are emitted or consumed by this architectural foundation.

## 9. Background Jobs
No background jobs are scheduled in this initial setup.

## 10. Acceptance Criteria
- **Scenario: FastAPI startup**
  - **Given** the environment variables are correctly configured,
  - **When** executing `docker compose up`,
  - **Then** the FastAPI application boots up without errors, binds to port 8000, and is ready to accept requests.
- **Scenario: Healthy API Healthcheck**
  - **Given** Postgres, Redis, and Qdrant are fully running,
  - **When** calling `GET /api/v2/health`,
  - **Then** return HTTP status `200 OK` with all services marked as "connected".
- **Scenario: Degraded Database Healthcheck**
  - **Given** Postgres is unreachable,
  - **When** calling `GET /api/v2/health`,
  - **Then** return HTTP status `503 Service Unavailable` with `database` marked as "disconnected".

## 11. Edge Cases
- **Database Connection Latency / Retry during Startup**: In Docker Compose, the API container may start before Postgres is ready. The database connection pooling service must retry connection attempts up to 5 times (every 2 seconds) before failing.
- **Missing Required Environment Variables**: If required variables (e.g., `DATABASE_URL`) are omitted, Pydantic's `BaseSettings` validation must raise an exception immediately, terminating startup to prevent running in a broken state.
- **Connection Pool Exhaustion**: If connection pool requests time out, the system must log detailed error summaries (including active connections count) and return clean HTTP 500 errors to clients rather than hanging indefinitely.

## 12. Test Requirements
- **Unit Tests**:
  - Assert that `Settings` fails validation if required variables are missing.
  - Mock the database connector to verify connection pool creation parameters.
- **Integration Tests**:
  - Spin up test containers and assert that `GET /api/v2/health` returns status `200 OK` with valid json keys.
  - Simulate database network loss and assert that the health endpoint returns status `503 Service Unavailable` with details.

## 13. Dependencies
This is the root feature of the platform. It has no dependencies. All other features depend on this setup.
See details in [DEPENDENCY_GRAPH.md](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/DEPENDENCY_GRAPH.md).
