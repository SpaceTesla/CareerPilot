"""Analysis tools for resume insights and recommendations."""

from __future__ import annotations

from typing import Any

from app.infrastructure.database.connection import get_session
from app.infrastructure.database.repositories.resume_repository import ResumeRepository


async def analyze_resume_strengths_tool(user_id: str | None) -> dict[str, Any]:
    """Analyze resume strengths and provide insights."""
    if not user_id:
        return {"error": "User ID is required to analyze resume."}

    with get_session() as session:
        repo = ResumeRepository(session)
        profiles = repo.get_by_user(user_id)
        if not profiles:
            return {"error": "No resume profile found for this user."}

        profile = sorted(profiles, key=lambda p: p.updated_at, reverse=True)[0]
        raw_data = getattr(profile, "raw_data", {}) or {}

        # Analyze different sections
        analysis = {
            "overall_score": 0,
            "strengths": [],
            "areas_for_improvement": [],
            "section_analysis": {},
        }

        # Contact Information Analysis
        contact_info = {
            "email": getattr(profile, "email", None),
            "phone": getattr(profile, "phone", None),
            "location": getattr(profile, "location", None),
        }
        contact_score = sum(1 for v in contact_info.values() if v)
        analysis["section_analysis"]["contact"] = {
            "score": contact_score,
            "max_score": 3,
            "completeness": f"{(contact_score / 3) * 100:.1f}%",
        }

        # Skills Analysis
        skills = raw_data.get("skills", {})
        total_skills = (
            len(skills.get("languages", []))
            + len(skills.get("frameworks", []))
            + len(skills.get("tools", []))
        )
        skills_score = min(total_skills / 10, 1)  # Normalize to 0-1
        analysis["section_analysis"]["skills"] = {
            "score": skills_score,
            "total_skills": total_skills,
            "breakdown": {
                "languages": len(skills.get("languages", [])),
                "frameworks": len(skills.get("frameworks", [])),
                "tools": len(skills.get("tools", [])),
            },
        }

        # Experience Analysis
        experience = raw_data.get("experience", [])
        exp_score = min(len(experience) / 3, 1)  # Normalize to 0-1
        analysis["section_analysis"]["experience"] = {
            "score": exp_score,
            "total_positions": len(experience),
            "has_details": sum(1 for exp in experience if exp.get("details")),
        }

        # Projects Analysis
        projects = raw_data.get("projects", [])
        proj_score = min(len(projects) / 2, 1)  # Normalize to 0-1
        analysis["section_analysis"]["projects"] = {
            "score": proj_score,
            "total_projects": len(projects),
            "has_tech_stack": sum(1 for proj in projects if proj.get("tech_stack")),
        }

        # Education Analysis
        education = raw_data.get("education", [])
        edu_score = min(len(education) / 2, 1)  # Normalize to 0-1
        analysis["section_analysis"]["education"] = {
            "score": edu_score,
            "total_degrees": len(education),
            "has_gpa": sum(1 for edu in education if edu.get("gpa")),
        }

        # Calculate overall score
        section_scores = [
            analysis["section_analysis"][section]["score"]
            for section in analysis["section_analysis"]
        ]
        analysis["overall_score"] = (
            sum(section_scores) / len(section_scores) if section_scores else 0
        )

        # Generate strengths and improvements
        if contact_score >= 2:
            analysis["strengths"].append("Complete contact information")
        if total_skills >= 5:
            analysis["strengths"].append("Strong technical skills profile")
        if len(experience) >= 2:
            analysis["strengths"].append("Relevant work experience")
        if len(projects) >= 1:
            analysis["strengths"].append("Project portfolio demonstrates skills")

        if contact_score < 2:
            analysis["areas_for_improvement"].append("Add missing contact information")
        if total_skills < 5:
            analysis["areas_for_improvement"].append("Expand technical skills section")
        if len(experience) < 2:
            analysis["areas_for_improvement"].append(
                "Consider adding more experience or internships"
            )
        if not raw_data.get("summary"):
            analysis["areas_for_improvement"].append("Add a professional summary")

        return analysis


async def suggest_improvements_tool(user_id: str | None) -> dict[str, Any]:
    """Suggest specific improvements for the resume."""
    if not user_id:
        return {"error": "User ID is required to suggest improvements."}

    with get_session() as session:
        repo = ResumeRepository(session)
        profiles = repo.get_by_user(user_id)
        if not profiles:
            return {"error": "No resume profile found for this user."}

        profile = sorted(profiles, key=lambda p: p.updated_at, reverse=True)[0]
        raw_data = getattr(profile, "raw_data", {}) or {}

        suggestions = {
            "priority_improvements": [],
            "optional_enhancements": [],
            "ats_optimization": [],
            "content_suggestions": [],
        }

        # Priority improvements
        if not getattr(profile, "summary", None):
            suggestions["priority_improvements"].append(
                {
                    "section": "Professional Summary",
                    "suggestion": "Add a compelling 2-3 line professional summary highlighting your key strengths and career objectives",
                    "impact": "High - First thing recruiters see",
                }
            )

        if not getattr(profile, "phone", None):
            suggestions["priority_improvements"].append(
                {
                    "section": "Contact Information",
                    "suggestion": "Add your phone number for better accessibility",
                    "impact": "High - Essential for recruiter contact",
                }
            )

        # Skills optimization
        skills = raw_data.get("skills", {})
        if len(skills.get("languages", [])) < 3:
            suggestions["optional_enhancements"].append(
                {
                    "section": "Technical Skills",
                    "suggestion": "Add more programming languages you're familiar with",
                    "impact": "Medium - Shows technical breadth",
                }
            )

        # Experience improvements
        experience = raw_data.get("experience", [])
        for i, exp in enumerate(experience):
            if not exp.get("details") or len(exp.get("details", [])) < 2:
                suggestions["content_suggestions"].append(
                    {
                        "section": f"Experience #{i + 1}",
                        "suggestion": f"Add more detailed bullet points for {exp.get('role', 'this position')}",
                        "impact": "Medium - Quantifies your impact",
                    }
                )

        # ATS optimization
        suggestions["ats_optimization"].extend(
            [
                "Use standard section headings (Experience, Education, Skills)",
                "Include relevant keywords from job descriptions",
                "Use consistent formatting and bullet points",
                "Keep the resume length to 1-2 pages maximum",
            ]
        )

        return suggestions


async def get_resume_metrics_tool(user_id: str | None) -> dict[str, Any]:
    """Get quantitative metrics about the resume."""
    if not user_id:
        return {"error": "User ID is required to get resume metrics."}

    with get_session() as session:
        repo = ResumeRepository(session)
        profiles = repo.get_by_user(user_id)
        if not profiles:
            return {"error": "No resume profile found for this user."}

        profile = sorted(profiles, key=lambda p: p.updated_at, reverse=True)[0]
        raw_data = getattr(profile, "raw_data", {}) or {}

        metrics = {
            "word_count": 0,
            "section_counts": {},
            "completeness_scores": {},
            "diversity_metrics": {},
        }

        # Count words in text fields
        text_fields = ["summary", "name", "email", "phone", "location"]
        total_words = 0
        for field in text_fields:
            value = getattr(profile, field, None) or raw_data.get(field, "")
            if value:
                total_words += len(str(value).split())

        # Count words in structured data
        for section in ["experience", "education", "projects", "achievements"]:
            items = raw_data.get(section, [])
            section_words = 0
            for item in items:
                if isinstance(item, dict):
                    for key, value in item.items():
                        if isinstance(value, (str, list)):
                            if isinstance(value, list):
                                section_words += sum(len(str(v).split()) for v in value)
                            else:
                                section_words += len(str(value).split())
            metrics["section_counts"][section] = {
                "item_count": len(items),
                "word_count": section_words,
            }
            total_words += section_words

        metrics["word_count"] = total_words

        # Completeness scores
        required_fields = ["name", "email", "phone", "location", "summary"]
        completed_fields = sum(
            1 for field in required_fields if getattr(profile, field, None)
        )
        metrics["completeness_scores"]["contact_info"] = (
            completed_fields / len(required_fields)
        ) * 100

        # Skills diversity
        skills = raw_data.get("skills", {})
        total_skills = (
            len(skills.get("languages", []))
            + len(skills.get("frameworks", []))
            + len(skills.get("tools", []))
        )
        metrics["diversity_metrics"]["total_skills"] = total_skills
        metrics["diversity_metrics"]["skill_categories"] = len(
            [cat for cat in skills.keys() if skills[cat]]
        )

        return metrics
