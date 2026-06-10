from __future__ import annotations

import logging
from datetime import date, datetime
from uuid import uuid4
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.infrastructure.database.models import (
    User,
    CareerProfile,
    CareerGoals,
    JobPosting,
    JobPostingSkill,
    NormalizedSkill,
    Company,
    OpportunityScore,
    Skill,
)

logger = get_logger(__name__)


class OpportunityScoringEngine:
    """Engine to calculate personalized candidate-job fit scores."""

    @staticmethod
    async def calculate_fit_score(
        db: AsyncSession, user_id: str, job_posting_id: str
    ) -> OpportunityScore | None:
        """
        Computes fit score (0-100) combining skills, experience, pay, and company.
        """
        # Fetch job posting
        job = await db.get(JobPosting, job_posting_id)
        if not job:
            return None

        # Fetch company
        company = await db.get(Company, job.company_id)

        # Fetch user goals and profile
        goals_stmt = select(CareerGoals).where(CareerGoals.user_id == user_id)
        goals_res = await db.execute(goals_stmt)
        goals = goals_res.scalar_one_or_none()

        from sqlalchemy.orm import selectinload
        profile_stmt = select(CareerProfile).where(
            CareerProfile.user_id == user_id
        ).options(
            selectinload(CareerProfile.experiences)
        )
        profile_res = await db.execute(profile_stmt)
        profile = profile_res.scalar_one_or_none()

        if not goals or not profile:
            return None

        # 1. Skill Fit (40%)
        # Fetch skills linked to the posting
        job_skills_stmt = (
            select(NormalizedSkill.name)
            .join(JobPostingSkill, JobPostingSkill.skill_id == NormalizedSkill.id)
            .where(JobPostingSkill.job_posting_id == job_posting_id)
        )
        job_skills_res = await db.execute(job_skills_stmt)
        job_skills = {s.lower() for s in job_skills_res.scalars().all()}

        user_skills_stmt = select(Skill).where(Skill.profile_id == profile.id)
        user_skills_res = await db.execute(user_skills_stmt)
        user_skills = {s.skill_name.lower() for s in user_skills_res.scalars().all()}

        if job_skills:
            matching = job_skills.intersection(user_skills)
            skill_fit = (len(matching) / len(job_skills)) * 100.0
        else:
            skill_fit = 100.0

        # 2. Experience Fit (20%)
        title_lower = job.title.lower()
        if "principal" in title_lower or "staff" in title_lower:
            req_exp = 10.0
        elif "lead" in title_lower:
            req_exp = 8.0
        elif "senior" in title_lower or "sr" in title_lower:
            req_exp = 6.0
        elif "junior" in title_lower or "jr" in title_lower:
            req_exp = 1.5
        else:
            req_exp = 4.0

        user_exp = 0.0
        for exp in profile.experiences:
            end_date = exp.end_date or date.today()
            days = (end_date - exp.start_date).days
            user_exp += days / 365.25

        if user_exp >= req_exp:
            exp_fit = 100.0
        elif req_exp > 0:
            exp_fit = (user_exp / req_exp) * 100.0
        else:
            exp_fit = 100.0

        # 3. Compensation Fit (20%)
        user_min = float(goals.target_compensation_min or 0.0)
        user_max = float(goals.target_compensation_max or 999999.0)

        post_min = (
            float(job.compensation_min)
            if job.compensation_min is not None
            else None
        )
        post_max = (
            float(job.compensation_max)
            if job.compensation_max is not None
            else None
        )

        if post_min is None and post_max is None:
            comp_fit = 75.0
        else:
            if post_min is None and post_max is not None:
                post_min = post_max * 0.7
            if post_max is None and post_min is not None:
                post_max = post_min * 1.5

            if post_max >= user_min and post_min <= user_max:
                comp_fit = 100.0
            elif post_max < user_min and user_min > 0:
                comp_fit = (post_max / user_min) * 100.0
            else:
                comp_fit = 50.0

        # 4. Company Score (20%)
        company_score = (
            float(company.attractiveness_score)
            if company and company.attractiveness_score is not None
            else 70.0
        )

        # Composite score
        fit_score = (
            (skill_fit * 0.4) +
            (exp_fit * 0.2) +
            (comp_fit * 0.2) +
            (company_score * 0.2)
        )
        fit_score = min(100.0, max(0.0, fit_score))

        explanation = {
            "skill_fit": round(skill_fit, 2),
            "experience_fit": round(exp_fit, 2),
            "compensation_fit": round(comp_fit, 2),
            "company_attractiveness": round(company_score, 2),
        }

        # Save score
        score_stmt = select(OpportunityScore).where(
            OpportunityScore.user_id == user_id,
            OpportunityScore.job_posting_id == job_posting_id,
        )
        score_res = await db.execute(score_stmt)
        record = score_res.scalar_one_or_none()

        if not record:
            record = OpportunityScore(
                id=str(uuid4()),
                user_id=user_id,
                job_posting_id=job_posting_id,
                fit_score=float(fit_score),
                skill_fit_score=float(skill_fit),
                experience_fit_score=float(exp_fit),
                compensation_fit_score=float(comp_fit),
                company_attractiveness_score=float(company_score),
                explanation_json=explanation,
                computed_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            db.add(record)
        else:
            record.fit_score = float(fit_score)
            record.skill_fit_score = float(skill_fit)
            record.experience_fit_score = float(exp_fit)
            record.compensation_fit_score = float(comp_fit)
            record.company_attractiveness_score = float(company_score)
            record.explanation_json = explanation
            record.updated_at = datetime.utcnow()

        await db.flush()
        return record


class OpportunityRankingService:
    """Service to rank job opportunities for a user."""

    @staticmethod
    async def rank_opportunities(
        db: AsyncSession, user_id: str, limit: int = 10
    ) -> list[dict]:
        """Pre-filters active postings and ranks them using fit score."""
        goals_stmt = select(CareerGoals).where(CareerGoals.user_id == user_id)
        goals_res = await db.execute(goals_stmt)
        goals = goals_res.scalar_one_or_none()

        if not goals:
            return []

        # Simple pre-filter on active postings matching target_role or target_companies
        # Also exclude ghost postings to keep recommendations high quality
        stmt = select(JobPosting).where(
            JobPosting.is_active == True,
            JobPosting.is_ghost_posting == False,
        )
        res = await db.execute(stmt)
        postings = res.scalars().all()

        results = []
        for job in postings:
            score = await OpportunityScoringEngine.calculate_fit_score(
                db, user_id, job.id
            )
            if score:
                results.append({"job": job, "score": score})

        # Sort by fit_score descending
        results.sort(key=lambda x: x["score"].fit_score, reverse=True)
        return results[:limit]
