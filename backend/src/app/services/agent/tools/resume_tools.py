"""Resume-specific tools for the agent."""

from __future__ import annotations

from typing import Any

from app.infrastructure.database.connection import get_session
from app.infrastructure.database.repositories.resume_repository import ResumeRepository


async def get_contact_info_tool(user_id: str | None) -> dict[str, Any]:
    """Get user's contact information including email, phone, and location."""
    if not user_id:
        return {"error": "User ID is required to fetch contact info."}

    with get_session() as session:
        repo = ResumeRepository(session)
        profiles = repo.get_by_user(user_id)
        if not profiles:
            return {"error": "No resume profile found for this user."}

        profile = sorted(profiles, key=lambda p: p.updated_at, reverse=True)[0]
        return {
            "email": getattr(profile, "email", None),
            "phone": getattr(profile, "phone", None),
            "location": getattr(profile, "location", None),
            "name": getattr(profile, "name", None),
        }


async def get_skills_tool(user_id: str | None) -> dict[str, Any]:
    """Get user's technical skills and competencies."""
    if not user_id:
        return {"error": "User ID is required to fetch skills."}

    with get_session() as session:
        repo = ResumeRepository(session)
        profiles = repo.get_by_user(user_id)
        if not profiles:
            return {"error": "No resume profile found for this user."}

        profile = sorted(profiles, key=lambda p: p.updated_at, reverse=True)[0]
        raw_data = getattr(profile, "raw_data", {}) or {}
        skills = raw_data.get("skills", {})

        return {
            "languages": skills.get("languages", []),
            "frameworks": skills.get("frameworks", []),
            "tools": skills.get("tools", []),
            "total_skills": len(skills.get("languages", []))
            + len(skills.get("frameworks", []))
            + len(skills.get("tools", [])),
        }


async def get_experience_tool(user_id: str | None) -> list[dict[str, Any]]:
    """Get user's work experience."""
    if not user_id:
        return [{"error": "User ID is required to fetch experience."}]

    with get_session() as session:
        repo = ResumeRepository(session)
        profiles = repo.get_by_user(user_id)
        if not profiles:
            return [{"error": "No resume profile found for this user."}]

        profile = sorted(profiles, key=lambda p: p.updated_at, reverse=True)[0]
        raw_data = getattr(profile, "raw_data", {}) or {}
        experience = raw_data.get("experience", [])

        return [exp for exp in experience if isinstance(exp, dict)]


async def get_education_tool(user_id: str | None) -> list[dict[str, Any]]:
    """Get user's educational background."""
    if not user_id:
        return [{"error": "User ID is required to fetch education."}]

    with get_session() as session:
        repo = ResumeRepository(session)
        profiles = repo.get_by_user(user_id)
        if not profiles:
            return [{"error": "No resume profile found for this user."}]

        profile = sorted(profiles, key=lambda p: p.updated_at, reverse=True)[0]
        raw_data = getattr(profile, "raw_data", {}) or {}
        education = raw_data.get("education", [])

        return [edu for edu in education if isinstance(edu, dict)]


async def get_projects_tool(user_id: str | None) -> list[dict[str, Any]]:
    """Get user's projects and portfolio."""
    if not user_id:
        return [{"error": "User ID is required to fetch projects."}]

    with get_session() as session:
        repo = ResumeRepository(session)
        profiles = repo.get_by_user(user_id)
        if not profiles:
            return [{"error": "No resume profile found for this user."}]

        profile = sorted(profiles, key=lambda p: p.updated_at, reverse=True)[0]
        raw_data = getattr(profile, "raw_data", {}) or {}
        projects = raw_data.get("projects", [])

        return [proj for proj in projects if isinstance(proj, dict)]


async def get_achievements_tool(user_id: str | None) -> list[dict[str, Any]]:
    """Get user's achievements and awards."""
    if not user_id:
        return [{"error": "User ID is required to fetch achievements."}]

    with get_session() as session:
        repo = ResumeRepository(session)
        profiles = repo.get_by_user(user_id)
        if not profiles:
            return [{"error": "No resume profile found for this user."}]

        profile = sorted(profiles, key=lambda p: p.updated_at, reverse=True)[0]
        raw_data = getattr(profile, "raw_data", {}) or {}
        achievements = raw_data.get("achievements", [])

        return [ach for ach in achievements if isinstance(ach, dict)]


async def get_co_curricular_tool(user_id: str | None) -> list[dict[str, Any]]:
    """Get user's co-curricular activities."""
    if not user_id:
        return [{"error": "User ID is required to fetch co-curricular activities."}]

    with get_session() as session:
        repo = ResumeRepository(session)
        profiles = repo.get_by_user(user_id)
        if not profiles:
            return [{"error": "No resume profile found for this user."}]

        profile = sorted(profiles, key=lambda p: p.updated_at, reverse=True)[0]
        raw_data = getattr(profile, "raw_data", {}) or {}
        co_curricular = raw_data.get("coCurricular", [])

        return [activity for activity in co_curricular if isinstance(activity, dict)]


async def get_summary_tool(user_id: str | None) -> dict[str, Any]:
    """Get user's professional summary."""
    if not user_id:
        return {"error": "User ID is required to fetch summary."}

    with get_session() as session:
        repo = ResumeRepository(session)
        profiles = repo.get_by_user(user_id)
        if not profiles:
            return {"error": "No resume profile found for this user."}

        profile = sorted(profiles, key=lambda p: p.updated_at, reverse=True)[0]
        summary = getattr(profile, "summary", None)
        raw_data = getattr(profile, "raw_data", {}) or {}

        return {
            "summary": summary,
            "name": getattr(profile, "name", None),
            "email": getattr(profile, "email", None),
        }
