"""Job Application Workflow Service."""

from __future__ import annotations

import json
from datetime import datetime
from uuid import uuid4
from typing import Any, Dict, Optional, List
from sqlalchemy import select

from app.core.logging import get_logger
from app.infrastructure.database.models import (
    JobApplication,
    ApplicationWorkflowCheckpoint,
    FormExecutionLog,
    BrowserExecutionLog,
)
from app.services.database_service import AsyncSessionLocal
from app.services.temporal_service import TemporalWorkflowService

logger = get_logger(__name__)


class ApplicationWorkflowService:
    """Service handling coordination and scheduling of the job application Temporal workflow."""

    @classmethod
    async def queue_application(
        cls,
        user_id: str,
        opportunity_id: str,
        resume_version_id: str,
        cover_letter_text: Optional[str] = None,
        custom_answers: Optional[Dict[str, Any]] = None,
        ats_type: Optional[str] = None,
        board_token: Optional[str] = None,
        job_id: Optional[str] = None,
        company_domain: Optional[str] = None,
        application_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Creates job application in DB, generates workflow id and triggers Temporal workflow.
        """
        application_id = str(uuid4())
        workflow_id = f"app-wf-{application_id}"
        
        async with AsyncSessionLocal() as session:
            # Check if there is an existing job posting or company details to populate
            job_title = "Senior Software Engineer"
            company = "TechCorp"
            if company_domain:
                company = company_domain.split(".")[0].capitalize()
            
            application = JobApplication(
                id=application_id,
                user_id=user_id,
                job_title=job_title,
                company=company,
                job_url=application_url or f"https://{company_domain or 'careers.com'}/apply",
                source=ats_type or "FORM",
                status="queued",
                opportunity_id=opportunity_id,
                resume_version_id=resume_version_id,
                cover_letter_text=cover_letter_text,
                custom_answers=custom_answers,
                workflow_id=workflow_id,
                applied_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            session.add(application)
            await session.commit()
            
            # Start Temporal workflow asynchronously
            input_payload = {
                "application_id": application_id,
                "ats_type": ats_type,
                "board_token": board_token,
                "job_id": job_id,
                "company_domain": company_domain,
                "application_url": application_url or application.job_url,
                "cover_letter_text": cover_letter_text,
                "custom_answers": custom_answers,
            }
            
            await TemporalWorkflowService.start_workflow(
                workflow_name="ApplicationExecutionWorkflow",
                workflow_id=workflow_id,
                task_queue="application-queue",
                input_data=input_payload,
                user_id=user_id,
            )
            
            return {
                "application_id": application.id,
                "status": "QUEUED",
                "workflow_id": workflow_id,
                "created_at": application.applied_at.isoformat()
            }

    @classmethod
    async def get_execution_logs(cls, application_id: str) -> Dict[str, Any]:
        """Compile a list of execution logs across checkpoints, forms, and browser steps."""
        logs = []
        
        async with AsyncSessionLocal() as session:
            # 1. Fetch Checkpoints
            cp_stmt = (
                select(ApplicationWorkflowCheckpoint)
                .where(ApplicationWorkflowCheckpoint.application_id == application_id)
                .order_by(ApplicationWorkflowCheckpoint.saved_at.asc())
            )
            cp_res = await session.execute(cp_stmt)
            for cp in cp_res.scalars().all():
                logs.append({
                    "timestamp": cp.saved_at.isoformat(),
                    "state": cp.current_state,
                    "message": f"Checkpoint reached state: {cp.current_state}"
                })
                
            # 2. Fetch Form execution
            form_stmt = (
                select(FormExecutionLog)
                .where(FormExecutionLog.application_id == application_id)
                .order_by(FormExecutionLog.created_at.asc())
            )
            form_res = await session.execute(form_stmt)
            for form in form_res.scalars().all():
                logs.append({
                    "timestamp": form.created_at.isoformat(),
                    "state": "FORM_SUBMISSION",
                    "message": f"Step {form.step_number} ({form.step_name}): Status {form.response_status}"
                })

            # 3. Fetch Browser execution
            browser_stmt = (
                select(BrowserExecutionLog)
                .where(BrowserExecutionLog.application_id == application_id)
                .order_by(BrowserExecutionLog.created_at.asc())
            )
            browser_res = await session.execute(browser_stmt)
            for browser in browser_res.scalars().all():
                logs.append({
                    "timestamp": browser.created_at.isoformat(),
                    "state": "BROWSER_SUBMISSION",
                    "message": f"Step {browser.step_index} ({browser.action_type}): Status {browser.status}"
                })
                
        # Sort logs by timestamp
        logs.sort(key=lambda x: x["timestamp"])
        
        return {
            "application_id": application_id,
            "status": "PROCESSING" if logs else "UNKNOWN",
            "logs": logs
        }
