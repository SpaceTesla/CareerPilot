"""Comprehensive analysis service for resume evaluation."""

from __future__ import annotations

import asyncio
from typing import Any

from app.services.agent.tools.analysis_tools import (
    analyze_resume_strengths_tool,
    get_resume_metrics_tool,
    suggest_improvements_tool,
)


class AnalysisService:
    """Service for comprehensive resume analysis."""

    async def get_overview(self, user_id: str | None) -> dict[str, Any]:
        """Get complete analysis overview including scores, strengths, and weaknesses."""
        if not user_id:
            return {"error": "User ID is required"}

        # Run all analysis tools in parallel for faster response
        strengths_analysis, improvements, metrics = await asyncio.gather(
            analyze_resume_strengths_tool(user_id),
            suggest_improvements_tool(user_id),
            get_resume_metrics_tool(user_id),
        )

        if "error" in strengths_analysis:
            return strengths_analysis

        # Calculate grade from overall score
        # Ensure score is between 0-1, then multiply by 100 and cap at 100
        raw_score = strengths_analysis.get("overall_score", 0)
        # If score is already > 1, it's likely already in 0-100 scale, otherwise it's 0-1
        if raw_score > 1:
            overall_score = min(raw_score, 100)
        else:
            overall_score = min(raw_score * 100, 100)
        
        grade = self._calculate_grade(overall_score)

        return {
            "overall_score": round(overall_score, 1),
            "grade": grade,
            "strengths": strengths_analysis.get("strengths", []),
            "weaknesses": strengths_analysis.get("areas_for_improvement", []),
            "section_analysis": strengths_analysis.get("section_analysis", {}),
            "improvements": improvements,
            "metrics": metrics,
        }

    async def get_overview_for_profile(self, profile_id: str | None) -> dict[str, Any]:
        """Get analysis overview for a specific profile ID."""
        if not profile_id:
            return {"error": "Profile ID is required"}

        from app.infrastructure.database.connection import get_session
        from app.infrastructure.database.repositories.resume_repository import ResumeRepository

        # Get profile to find the user_id
        with get_session() as session:
            repo = ResumeRepository(session)
            profile = repo.get_by_id(profile_id)
            if not profile:
                return {"error": "Profile not found"}
            user_id = profile.user_id

        # Use the regular overview method with the user_id
        # Note: This assumes the tools will work with this user_id
        # For a more accurate per-profile analysis, tools would need to be updated
        # to accept profile_id directly. For now, we'll use a simplified approach.
        
        from app.services.agent.tools.analysis_tools import (
            analyze_resume_strengths_for_profile_tool,
        )

        try:
            strengths_analysis = await analyze_resume_strengths_for_profile_tool(profile_id)
            if "error" in strengths_analysis:
                return strengths_analysis

            raw_score = strengths_analysis.get("overall_score", 0)
            if raw_score > 1:
                overall_score = min(raw_score, 100)
            else:
                overall_score = min(raw_score * 100, 100)
            
            grade = self._calculate_grade(overall_score)

            return {
                "overall_score": round(overall_score, 1),
                "grade": grade,
                "strengths": strengths_analysis.get("strengths", []),
                "weaknesses": strengths_analysis.get("areas_for_improvement", []),
            }
        except Exception as e:
            return {"error": f"Analysis failed: {str(e)}"}

    def _calculate_grade(self, score: float) -> str:
        """Calculate letter grade from score (0-100)."""
        if score >= 90:
            return "A"
        elif score >= 80:
            return "B"
        elif score >= 70:
            return "C"
        elif score >= 60:
            return "D"
        else:
            return "F"

    async def get_ats_score(self, user_id: str | None) -> dict[str, Any]:
        """Get ATS optimization score and keyword analysis."""
        if not user_id:
            return {"error": "User ID is required"}

        metrics = await get_resume_metrics_tool(user_id)
        improvements = await suggest_improvements_tool(user_id)

        if "error" in metrics:
            return metrics

        # Calculate ATS score based on various factors
        ats_score = self._calculate_ats_score(metrics, improvements)

        # Extract keywords suggestions
        keywords = self._extract_keyword_suggestions(improvements)

        return {
            "ats_score": ats_score,
            "keyword_suggestions": keywords,
            "optimization_tips": improvements.get("ats_optimization", []),
        }

    def _calculate_ats_score(self, metrics: dict[str, Any], improvements: dict[str, Any]) -> float:
        """Calculate ATS optimization score (0-100)."""
        score = 50.0  # Base score

        # Completeness contributes to ATS score
        completeness = metrics.get("completeness_scores", {}).get("contact_info", 0)
        score += (completeness / 100) * 20

        # Skills diversity
        total_skills = metrics.get("diversity_metrics", {}).get("total_skills", 0)
        if total_skills >= 10:
            score += 15
        elif total_skills >= 5:
            score += 10

        # Word count (optimal is 400-600 words)
        word_count = metrics.get("word_count", 0)
        if 400 <= word_count <= 600:
            score += 15
        elif 300 <= word_count < 400 or 600 < word_count <= 800:
            score += 10

        # Penalize for priority improvements
        priority_count = len(improvements.get("priority_improvements", []))
        score -= priority_count * 5

        return min(max(score, 0), 100)

    def _extract_keyword_suggestions(self, improvements: dict[str, Any]) -> list[str]:
        """Extract keyword suggestions from improvements."""
        keywords = []
        content_suggestions = improvements.get("content_suggestions", [])
        for suggestion in content_suggestions:
            text = suggestion.get("suggestion", "").lower()
            # Extract potential keywords (simplified)
            if "keyword" in text or "skill" in text:
                keywords.append(suggestion.get("section", ""))
        return keywords

    async def get_skills_gap(self, user_id: str | None, target_role: str | None = None) -> dict[str, Any]:
        """Analyze skills gap for target role using hybrid exact + semantic scoring."""
        if not user_id:
            return {"error": "User ID is required"}

        from app.services.agent.tools.resume_tools import get_skills_tool
        from app.services.role_embeddings import compute_semantic_gap_score, get_role_requirements

        skills_data = await get_skills_tool(user_id)
        if "error" in skills_data:
            return skills_data

        current_skills: list[str] = []
        current_skills.extend(skills_data.get("languages", []))
        current_skills.extend(skills_data.get("frameworks", []))
        current_skills.extend(skills_data.get("tools", []))

        role_requirements = get_role_requirements(target_role)
        current_set = set(current_skills)
        required_skills = set(role_requirements.get("required", []))
        recommended_skills = set(role_requirements.get("recommended", []))

        missing_required = required_skills - current_set
        missing_recommended = recommended_skills - current_set
        matching_skills = current_set & (required_skills | recommended_skills)

        # Retrieve stored skills embedding from the profile (if available)
        resume_embedding: list[float] | None = None
        try:
            from app.infrastructure.database.connection import get_session
            from app.infrastructure.database.repositories.resume_repository import ResumeRepository

            with get_session() as session:
                repo = ResumeRepository(session)
                profiles = repo.get_by_user(user_id)
                if profiles:
                    profile = sorted(profiles, key=lambda p: p.updated_at, reverse=True)[0]
                    stored = getattr(profile, "skills_embedding", None)
                    if stored is not None and isinstance(stored, list):
                        resume_embedding = stored
        except Exception:
            pass

        # Semantic gap score (falls back to exact if embeddings not available)
        gap_score = await compute_semantic_gap_score(
            current_skills, target_role, resume_embedding
        )

        return {
            "target_role": target_role or "General",
            "current_skills": list(current_set),
            "missing_required": list(missing_required),
            "missing_recommended": list(missing_recommended),
            "matching_skills": list(matching_skills),
            "gap_score": gap_score,
            "recommendations": list(missing_required)[:5],
        }

    def _get_role_requirements(self, role: str | None) -> dict[str, list[str]]:
        """Get skill requirements for a specific role. Delegates to role_embeddings module."""
        from app.services.role_embeddings import get_role_requirements
        return get_role_requirements(role)

    async def get_job_match(self, user_id: str | None, role: str | None = None) -> dict[str, Any]:
        """Get job matching score for specific role."""
        if not user_id:
            return {"error": "User ID is required"}

        skills_gap = await self.get_skills_gap(user_id, role)
        strengths = await analyze_resume_strengths_tool(user_id)

        if "error" in skills_gap:
            return skills_gap

        # Calculate match score
        gap_score = skills_gap.get("gap_score", 0)
        raw_score = strengths.get("overall_score", 0)
        # Ensure score is capped at 100
        if raw_score > 1:
            overall_score = min(raw_score, 100)
        else:
            overall_score = min(raw_score * 100, 100)

        # Weighted match score
        match_score = (gap_score * 0.6) + (overall_score * 0.4)

        return {
            "role": role or "General",
            "match_score": round(match_score, 1),
            "skills_match": round(gap_score, 1),
            "resume_quality": round(overall_score, 1),
            "missing_skills": skills_gap.get("missing_required", [])[:5],
            "recommendations": skills_gap.get("recommendations", []),
        }

    async def get_career_path(self, user_id: str | None) -> dict[str, Any]:
        """Get career path recommendations based on current profile."""
        if not user_id:
            return {"error": "User ID is required"}

        from app.services.agent.tools.resume_tools import (
            get_experience_tool,
            get_skills_tool,
        )

        skills_data = await get_skills_tool(user_id)
        experience_data = await get_experience_tool(user_id)

        if "error" in skills_data:
            return skills_data

        # Determine current role focus
        current_focus = self._determine_role_focus(skills_data, experience_data)

        # Generate career progression paths
        career_paths = self._generate_career_paths(current_focus, skills_data, experience_data)

        return {
            "current_focus": current_focus,
            "career_paths": career_paths,
            "next_steps": self._get_next_steps(current_focus, skills_data),
        }

    def _determine_role_focus(
        self, skills_data: dict[str, Any], experience_data: list[dict[str, Any]]
    ) -> str:
        """Determine primary role focus from skills and experience."""
        all_skills = []
        all_skills.extend(skills_data.get("languages", []))
        all_skills.extend(skills_data.get("frameworks", []))
        all_skills.extend(skills_data.get("tools", []))

        skills_text = " ".join([s.lower() for s in all_skills])

        backend_indicators = ["python", "java", "backend", "api", "database", "sql", "django", "flask"]
        frontend_indicators = ["react", "javascript", "frontend", "ui", "css", "html", "vue", "angular"]
        devops_indicators = ["docker", "kubernetes", "ci/cd", "aws", "devops", "terraform"]

        backend_score = sum(1 for ind in backend_indicators if ind in skills_text)
        frontend_score = sum(1 for ind in frontend_indicators if ind in skills_text)
        devops_score = sum(1 for ind in devops_indicators if ind in skills_text)

        if backend_score >= frontend_score and backend_score >= devops_score:
            return "Backend Developer"
        elif frontend_score >= devops_score:
            return "Frontend Developer"
        elif devops_score > 0:
            return "DevOps Engineer"
        else:
            return "Software Developer"

    def _generate_career_paths(
        self, current_focus: str, skills_data: dict[str, Any], experience_data: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Generate career progression paths."""
        paths = []

        if "Backend" in current_focus:
            paths.append({
                "title": "Senior Backend Developer",
                "timeline": "2-3 years",
                "required_skills": ["System Design", "Microservices", "Cloud Architecture"],
                "description": "Focus on scalable systems and architecture",
            })
            paths.append({
                "title": "Full-Stack Developer",
                "timeline": "1-2 years",
                "required_skills": ["React", "Frontend Fundamentals", "API Design"],
                "description": "Expand to frontend technologies",
            })

        elif "Frontend" in current_focus:
            paths.append({
                "title": "Senior Frontend Developer",
                "timeline": "2-3 years",
                "required_skills": ["Advanced React", "Performance Optimization", "Accessibility"],
                "description": "Master frontend architecture and optimization",
            })
            paths.append({
                "title": "Full-Stack Developer",
                "timeline": "1-2 years",
                "required_skills": ["Node.js", "Backend Fundamentals", "Database Design"],
                "description": "Add backend capabilities",
            })

        else:
            paths.append({
                "title": "Senior Software Developer",
                "timeline": "2-3 years",
                "required_skills": ["System Design", "Leadership", "Architecture"],
                "description": "Advance to senior level with broader responsibilities",
            })

        return paths

    def _get_next_steps(self, current_focus: str, skills_data: dict[str, Any]) -> list[str]:
        """Get actionable next steps."""
        steps = []
        total_skills = (
            len(skills_data.get("languages", []))
            + len(skills_data.get("frameworks", []))
            + len(skills_data.get("tools", []))
        )

        if total_skills < 10:
            steps.append("Expand your technical skills portfolio")
        if "Backend" in current_focus:
            steps.append("Learn system design and architecture patterns")
            steps.append("Gain experience with cloud platforms (AWS/GCP/Azure)")
        elif "Frontend" in current_focus:
            steps.append("Master performance optimization techniques")
            steps.append("Learn advanced state management patterns")

        steps.append("Build 2-3 substantial projects showcasing your skills")
        steps.append("Contribute to open-source projects")

        return steps


# Singleton instance
analysis_service = AnalysisService()


