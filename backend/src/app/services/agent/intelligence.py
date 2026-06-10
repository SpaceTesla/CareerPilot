from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, List, Optional
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.infrastructure.database.models import AgentIntelligenceReport
from app.services.career_health_service import CareerHealthService
from app.services.position_delta_service import PositionDeltaService
from app.services.opportunity_scoring_service import OpportunityScoringEngine
from app.services.agent.models import (
    CareerPilotState,
    EvidenceBlock,
    IntelligenceReportPayload,
    RoadmapItem,
    CompensationAnalysis,
)
from langchain_google_genai import ChatGoogleGenerativeAI

logger = get_logger(__name__)


class IntelligenceAgentService:
    """
    Synthesizes health score, delta mapping, opportunity scoring, and compensation data
    into a comprehensive, written "Intelligence Report".
    """

    def __init__(self) -> None:
        self.llm = ChatGoogleGenerativeAI(
            model=settings_name() if hasattr(self, "settings_name") else "gemini-2.5-flash",
            temperature=0.1,
        )

    async def generate_intelligence_report(
        self, db: AsyncSession, thread_id: str, state: CareerPilotState
    ) -> IntelligenceReportPayload:
        user_id_str = str(state.user_id)

        # 1. Fetch Downstream Heuristics
        # Health Score
        try:
            health_score_data = await CareerHealthService.compute_health_score(db, user_id_str)
            overall_health_score = float(health_score_data.score) if health_score_data else 75.0
        except Exception as e:
            logger.warning(f"Failed to fetch health score, using fallback: {e}")
            overall_health_score = 75.0

        # Position Delta
        try:
            delta_data = await PositionDeltaService.calculate_position_delta(db, user_id_str)
            position_delta_score = 70.0  # default delta score
            missing_skills = []
            if delta_data:
                missing_skills = [s.get("skill_name") if isinstance(s, dict) else str(s) for s in delta_data.missing_skills]
                # estimate a score based on number of missing skills
                position_delta_score = max(100.0 - len(missing_skills) * 8.0, 30.0)
        except Exception as e:
            logger.warning(f"Failed to fetch position delta, using fallback: {e}")
            position_delta_score = 70.0
            missing_skills = []

        # Opportunity Score / Fit Score
        fit_score = 80.0
        try:
            # If retrieved jobs exist, compute fit score for the top one
            if state.retrieved_jobs:
                top_job = state.retrieved_jobs[0]
                opp_fit = await OpportunityScoringEngine.calculate_fit_score(db, user_id_str, top_job.job_id)
                if opp_fit:
                    fit_score = float(opp_fit.fit_score)
        except Exception as e:
            logger.warning(f"Failed to compute opportunity fit score, using fallback: {e}")
            fit_score = 80.0

        # 2. Synthesize with LLM
        prompt = f"""
        You are a Career Intelligence synthesis agent.
        Create a detailed, evidence-backed Intelligence Report for user "{user_id_str}".

        Input metrics:
        - Overall Career Health Score: {overall_health_score:.1f}/100
        - Position Delta Score: {position_delta_score:.1f}/100
        - Gaps / Missing Skills: {', '.join(missing_skills) if missing_skills else 'None detected'}
        - Target Role Fit Score: {fit_score:.1f}/100
        - User Profile Snap: {json.dumps(state.user_profile.model_dump(), default=str)}
        - Research Signals: {json.dumps(state.research_signals)}

        Your output must be a valid JSON object matching this schema:
        {{
            "summary_explanation": "A concise summary of user's overall positioning, health, and gap resolution strategy.",
            "evidence_trail": [
                {{
                    "claim": "User has a 80% alignment but lacks Kubernetes experience.",
                    "source_reference": "position_delta_service",
                    "source_type": "peer_benchmark", // e.g. "job_post", "peer_benchmark", "resume_experience"
                    "confidence_rating": "high" // "high", "medium", or "low"
                }}
            ],
            "profile_roadmap": [
                {{
                    "priority_order": 1,
                    "actionable_task": "Add a deployment project with Kubernetes under Projects section.",
                    "estimated_impact": "+10% fit improvement",
                    "associated_gaps": ["Kubernetes"]
                }}
            ],
            "compensation_context": {{
                "market_percentile": 75.0, // float
                "salary_range_min": 120000, // int
                "salary_range_max": 160000, // int
                "negotiation_advice": "Your strong backend stack places you in a solid negotiation position. Leverage Kubernetes addition to target upper tier."
            }}
        }}

        Do not hallucinate claims; reference actual metrics and targets. Output only valid JSON.
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

        report = IntelligenceReportPayload(
            overall_health_score=overall_health_score,
            position_delta_score=position_delta_score,
            fit_score=fit_score,
            summary_explanation=data.get("summary_explanation", ""),
            evidence_trail=[EvidenceBlock(**e) for e in data.get("evidence_trail", [])],
            profile_roadmap=[RoadmapItem(**r) for r in data.get("profile_roadmap", [])],
            compensation_context=CompensationAnalysis(**data.get("compensation_context", {
                "market_percentile": 50.0,
                "salary_range_min": 100000,
                "salary_range_max": 120000,
                "negotiation_advice": "No specific market benchmark data available."
            })),
        )

        # 3. Persist
        await self.persist_intelligence_report(db, thread_id, state.user_id, report)
        return report

    async def persist_intelligence_report(
        self, db: AsyncSession, thread_id: str, user_id: UUID, report: IntelligenceReportPayload
    ) -> UUID:
        report_id = uuid4()
        try:
            db_report = AgentIntelligenceReport(
                id=str(report_id),
                thread_id=thread_id,
                user_id=str(user_id),
                overall_health_score=report.overall_health_score,
                position_delta_score=report.position_delta_score,
                fit_score=report.fit_score,
                structured_explanation=report.model_dump(),
                created_at=datetime.utcnow(),
            )
            db.add(db_report)
            await db.commit()
            return report_id
        except Exception as e:
            logger.error(f"Failed to persist intelligence report: {e}")
            await db.rollback()
            return report_id


def settings_name() -> str:
    from app.core.config import settings
    return settings.model_name
