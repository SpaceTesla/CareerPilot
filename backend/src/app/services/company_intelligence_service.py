from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from uuid import uuid4
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.infrastructure.database.models import (
    Company,
    JobPosting,
    CompanySnapshot,
    CompanyWatchlist,
)
from app.utils.event_bus import EventBus

logger = get_logger(__name__)


class CompanyIntelligenceService:
    """Service for company intelligence scoring and snapshots."""

    @staticmethod
    def _calculate_size_score(size_range: str | None) -> float:
        """Map size range to a stability score (0-100)."""
        if not size_range:
            return 70.0
        size_map = {
            "10000+": 100.0,
            "5001-10000": 95.0,
            "1001-5000": 90.0,
            "501-1000": 85.0,
            "201-500": 80.0,
            "51-200": 70.0,
            "11-50": 60.0,
            "1-10": 50.0,
        }
        return size_map.get(size_range.strip(), 70.0)

    @staticmethod
    async def aggregate_company_intelligence(
        db: AsyncSession, company_id: str
    ) -> Company | None:
        """
        Computes velocity, trend, attractiveness, and stores a snapshot.
        """
        company = await db.get(Company, company_id)
        if not company:
            return None

        today = date.today()
        date_30d = today - timedelta(days=30)
        date_90d = today - timedelta(days=90)

        # 1. Active job postings
        postings_stmt = select(JobPosting).where(
            JobPosting.company_id == company_id,
            JobPosting.is_active == True,
        )
        result = await db.execute(postings_stmt)
        postings = result.scalars().all()

        active_count = len(postings)

        # 2. Hiring Velocities
        vel_30d = sum(1 for p in postings if p.post_date >= date_30d)
        vel_90d = sum(1 for p in postings if p.post_date >= date_90d)

        # 3. Trend direction
        prev_trend = company.trend_direction
        monthly_avg_90d = vel_90d / 3.0
        if monthly_avg_90d == 0:
            trend = "GROWING" if vel_30d > 0 else "STABLE"
        elif vel_30d > monthly_avg_90d * 1.1:
            trend = "GROWING"
        elif vel_30d < monthly_avg_90d * 0.9:
            trend = "DECLINING"
        else:
            trend = "STABLE"

        # 4. Attractiveness Score Components
        # A. Growth score (40%)
        if monthly_avg_90d == 0:
            growth_ratio = 1.0 if vel_30d == 0 else 2.0
        else:
            growth_ratio = vel_30d / monthly_avg_90d
        growth_score = min(100.0, max(0.0, 50.0 + (growth_ratio - 1.0) * 50.0))

        # B. Salary Score (40%)
        salary_midpoints = []
        for p in postings:
            if p.compensation_min is not None and p.compensation_max is not None:
                salary_midpoints.append((float(p.compensation_min) + float(p.compensation_max)) / 2.0)
            elif p.compensation_min is not None:
                salary_midpoints.append(float(p.compensation_min))
            elif p.compensation_max is not None:
                salary_midpoints.append(float(p.compensation_max))

        if salary_midpoints:
            avg_salary = sum(salary_midpoints) / len(salary_midpoints)
            salary_score = 30.0 + ((avg_salary - 60000.0) / 120000.0) * 70.0
            salary_score = min(100.0, max(0.0, salary_score))
        else:
            salary_score = 70.0

        # C. Size Score (20%)
        size_score = CompanyIntelligenceService._calculate_size_score(
            company.size_range
        )

        # Composite score
        old_score = float(company.attractiveness_score or 0.0)
        attractiveness = growth_score * 0.4 + salary_score * 0.4 + size_score * 0.2
        attractiveness = min(100.0, max(0.0, attractiveness))

        # Update company
        company.hiring_velocity_30d = float(vel_30d)
        company.hiring_velocity_90d = float(vel_90d)
        company.trend_direction = trend
        company.attractiveness_score = float(attractiveness)
        company.last_aggregated_at = datetime.utcnow()

        # Create snapshot
        snapshot = CompanySnapshot(
            id=str(uuid4()),
            company_id=company_id,
            active_postings_count=active_count,
            hiring_velocity=float(vel_30d),
            attractiveness_score=float(attractiveness),
            snapshot_date=today,
            created_at=datetime.utcnow(),
        )
        db.add(snapshot)
        await db.flush()

        # Trigger watchlist notifications if change is significant (> 5.0)
        score_diff = abs(attractiveness - old_score)
        trend_changed = prev_trend is not None and prev_trend != trend
        if score_diff >= 5.0 or trend_changed:
            watchlist_stmt = select(CompanyWatchlist.user_id).where(
                CompanyWatchlist.company_id == company_id,
                CompanyWatchlist.notifications_enabled == True,
            )
            watchlist_res = await db.execute(watchlist_stmt)
            watcher_ids = watchlist_res.scalars().all()

            for user_id in watcher_ids:
                alert_data = {
                    "user_id": user_id,
                    "company_id": company_id,
                    "company_name": company.name,
                    "old_score": old_score,
                    "new_score": attractiveness,
                    "old_trend": prev_trend,
                    "new_trend": trend,
                    "alert_type": "METRIC_UPDATE",
                }
                await EventBus.publish("company.watchlist.alert", alert_data)

        return company


class WatchlistService:
    """Service for managing company watchlists."""

    @staticmethod
    async def add_to_watchlist(
        db: AsyncSession, user_id: str, company_id: str
    ) -> CompanyWatchlist:
        """Add a company to a user's watchlist."""
        watchlist = CompanyWatchlist(
            user_id=user_id,
            company_id=company_id,
            notifications_enabled=True,
            created_at=datetime.utcnow(),
        )
        await db.merge(watchlist)
        await db.flush()
        return watchlist

    @staticmethod
    async def remove_from_watchlist(
        db: AsyncSession, user_id: str, company_id: str
    ) -> bool:
        """Remove a company from a user's watchlist."""
        stmt = select(CompanyWatchlist).where(
            CompanyWatchlist.user_id == user_id,
            CompanyWatchlist.company_id == company_id,
        )
        res = await db.execute(stmt)
        watchlist = res.scalar_one_or_none()
        if watchlist:
            await db.delete(watchlist)
            await db.flush()
            return True
        return False

    @staticmethod
    async def get_watchlist(
        db: AsyncSession, user_id: str
    ) -> list[Company]:
        """Get list of companies on a user's watchlist."""
        stmt = (
            select(Company)
            .join(CompanyWatchlist, Company.id == CompanyWatchlist.company_id)
            .where(CompanyWatchlist.user_id == user_id)
        )
        res = await db.execute(stmt)
        return list(res.scalars().all())

    @staticmethod
    async def is_watched(
        db: AsyncSession, user_id: str, company_id: str
    ) -> bool:
        """Check if a user is watching a company."""
        stmt = select(CompanyWatchlist).where(
            CompanyWatchlist.user_id == user_id,
            CompanyWatchlist.company_id == company_id,
        )
        res = await db.execute(stmt)
        return res.scalar_one_or_none() is not None
