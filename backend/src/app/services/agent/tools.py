from __future__ import annotations

from typing import Any

from app.infrastructure.database.connection import get_session
from app.infrastructure.database.repositories.resume_repository import ResumeRepository


async def get_contact_info_tool(user_id: str | None) -> dict[str, Any]:
    if not user_id:
        return {"email": None, "phone": None, "location": None}
    with get_session() as session:
        repo = ResumeRepository(session)
        profiles = repo.get_by_user(user_id)
        if not profiles:
            return {"email": None, "phone": None, "location": None}
        profile = sorted(profiles, key=lambda p: p.updated_at, reverse=True)[0]
        return {
            "email": getattr(profile, "email", None),
            "phone": getattr(profile, "phone", None),
            "location": getattr(profile, "location", None),
        }


async def get_projects_tool(user_id: str | None) -> list[dict[str, Any]]:
    if not user_id:
        return []
    with get_session() as session:
        repo = ResumeRepository(session)
        profiles = repo.get_by_user(user_id)
        if not profiles:
            return []
        profile = sorted(profiles, key=lambda p: p.updated_at, reverse=True)[0]
        raw = getattr(profile, "raw_data", {}) or {}
        projects = raw.get("projects") or []
        return [p for p in projects if isinstance(p, dict)]
