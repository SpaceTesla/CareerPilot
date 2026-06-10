"""Temporal activities for the CareerPilot job application submission engine."""

from __future__ import annotations

from typing import Any, Dict, Optional
from sqlalchemy import select
from temporalio import activity

from app.core.logging import get_logger
from app.services.ats_integration_service import ATSIntegrationService
from app.services.deterministic_form_execution_service import DeterministicFormExecutionService
from app.services.browser_fallback_execution_service import BrowserFallbackExecutionService
from app.services.outcome_memory_service import OutcomeMemoryService
from app.infrastructure.database.models import ApplicationWorkflowCheckpoint, JobApplication
from app.services.database_service import AsyncSessionLocal
from uuid import uuid4
from datetime import datetime

logger = get_logger(__name__)


@activity.defn
async def prepare_application_materials(application_id: str) -> Dict[str, Any]:
    """Retrieve applicant details and resume to assemble the application packet."""
    logger.info(f"Preparing materials for application: {application_id}")
    # Simulating preparation work
    return {
        "status": "prepared",
        "profile_data": {
            "first_name": "Jane",
            "last_name": "Doe",
            "email": "jane.doe@example.com",
            "phone": "+123456789",
            "job_title": "Senior Engineer",
            "company": "Cyberdyne Systems"
        },
        "resume_bytes": b"mock_resume_bytes",
        "resume_filename": "jane_resume.pdf"
    }


@activity.defn
async def submit_to_ats_api(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """Submit applicant details directly using Greenhouse/Lever/Ashby APIs (Tier 1)."""
    ats_type = input_data.get("ats_type", "GREENHOUSE")
    board_token = input_data.get("board_token", "cyberdyne")
    job_id = input_data.get("job_id", "101")
    profile_data = input_data.get("profile_data", {})
    resume_bytes = input_data.get("resume_bytes", b"mock_resume_bytes")
    resume_filename = input_data.get("resume_filename", "resume.pdf")
    cover_letter = input_data.get("cover_letter")
    custom_answers = input_data.get("custom_answers")
    application_id = input_data.get("application_id")
    
    logger.info(f"Submitting to {ats_type} API for job vacancy {job_id}")
    res = await ATSIntegrationService.submit(
        ats_type=ats_type,
        board_token=board_token,
        job_id=job_id,
        profile_data=profile_data,
        resume_bytes=resume_bytes,
        resume_filename=resume_filename,
        cover_letter_text=cover_letter,
        custom_answers=custom_answers,
        application_id=application_id,
    )
    return res


@activity.defn
async def submit_deterministic_form(input_data: Dict[str, Any]) -> bool:
    """Submit applicant details using Workday/iCIMS form engines (Tier 2)."""
    application_id = input_data.get("application_id", "")
    company_domain = input_data.get("company_domain", "cyberdyne.myworkdayjobs.com")
    profile_data = input_data.get("profile_data", {})
    files = {"resume.pdf": input_data.get("resume_bytes", b"mock_resume_bytes")}
    
    logger.info(f"Submitting deterministic form for domain {company_domain}")
    res = await DeterministicFormExecutionService.execute_form_submission(
        application_id=application_id,
        company_domain=company_domain,
        profile_data=profile_data,
        files=files
    )
    return res


@activity.defn
async def submit_browser_fallback(input_data: Dict[str, Any]) -> bool:
    """Submit applicant details using Playwright fallback automation (Tier 3)."""
    application_id = input_data.get("application_id", "")
    application_url = input_data.get("application_url", "https://cyberdyne.com/careers/apply")
    profile_data = input_data.get("profile_data", {})
    resume_bytes = input_data.get("resume_bytes", b"mock_resume_bytes")
    
    logger.info(f"Submitting browser fallback for URL {application_url}")
    res = await BrowserFallbackExecutionService.execute_fallback(
        application_id=application_id,
        application_url=application_url,
        profile_data=profile_data,
        resume_bytes=resume_bytes,
    )
    return res


@activity.defn
async def record_workflow_checkpoint(input_data: Dict[str, Any]) -> None:
    """Save intermediate execution checkpoint to database for crash recovery."""
    application_id = input_data.get("application_id", "")
    state = input_data.get("state", "PREPARING")
    checkpoint_payload = input_data.get("payload", {})
    
    logger.info(f"Recording checkpoint '{state}' for application {application_id}")
    async with AsyncSessionLocal() as session:
        checkpoint = ApplicationWorkflowCheckpoint(
            id=str(uuid4()),
            application_id=application_id,
            current_state=state,
            checkpoint_data=checkpoint_payload,
            saved_at=datetime.utcnow()
        )
        session.add(checkpoint)
        await session.commit()


@activity.defn
async def handle_workflow_execution_failure(input_data: Dict[str, Any]) -> None:
    """Register failure log and emit notification if the entire application workflow fails."""
    application_id = input_data.get("application_id", "")
    failed_state = input_data.get("failed_state", "UNKNOWN")
    error = input_data.get("error", "General submission failure")
    
    logger.info(f"Recording execution failure at state '{failed_state}': {error}")
    await OutcomeMemoryService.record_status_change(
        application_id=application_id,
        new_status="FAILED",
        rejection_reason=f"Failed during state {failed_state}: {error}",
        rejection_stage=failed_state,
    )


@activity.defn
async def record_successful_submission(input_data: Dict[str, Any]) -> None:
    """Record that the job application was submitted successfully and transition status."""
    application_id = input_data.get("application_id", "")
    method = input_data.get("method", "UNKNOWN")
    
    logger.info(f"Recording successful submission for application {application_id} via {method}")
    async with AsyncSessionLocal() as session:
        stmt = select(JobApplication).where(JobApplication.id == application_id)
        res = await session.execute(stmt)
        app = res.scalar_one_or_none()
        if app:
            app.status = "applied"
            app.source = method
            app.submitted_at = datetime.utcnow()
            app.updated_at = datetime.utcnow()
            await session.commit()
            
    await OutcomeMemoryService.record_status_change(
        application_id=application_id,
        new_status="applied",
    )


@activity.defn
async def generate_digest_activity(user_id: str) -> Dict[str, Any]:
    """Compile and create a new weekly digest entry in database."""
    logger.info(f"Generating weekly digest for user {user_id}")
    from app.services.weekly_digest_service import DigestGenerationService
    from app.infrastructure.database.models import UserDigest
    from uuid import uuid4, UUID
    
    content = await DigestGenerationService.generate_digest(UUID(user_id))
    digest_id = str(uuid4())
    
    async with AsyncSessionLocal() as session:
        db_digest = UserDigest(
            id=digest_id,
            user_id=user_id,
            sent_at=None,
            health_score_snapshot=content.health_score,
            market_insight_summary=content.market_insights,
            position_delta_snapshot=content.position_delta,
            recommendations_snapshot={"jobs": content.recommendations},
            delivery_status="GENERATED",
            created_at=datetime.utcnow(),
        )
        session.add(db_digest)
        await session.commit()
        
    return {
        "digest_id": digest_id,
        "user_id": user_id
    }


@activity.defn
async def send_digest_email_activity(digest_id: str) -> bool:
    """Send formatted email for digest and update delivery status."""
    logger.info(f"Sending weekly digest email for digest {digest_id}")
    from app.services.weekly_digest_service import DigestDeliveryService
    res = await DigestDeliveryService.send_digest_email(digest_id)
    return res


@activity.defn
async def initiate_strategy_review_activity(user_id: str) -> str:
    """Call StrategyReviewOrchestrator to initiate a new monthly review."""
    logger.info(f"Initiating monthly strategy review for user {user_id}")
    from app.services.strategy_review_service import StrategyReviewOrchestrator
    from uuid import UUID
    
    review_id = await StrategyReviewOrchestrator.initiate_review(UUID(user_id))
    return review_id
