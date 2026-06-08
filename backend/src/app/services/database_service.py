import time
from collections.abc import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Configure connection pooling (pool size = 20, max overflow = 10, pool pre-ping = True)
# We use settings.async_database_url which defaults to asyncpg dialect
async_engine = create_async_engine(
    settings.async_database_url,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


class DatabaseService:
    """
    Manages the life cycle of the async database engine and sessions.
    """

    @staticmethod
    async def get_session() -> AsyncGenerator[AsyncSession]:
        """
        Dependency injection provider yielding an async SQLAlchemy session.
        """
        async with AsyncSessionLocal() as session:
            try:
                yield session
                await session.commit()
            except Exception as e:
                await session.rollback()
                logger.error(f"Database session error, rolled back: {e}")
                raise
            finally:
                await session.close()

    @staticmethod
    async def check_health() -> tuple[bool, float]:
        """
        Executes a raw query `SELECT 1` to measure database connectivity
        and latency in milliseconds.
        Returns:
            A tuple of (is_connected, latency_ms)
        """

        start_time = time.perf_counter()
        try:
            async with AsyncSessionLocal() as session:
                await session.execute(text("SELECT 1"))
            latency_ms = (time.perf_counter() - start_time) * 1000
            return True, round(latency_ms, 2)
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False, 0.0
