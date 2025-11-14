"""Interview preparation service."""

from __future__ import annotations

from typing import Any

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI

from app.core.config import settings
from app.infrastructure.database.connection import get_session
from app.infrastructure.database.repositories.resume_repository import ResumeRepository
from app.services.agent.tools.resume_tools import (
    get_achievements_tool,
    get_education_tool,
    get_experience_tool,
    get_projects_tool,
    get_skills_tool,
)


class InterviewService:
    """Service for interview preparation and question generation."""

    def __init__(self) -> None:
        self.llm = ChatGoogleGenerativeAI(
            model=settings.model_name,
            temperature=0.7,  # Slightly higher for more creative responses
        )

    def _load_resume_context(self, user_id: str | None) -> dict[str, Any]:
        """Load resume context for interview prep."""
        if not user_id:
            return {}

        with get_session() as session:
            repo = ResumeRepository(session)
            profiles = repo.get_by_user(user_id)
            if not profiles:
                return {}

            profile = sorted(profiles, key=lambda p: p.updated_at, reverse=True)[0]
            raw_data = getattr(profile, "raw_data", {}) or {}

            return {
                "name": getattr(profile, "name", ""),
                "summary": getattr(profile, "summary", ""),
                "experience": raw_data.get("experience", []),
                "education": raw_data.get("education", []),
                "projects": raw_data.get("projects", []),
                "skills": raw_data.get("skills", {}),
            }

    async def get_prep_tips(self, user_id: str | None, role: str | None = None) -> dict[str, Any]:
        """Get interview preparation tips."""
        if not user_id:
            return {"error": "User ID is required"}

        context = self._load_resume_context(user_id)
        if not context:
            return {"error": "No resume found"}

        # Build context summary
        experience_summary = f"{len(context.get('experience', []))} positions"
        skills_summary = ", ".join(
            context.get("skills", {}).get("languages", [])[:5]
        )

        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are an expert career coach helping with interview preparation."),
            ("user", f"""Based on this resume profile:
- Experience: {experience_summary}
- Key Skills: {skills_summary}
- Target Role: {role or 'General Software Developer'}

Provide comprehensive interview preparation tips including:
1. Common questions to expect
2. How to highlight relevant experience
3. Technical topics to review
4. Questions to ask the interviewer
5. Red flags to address

Format as a structured list with actionable advice."""),
        ])

        chain = prompt | self.llm | StrOutputParser()

        try:
            tips = await chain.ainvoke({})
            return {
                "role": role or "General",
                "tips": tips,
                "preparation_checklist": self._generate_checklist(context, role),
            }
        except Exception as e:
            return {"error": f"Failed to generate tips: {str(e)}"}

    def _generate_checklist(self, context: dict[str, Any], role: str | None) -> list[str]:
        """Generate interview preparation checklist."""
        checklist = [
            "Review your resume and be ready to discuss each experience",
            "Prepare STAR method examples for behavioral questions",
            "Research the company and role thoroughly",
            "Prepare 3-5 thoughtful questions to ask the interviewer",
        ]

        if context.get("projects"):
            checklist.append("Be ready to explain your projects in detail")
        if context.get("skills", {}).get("languages"):
            checklist.append("Review key programming concepts and languages")
        if role:
            checklist.append(f"Study role-specific technical requirements for {role}")

        return checklist

    async def get_questions(self, user_id: str | None) -> dict[str, Any]:
        """Get common interview questions based on resume."""
        if not user_id:
            return {"error": "User ID is required"}

        # Load resume data
        skills_data = await get_skills_tool(user_id)
        experience_data = await get_experience_tool(user_id)
        projects_data = await get_projects_tool(user_id)
        education_data = await get_education_tool(user_id)

        if "error" in skills_data:
            return skills_data

        # Build context
        context_parts = []
        if experience_data and not isinstance(experience_data, dict):
            context_parts.append(f"Work experience: {len(experience_data)} positions")
        if projects_data and not isinstance(projects_data, dict):
            context_parts.append(f"Projects: {len(projects_data)} projects")
        if skills_data and not isinstance(skills_data, dict):
            languages = skills_data.get("languages", [])
            if languages:
                context_parts.append(f"Programming languages: {', '.join(languages[:5])}")

        context_str = ". ".join(context_parts)

        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are an expert interviewer. Generate relevant interview questions."),
            ("user", f"""Based on this candidate profile:
{context_str}

Generate 10 interview questions including:
- 3-4 technical questions relevant to their skills
- 3-4 behavioral questions using STAR method
- 2-3 questions about their projects/experience

Format each question clearly and indicate the type (Technical/Behavioral/Project)."""),
        ])

        chain = prompt | self.llm | StrOutputParser()

        try:
            questions_text = await chain.ainvoke({})
            return {
                "questions": questions_text,
                "categories": ["Technical", "Behavioral", "Projects"],
                "total_questions": 10,
            }
        except Exception as e:
            return {"error": f"Failed to generate questions: {str(e)}"}

    async def get_star_examples(self, user_id: str | None) -> dict[str, Any]:
        """Get STAR method examples from user's experience."""
        if not user_id:
            return {"error": "User ID is required"}

        experience_data = await get_experience_tool(user_id)
        projects_data = await get_projects_tool(user_id)

        if "error" in experience_data:
            return experience_data

        examples = []

        # Extract from experience
        if experience_data and isinstance(experience_data, list):
            for exp in experience_data[:3]:
                if isinstance(exp, dict) and exp.get("details"):
                    examples.append({
                        "situation": exp.get("role", "Work Experience"),
                        "task": exp.get("company", ""),
                        "action": exp.get("details", [])[0] if exp.get("details") else "",
                        "result": "Achieved project goals and demonstrated skills",
                    })

        # Extract from projects
        if projects_data and isinstance(projects_data, list):
            for proj in projects_data[:2]:
                if isinstance(proj, dict):
                    examples.append({
                        "situation": proj.get("name", "Project"),
                        "task": "Develop and deliver project",
                        "action": proj.get("details", [])[0] if proj.get("details") else "",
                        "result": "Successfully completed project",
                    })

        return {
            "examples": examples,
            "total": len(examples),
            "format": "STAR (Situation, Task, Action, Result)",
        }


# Singleton instance
interview_service = InterviewService()


