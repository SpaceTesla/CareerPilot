"""ATS (Applicant Tracking System) optimization service with LLM semantic analysis."""

from __future__ import annotations

import asyncio
from typing import Any

from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI

from app.core.config import settings
from app.infrastructure.database.connection import get_session
from app.infrastructure.database.repositories.resume_repository import ResumeRepository


class ATSService:
    """Service for ATS optimization and keyword analysis with LLM-powered semantic matching."""

    def __init__(self) -> None:
        self.llm = ChatGoogleGenerativeAI(
            model=settings.model_name,
            temperature=0.3,
        )

    async def get_ats_score(self, user_id: str | None) -> dict[str, Any]:
        """Get comprehensive ATS optimization score with LLM semantic analysis."""
        if not user_id:
            return {"error": "User ID is required"}

        with get_session() as session:
            repo = ResumeRepository(session)
            profiles = repo.get_by_user(user_id)
            if not profiles:
                return {"error": "No resume profile found for this user."}

            profile = sorted(profiles, key=lambda p: p.updated_at, reverse=True)[0]
            raw_data = getattr(profile, "raw_data", {}) or {}

            # Extract all profile attributes INSIDE session to avoid detached instance error
            profile_data = {
                "name": getattr(profile, "name", None),
                "email": getattr(profile, "email", None),
                "phone": getattr(profile, "phone", None),
                "location": getattr(profile, "location", None),
                "summary": getattr(profile, "summary", None) or raw_data.get("summary", ""),
            }

        # Run basic scoring and LLM analysis in parallel
        basic_score_task = self._calculate_basic_ats_score(raw_data, profile_data)
        llm_analysis_task = self._get_llm_ats_analysis(raw_data, profile_data)

        basic_result, llm_result = await asyncio.gather(
            basic_score_task,
            llm_analysis_task,
        )

        # Combine scores: 40% basic metrics + 60% LLM semantic analysis
        combined_score = (basic_result["score"] * 0.4) + (llm_result.get("semantic_score", 50) * 0.6)

        return {
            "ats_score": round(min(combined_score, 100), 1),
            "keyword_suggestions": llm_result.get("keyword_suggestions", []),
            "optimization_tips": llm_result.get("optimization_tips", []),
            "semantic_analysis": llm_result.get("analysis_summary", ""),
            "format_score": basic_result.get("format_score", 0),
            "content_score": basic_result.get("content_score", 0),
            "keyword_density": basic_result.get("keyword_density", 0),
        }

    async def _calculate_basic_ats_score(
        self, raw_data: dict[str, Any], profile_data: dict[str, Any]
    ) -> dict[str, Any]:
        """Calculate basic ATS metrics without LLM."""
        score = 50.0
        format_score = 0
        content_score = 0

        # Contact info completeness (15 points)
        contact_fields = ["email", "phone", "location"]
        contact_count = sum(1 for f in contact_fields if profile_data.get(f))
        contact_score = (contact_count / len(contact_fields)) * 15
        format_score += contact_score
        score += contact_score

        # Skills section (20 points)
        skills = raw_data.get("skills", {})
        total_skills = (
            len(skills.get("languages", []))
            + len(skills.get("frameworks", []))
            + len(skills.get("tools", []))
        )
        skills_score = min(total_skills / 10, 1) * 20
        content_score += skills_score
        score += skills_score

        # Experience with action verbs (15 points)
        experience = raw_data.get("experience", [])
        action_verbs = ["developed", "implemented", "designed", "managed", "led", "created", "built", "optimized", "improved", "achieved"]
        exp_text = " ".join(
            str(detail).lower()
            for exp in experience
            for detail in exp.get("details", [])
        )
        verb_count = sum(1 for verb in action_verbs if verb in exp_text)
        exp_score = min(verb_count / 5, 1) * 15
        content_score += exp_score

        # Word count (optimal 400-700) - 10 points
        text_content = str(raw_data)
        word_count = len(text_content.split())
        if 400 <= word_count <= 700:
            word_score = 10
        elif 300 <= word_count < 400 or 700 < word_count <= 900:
            word_score = 7
        else:
            word_score = 4
        format_score += word_score

        # Section headers present (10 points)
        sections = ["experience", "education", "skills", "projects"]
        present_sections = sum(1 for s in sections if raw_data.get(s))
        section_score = (present_sections / len(sections)) * 10
        format_score += section_score

        keyword_density = round((total_skills + verb_count) / max(word_count / 100, 1), 2)

        return {
            "score": min(score, 100),
            "format_score": round(format_score, 1),
            "content_score": round(content_score, 1),
            "keyword_density": keyword_density,
        }

    async def _get_llm_ats_analysis(
        self, raw_data: dict[str, Any], profile_data: dict[str, Any]
    ) -> dict[str, Any]:
        """Use LLM for semantic ATS analysis."""
        try:
            # Build resume summary for LLM
            skills = raw_data.get("skills", {})
            experience = raw_data.get("experience", [])
            summary = profile_data.get("summary", "")

            resume_summary = f"""
Resume Summary:
- Name: {profile_data.get('name', 'Unknown')}
- Summary: {summary[:500] if summary else 'Not provided'}
- Skills: Languages: {', '.join(skills.get('languages', [])[:10])}, Frameworks: {', '.join(skills.get('frameworks', [])[:10])}, Tools: {', '.join(skills.get('tools', [])[:10])}
- Experience: {len(experience)} positions
- Recent Role: {experience[0].get('role', 'N/A') if experience else 'N/A'} at {experience[0].get('company', 'N/A') if experience else 'N/A'}
"""

            prompt = ChatPromptTemplate.from_messages([
                ("system", """You are an expert ATS (Applicant Tracking System) analyzer. Analyze the resume and provide:
1. A semantic score (0-100) based on how well the resume would perform in ATS systems
2. 5-8 specific keyword suggestions that are commonly searched by recruiters but missing from this resume
3. 3-5 actionable optimization tips to improve ATS compatibility

Consider:
- Industry-standard terminology and buzzwords
- Quantifiable achievements and metrics
- Technical skills alignment with job market trends
- Proper formatting for ATS parsing
- Semantic relevance of content

Respond in JSON format:
{{"semantic_score": <number>, "keyword_suggestions": [<string>], "optimization_tips": [<string>], "analysis_summary": "<brief summary>"}}"""),
                ("user", "{resume}")
            ])

            chain = prompt | self.llm
            response = await chain.ainvoke({"resume": resume_summary})

            # Parse LLM response
            import json
            import re
            
            content = response.content
            # Extract JSON from response
            json_match = re.search(r'\{[\s\S]*\}', str(content))
            if json_match:
                result = json.loads(json_match.group())
                return result
            
            return {
                "semantic_score": 60,
                "keyword_suggestions": [],
                "optimization_tips": ["Unable to analyze - please try again"],
                "analysis_summary": "Analysis incomplete"
            }

        except Exception as e:
            # Fallback if LLM fails
            return {
                "semantic_score": 55,
                "keyword_suggestions": [
                    "Agile/Scrum methodology",
                    "Cross-functional collaboration", 
                    "Performance optimization",
                    "System design",
                    "CI/CD pipelines"
                ],
                "optimization_tips": [
                    "Add quantifiable achievements with metrics",
                    "Include industry-standard terminology",
                    "Use action verbs at the start of bullet points"
                ],
                "analysis_summary": f"Basic analysis applied (LLM unavailable: {str(e)[:50]})"
            }

    async def get_missing_keywords(
        self, user_id: str | None, target_role: str | None = None
    ) -> dict[str, Any]:
        """Get missing keywords for ATS optimization."""
        if not user_id:
            return {"error": "User ID is required"}

        from app.services.agent.tools.resume_tools import get_skills_tool
        from app.services.analysis_service import analysis_service

        skills_data = await get_skills_tool(user_id)
        if "error" in skills_data:
            return skills_data

        # Get role requirements
        role_requirements = analysis_service._get_role_requirements(target_role)

        current_skills = set()
        current_skills.update(skills_data.get("languages", []))
        current_skills.update(skills_data.get("frameworks", []))
        current_skills.update(skills_data.get("tools", []))

        # Normalize for comparison
        current_skills_lower = {s.lower() for s in current_skills}

        required_skills = set(role_requirements.get("required", []))
        recommended_skills = set(role_requirements.get("recommended", []))

        missing_required = {s for s in required_skills if s.lower() not in current_skills_lower}
        missing_recommended = {s for s in recommended_skills if s.lower() not in current_skills_lower}

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
            "Performance Optimization",
            "System Design",
        ]

        # Check which common keywords are missing
        missing_common = [kw for kw in common_keywords if kw.lower() not in " ".join([s.lower() for s in current_skills])]

        return {
            "missing_technical": list(missing_required | missing_recommended),
            "missing_common": missing_common[:5],
            "recommended_keywords": list(missing_required)[:5] + list(missing_recommended)[:5],
        }


# Singleton instance
ats_service = ATSService()


