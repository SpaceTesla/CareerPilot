from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_user
from app.infrastructure.database import models as db_models
from app.services.database_service import DatabaseService, AsyncSessionLocal
from app.services.agent.graph import GraphExecutionService
from app.services.agent.hitl import HumanInTheLoopService
from app.services.agent.models import CareerPilotState, UserProfileSnapshot, ResearchReport
from app.services.agent.research import ResearchAgentService

router = APIRouter(tags=["agent-system"])
research_service = ResearchAgentService()

# --- Request Schemas ---

class CreateSessionRequest(BaseModel):
    user_id: UUID


class RunGraphRequest(BaseModel):
    thread_id: str
    user_message: str
    bypass_human_gate: bool = False


class SupervisorApproveRequest(BaseModel):
    thread_id: str
    decision_id: str
    approved: bool
    user_notes: Optional[str] = None


class ResearchAnalyzeRequest(BaseModel):
    company_name: str
    job_description_raw: str
    bypass_cache: bool = False


class ApprovalActionRequest(BaseModel):
    action: str  # approved, rejected, modified
    edited_payload: Optional[Dict[str, Any]] = None


# --- Endpoints ---

# 1. LangGraph Foundation (F3.1)
@router.post("/agents/session", status_code=status.HTTP_201_CREATED)
async def create_agent_session(
    req: CreateSessionRequest,
    db: AsyncSession = Depends(DatabaseService.get_session),
    current_user: db_models.User = Depends(get_current_user),
):
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    thread_id = f"thread_{uuid4().hex[:8]}_user_{req.user_id.hex[:8]}"

    session = db_models.AgentSession(
        id=str(uuid4()),
        user_id=str(req.user_id),
        thread_id=thread_id,
        current_status="active",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(session)
    await db.commit()

    return {
        "session_id": session.id,
        "thread_id": thread_id,
        "status": session.current_status,
        "created_at": session.created_at.isoformat()
    }


@router.post("/agents/run", status_code=status.HTTP_202_ACCEPTED)
async def run_agent_workflow(
    req: RunGraphRequest,
    db: AsyncSession = Depends(DatabaseService.get_session),
    current_user: db_models.User = Depends(get_current_user),
):
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    # Fetch user profile snapshot
    profile_stmt = select(db_models.CareerProfile).where(db_models.CareerProfile.user_id == current_user.id)
    profile_res = await db.execute(profile_stmt)
    profile = profile_res.scalar_one_or_none()

    if not profile:
        raise HTTPException(status_code=404, detail="User career profile not found.")

    # Fetch skills
    skills_stmt = select(db_models.Skill).where(db_models.Skill.profile_id == profile.id)
    skills_res = await db.execute(skills_stmt)
    skills = [s.skill_name for s in skills_res.scalars().all()]

    # Fetch target goals
    goals_stmt = select(db_models.CareerGoals).where(db_models.CareerGoals.user_id == current_user.id)
    goals_res = await db.execute(goals_stmt)
    goals = goals_res.scalar_one_or_none()

    target_roles = [goals.target_role] if goals else []
    target_salary_min = int(goals.target_compensation_min) if goals else None
    target_companies = goals.target_companies if goals else []

    profile_snap = UserProfileSnapshot(
        id=UUID(current_user.id),
        skills=skills,
        experience_years=3.0,  # default placeholder
        target_roles=target_roles,
        target_salary_min=target_salary_min,
        target_companies=target_companies
    )

    run_id = await GraphExecutionService.run_graph_async(
        db, req.thread_id, UUID(current_user.id), req.user_message, profile_snap
    )

    return {
        "run_id": run_id,
        "thread_id": req.thread_id,
        "status": "processing",
        "message": "Graph execution started in background"
    }


@router.get("/agents/session/{thread_id}/state")
async def get_agent_state(
    thread_id: str,
    db: AsyncSession = Depends(DatabaseService.get_session),
    current_user: db_models.User = Depends(get_current_user),
):
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    state = await GraphExecutionService.get_state(thread_id)
    if not state:
        raise HTTPException(status_code=404, detail="Agent thread state not found.")

    # Get session status
    stmt = select(db_models.AgentSession).where(db_models.AgentSession.thread_id == thread_id)
    res = await db.execute(stmt)
    session = res.scalar_one_or_none()
    status_str = session.current_status if session else "active"

    return {
        "thread_id": thread_id,
        "status": status_str,
        "next_nodes": [state.next_node_override] if state.next_node_override else [],
        "state": state.model_dump()
    }


# 2. Supervisor Agent (F3.2)
@router.post("/supervisor/approve")
async def supervisor_approve(
    req: SupervisorApproveRequest,
    db: AsyncSession = Depends(DatabaseService.get_session),
    current_user: db_models.User = Depends(get_current_user),
):
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    # Resumes graph using the checkpointer
    run_id = await GraphExecutionService.resume_graph(
        db, req.thread_id, req.approved, {"user_notes": req.user_notes} if req.user_notes else None
    )

    return {
        "status": "resumed",
        "next_node": "execution_node" if req.approved else "end",
        "message": "Thread execution resumed successfully",
        "run_id": run_id
    }


@router.get("/supervisor/sessions/{thread_id}/decisions")
async def get_supervisor_decisions(
    thread_id: str,
    db: AsyncSession = Depends(DatabaseService.get_session),
    current_user: db_models.User = Depends(get_current_user),
):
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    stmt = select(db_models.AgentDecisionLog).where(
        db_models.AgentDecisionLog.thread_id == thread_id
    ).order_by(db_models.AgentDecisionLog.created_at.asc())
    res = await db.execute(stmt)
    decisions = res.scalars().all()

    return {
        "thread_id": thread_id,
        "decisions": [
            {
                "id": d.id,
                "current_node": d.current_node,
                "routing_decision": d.routing_decision,
                "reasoning_explanation": d.reasoning_explanation,
                "created_at": d.created_at.isoformat()
            }
            for d in decisions
        ]
    }


# 3. Research Agent (F3.3)
@router.get("/research/company/{company_name}", response_model=ResearchReport)
async def get_company_research(
    company_name: str,
    role_category: Optional[str] = "ml-engineer",
    db: AsyncSession = Depends(DatabaseService.get_session),
    current_user: db_models.User = Depends(get_current_user),
):
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    report = await research_service.research_opportunity(
        db, company_name, "", role_category
    )
    return report


@router.post("/research/analyze", status_code=status.HTTP_202_ACCEPTED)
async def analyze_research_adhoc(
    req: ResearchAnalyzeRequest,
    db: AsyncSession = Depends(DatabaseService.get_session),
    current_user: db_models.User = Depends(get_current_user),
):
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    # Trigger ad-hoc research in background task
    import asyncio
    task_id = f"task_res_{uuid4().hex[:6]}"
    
    async def run_research_background():
        async with AsyncSessionLocal() as session:
            await research_service.research_opportunity(
                session, req.company_name, req.job_description_raw
            )

    asyncio.create_task(run_research_background())

    return {
        "task_id": task_id,
        "status": "queued",
        "message": "Deep company intelligence gathering initiated."
    }


# 4. Human-in-the-Loop Review (F3.7)
@router.get("/approvals/pending")
async def get_pending_approvals(
    db: AsyncSession = Depends(DatabaseService.get_session),
    current_user: db_models.User = Depends(get_current_user),
):
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    stmt = select(db_models.AgentApprovalRequest).where(
        db_models.AgentApprovalRequest.user_id == current_user.id,
        db_models.AgentApprovalRequest.status == "pending"
    ).order_by(db_models.AgentApprovalRequest.created_at.desc())
    res = await db.execute(stmt)
    approvals = res.scalars().all()

    return [
        {
            "id": a.id,
            "thread_id": a.thread_id,
            "action_type": a.action_type,
            "payload": a.payload,
            "status": a.status,
            "created_at": a.created_at.isoformat()
        }
        for a in approvals
    ]


@router.post("/approvals/{approval_id}/action")
async def process_approval_decision(
    approval_id: UUID,
    req: ApprovalActionRequest,
    db: AsyncSession = Depends(DatabaseService.get_session),
    current_user: db_models.User = Depends(get_current_user),
):
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    res = await HumanInTheLoopService.process_approval_action(
        db, approval_id, UUID(current_user.id), req.action, req.edited_payload
    )
    return res
