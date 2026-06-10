from __future__ import annotations

from datetime import date, datetime
from uuid import uuid4
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.infrastructure.database.models import (
    JobPosting,
    Company,
    JobDuplicate,
    JobApplication,
    GhostPostingSignal,
)

logger = get_logger(__name__)


class GhostPostingDetectorService:
    """Service for analyzing and flagging ghost job postings."""

    @staticmethod
    async def detect_ghost_posting(
        db: AsyncSession, job_posting_id: str
    ) -> GhostPostingSignal | None:
        """
        Calculates ghost score for a job posting and flags it if score > 70.
        """
        job = await db.get(JobPosting, job_posting_id)
        if not job:
            return None

        company = await db.get(Company, job.company_id)

        # 1. Age Score (30%)
        age_days = (date.today() - job.post_date).days
        if age_days < 0:
            age_days = 0

        if age_days >= 90:
            age_score = 100.0
        elif age_days >= 60:
            age_score = 80.0
        elif age_days >= 30:
            age_score = 50.0
        else:
            age_score = float(age_days) * 1.5

        ratio = 1.0
        if company and company.hiring_velocity_90d is not None and float(company.hiring_velocity_90d) > 0:
            ratio = float(company.hiring_velocity_30d or 0.0) / (float(company.hiring_velocity_90d) / 3.0)

        if ratio <= 0.2:
            vel_score = 100.0
        elif ratio <= 0.5:
            vel_score = 80.0
        elif ratio <= 0.8:
            vel_score = 50.0
        elif ratio >= 1.2:
            vel_score = 10.0
        else:
            vel_score = 30.0

        # 3. Repost Freq (20%)
        dup_stmt = select(func.count(JobDuplicate.id)).where(
            (JobDuplicate.primary_job_id == job_posting_id) |
            (JobDuplicate.duplicate_job_id == job_posting_id)
        )
        dup_res = await db.execute(dup_stmt)
        repost_count = dup_res.scalar() or 0

        if repost_count >= 3:
            repost_score = 100.0
        elif repost_count == 2:
            repost_score = 75.0
        elif repost_count == 1:
            repost_score = 40.0
        else:
            repost_score = 0.0

        # 4. Cohort Response (20%)
        app_stmt = select(func.count(JobApplication.id)).where(
            JobApplication.job_url == job.url
        )
        app_res = await db.execute(app_stmt)
        cohort_apps = app_res.scalar() or 0

        int_stmt = select(func.count(JobApplication.id)).where(
            JobApplication.job_url == job.url,
            JobApplication.status.in_(["interviewing", "offer"]),
        )
        int_res = await db.execute(int_stmt)
        cohort_ints = int_res.scalar() or 0

        if cohort_apps > 0:
            rate = cohort_ints / cohort_apps
            if rate == 0:
                cohort_score = 100.0
            elif rate <= 0.1:
                cohort_score = 80.0
            elif rate <= 0.2:
                cohort_score = 50.0
            else:
                cohort_score = 0.0
        else:
            cohort_score = 50.0

        # Calculate composite score
        ghost_score = (
            (age_score * 0.3) +
            (vel_score * 0.3) +
            (repost_score * 0.2) +
            (cohort_score * 0.2)
        )
        is_ghost = ghost_score > 70.0

        # Generate explanation
        explanations = []
        if age_score >= 80:
            explanations.append(f"Posting is very old ({age_days} days)")
        if vel_score >= 80:
            explanations.append("Company hiring velocity has dropped significantly")
        if repost_score >= 75:
            explanations.append("Job has been reposted/duplicated multiple times")
        if cohort_score >= 80 and cohort_apps > 0:
            explanations.append("Low application response rate in cohort")

        if not explanations:
            explanation = "Posting shows normal activity levels."
        else:
            explanation = "Potential ghost posting: " + ", ".join(explanations) + "."

        # Save/update signal
        sig_stmt = select(GhostPostingSignal).where(
            GhostPostingSignal.job_posting_id == job_posting_id
        )
        sig_res = await db.execute(sig_stmt)
        signal = sig_res.scalar_one_or_none()

        if not signal:
            signal = GhostPostingSignal(
                id=str(uuid4()),
                job_posting_id=job_posting_id,
                ghost_score=float(ghost_score),
                is_flagged_ghost=is_ghost,
                age_days=age_days,
                repost_count=repost_count,
                company_velocity_ratio=float(ratio),
                cohort_applications=cohort_apps,
                cohort_interviews=cohort_ints,
                explanation=explanation,
                computed_at=datetime.utcnow(),
            )
            db.add(signal)
        else:
            signal.ghost_score = float(ghost_score)
            signal.is_flagged_ghost = is_ghost
            signal.age_days = age_days
            signal.repost_count = repost_count
            signal.company_velocity_ratio = float(ratio)
            signal.cohort_applications = cohort_apps
            signal.cohort_interviews = cohort_ints
            signal.explanation = explanation
            signal.computed_at = datetime.utcnow()

        # Update job posting fields
        job.is_ghost_posting = is_ghost
        job.ghost_score = float(ghost_score)

        await db.flush()
        return signal
