"""ATS (Applicant Tracking System) optimization service."""

from __future__ import annotations

from typing import Any

from app.services.analysis_service import analysis_service


class ATSService:
    """Service for ATS optimization and keyword analysis."""

    async def get_ats_score(self, user_id: str | None) -> dict[str, Any]:
        """Get ATS optimization score."""
        return await analysis_service.get_ats_score(user_id)

    async def get_missing_keywords(
        self, user_id: str | None, target_role: str | None = None
    ) -> dict[str, Any]:
        """Get missing keywords for ATS optimization."""
        if not user_id:
            return {"error": "User ID is required"}

        from app.services.agent.tools.resume_tools import get_skills_tool

        skills_data = await get_skills_tool(user_id)
        if "error" in skills_data:
            return skills_data

        # Get role requirements
        role_requirements = analysis_service._get_role_requirements(target_role)

        current_skills = set()
        current_skills.update(skills_data.get("languages", []))
        current_skills.update(skills_data.get("frameworks", []))
        current_skills.update(skills_data.get("tools", []))

        required_skills = set(role_requirements.get("required", []))
        recommended_skills = set(role_requirements.get("recommended", []))

        missing_keywords = (required_skills | recommended_skills) - current_skills

        # Common ATS keywords
        common_keywords = [
            "Problem Solving",
            "Team Collaboration",
            "Agile",
            "Scrum",
            "Version Control",
            "Code Review",
            "Testing",
            "Documentation",
        ]

        # Check which common keywords are missing
        missing_common = [kw for kw in common_keywords if kw.lower() not in " ".join([s.lower() for s in current_skills])]

        return {
            "missing_technical": list(missing_keywords),
            "missing_common": missing_common[:5],
            "recommended_keywords": list(missing_keywords)[:10],
        }


# Singleton instance
ats_service = ATSService()


