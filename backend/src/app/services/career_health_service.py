from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from uuid import uuid4
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.infrastructure.database.models import (
    User,
    CareerProfile,
    CareerGoals,
    UserPreferences,
    JobApplication,
    TargetRoleSpecification,
    CareerHealthScore,
    Skill,
    JobPosting,
    JobPostingSkill,
    NormalizedSkill,
)

logger = get_logger(__name__)


class CareerHealthService:
    """Service to compute and track user's Career Health Score."""

    @staticmethod
    async def compute_health_score(
        db: AsyncSession, user_id: str
    ) -> CareerHealthScore | None:
        """
        Computes composite career health score (0-100) using 5 weighted metrics.
        """
        # 1. Fetch user data
        from sqlalchemy.orm import selectinload
        profile_stmt = select(CareerProfile).where(
            CareerProfile.user_id == user_id
        ).options(
            selectinload(CareerProfile.experiences),
            selectinload(CareerProfile.skills),
            selectinload(CareerProfile.education),
            selectinload(CareerProfile.projects),
        )
        profile_res = await db.execute(profile_stmt)
        profile = profile_res.scalar_one_or_none()

        goals_stmt = select(CareerGoals).where(CareerGoals.user_id == user_id)
        goals_res = await db.execute(goals_stmt)
        goals = goals_res.scalar_one_or_none()

        pref_stmt = select(UserPreferences).where(
            UserPreferences.user_id == user_id
        )
        pref_res = await db.execute(pref_stmt)
        pref = pref_res.scalar_one_or_none()

        # If user has no goals, we cannot compute target alignment
        if not goals:
            return None

        target_role = goals.target_role

        # 2. Get Target Specification
        spec_stmt = select(TargetRoleSpecification).where(
            TargetRoleSpecification.role_title == target_role
        )
        spec_res = await db.execute(spec_stmt)
        spec = spec_res.scalar_one_or_none()

        # ---------------------------------------------------------
        # Metric 1: Skill Alignment (30%)
        # Core target skills: top 10 most demanded skills for target_role
        # ---------------------------------------------------------
        core_stmt = (
            select(NormalizedSkill.name)
            .join(JobPostingSkill, JobPostingSkill.skill_id == NormalizedSkill.id)
            .join(JobPosting, JobPosting.id == JobPostingSkill.job_posting_id)
            .where(
                JobPosting.title.ilike(f"%{target_role}%"),
                JobPosting.is_active == True,
            )
            .group_by(NormalizedSkill.name)
            .order_by(func.count(JobPostingSkill.id).desc())
            .limit(10)
        )
        core_res = await db.execute(core_stmt)
        core_skills = {s.lower() for s in core_res.scalars().all()}

        user_skills = set()
        if profile:
            skills_stmt = select(Skill).where(Skill.profile_id == profile.id)
            skills_res = await db.execute(skills_stmt)
            user_skills = {s.skill_name.lower() for s in skills_res.scalars().all()}

        if core_skills:
            matching = core_skills.intersection(user_skills)
            skill_align = (len(matching) / len(core_skills)) * 100.0
        else:
            skill_align = 100.0

        # ---------------------------------------------------------
        # Metric 2: Market Positioning (25%)
        # User exp years vs target specification years
        # ---------------------------------------------------------
        exp_years = 0.0
        if profile:
            for exp in profile.experiences:
                end_date = exp.end_date or date.today()
                days = (end_date - exp.start_date).days
                exp_years += days / 365.25

        target_exp = 5.0
        if spec:
            target_exp = float(spec.typical_experience_years)

        if target_exp > 0:
            market_pos = min(100.0, (exp_years / target_exp) * 100.0)
        else:
            market_pos = 100.0

        # ---------------------------------------------------------
        # Metric 3: Activity Health (20%)
        # Based on search status and recent applications
        # ---------------------------------------------------------
        status = pref.job_search_status if pref else "PASSIVE"
        if status == "ACTIVE":
            thirty_days_ago = datetime.utcnow() - timedelta(days=30)
            app_stmt = select(func.count(JobApplication.id)).where(
                JobApplication.user_id == user_id,
                JobApplication.applied_at >= thirty_days_ago,
            )
            app_res = await db.execute(app_stmt)
            app_count = app_res.scalar() or 0

            if app_count >= 10:
                activity_health = 100.0
            elif app_count >= 5:
                activity_health = 80.0
            elif app_count >= 1:
                activity_health = 60.0
            else:
                activity_health = 40.0
        elif status == "PASSIVE":
            activity_health = 95.0
        else:
            activity_health = 90.0

        # ---------------------------------------------------------
        # Metric 4: Compensation Alignment (15%)
        # User target min vs market benchmark (typical_salary_p50)
        # ---------------------------------------------------------
        target_min = float(goals.target_compensation_min or 0.0)
        market_p50 = 100000.0
        if spec and spec.typical_salary_p50 is not None:
            market_p50 = float(spec.typical_salary_p50)

        if target_min <= market_p50:
            comp_align = 100.0
        else:
            comp_align = 100.0 - min(50.0, ((target_min - market_p50) / market_p50) * 100.0)

        # ---------------------------------------------------------
        # Metric 5: Profile Completeness (10%)
        # Presence of fields in career profile
        # ---------------------------------------------------------
        completeness = 0.0
        if profile:
            if profile.headline:
                completeness += 15.0
            if profile.summary:
                completeness += 15.0
            if profile.location:
                completeness += 10.0
            if profile.current_salary:
                completeness += 10.0
            if user_skills:
                completeness += 20.0
            if profile.experiences:
                completeness += 20.0
            if profile.education:
                completeness += 10.0
        else:
            completeness = 0.0

        # ---------------------------------------------------------
        # Composite Health Score
        # ---------------------------------------------------------
        score = (
            (skill_align * 0.30) +
            (market_pos * 0.25) +
            (activity_health * 0.20) +
            (comp_align * 0.15) +
            (completeness * 0.10)
        )
        score = min(100.0, max(0.0, score))

        # Driver and Detractor
        metrics = {
            "Skill Alignment": skill_align,
            "Market Positioning": market_pos,
            "Activity Health": activity_health,
            "Compensation Alignment": comp_align,
            "Profile Completeness": completeness,
        }

        top_driver = max(metrics, key=metrics.get)
        top_detractor = min(metrics, key=metrics.get)

        # Generate insight
        if score >= 85.0:
            insight = "Your career health is excellent. You are well positioned for your goals."
        elif score >= 70.0:
            insight = "Your career health is good, but addressing your gaps would boost alignment."
        else:
            insight = f"Your career health is average. Focus on improving your {top_detractor}."

        # Save health score record
        health_record = CareerHealthScore(
            id=str(uuid4()),
            user_id=user_id,
            score=float(score),
            skill_alignment_score=float(skill_align),
            market_positioning_score=float(market_pos),
            activity_health_score=float(activity_health),
            compensation_alignment_score=float(comp_align),
            profile_completeness_score=float(completeness),
            primary_insight=insight,
            top_driver=top_driver,
            top_detractor=top_detractor,
            computed_at=datetime.utcnow(),
        )
        db.add(health_record)
        await db.flush()

        return health_record
