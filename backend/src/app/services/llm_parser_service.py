from __future__ import annotations

import contextlib
import re
from datetime import date, datetime
from decimal import Decimal

from fastapi import HTTPException
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.logging import get_logger
from app.schemas.profile import (
    EducationSchema,
    ExperienceSchema,
    ProficiencyLevel,
    ProfileUpdate,
    ProjectSchema,
    SkillSchema,
)

logger = get_logger(__name__)


class RelaxedSkill(BaseModel):
    skill_name: str | None = None
    years_experience: float | None = None
    proficiency: str | None = None


class RelaxedExperience(BaseModel):
    company_name: str | None = None
    job_title: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    description: str | None = None
    is_current: bool | None = None


class RelaxedEducation(BaseModel):
    institution: str | None = None
    degree: str | None = None
    field_of_study: str | None = None
    start_date: str | None = None
    end_date: str | None = None


class RelaxedProject(BaseModel):
    project_name: str | None = None
    description: str | None = None
    role_description: str | None = None
    url: str | None = None


class RelaxedProfile(BaseModel):
    headline: str | None = None
    summary: str | None = None
    location: str | None = None
    current_salary: float | None = None
    skills: list[RelaxedSkill] = Field(default_factory=list)
    experiences: list[RelaxedExperience] = Field(default_factory=list)
    education: list[RelaxedEducation] = Field(default_factory=list)
    projects: list[RelaxedProject] = Field(default_factory=list)
    self_evaluation_score: float = Field(
        default=0.5,
        description=(
            "Self-evaluation score between 0.0 and 1.0 "
            "based on extraction completeness and confidence"
        ),
    )


class LLMParserService:
    @staticmethod
    def _parse_date(date_str: str | None) -> date | None:
        if not date_str:
            return None
        date_str = date_str.strip()
        # Try different formats
        for fmt in ("%Y-%m-%d", "%Y-%m", "%Y/%m/%d", "%Y/%m"):
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue
        # Fallback regex search for YYYY
        match = re.search(r"\b(19|20)\d{2}\b", date_str)
        if match:
            year = int(match.group(0))
            # Try to guess month
            months = {
                "jan": 1,
                "feb": 2,
                "mar": 3,
                "apr": 4,
                "may": 5,
                "jun": 6,
                "jul": 7,
                "aug": 8,
                "sep": 9,
                "oct": 10,
                "nov": 11,
                "dec": 12,
            }
            month = 1
            date_str_lower = date_str.lower()
            for m_name, m_val in months.items():
                if m_name in date_str_lower:
                    month = m_val
                    break
            return date(year, month, 1)
        return None

    @staticmethod
    def calculate_confidence(raw_extracted: RelaxedProfile) -> float:
        # Start with LLM's self-evaluation score (clamped between 0 and 1)
        score = max(0.0, min(1.0, raw_extracted.self_evaluation_score))

        # Deduct for missing general info
        if not raw_extracted.headline:
            score -= 0.05
        if not raw_extracted.summary:
            score -= 0.10
        if not raw_extracted.location:
            score -= 0.05

        # Deduct for empty collections
        if not raw_extracted.skills:
            score -= 0.15
        if not raw_extracted.experiences:
            score -= 0.20
        if not raw_extracted.education:
            score -= 0.10

        # Heuristics for incomplete items
        for exp in raw_extracted.experiences:
            if not exp.company_name or not exp.job_title:
                score -= 0.05
            if not exp.start_date:
                score -= 0.05

        for edu in raw_extracted.education:
            if not edu.institution:
                score -= 0.05
            if not edu.start_date:
                score -= 0.05

        return max(0.0, min(1.0, score))

    @staticmethod
    async def parse_resume_text(text: str) -> tuple[ProfileUpdate, float]:
        """
        Parses raw resume text using LLM. Returns a clean, validated
        ProfileUpdate schema and a calculated confidence score.
        """
        if not text or len(text.strip()) < 50:
            raise HTTPException(
                status_code=422,
                detail=(
                    "Resume content too short or empty. "
                    "Ensure the PDF/DOCX contains extractable text."
                ),
            )

        try:
            llm = ChatGoogleGenerativeAI(
                model=settings.model_name,
                temperature=settings.temperature,
            )
            structured_llm = llm.with_structured_output(RelaxedProfile)

            prompt = ChatPromptTemplate.from_messages(
                [
                    (
                        "system",
                        (
                            "You are an expert AI resume parser. Extract the "
                            "structured career profile information from the "
                            "resume text provided by the user. Be thorough "
                            "but extract only real information. If a field "
                            "is missing, leave it as null/empty. Provide a "
                            "self_evaluation_score between 0.0 and 1.0 "
                            "indicating your confidence in the extraction quality."
                        ),
                    ),
                    ("human", "{resume_text}"),
                ]
            )

            chain = prompt | structured_llm
            raw_extracted = await chain.ainvoke({"resume_text": text})
        except Exception as e:
            logger.error(f"LLM parsing failed: {e}")
            # Return empty ProfileUpdate with 0 confidence if LLM invocation fails
            return (
                ProfileUpdate(
                    headline=None,
                    summary=None,
                    location=None,
                    current_salary=None,
                    skills=[],
                    experiences=[],
                    education=[],
                    projects=[],
                ),
                0.0,
            )

        # Now, clean and map RelaxedProfile to ProfileUpdate
        skills_cleaned = []
        for s in raw_extracted.skills:
            if not s.skill_name:
                continue
            # Map proficiency
            prof = ProficiencyLevel.INTERMEDIATE
            if s.proficiency:
                val = s.proficiency.upper()
                if val in [p.value for p in ProficiencyLevel]:
                    prof = ProficiencyLevel(val)
                elif "EXPERT" in val:
                    prof = ProficiencyLevel.EXPERT
                elif "ADVANCED" in val or "SENIOR" in val:
                    prof = ProficiencyLevel.ADVANCED
                elif "NOVICE" in val or "BEGINNER" in val or "ENTRY" in val:
                    prof = ProficiencyLevel.NOVICE

            years_exp = 1.0
            if s.years_experience is not None:
                with contextlib.suppress(ValueError):
                    years_exp = float(s.years_experience)

            skills_cleaned.append(
                SkillSchema(
                    skill_name=s.skill_name,
                    years_experience=Decimal(str(round(years_exp, 1))),
                    proficiency=prof,
                )
            )

        experiences_cleaned = []
        for e in raw_extracted.experiences:
            # Skip experience only if it doesn't have any meaningful info
            if not e.company_name and not e.job_title:
                continue

            comp = e.company_name or "Unknown Company"
            title = e.job_title or "Software Engineer"
            desc = e.description or "Job description not provided."
            is_curr = bool(e.is_current)

            start = LLMParserService._parse_date(e.start_date)
            end = LLMParserService._parse_date(e.end_date)

            if not start:
                start = date(2020, 1, 1)

            if not is_curr and end and start > end:
                # Swap dates if they are invalid
                start, end = end, start

            # If still invalid (no end date and not current), set end to start
            if not is_curr and not end:
                end = start

            experiences_cleaned.append(
                ExperienceSchema(
                    company_name=comp,
                    job_title=title,
                    start_date=start,
                    end_date=end if not is_curr else None,
                    description=desc,
                    is_current=is_curr,
                )
            )

        # Enforce maximum 2 current experiences
        current_count = 0
        for exp in experiences_cleaned:
            if exp.is_current:
                current_count += 1
                if current_count > 2:
                    exp.is_current = False
                    exp.end_date = exp.start_date  # Ensure it has a non-null end date

        education_cleaned = []
        for ed in raw_extracted.education:
            if not ed.institution:
                continue

            inst = ed.institution
            deg = ed.degree
            field = ed.field_of_study

            start = LLMParserService._parse_date(ed.start_date)
            end = LLMParserService._parse_date(ed.end_date)

            if not start:
                start = date(2020, 1, 1)

            if end and start > end:
                start, end = end, start

            education_cleaned.append(
                EducationSchema(
                    institution=inst,
                    degree=deg,
                    field_of_study=field,
                    start_date=start,
                    end_date=end,
                )
            )

        projects_cleaned = []
        for p in raw_extracted.projects:
            if not p.project_name and not p.description:
                continue
            p_name = p.project_name or "Unnamed Project"
            p_desc = p.description or "Project description not provided."
            projects_cleaned.append(
                ProjectSchema(
                    project_name=p_name,
                    description=p_desc,
                    role_description=p.role_description,
                    url=p.url,
                )
            )

        profile_update = ProfileUpdate(
            headline=raw_extracted.headline,
            summary=raw_extracted.summary,
            location=raw_extracted.location,
            current_salary=Decimal(str(round(raw_extracted.current_salary, 2)))
            if raw_extracted.current_salary is not None
            else None,
            skills=skills_cleaned,
            experiences=experiences_cleaned,
            education=education_cleaned,
            projects=projects_cleaned,
        )

        confidence = LLMParserService.calculate_confidence(raw_extracted)

        return profile_update, confidence
