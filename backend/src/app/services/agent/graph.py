from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.errors import NodeInterrupt
from langgraph.graph import END, START, StateGraph
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.services.database_service import AsyncSessionLocal
from app.infrastructure.database.models import AgentRun, AgentSession
from app.services.agent.intelligence import IntelligenceAgentService
from app.services.agent.models import CareerPilotState, JobDocument, UserProfileSnapshot
from app.services.agent.research import ResearchAgentService
from app.services.agent.supervisor import SupervisorOrchestrationService

logger = get_logger(__name__)

_checkpointer_setup_done = False
_checkpointer_setup_lock = asyncio.Lock()

async def _ensure_checkpointer_setup(checkpointer) -> None:
    global _checkpointer_setup_done
    if _checkpointer_setup_done:
        return
    async with _checkpointer_setup_lock:
        if not _checkpointer_setup_done:
            await checkpointer.setup()
            _checkpointer_setup_done = True

# Singletons of specialized services
supervisor_service = SupervisorOrchestrationService()
research_service = ResearchAgentService()
intelligence_service = IntelligenceAgentService()


# --- Nodes ---

async def supervisor_node(state: CareerPilotState, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    run_id = config.get("configurable", {}).get("run_id") if config else None
    if not run_id:
        run_id = str(uuid4())

    async with AsyncSessionLocal() as db:
        decision = await supervisor_service.route_next(state)

        # Log decision
        state_before = state.model_dump()
        state_after = state_before.copy()
        state_after["next_node_override"] = decision.next_node

        audit_trail = list(state.audit_trail)
        audit_trail.append(f"Supervisor routed to: {decision.next_node}")

        await supervisor_service.log_decision(
            db, state.thread_id, UUID(run_id), "supervisor", decision, state_before, state_after
        )

        return {
            "next_node_override": decision.next_node,
            "audit_trail": audit_trail
        }


async def research_node(state: CareerPilotState, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    async with AsyncSessionLocal() as db:
        # Default target company from preferences/profile
        company_name = "Target Company"
        if state.user_profile.target_companies:
            company_name = state.user_profile.target_companies[0]

        report = await research_service.research_opportunity(
            db, company_name, state.user_input_query
        )

        signals = {
            "tech_stack": report.signals.tech_stack,
            "hiring_velocity": report.signals.hiring_velocity,
            "critical_requirements": report.requirements.critical,
            "preferred_requirements": report.requirements.preferred,
            "bonus_requirements": report.requirements.bonus,
            "confidence_score": report.confidence_score
        }

        audit_trail = list(state.audit_trail)
        audit_trail.append("Executed Research Agent")

        return {
            "research_signals": signals,
            "next_node_override": None,
            "audit_trail": audit_trail
        }


async def intelligence_node(state: CareerPilotState, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    async with AsyncSessionLocal() as db:
        report = await intelligence_service.generate_intelligence_report(
            db, state.thread_id, state
        )

        audit_trail = list(state.audit_trail)
        audit_trail.append("Executed Intelligence Agent")

        return {
            "intelligence_report": report.model_dump(),
            "next_node_override": None,
            "audit_trail": audit_trail
        }


async def human_gate_node(state: CareerPilotState, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    # Check if approval status is granted
    if state.approved_by_user:
        audit_trail = list(state.audit_trail)
        audit_trail.append("Human-in-the-loop review approved. Resuming.")
        return {
            "approved_by_user": True,
            "next_node_override": "intelligence_agent",
            "audit_trail": audit_trail
        }
    else:
        # Halt execution using NodeInterrupt
        raise NodeInterrupt("Halted for Human-in-the-loop approval.")


# --- Routing ---

def router(state: CareerPilotState) -> str:
    node = state.next_node_override
    if node == "research_agent":
        return "research_agent"
    elif node == "intelligence_agent":
        return "intelligence_agent"
    elif node == "human_gate":
        return "human_gate"
    return END


# --- Compile Graph ---

def _build_workflow() -> StateGraph:
    workflow = StateGraph(CareerPilotState)

    # Add Nodes
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("research_agent", research_node)
    workflow.add_node("intelligence_agent", intelligence_node)
    workflow.add_node("human_gate", human_gate_node)

    # Set Entry Point
    workflow.set_entry_point("supervisor")

    # Add Conditional Edges
    workflow.add_conditional_edges(
        "supervisor",
        router,
        {
            "research_agent": "research_agent",
            "intelligence_agent": "intelligence_agent",
            "human_gate": "human_gate",
            "end": END
        }
    )

    # Add normal looping back edges
    workflow.add_edge("research_agent", "supervisor")
    workflow.add_edge("intelligence_agent", "supervisor")
    workflow.add_edge("human_gate", "supervisor")

    return workflow


# Compiled singleton reference
_workflow = _build_workflow()


# --- Execution Service ---

class GraphExecutionService:
    """
    Service to compile and run the LangGraph workflow.
    Configures checkpointing with AsyncPostgresSaver.
    """

    @staticmethod
    async def run_graph_async(
        db: AsyncSession,
        thread_id: str,
        user_id: UUID,
        user_message: str,
        user_profile: UserProfileSnapshot
    ) -> str:
        """
        Kicks off graph execution in the background, persisting runs.
        """
        run_id = str(uuid4())

        # 1. Create run record
        db_run = AgentRun(
            id=run_id,
            thread_id=thread_id,
            trigger_source="user_prompt",
            start_time=datetime.utcnow(),
            success=True,
        )
        db.add(db_run)
        await db.commit()

        # 2. Compile and run graph with checkpointer
        # Run graph in the background
        import asyncio
        asyncio.create_task(
            GraphExecutionService._execute_graph_task(
                thread_id, user_id, user_message, user_profile, run_id
            )
        )

        return run_id

    @staticmethod
    async def _execute_graph_task(
        thread_id: str,
        user_id: UUID,
        user_message: str,
        user_profile: UserProfileSnapshot,
        run_id: str
    ) -> None:
        try:
            async with AsyncPostgresSaver.from_conn_string(
                settings.async_database_url.replace("postgresql+asyncpg://", "postgresql://")
            ) as checkpointer:
                await _ensure_checkpointer_setup(checkpointer)
                app = _workflow.compile(checkpointer=checkpointer)

                initial_state = {
                    "thread_id": thread_id,
                    "user_id": user_id,
                    "user_profile": user_profile,
                    "user_input_query": user_message,
                    "audit_trail": ["Graph execution initialized."]
                }

                config = {
                    "configurable": {
                        "thread_id": thread_id,
                        "run_id": run_id
                    }
                }

                async for event in app.astream(initial_state, config):
                    logger.debug(f"Event: {event}")

                # Update run record to success
                async with AsyncSessionLocal() as session:
                    stmt = update(AgentRun).where(AgentRun.id == run_id).values(
                        end_time=datetime.utcnow(),
                        success=True
                    )
                    await session.execute(stmt)
                    # Update session status
                    stmt_sess = update(AgentSession).where(AgentSession.thread_id == thread_id).values(
                        current_status="completed",
                        updated_at=datetime.utcnow()
                    )
                    await session.execute(stmt_sess)
                    await session.commit()

        except Exception as e:
            logger.error(f"Graph execution failed: {e}")
            async with AsyncSessionLocal() as session:
                stmt = update(AgentRun).where(AgentRun.id == run_id).values(
                    end_time=datetime.utcnow(),
                    success=False,
                    error_message=str(e)
                )
                await session.execute(stmt)
                stmt_sess = update(AgentSession).where(AgentSession.thread_id == thread_id).values(
                    current_status="failed",
                    updated_at=datetime.utcnow()
                )
                await session.execute(stmt_sess)
                await session.commit()

    @staticmethod
    async def resume_graph(
        db: AsyncSession,
        thread_id: str,
        approval_status: bool,
        edited_payload: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Resumes graph execution from a paused checkpointer state.
        """
        run_id = str(uuid4())

        # 1. Update session status back to active
        stmt = update(AgentSession).where(AgentSession.thread_id == thread_id).values(
            current_status="active",
            updated_at=datetime.utcnow()
        )
        await db.execute(stmt)

        # Create run record
        db_run = AgentRun(
            id=run_id,
            thread_id=thread_id,
            trigger_source="manual_resume",
            start_time=datetime.utcnow(),
            success=True,
        )
        db.add(db_run)
        await db.commit()

        # 2. Execute task to resume graph
        import asyncio
        asyncio.create_task(
            GraphExecutionService._resume_graph_task(
                thread_id, approval_status, edited_payload, run_id
            )
        )

        return run_id

    @staticmethod
    async def _resume_graph_task(
        thread_id: str,
        approval_status: bool,
        edited_payload: Optional[Dict[str, Any]],
        run_id: str
    ) -> None:
        try:
            async with AsyncPostgresSaver.from_conn_string(
                settings.async_database_url.replace("postgresql+asyncpg://", "postgresql://")
            ) as checkpointer:
                await _ensure_checkpointer_setup(checkpointer)
                app = _workflow.compile(checkpointer=checkpointer)

                config = {
                    "configurable": {
                        "thread_id": thread_id,
                        "run_id": run_id
                    }
                }

                # Update the state of the thread with the user approval details
                state_updates = {
                    "approved_by_user": approval_status,
                    "next_node_override": "human_gate" if approval_status else "end"
                }

                # If there are payload edits, merge them in (simplified mapping)
                if edited_payload:
                    state_updates["research_signals"] = edited_payload

                await app.aupdate_state(config, state_updates)

                async for event in app.astream(None, config):
                    logger.debug(f"Event: {event}")

                # Update run record to success
                async with AsyncSessionLocal() as session:
                    stmt = update(AgentRun).where(AgentRun.id == run_id).values(
                        end_time=datetime.utcnow(),
                        success=True
                    )
                    await session.execute(stmt)
                    # Update session status
                    stmt_sess = update(AgentSession).where(AgentSession.thread_id == thread_id).values(
                        current_status="completed",
                        updated_at=datetime.utcnow()
                    )
                    await session.execute(stmt_sess)
                    await session.commit()

        except Exception as e:
            logger.error(f"Graph resumption failed: {e}")
            async with AsyncSessionLocal() as session:
                stmt = update(AgentRun).where(AgentRun.id == run_id).values(
                    end_time=datetime.utcnow(),
                    success=False,
                    error_message=str(e)
                )
                await session.execute(stmt)
                stmt_sess = update(AgentSession).where(AgentSession.thread_id == thread_id).values(
                    current_status="failed",
                    updated_at=datetime.utcnow()
                )
                await session.execute(stmt_sess)
                await session.commit()

    @staticmethod
    async def get_state(thread_id: str) -> Optional[CareerPilotState]:
        try:
            async with AsyncPostgresSaver.from_conn_string(
                settings.async_database_url.replace("postgresql+asyncpg://", "postgresql://")
            ) as checkpointer:
                await _ensure_checkpointer_setup(checkpointer)
                app = _workflow.compile(checkpointer=checkpointer)
                config = {"configurable": {"thread_id": thread_id}}
                state = await app.aget_state(config)
                if state and state.values:
                    return CareerPilotState(**state.values)
            return None
        except Exception as e:
            logger.warning(f"Failed to get graph state: {e}")
            return None
