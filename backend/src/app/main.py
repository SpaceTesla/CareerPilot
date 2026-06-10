import os
import sys
import asyncio
from contextlib import asynccontextmanager

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

import uvicorn
from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from app.api.v1.agent import router as agent_router
from app.api.v1.analysis import router as analysis_router
from app.api.v1.applications import router as applications_router
from app.api.v1.chat import router as chat_router
from app.api.v1.courses import router as courses_router
from app.api.v1.feedback import router as feedback_router
from app.api.v1.index import router as index_router
from app.api.v1.interview import router as interview_router
from app.api.v1.jobs import router as jobs_router
from app.api.v1.progress import router as progress_router
from app.api.v1.resume import router as resume_router
from app.api.v1.sessions import router as sessions_router
from app.api.v2 import router as api_v2_router
from app.core.config import settings
from app.core.logging import get_logger, setup_logging
from app.infrastructure.database.connection import engine
from app.infrastructure.database.init_db import init_db
from app.middleware.request_id import RequestIDMiddleware
from app.services.observability_telemetry_service import ObservabilityTelemetryService
from app.services.metrics_collection_service import MetricsCollectionService
from app.middleware.metrics import MetricsMiddleware
from app.middleware.rate_limit import RateLimitMiddleware

# Configure logging
setup_logging(level="INFO", include_file_handler=True, log_file="logs/app.log")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # At startup
    logger = get_logger(__name__)
    logger.info(f"Starting {app.title} v{settings.app_version}")
    logger.info(f"Using model: {settings.model_name}")
    
    # Initialize OpenTelemetry
    collector_url = os.getenv("OTEL_COLLECTOR_URL", "http://localhost:4318/v1/traces")
    ObservabilityTelemetryService.initialize_telemetry("careerpilot-api", collector_url)
    ObservabilityTelemetryService.instrument_app(app)
    # DB health check
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("Database connection OK")

        # Initialize database tables (creates missing tables)
        try:
            init_db()
            logger.info("Database tables initialized")
        except Exception as e:
            logger.warning(f"Database initialization warning: {e}")
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        raise
    yield

    # At shutdown
    logger.info(f"Shutting down {app.title} v{settings.app_version}")
    try:
        from app.services.neo4j_service import Neo4jService
        await Neo4jService.close_driver()
    except Exception as e:
        logger.warning(f"Error closing Neo4j driver on shutdown: {e}")


app = FastAPI(title=settings.app_name, version=settings.app_version, lifespan=lifespan)

# Configure Middlewares
# 1. Request ID tracing middleware (runs first to trace subsequent middleware & route logs)
app.add_middleware(RequestIDMiddleware)

# 2. Trusted Host middleware
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"],
)

# 3. Configure CORS
allow_all_origins = settings.cors_origins.strip() == "*"
cors_origins = (
    ["*"]
    if allow_all_origins
    else [origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()]
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=not allow_all_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 4. Metrics middleware
app.add_middleware(MetricsMiddleware)

# 5. Rate limit middleware
app.add_middleware(RateLimitMiddleware)

# Expose /metrics scrape endpoint
@app.get("/metrics")
def metrics_endpoint():
    return Response(
        content=MetricsCollectionService.get_serialized_metrics(),
        media_type="text/plain; version=0.0.4"
    )

# Include v2 API Router
app.include_router(api_v2_router)

# Include v1 API Routers
app.include_router(index_router)
app.include_router(chat_router)
app.include_router(agent_router)
app.include_router(resume_router)
app.include_router(analysis_router)
app.include_router(jobs_router)
app.include_router(interview_router)
app.include_router(progress_router)
app.include_router(courses_router)
app.include_router(sessions_router)
app.include_router(applications_router)
app.include_router(feedback_router)

# Create static directory if it doesn't exist
static_dir = "static"
if not os.path.exists(static_dir):
    os.makedirs(static_dir)

# Mount static files
app.mount("/static", StaticFiles(directory=static_dir), name="static")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
