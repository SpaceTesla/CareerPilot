from __future__ import annotations

import asyncio
import json
from datetime import datetime
from uuid import uuid4
from typing import Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.services.database_service import AsyncSessionLocal
from app.services.redis_service import RedisService
from app.services.career_health_service import CareerHealthService
from app.services.position_delta_service import PositionDeltaService
from app.services.opportunity_scoring_service import OpportunityRankingService
from app.infrastructure.database.models import (
    DashboardAnalyticsEvent,
    CareerHealthScore,
    PositionDelta,
    Company,
)

logger = get_logger(__name__)


class DashboardAggregationService:
    """Service to aggregate dashboard widgets concurrently with caching."""

    @staticmethod
    async def _get_health(user_id: str) -> Any:
        async with AsyncSessionLocal() as db:
            stmt = (
                select(CareerHealthScore)
                .where(CareerHealthScore.user_id == user_id)
                .order_by(CareerHealthScore.computed_at.desc())
                .limit(1)
            )
            res = await db.execute(stmt)
            health = res.scalar_one_or_none()
            if not health:
                health = await CareerHealthService.compute_health_score(db, user_id)
                if health:
                    await db.commit()
            return health

    @staticmethod
    async def _get_delta(user_id: str) -> Any:
        async with AsyncSessionLocal() as db:
            stmt = (
                select(PositionDelta)
                .where(PositionDelta.user_id == user_id)
                .order_by(PositionDelta.computed_at.desc())
                .limit(1)
            )
            res = await db.execute(stmt)
            delta = res.scalar_one_or_none()
            if not delta:
                delta = await PositionDeltaService.calculate_position_delta(db, user_id)
                if delta:
                    await db.commit()
            return delta

    @staticmethod
    async def _get_opportunities(user_id: str) -> list[dict]:
        async with AsyncSessionLocal() as db:
            items = await OpportunityRankingService.rank_opportunities(
                db, user_id, limit=5
            )
            serialized = []
            for item in items:
                job = item["job"]
                score = item["score"]

                company_name = "Unknown"
                if job.company_id:
                    comp = await db.get(Company, job.company_id)
                    if comp:
                        company_name = comp.name

                serialized.append({
                    "job_id": job.id,
                    "title": job.title,
                    "company_name": company_name,
                    "location": job.location,
                    "compensation_min": (
                        float(job.compensation_min)
                        if job.compensation_min is not None
                        else None
                    ),
                    "compensation_max": (
                        float(job.compensation_max)
                        if job.compensation_max is not None
                        else None
                    ),
                    "fit_score": float(score.fit_score),
                    "skill_fit_score": float(score.skill_fit_score),
                    "experience_fit_score": float(score.experience_fit_score),
                    "compensation_fit_score": float(score.compensation_fit_score),
                    "company_attractiveness_score": float(
                        score.company_attractiveness_score
                    ),
                    "explanation": score.explanation_json,
                })
            return serialized

    @staticmethod
    async def get_dashboard_payload(
        user_id: str, force_refresh: bool = False
    ) -> dict:
        """Fetch dashboard analytics from cache or aggregate concurrently."""
        cache_key = f"dashboard:user:{user_id}"

        if not force_refresh:
            try:
                redis = RedisService.get_client()
                cached = await redis.get(cache_key)
                await redis.close()
                if cached:
                    return json.loads(cached)
            except Exception as e:
                logger.error(f"Redis get failed: {e}")

        # Concurrently gather sub-scores/gaps/opportunities
        health, delta, opps = await asyncio.gather(
            DashboardAggregationService._get_health(user_id),
            DashboardAggregationService._get_delta(user_id),
            DashboardAggregationService._get_opportunities(user_id),
        )

        payload = {
            "health_score": {
                "score": float(health.score),
                "skill_alignment_score": float(health.skill_alignment_score),
                "market_positioning_score": float(health.market_positioning_score),
                "activity_health_score": float(health.activity_health_score),
                "compensation_alignment_score": float(
                    health.compensation_alignment_score
                ),
                "profile_completeness_score": float(health.profile_completeness_score),
                "primary_insight": health.primary_insight,
                "top_driver": health.top_driver,
                "top_detractor": health.top_detractor,
                "computed_at": health.computed_at.isoformat(),
            }
            if health
            else None,
            "position_delta": {
                "target_role": delta.target_role,
                "missing_skills": delta.missing_skills,
                "top_3_prioritized_gaps": delta.top_3_prioritized_gaps,
                "recommendation_summary": delta.recommendation_summary,
                "computed_at": delta.computed_at.isoformat(),
            }
            if delta
            else None,
            "opportunity_spotlight": opps,
        }

        # Cache payload
        try:
            redis = RedisService.get_client()
            await redis.setex(cache_key, 3600, json.dumps(payload))
            await redis.close()
        except Exception as e:
            logger.error(f"Redis set failed: {e}")

        return payload

    @staticmethod
    async def invalidate_cache(user_id: str) -> None:
        """Evict the cached dashboard payload for user."""
        cache_key = f"dashboard:user:{user_id}"
        try:
            redis = RedisService.get_client()
            await redis.delete(cache_key)
            await redis.close()
        except Exception as e:
            logger.error(f"Redis cache eviction failed: {e}")


class AnalyticsService:
    """Service to track and record dashboard analytics events."""

    @staticmethod
    async def log_dashboard_event(
        db: AsyncSession,
        user_id: str,
        event_type: str,
        widget_name: str | None,
        metadata: dict,
    ) -> DashboardAnalyticsEvent:
        """Log a dashboard interaction or widget click."""
        event = DashboardAnalyticsEvent(
            id=str(uuid4()),
            user_id=user_id,
            event_type=event_type,
            widget_name=widget_name,
            metadata_json=metadata,
            created_at=datetime.utcnow(),
        )
        db.add(event)
        await db.flush()
        return event
