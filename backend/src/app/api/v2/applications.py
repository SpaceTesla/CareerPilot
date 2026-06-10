"""FastAPI Router for Wave 7: Execution Engine & Outcome Memory endpoints."""

from __future__ import annotations

from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func

from app.api.dependencies.auth import get_current_user
from app.infrastructure.database.models import User, WorkflowExecutionLog, JobApplication, ApplicationOutcome
from app.services.database_service import AsyncSessionLocal
from app.services.temporal_service import TemporalWorkflowService
from app.services.application_workflow_service import ApplicationWorkflowService
from app.services.outcome_memory_service import OutcomeMemoryService

router = APIRouter()


@router.post("/applications/workflows/trigger", status_code=status.HTTP_202_ACCEPTED)
async def trigger_application_workflow(
    payload: Dict[str, Any],
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Trigger the multi-tier application execution workflow for a job opportunity."""
    opportunity_id = payload.get("opportunity_id")
    resume_version_id = payload.get("resume_version_id")
    if not opportunity_id or not resume_version_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="opportunity_id and resume_version_id are required fields.",
        )
        
    try:
        res = await ApplicationWorkflowService.queue_application(
            user_id=current_user.id,
            opportunity_id=opportunity_id,
            resume_version_id=resume_version_id,
            cover_letter_text=payload.get("cover_letter_text"),
            custom_answers=payload.get("custom_answers"),
            ats_type=payload.get("ats_type"),
            board_token=payload.get("board_token"),
            job_id=payload.get("job_id"),
            company_domain=payload.get("company_domain"),
            application_url=payload.get("application_url"),
        )
        return res
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to queue application: {str(e)}"
        )


@router.get("/applications/{application_id}/logs")
async def get_application_logs(
    application_id: str,
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Retrieve checkpoint, form filling, and browser fallback execution log traces."""
    # Ensure application exists and belongs to user
    async with AsyncSessionLocal() as session:
        stmt = select(JobApplication).where(JobApplication.id == application_id)
        res = await session.execute(stmt)
        app = res.scalar_one_or_none()
        if not app:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Application not found: {application_id}"
            )
        if app.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to view logs for this application."
            )
            
    res = await ApplicationWorkflowService.get_execution_logs(application_id)
    return res


@router.get("/workflows/executions/{workflow_id}")
async def get_workflow_status(
    workflow_id: str,
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Get the current execution state of a Temporal workflow."""
    async with AsyncSessionLocal() as session:
        stmt = select(WorkflowExecutionLog).where(WorkflowExecutionLog.workflow_id == workflow_id)
        res = await session.execute(stmt)
        log = res.scalar_one_or_none()
        if not log:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Workflow execution log not found: {workflow_id}"
            )
            
        # Optional: sync status from Temporal client
        current_status = await TemporalWorkflowService.sync_workflow_status(log.workflow_id, log.run_id)
        
        return {
            "workflow_id": log.workflow_id,
            "run_id": log.run_id,
            "workflow_type": log.workflow_type,
            "status": current_status,
            "task_queue": log.task_queue,
            "created_at": log.created_at.isoformat(),
            "updated_at": log.updated_at.isoformat()
        }


@router.post("/workflows/executions/{workflow_id}/cancel", status_code=status.HTTP_202_ACCEPTED)
async def cancel_workflow(
    workflow_id: str,
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Request immediate cancellation of a running Temporal workflow."""
    async with AsyncSessionLocal() as session:
        stmt = select(WorkflowExecutionLog).where(WorkflowExecutionLog.workflow_id == workflow_id)
        res = await session.execute(stmt)
        log = res.scalar_one_or_none()
        if not log:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Workflow execution log not found: {workflow_id}"
            )
            
    await TemporalWorkflowService.cancel_workflow(workflow_id)
    return {
        "workflow_id": workflow_id,
        "message": "Cancellation request submitted successfully."
    }


@router.post("/applications/{application_id}/outcome")
async def record_application_outcome(
    application_id: str,
    payload: Dict[str, Any],
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Record status update, rejection stage, or compensation results for an application."""
    new_status = payload.get("new_status")
    if not new_status:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="new_status is a required field."
        )
        
    try:
        res = await OutcomeMemoryService.record_status_change(
            application_id=application_id,
            new_status=new_status,
            rejection_reason=payload.get("rejection_reason"),
            rejection_stage=payload.get("rejection_stage"),
        )
        return res
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/applications/outcomes/analytics")
async def get_outcome_analytics(
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Compile conversion rates, ghost ratios, and average latency metrics for the user."""
    async with AsyncSessionLocal() as session:
        # 1. Total applications
        total_stmt = select(func.count(JobApplication.id)).where(JobApplication.user_id == current_user.id)
        total_res = await session.execute(total_stmt)
        total_count = total_res.scalar() or 0
        
        # 2. Interviews scheduled
        int_stmt = (
            select(func.count(ApplicationOutcome.id))
            .join(JobApplication, JobApplication.id == ApplicationOutcome.application_id)
            .where(JobApplication.user_id == current_user.id)
            .where(ApplicationOutcome.final_outcome == "INTERVIEW_SCHEDULED")
        )
        int_res = await session.execute(int_stmt)
        interview_count = int_res.scalar() or 0
        
        # 3. Ghosted rate
        ghost_stmt = (
            select(func.count(ApplicationOutcome.id))
            .join(JobApplication, JobApplication.id == ApplicationOutcome.application_id)
            .where(JobApplication.user_id == current_user.id)
            .where(ApplicationOutcome.final_outcome == "GHOSTED")
        )
        ghost_res = await session.execute(ghost_stmt)
        ghost_count = ghost_res.scalar() or 0
        
        # 4. Average response time
        avg_stmt = (
            select(func.avg(ApplicationOutcome.days_to_response))
            .join(JobApplication, JobApplication.id == ApplicationOutcome.application_id)
            .where(JobApplication.user_id == current_user.id)
            .where(ApplicationOutcome.days_to_response != None)
        )
        avg_res = await session.execute(avg_stmt)
        avg_days = float(avg_res.scalar() or 0.0)
        
        conversion_rate = round(interview_count / max(total_count, 1), 2)
        ghost_rate = round(ghost_count / max(total_count, 1), 2)
        
        return {
            "total_applications": total_count,
            "interview_conversion_rate": conversion_rate,
            "average_days_to_response": avg_days,
            "ghost_rate": ghost_rate,
            "outcomes_by_ats": {
                "GREENHOUSE": {
                    "submissions": total_count,
                    "interviews": interview_count
                }
            }
        }
