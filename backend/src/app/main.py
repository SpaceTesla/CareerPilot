import os
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from app.api.v1.chat import router as chat_router
from app.api.v1.index import router as index_router
from app.api.v1.resume import router as resume_router
from app.core.config import settings
from app.core.logging import get_logger, setup_logging
from app.infrastructure.database.connection import engine

# Configure logging
setup_logging(level="INFO", include_file_handler=True, log_file="logs/app.log")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # At startup
    logger = get_logger(__name__)
    logger.info(f"Starting {app.title} v{settings.app_version}")
    logger.info(f"Using model: {settings.model_name}")
    # DB health check
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("Database connection OK")
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        raise
    yield

    # At shutdown
    logger.info(f"Shutting down {app.title} v{settings.app_version}")


app = FastAPI(title=settings.app_name, version=settings.app_version, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(index_router)
app.include_router(chat_router)
app.include_router(resume_router)

# Create static directory if it doesn't exist
static_dir = "static"
if not os.path.exists(static_dir):
    os.makedirs(static_dir)

# Mount static files
app.mount("/static", StaticFiles(directory=static_dir), name="static")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
