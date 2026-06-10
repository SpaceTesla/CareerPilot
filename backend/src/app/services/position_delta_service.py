from __future__ import annotations

import logging
from datetime import datetime
from uuid import uuid4
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.infrastructure.database.models import (
    User,
    CareerGoals,
    CareerProfile,
    Skill,
    JobPosting,
    JobPostingSkill,
    NormalizedSkill,
    TargetRoleSpecification,
    PositionDelta,
)

logger = get_logger(__name__)


def calculate_percentile(values: list[float], percentile: float) -> float:
    """Calculate percentile of list of numeric values (0.0 to 1.0)."""
    if not values:
        return 0.0
    sorted_val = sorted(values)
    k = (len(sorted_val) - 1) * percentile
    f = int(k)
    c = f + 1
    if c < len(sorted_val):
        return sorted_val[f] + (sorted_val[c] - sorted_val[f]) * (k - f)
    return sorted_val[f]


class TargetRoleSpecificationService:
    """Service to aggregate market data into target role specs."""

    @staticmethod
    async def rebuild_specifications(db: AsyncSession) -> None:
        """Rebuild target specifications from active job postings."""
        # Find unique job titles
        stmt = (
            select(JobPosting.title, func.count(JobPosting.id))
            .where(JobPosting.is_active == True)
            .group_by(JobPosting.title)
        )
        res = await db.execute(stmt)
        titles_counts = res.all()

        for title, count in titles_counts:
            # Experience heuristic based on title keywords
            title_lower = title.lower()
            if "principal" in title_lower or "staff" in title_lower:
                exp = 10.0
            elif "lead" in title_lower:
                exp = 8.0
            elif "senior" in title_lower or "sr" in title_lower:
                exp = 6.0
            elif "junior" in title_lower or "jr" in title_lower:
                exp = 1.5
            else:
                exp = 4.0

            # Get salary data
            sal_stmt = select(JobPosting).where(
                JobPosting.title == title,
                JobPosting.is_active == True,
            )
            sal_res = await db.execute(sal_stmt)
            postings = sal_res.scalars().all()

            salaries = []
            for p in postings:
                if p.compensation_min is not None and p.compensation_max is not None:
                    salaries.append(
                        (float(p.compensation_min) + float(p.compensation_max)) / 2.0
                    )
                elif p.compensation_min is not None:
                    salaries.append(float(p.compensation_min))
                elif p.compensation_max is not None:
                    salaries.append(float(p.compensation_max))

            p50 = None
            p75 = None
            if salaries:
                p50 = float(calculate_percentile(salaries, 0.50))
                p75 = float(calculate_percentile(salaries, 0.75))

            # Upsert spec
            spec_stmt = select(TargetRoleSpecification).where(
                TargetRoleSpecification.role_title == title
            )
            spec_res = await db.execute(spec_stmt)
            spec = spec_res.scalar_one_or_none()

            if not spec:
                spec = TargetRoleSpecification(
                    id=str(uuid4()),
                    role_title=title,
                    typical_experience_years=exp,
                    typical_salary_p50=p50,
                    typical_salary_p75=p75,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                )
                db.add(spec)
            else:
                spec.typical_experience_years = exp
                spec.typical_salary_p50 = p50
                spec.typical_salary_p75 = p75
                spec.updated_at = datetime.utcnow()

        await db.flush()


class PositionDeltaService:
    """Service to compute skills/experience gaps against target roles."""

    @staticmethod
    async def calculate_position_delta(
        db: AsyncSession, user_id: str
    ) -> PositionDelta | None:
        """Calculate skill gap delta and evidence-backed recommendation."""
        # 1. Fetch user goals
        goals_stmt = select(CareerGoals).where(CareerGoals.user_id == user_id)
        goals_res = await db.execute(goals_stmt)
        goals = goals_res.scalar_one_or_none()

        if not goals:
            return None

        target_role = goals.target_role

        # 2. Fetch user profile skills
        prof_stmt = select(CareerProfile).where(CareerProfile.user_id == user_id)
        prof_res = await db.execute(prof_stmt)
        profile = prof_res.scalar_one_or_none()

        user_skills = set()
        if profile:
            skills_stmt = select(Skill).where(Skill.profile_id == profile.id)
            skills_res = await db.execute(skills_stmt)
            user_skills = {s.skill_name.lower() for s in skills_res.scalars().all()}

        # 3. Retrieve target specification if exists
        spec_stmt = select(TargetRoleSpecification).where(
            TargetRoleSpecification.role_title == target_role
        )
        spec_res = await db.execute(spec_stmt)
        spec = spec_res.scalar_one_or_none()

        # 4. Fetch skill demand frequency for target role
        skill_demand_stmt = (
            select(
                NormalizedSkill.name,
                func.count(JobPostingSkill.id).label("demand_count"),
            )
            .join(JobPosting, JobPosting.id == JobPostingSkill.job_posting_id)
            .join(NormalizedSkill, NormalizedSkill.id == JobPostingSkill.skill_id)
            .where(
                JobPosting.title.ilike(f"%{target_role}%"),
                JobPosting.is_active == True,
            )
            .group_by(NormalizedSkill.name)
            .order_by(func.count(JobPostingSkill.id).desc())
        )
        demand_res = await db.execute(skill_demand_stmt)
        demanded_skills = demand_res.all()

        # Find missing skills
        missing_skills = []
        for name, count in demanded_skills:
            if name.lower() not in user_skills:
                missing_skills.append({"name": name, "frequency": int(count)})

        # Prioritize top 3 gaps
        top_3 = missing_skills[:3]

        # Recommendation summary
        if top_3:
            missing_names = [item["name"] for item in top_3]
            summary = (
                f"To transition to '{target_role}', prioritize acquiring: "
                f"{', '.join(missing_names)}. These skills are highly demanded "
                f"in active target postings."
            )
        else:
            summary = (
                f"Your skills are well aligned with the requirements for the "
                f"'{target_role}' role."
            )

        # Save delta
        delta_stmt = select(PositionDelta).where(PositionDelta.user_id == user_id)
        delta_res = await db.execute(delta_stmt)
        delta = delta_res.scalar_one_or_none()

        if not delta:
            delta = PositionDelta(
                id=str(uuid4()),
                user_id=user_id,
                target_role=target_role,
                missing_skills=missing_skills,
                top_3_prioritized_gaps=top_3,
                recommendation_summary=summary,
                computed_at=datetime.utcnow(),
            )
            db.add(delta)
        else:
            delta.target_role = target_role
            delta.missing_skills = missing_skills
            delta.top_3_prioritized_gaps = top_3
            delta.recommendation_summary = summary
            delta.computed_at = datetime.utcnow()

        await db.flush()
        return delta
