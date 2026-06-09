from __future__ import annotations

import contextlib
import re
from decimal import Decimal
from typing import Any, List, Optional
from uuid import uuid4

from fastapi import HTTPException
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.infrastructure.database.models import NormalizedSkill
from app.schemas.profile import ProficiencyLevel
from app.schemas.profile import SkillSchema as ProfileSkillSchema

logger = get_logger(__name__)


class LLMExtractedSkill(BaseModel):
    canonical_name: str = Field(description="Standardized skill name, e.g. React, Python")
    category: str = Field(description="Category, e.g. Language, Framework, Database, Infrastructure")
    alias_resolved_from: str = Field(description="The exact text phrase indicating the skill")
    confidence_score: float = Field(description="Confidence rating between 0.0 and 1.0")
    context_sentence: str = Field(description="The exact sentence containing the skill mention")


class LLMExtractionResponse(BaseModel):
    extracted_skills: List[LLMExtractedSkill] = Field(default_factory=list)


class ExtractedSkill(BaseModel):
    canonical_name: str
    category: str
    confidence_score: float
    context_sentence: str
    alias_resolved_from: str


class SkillExtractionService:
    """
    NLP Skill Extraction Service (F2.3). Maps raw strings in job postings
    and resumes to standardized skills in the taxonomy database.
    """

    @staticmethod
    def _extract_context_sentence(text: str, keyword: str) -> str:
        """
        Extracts the sentence containing the keyword from a larger text block.
        """
        idx = text.lower().find(keyword.lower())
        if idx == -1:
            return ""

        # Walk back to find the start of the sentence
        start = idx
        while start > 0 and text[start - 1] not in (".", "!", "?", "\n"):
            start -= 1

        # Walk forward to find the end of the sentence
        end = idx + len(keyword)
        while end < len(text) and text[end] not in (".", "!", "?", "\n"):
            end += 1

        return text[start:end].strip()

    @staticmethod
    async def extract_skills_from_text(db: AsyncSession, text: str) -> List[ExtractedSkill]:
        """
        Extracts skills from text by matching against database taxonomy.
        If confidence or coverage is low, runs an LLM fallback.
        """
        if not text or len(text.strip()) < 5:
            return []

        # 1. Fetch skills taxonomy from DB
        stmt = select(NormalizedSkill)
        res = await db.execute(stmt)
        skills_in_db = res.scalars().all()

        extracted = {}

        # 2. String/Regex Matching against DB skills
        for skill in skills_in_db:
            # Build search list (canonical name + aliases)
            terms = [skill.name] + (skill.aliases or [])
            for term in terms:
                pattern = r"\b" + re.escape(term.lower()) + r"\b"
                if re.search(pattern, text.lower()):
                    # Find context sentence
                    context = SkillExtractionService._extract_context_sentence(text, term)
                    # Deduplicate by canonical name
                    if skill.name not in extracted:
                        extracted[skill.name] = ExtractedSkill(
                            canonical_name=skill.name,
                            category=skill.category or "Other",
                            confidence_score=1.0,
                            context_sentence=context or f"Mentions {term}.",
                            alias_resolved_from=term,
                        )

        # 3. LLM Fallback: If no skills found or as a verification step, query the LLM
        # to catch other emerging skills not yet in our DB.
        if len(extracted) < 3:
            try:
                llm = ChatGoogleGenerativeAI(
                    model=settings.model_name,
                    temperature=0.0,
                )
                structured_llm = llm.with_structured_output(LLMExtractionResponse)

                prompt = ChatPromptTemplate.from_messages(
                    [
                        (
                            "system",
                            (
                                "You are an expert NLP parser specializing in technical skill extraction. "
                                "Identify all technical skills, frameworks, programming languages, databases, "
                                "cloud infrastructure tools, and methodologies in the text. "
                                "For each skill, extract the canonical name, standard category, "
                                "alias_resolved_from (exact mention), a confidence score (0.0 to 1.0), and "
                                "the context_sentence where it is mentioned."
                            ),
                        ),
                        ("human", "{text}"),
                    ]
                )

                chain = prompt | structured_llm
                llm_res = await chain.ainvoke({"text": text})

                for s in llm_res.extracted_skills:
                    if s.canonical_name not in extracted:
                        extracted[s.canonical_name] = ExtractedSkill(
                            canonical_name=s.canonical_name,
                            category=s.category,
                            confidence_score=s.confidence_score,
                            context_sentence=s.context_sentence,
                            alias_resolved_from=s.alias_resolved_from,
                        )
            except Exception as e:
                logger.error(f"LLM skill extraction fallback failed: {e}")

        return list(extracted.values())

    @staticmethod
    async def resolve_alias(db: AsyncSession, raw_skill_name: str) -> Optional[NormalizedSkill]:
        """
        Resolves a raw text skill string to a canonical NormalizedSkill record.
        """
        name_clean = raw_skill_name.strip().lower()

        # Query all skills to find matches (canonical or alias)
        stmt = select(NormalizedSkill)
        res = await db.execute(stmt)
        skills = res.scalars().all()

        for skill in skills:
            if skill.name.lower() == name_clean:
                return skill
            for alias in (skill.aliases or []):
                if alias.lower() == name_clean:
                    return skill

        return None

    @staticmethod
    async def add_new_skill(
        db: AsyncSession, name: str, category: str, aliases: List[str]
    ) -> NormalizedSkill:
        """
        Inserts a new canonical skill record into the skills taxonomy.
        """
        # Check if already exists
        stmt = select(NormalizedSkill).where(NormalizedSkill.name == name)
        res = await db.execute(stmt)
        existing = res.scalar_one_or_none()
        if existing:
            return existing

        skill = NormalizedSkill(
            id=str(uuid4()),
            name=name,
            category=category,
            aliases=aliases,
        )
        db.add(skill)
        await db.flush()
        return skill
