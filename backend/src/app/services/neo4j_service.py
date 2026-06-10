from __future__ import annotations

import time
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from neo4j import AsyncGraphDatabase, AsyncDriver, AsyncSession

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class Neo4jService:
    """
    Manages Neo4j driver lifecycle, sessions, health checks, and schemas/constraints.
    """

    _driver: AsyncDriver | None = None
    _constraints_created: bool = False

    @classmethod
    def get_driver(cls) -> AsyncDriver:
        if cls._driver is None:
            cls._driver = AsyncGraphDatabase.driver(
                settings.neo4j_uri,
                auth=(settings.neo4j_username, settings.neo4j_password),
            )
        return cls._driver

    @classmethod
    @asynccontextmanager
    async def get_session(cls) -> AsyncGenerator[AsyncSession, None]:
        driver = cls.get_driver()
        async with driver.session() as session:
            if not cls._constraints_created:
                try:
                    await cls.ensure_constraints(session)
                except Exception as e:
                    logger.warning(f"Failed to create Neo4j constraints: {e}")
            yield session

    @classmethod
    async def close_driver(cls) -> None:
        if cls._driver is not None:
            await cls._driver.close()
            cls._driver = None
            cls._constraints_created = False
            logger.info("Neo4j driver closed successfully.")

    @classmethod
    async def ensure_constraints(cls, session: AsyncSession) -> None:
        constraints = [
            "CREATE CONSTRAINT unique_role_name IF NOT EXISTS FOR (r:Role) REQUIRE r.name IS UNIQUE",
            "CREATE CONSTRAINT unique_skill_name IF NOT EXISTS FOR (s:Skill) REQUIRE s.canonical_name IS UNIQUE",
            "CREATE CONSTRAINT unique_company_name IF NOT EXISTS FOR (c:Company) REQUIRE c.name IS UNIQUE",
            "CREATE CONSTRAINT unique_profile_id IF NOT EXISTS FOR (p:CandidateProfile) REQUIRE p.profile_id IS UNIQUE",
        ]
        for query in constraints:
            await session.run(query)
        cls._constraints_created = True
        logger.info("Neo4j database constraints ensured successfully.")

    @classmethod
    async def check_health(cls) -> tuple[bool, float]:
        """
        Pings Neo4j and returns latency in milliseconds.
        Returns:
            A tuple of (is_connected, latency_ms)
        """
        start_time = time.perf_counter()
        try:
            driver = cls.get_driver()
            await driver.verify_connectivity()
            latency_ms = (time.perf_counter() - start_time) * 1000
            return True, round(latency_ms, 2)
        except Exception as e:
            logger.error(f"Neo4j health check failed: {e}")
            return False, 0.0
