from __future__ import annotations

import json
from datetime import date, datetime, UTC
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.infrastructure.database.models import (
    JobPosting,
    JobPostingSkill,
    NormalizedSkill,
    SkillTrendDaily,
)
from app.services.redis_service import RedisService
from app.utils.event_bus import EventBus

logger = get_logger(__name__)


class SkillTrendItem(BaseModel):
    skill_id: str
    skill_name: str
    count_30d: int
    frequency_30d: float
    velocity: float


class SkillTrendService:
    """
    Skill Trend Service (F1.6) for computingdaily snapshots, refreshing
    materialized views, and managing Redis trend caching.
    """

    @staticmethod
    async def get_trends(
        db: AsyncSession, sort_by: str, limit: int, offset: int
    ) -> List[SkillTrendItem]:
        """
        Retrieves top skill trends from Redis cache or falls back to
        mv_skill_trends.
        """
        sort_by_clean = "velocity" if sort_by.lower() == "velocity" else "frequency"
        cache_key = f"market:trends:{sort_by_clean}:{limit}:{offset}"

        # 1. Try Redis cache
        try:
            redis_client = RedisService.get_client()
            cached_data = await redis_client.get(cache_key)
            await redis_client.close()
            if cached_data:
                logger.info(f"Redis cache hit for key: {cache_key}")
                items_dict = json.loads(cached_data)
                return [SkillTrendItem(**item) for item in items_dict]
        except Exception as ex:
            logger.error(f"Failed to read from Redis cache: {ex}")

        # 2. Query materialized view
        logger.info(f"Redis cache miss. Querying mv_skill_trends.")
        order_col = "velocity" if sort_by_clean == "velocity" else "freq_30d"

        # Safe parameter substitution for LIMIT and OFFSET
        stmt = text(
            f"""
            SELECT skill_id, skill_name, count_30d, freq_30d, velocity
            FROM mv_skill_trends
            ORDER BY {order_col} DESC
            LIMIT :limit OFFSET :offset
            """
        )
        res = await db.execute(stmt, {"limit": limit, "offset": offset})
        rows = res.fetchall()

        trends = []
        for row in rows:
            trends.append(
                SkillTrendItem(
                    skill_id=str(row[0]),
                    skill_name=row[1],
                    count_30d=row[2],
                    frequency_30d=float(row[3]),
                    velocity=float(row[4]),
                )
            )

        # 3. Save to Redis cache (12-hour TTL)
        try:
            redis_client = RedisService.get_client()
            serialized = json.dumps([t.model_dump() for t in trends])
            await redis_client.setex(cache_key, 43200, serialized)  # 12 hours
            await redis_client.close()
        except Exception as ex:
            logger.error(f"Failed to write to Redis cache: {ex}")

        return trends

    @staticmethod
    async def compute_daily_snapshots(db: AsyncSession) -> None:
        """
        Computes daily frequency & volume snapshots of skills required in active job postings.
        """
        # Count total active job postings
        total_stmt = select(func.count(JobPosting.id)).where(
            JobPosting.is_active == True,
            (JobPosting.expiry_date == None) | (JobPosting.expiry_date >= date.today()),
        )
        total_res = await db.execute(total_stmt)
        total_active_postings = total_res.scalar() or 0

        if total_active_postings == 0:
            logger.info("No active job postings found. Snapshot skipped.")
            return

        # Query group counts of active skills
        group_stmt = (
            select(
                JobPostingSkill.skill_id,
                func.count(JobPostingSkill.job_posting_id),
            )
            .join(JobPosting, JobPosting.id == JobPostingSkill.job_posting_id)
            .where(
                JobPosting.is_active == True,
                (JobPosting.expiry_date == None)
                | (JobPosting.expiry_date >= date.today()),
            )
            .group_by(JobPostingSkill.skill_id)
        )
        group_res = await db.execute(group_stmt)
        skill_counts = group_res.fetchall()

        today_date = date.today()

        # Delete existing snapshot records for today to avoid duplicate key errors on recalculation
        del_stmt = text(
            "DELETE FROM skill_trends_daily WHERE snapshot_date = :today"
        )
        await db.execute(del_stmt, {"today": today_date})
        await db.flush()

        for skill_id, cnt in skill_counts:
            freq = cnt / total_active_postings
            snapshot = SkillTrendDaily(
                id=str(uuid4()),
                skill_id=str(skill_id),
                snapshot_date=today_date,
                posting_count=cnt,
                total_postings_count=total_active_postings,
                frequency=Decimal(str(round(freq, 5))),
            )
            db.add(snapshot)

        await db.flush()
        logger.info(
            f"Computed daily skill snapshots for {len(skill_counts)} skills on {today_date}."
        )

    @staticmethod
    async def refresh_materialized_view(db: AsyncSession) -> None:
        """
        Refreshes mv_skill_trends materialized view and evicts Redis caches.
        """
        logger.info("Refreshing mv_skill_trends concurrently.")
        await db.execute(text("REFRESH MATERIALIZED VIEW CONCURRENTLY mv_skill_trends"))
        await db.flush()

        # Evict all market trend keys in Redis
        try:
            redis_client = RedisService.get_client()
            keys = await redis_client.keys("market:trends:*")
            if keys:
                await redis_client.delete(*keys)
                logger.info(f"Evicted {len(keys)} market trend cache keys from Redis.")
            await redis_client.close()
        except Exception as ex:
            logger.error(f"Failed to clear Redis cache keys during refresh: {ex}")

        # Count total skills tracked
        cnt_stmt = select(func.count(NormalizedSkill.id))
        cnt_res = await db.execute(cnt_stmt)
        total_skills = cnt_res.scalar() or 0

        await EventBus.publish(
            "market.skill_trends_refreshed",
            {
                "snapshot_date": str(date.today()),
                "total_skills_tracked": total_skills,
            },
        )
        logger.info("Finished materialized view refresh.")
