from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.infrastructure.database.models import AgentDecisionLog, AgentSession
from app.services.agent.models import CareerPilotState, RoutingDecision
from langchain_google_genai import ChatGoogleGenerativeAI

logger = get_logger(__name__)


class SupervisorOrchestrationService:
    """
    Orchestrates the multi-agent graph execution loop.
    Decides routing between research_agent, intelligence_agent, human_gate, and end.
    """

    def __init__(self) -> None:
        self.llm = ChatGoogleGenerativeAI(
            model=settings_name() if hasattr(self, "settings_name") else "gemini-2.5-flash",
            temperature=0.0,
        )

    async def route_next(self, state: CareerPilotState) -> RoutingDecision:
        # Check override
        if state.next_node_override:
            logger.info(f"Using next_node_override: {state.next_node_override}")
            return RoutingDecision(
                next_node=state.next_node_override,
                reasoning="Resuming from user action override.",
                required_context=[]
            )

        prompt = f"""
        You are the Supervisor Agent for CareerPilot.
        Your job is to orchestrate the multi-agent execution loop to answer the user's career or job search query.
        
        Available Nodes:
        1. 'research_agent': Use when target company details, hiring velocity, engineering tech stacks, or job posting requirements are missing or need research.
        2. 'intelligence_agent': Use when we have researched signals and need to synthesize health scores, positioning delta, or opportunity fit recommendations.
        3. 'human_gate': Use when external applications are ready or customization is proposed that requires explicit human review.
        4. 'end': Use when the final answer or intelligence report has been fully completed and no further agent execution is required.

        Current Graph State:
        - Thread ID: {state.thread_id}
        - User Query: "{state.user_input_query}"
        - User Profile: {json.dumps(state.user_profile.model_dump(), default=str)}
        - Retrieved Jobs Count: {len(state.retrieved_jobs)}
        - Research Signals Present: {list(state.research_signals.keys()) if state.research_signals else 'None'}
        - Has Intelligence Report: {state.intelligence_report is not None}
        - Audit Trail: {state.audit_trail}

        Decide which node is the most appropriate next step.
        Format your response as a valid JSON object matching this schema:
        {{
            "next_node": "research_agent", // Must be one of: "research_agent", "intelligence_agent", "human_gate", "end"
            "reasoning": "Reason for choosing this next step.",
            "required_context": ["user_profile", "research_signals"] // Context fields required
        }}

        Output only the valid JSON. No markdown wrappers.
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

        next_node = data.get("next_node", "end")
        if next_node not in ["research_agent", "intelligence_agent", "human_gate", "end"]:
            next_node = "end"

        return RoutingDecision(
            next_node=next_node,
            reasoning=data.get("reasoning", "Routing to next available node."),
            required_context=data.get("required_context", [])
        )

    async def log_decision(
        self,
        db: AsyncSession,
        thread_id: str,
        run_id: UUID,
        current_node: str,
        decision: RoutingDecision,
        state_before: dict,
        state_after: dict,
    ) -> None:
        try:
            log_id = uuid4()
            db_log = AgentDecisionLog(
                id=str(log_id),
                thread_id=thread_id,
                run_id=str(run_id),
                current_node=current_node,
                routing_decision=decision.next_node,
                reasoning_explanation=decision.reasoning,
                state_snapshot_before=state_before,
                state_snapshot_after=state_after,
                created_at=datetime.utcnow(),
            )
            db.add(db_log)
            await db.commit()
            logger.info(f"Logged decision for thread {thread_id} / node {current_node}")
        except Exception as e:
            logger.error(f"Failed to log decision: {e}")
            await db.rollback()

    async def apply_human_gate(self, db: AsyncSession, thread_id: str) -> None:
        try:
            stmt = update(AgentSession).where(
                AgentSession.thread_id == thread_id
            ).values(
                current_status="paused_for_approval",
                updated_at=datetime.utcnow()
            )
            await db.execute(stmt)
            await db.commit()
            logger.info(f"Human gate applied on thread {thread_id}")
        except Exception as e:
            logger.error(f"Failed to apply human gate: {e}")
            await db.rollback()


def settings_name() -> str:
    from app.core.config import settings
    return settings.model_name
