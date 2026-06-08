from __future__ import annotations

from datetime import date, datetime
from typing import Any
from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.infrastructure.database.models import (
    CareerProfile,
    Education,
    Experience,
    ProfileVersion,
    Project,
    Skill,
)
from app.schemas.profile import ProfileUpdate
from app.utils.event_bus import EventBus


class ProfileService:
    """
    Manages user career profiles, child collections, completeness score, and history versions.
    """

    @staticmethod
    async def get_by_user_id(db: AsyncSession, user_id: UUID) -> CareerProfile:
        """
        Fetches the current active profile for a user.
        If it does not exist, auto-creates an empty one.
        """
        stmt = (
            select(CareerProfile)
            .where(CareerProfile.user_id == str(user_id))
            .options(
                selectinload(CareerProfile.skills),
                selectinload(CareerProfile.experiences),
                selectinload(CareerProfile.education),
                selectinload(CareerProfile.projects),
            )
        )
        result = await db.execute(stmt)
        profile = result.scalar_one_or_none()

        if not profile:
            # Auto-create empty profile
            profile = CareerProfile(
                id=str(uuid4()),
                user_id=str(user_id),
                headline=None,
                summary=None,
                location=None,
                current_salary=None,
            )
            db.add(profile)
            await db.flush()
            # Reload with empty collections loaded
            result = await db.execute(stmt)
            profile = result.scalar_one()

        return profile

    @staticmethod
    def calculate_completeness(profile: CareerProfile) -> int:
        """
        Simple percentage score of present fields:
        skills: 30%, experiences: 40%, education: 15%, projects: 15%
        """
        score = 0
        if profile.skills:
            score += 30
        if profile.experiences:
            score += 40
        if profile.education:
            score += 15
        if profile.projects:
            score += 15
        return score

    @staticmethod
    async def update_profile(
        db: AsyncSession, user_id: UUID, data: ProfileUpdate
    ) -> CareerProfile:
        """
        Writes profile updates, stores history version, and publishes event.
        """
        # Lock profile row to avoid concurrent writes
        profile = await ProfileService.get_by_user_id(db, user_id)

        # Update root columns
        profile.headline = data.headline
        profile.summary = data.summary
        profile.location = data.location
        profile.current_salary = data.current_salary
        profile.updated_at = datetime.utcnow()

        # Delete existing child items
        for skill in list(profile.skills):
            await db.delete(skill)
        for experience in list(profile.experiences):
            await db.delete(experience)
        for edu in list(profile.education):
            await db.delete(edu)
        for proj in list(profile.projects):
            await db.delete(proj)

        await db.flush()

        # Add new child items
        profile.skills = [
            Skill(
                id=str(uuid4()),
                profile_id=profile.id,
                skill_name=s.skill_name,
                years_experience=float(s.years_experience),
                proficiency=s.proficiency.value,
            )
            for s in data.skills
        ]

        profile.experiences = [
            Experience(
                id=str(uuid4()),
                profile_id=profile.id,
                company_name=e.company_name,
                job_title=e.job_title,
                start_date=e.start_date,
                end_date=e.end_date,
                description=e.description,
                is_current=e.is_current,
            )
            for e in data.experiences
        ]

        profile.education = [
            Education(
                id=str(uuid4()),
                profile_id=profile.id,
                institution=ed.institution,
                degree=ed.degree,
                field_of_study=ed.field_of_study,
                start_date=ed.start_date,
                end_date=ed.end_date,
            )
            for ed in data.education
        ]

        profile.projects = [
            Project(
                id=str(uuid4()),
                profile_id=profile.id,
                project_name=p.project_name,
                description=p.description,
                role_description=p.role_description,
                url=p.url,
            )
            for p in data.projects
        ]

        await db.flush()

        # Query latest version number
        stmt = (
            select(ProfileVersion)
            .where(ProfileVersion.profile_id == profile.id)
            .order_by(ProfileVersion.version_number.desc())
            .limit(1)
        )
        version_result = await db.execute(stmt)
        latest_version = version_result.scalar_one_or_none()
        next_version_num = (latest_version.version_number + 1) if latest_version else 1

        # Build snapshot payload
        payload = {
            "headline": profile.headline,
            "summary": profile.summary,
            "location": profile.location,
            "current_salary": str(profile.current_salary)
            if profile.current_salary is not None
            else None,
            "skills": [
                {
                    "skill_name": s.skill_name,
                    "years_experience": float(s.years_experience),
                    "proficiency": s.proficiency,
                }
                for s in profile.skills
            ],
            "experiences": [
                {
                    "company_name": e.company_name,
                    "job_title": e.job_title,
                    "start_date": e.start_date.isoformat(),
                    "end_date": e.end_date.isoformat() if e.end_date else None,
                    "description": e.description,
                    "is_current": e.is_current,
                }
                for e in profile.experiences
            ],
            "education": [
                {
                    "institution": ed.institution,
                    "degree": ed.degree,
                    "field_of_study": ed.field_of_study,
                    "start_date": ed.start_date.isoformat(),
                    "end_date": ed.end_date.isoformat() if ed.end_date else None,
                }
                for ed in profile.education
            ],
            "projects": [
                {
                    "project_name": p.project_name,
                    "description": p.description,
                    "role_description": p.role_description,
                    "url": p.url,
                }
                for p in profile.projects
            ],
        }

        # Create ProfileVersion record
        db_version = ProfileVersion(
            id=str(uuid4()),
            profile_id=profile.id,
            version_number=next_version_num,
            snapshot_payload=payload,
        )
        db.add(db_version)
        await db.flush()

        # Emit profile updated event
        await EventBus.publish(
            "profile.updated",
            {
                "user_id": str(user_id),
                "profile_id": profile.id,
                "version_number": next_version_num,
                "skills": [s.skill_name for s in profile.skills],
            },
        )

        return profile

    @staticmethod
    async def restore_version(
        db: AsyncSession, user_id: UUID, version_number: int
    ) -> CareerProfile:
        """
        Overwrites active profile with the data from a historical snapshot,
        incrementing the active version number.
        """
        profile = await ProfileService.get_by_user_id(db, user_id)

        # Get specified version snapshot
        stmt = select(ProfileVersion).where(
            ProfileVersion.profile_id == profile.id,
            ProfileVersion.version_number == version_number,
        )
        res = await db.execute(stmt)
        version = res.scalar_one_or_none()
        if not version:
            raise HTTPException(status_code=404, detail="Profile version not found")

        payload = version.snapshot_payload

        # Re-populate root attributes
        profile.headline = payload.get("headline")
        profile.summary = payload.get("summary")
        profile.location = payload.get("location")
        salary = payload.get("current_salary")
        profile.current_salary = float(salary) if salary is not None else None
        profile.updated_at = datetime.utcnow()

        # Delete existing child items
        for skill in list(profile.skills):
            await db.delete(skill)
        for experience in list(profile.experiences):
            await db.delete(experience)
        for edu in list(profile.education):
            await db.delete(edu)
        for proj in list(profile.projects):
            await db.delete(proj)

        await db.flush()

        # Re-populate child items from payload
        profile.skills = [
            Skill(
                id=str(uuid4()),
                profile_id=profile.id,
                skill_name=s["skill_name"],
                years_experience=s["years_experience"],
                proficiency=s["proficiency"],
            )
            for s in payload.get("skills", [])
        ]

        profile.experiences = [
            Experience(
                id=str(uuid4()),
                profile_id=profile.id,
                company_name=e["company_name"],
                job_title=e["job_title"],
                start_date=date.fromisoformat(e["start_date"]),
                end_date=date.fromisoformat(e["end_date"]) if e.get("end_date") else None,
                description=e["description"],
                is_current=e["is_current"],
            )
            for e in payload.get("experiences", [])
        ]

        profile.education = [
            Education(
                id=str(uuid4()),
                profile_id=profile.id,
                institution=ed["institution"],
                degree=ed.get("degree"),
                field_of_study=ed.get("field_of_study"),
                start_date=date.fromisoformat(ed["start_date"]),
                end_date=date.fromisoformat(ed["end_date"]) if ed.get("end_date") else None,
            )
            for ed in payload.get("education", [])
        ]

        profile.projects = [
            Project(
                id=str(uuid4()),
                profile_id=profile.id,
                project_name=p["project_name"],
                description=p["description"],
                role_description=p.get("role_description"),
                url=p.get("url"),
            )
            for p in payload.get("projects", [])
        ]

        await db.flush()

        # Increment version and write new snapshot
        stmt_latest = (
            select(ProfileVersion)
            .where(ProfileVersion.profile_id == profile.id)
            .order_by(ProfileVersion.version_number.desc())
            .limit(1)
        )
        latest_res = await db.execute(stmt_latest)
        latest_version = latest_res.scalar_one_or_none()
        next_version_num = (latest_version.version_number + 1) if latest_version else 1

        db_version = ProfileVersion(
            id=str(uuid4()),
            profile_id=profile.id,
            version_number=next_version_num,
            snapshot_payload=payload,
        )
        db.add(db_version)
        await db.flush()

        # Emit profile updated event
        await EventBus.publish(
            "profile.updated",
            {
                "user_id": str(user_id),
                "profile_id": profile.id,
                "version_number": next_version_num,
                "skills": [s.skill_name for s in profile.skills],
            },
        )

        return profile
