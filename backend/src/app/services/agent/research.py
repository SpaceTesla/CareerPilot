from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any, List, Optional
from uuid import UUID, uuid4

from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from tavily import TavilyClient

from app.core.config import settings
from app.core.logging import get_logger
from app.infrastructure.database.models import ResearchMemory
from app.services.agent.models import (
    CompanySignals,
    RequirementsMap,
    ResearchReport,
    ResearchSource,
)
from langchain_google_genai import ChatGoogleGenerativeAI

logger = get_logger(__name__)


class ResearchAgentService:
    """
    Handles deep investigations of companies and job descriptions.
    Uses Tavily Search to gather external data and Gemini to synthesize structured reports.
    Caches results in PostgreSQL for 14 days.
    """

    def __init__(self) -> None:
        self.tavily = TavilyClient(api_key=settings.tavily_api_key) if settings.tavily_api_key else None
        self.llm = ChatGoogleGenerativeAI(
            model=settings.model_name,
            temperature=0.1,
        )

    async def research_opportunity(
        self, db: AsyncSession, company_name: str, job_description: str, role_category: str = "ml-engineer"
    ) -> ResearchReport:
        # 1. Check Cache
        cached = await self._get_cached_research(db, company_name, role_category)
        if cached:
            logger.info(f"Returning cached research report for company: {company_name}")
            return cached

        # 2. Gather External Context
        search_results_text = ""
        sources = []
        if self.tavily:
            try:
                query = f"{company_name} engineering tech stack developer hiring velocity"
                response = self.tavily.search(query=query, max_results=5)
                results = response.get("results", [])
                for idx, r in enumerate(results):
                    snippet = r.get("content", "")
                    url = r.get("url", "")
                    search_results_text += f"\nSource [{idx+1}]: {url}\nSnippet: {snippet}\n"
                    sources.append(
                        ResearchSource(
                            source_type="company_page" if "jobs" in url or "career" in url else "news_article",
                            reference_id=f"tavily_{idx+1}",
                            url=url,
                            snippet=snippet[:200],
                            verified_at=datetime.utcnow(),
                        )
                    )
            except Exception as e:
                logger.warning(f"Tavily search failed for company {company_name}: {e}")

        # Fallback if no external search results
        if not search_results_text:
            search_results_text = "No web search data available."
            sources.append(
                ResearchSource(
                    source_type="job_posting",
                    reference_id="raw_job_description",
                    url=None,
                    snippet=job_description[:200] if job_description else "No description provided",
                    verified_at=datetime.utcnow(),
                )
            )

        # 3. Prompt LLM to Synthesize Report
        prompt = f"""
        You are a Company and Role Intelligence Researcher.
        Synthesize a structured research report for company "{company_name}" and role category "{role_category}".

        Job Description Details:
        {job_description or 'None provided.'}

        Web Search Context gathered:
        {search_results_text}

        Your output must be a valid JSON object conforming to this schema:
        {{
            "company_name": "Name of Company",
            "company_domain": "company website domain (e.g. stripe.com)",
            "role_category": "{role_category}",
            "requirements": {{
                "critical": ["must-have skill 1", "must-have skill 2"],
                "preferred": ["preferred skill 1"],
                "bonus": ["nice-to-have skill 1"]
            }},
            "signals": {{
                "hiring_velocity": "moderate", // "stagnant", "moderate", or "high"
                "tech_stack": ["Python", "JAX", "etc"],
                "organizational_notes": "Any other helpful notes"
            }},
            "confidence_score": 0.85 // float between 0.0 and 1.0 based on details available
        }}

        Ensure all values are accurate and backed by the provided context. Output only valid JSON.
        """
        response = await self.llm.ainvoke(prompt)
        content = response.content
        if isinstance(content, str):
            if content.strip().startswith("```"):
                lines = content.strip().split("\n")
                content = "\n".join(lines[1:-1]) if lines[-1].startswith("```") else "\n".join(lines[1:])
            data = json.loads(content)
        else:
            raise ValueError("Failed to parse LLM content")

        report = ResearchReport(
            company_name=data.get("company_name", company_name),
            company_domain=data.get("company_domain"),
            role_category=data.get("role_category", role_category),
            requirements=RequirementsMap(
                critical=data.get("requirements", {}).get("critical", []),
                preferred=data.get("requirements", {}).get("preferred", []),
                bonus=data.get("requirements", {}).get("bonus", []),
            ),
            signals=CompanySignals(
                hiring_velocity=data.get("signals", {}).get("hiring_velocity", "moderate"),
                tech_stack=data.get("signals", {}).get("tech_stack", []),
                organizational_notes=data.get("signals", {}).get("organizational_notes"),
            ),
            sources=sources,
            confidence_score=float(data.get("confidence_score", 0.75)),
        )

        # 4. Cache report
        await self.cache_research(db, report)
        return report

    async def _get_cached_research(self, db: AsyncSession, company_name: str, role_category: str) -> Optional[ResearchReport]:
        try:
            stmt = select(ResearchMemory).where(
                text("LOWER(company_name) = :cname"),
                ResearchMemory.role_category == role_category,
                ResearchMemory.expires_at > datetime.utcnow()
            )
            result = await db.execute(stmt, {"cname": company_name.lower()})
            row = result.scalar_one_or_none()
            if not row:
                return None

            raw_sources = row.raw_sources if isinstance(row.raw_sources, list) else []
            sources = [
                ResearchSource(
                    source_type=s.get("source_type"),
                    reference_id=s.get("reference_id"),
                    url=s.get("url"),
                    snippet=s.get("snippet"),
                    verified_at=datetime.fromisoformat(s.get("verified_at")) if s.get("verified_at") else datetime.utcnow()
                )
                for s in raw_sources
            ]

            return ResearchReport(
                company_name=row.company_name,
                company_domain=row.company_domain,
                role_category=row.role_category,
                requirements=RequirementsMap(**row.structured_data.get("requirements", {})),
                signals=CompanySignals(**row.structured_data.get("signals", {})),
                sources=sources,
                confidence_score=float(row.confidence_score),
            )
        except Exception as e:
            logger.warning(f"Error checking research cache: {e}")
            return None

    async def cache_research(self, db: AsyncSession, report: ResearchReport) -> None:
        try:
            # Delete old matching memory first (upsert behavior)
            delete_stmt = delete(ResearchMemory).where(
                text("LOWER(company_name) = :cname"),
                ResearchMemory.role_category == report.role_category
            )
            await db.execute(delete_stmt, {"cname": report.company_name.lower()})

            sources_json = [
                {
                    "source_type": s.source_type,
                    "reference_id": s.reference_id,
                    "url": s.url,
                    "snippet": s.snippet,
                    "verified_at": s.verified_at.isoformat() if isinstance(s.verified_at, datetime) else s.verified_at
                }
                for s in report.sources
            ]

            memory = ResearchMemory(
                id=str(uuid4()),
                company_name=report.company_name,
                company_domain=report.company_domain,
                role_category=report.role_category,
                structured_data={
                    "requirements": report.requirements.model_dump(),
                    "signals": report.signals.model_dump(),
                },
                raw_sources=sources_json,
                confidence_score=report.confidence_score,
                expires_at=datetime.utcnow() + timedelta(days=14),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            db.add(memory)
            await db.commit()
        except Exception as e:
            logger.error(f"Failed to cache research: {e}")
            await db.rollback()

    async def invalidate_expired_memories(self, db: AsyncSession) -> int:
        try:
            stmt = delete(ResearchMemory).where(ResearchMemory.expires_at < datetime.utcnow())
            res = await db.execute(stmt)
            await db.commit()
            return res.rowcount
        except Exception as e:
            logger.error(f"Failed to invalidate expired memories: {e}")
            await db.rollback()
            return 0
