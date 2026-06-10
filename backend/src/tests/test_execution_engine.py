from __future__ import annotations

import sys
import asyncio

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import random
from datetime import datetime, timedelta, date
from uuid import uuid4
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from unittest.mock import patch

from app.main import app
from app.infrastructure.database.models import (
    User,
    Company,
    JobPosting,
    CareerProfile,
    ProfileVersion,
    JobApplication,
    WorkflowExecutionLog,
    ApplicationWorkflowCheckpoint,
    FormSchema,
    FormExecutionLog,
    BrowserExecutionLog,
    ApplicationOutcome,
    ApplicationStatusHistory,
)
from app.services.database_service import async_engine, AsyncSessionLocal
from app.services.temporal_service import TemporalWorkflowService
from app.services.deterministic_form_execution_service import DeterministicFormExecutionService
from app.services.outcome_memory_service import OutcomeMemoryService
from app.services.ats_integration_service import ATSIntegrationService

# Temporal Testing
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker
from app.services.execution_engine.workflows import ApplicationExecutionWorkflow
import app.services.execution_engine.activities as activities


@pytest.fixture(scope="module", autouse=True)
async def cleanup_db_engine():
    await async_engine.dispose()
    yield
    await async_engine.dispose()


@pytest.fixture(autouse=True)
async def dispose_engine_per_test():
    await async_engine.dispose()
    yield
    await async_engine.dispose()


async def seed_user_and_opportunity(email: str, password: str, company_name: str, domain: str) -> tuple[str, str, str, str]:
    """Helper to register user, create company, target job posting, and career profile."""
    # Register/Login
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        reg_resp = await client.post(
            "/api/v2/auth/register", json={"email": email, "password": password}
        )
        assert reg_resp.status_code == 201
        tokens = reg_resp.json()
        user_id = tokens["id"]

    async with AsyncSessionLocal() as session:
        # Create Company (appended with random integer to avoid unique constraint collisions)
        unique_company_name = f"{company_name}_{random.randint(10000, 99999)}"
        company = Company(
            id=str(uuid4()),
            name=unique_company_name,
            website=f"https://{domain}",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        session.add(company)

        # Create Job Posting
        opportunity = JobPosting(
            id=str(uuid4()),
            company_id=company.id,
            title="Senior AI Engineer",
            raw_title="Senior AI Engineer",
            location="Remote",
            description="Build agentic workflows.",
            url=f"https://{domain}/apply/123",
            source="GREENHOUSE",
            source_id="gh-" + str(uuid4())[:8],
            post_date=date.today(),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        session.add(opportunity)

        # Create Career Profile
        profile = CareerProfile(
            id=str(uuid4()),
            user_id=user_id,
            headline="Expert AI Engineer",
            summary="Building temporal systems",
            location="Remote",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        session.add(profile)

        # Create Profile Version
        version = ProfileVersion(
            id=str(uuid4()),
            profile_id=profile.id,
            version_number=1,
            snapshot_payload={"name": "Jane Doe", "email": email},
            created_at=datetime.utcnow(),
        )
        session.add(version)
        await session.commit()
        
        return user_id, opportunity.id, version.id, company.id


@pytest.mark.asyncio
async def test_e2e_api_workflow_trigger_and_tier1_success():
    """
    Test Tier 1: ATS API integration submission.
    Workflow runs on the test Temporal environment and completes successfully via ATS API.
    Also validates logs retrieval, cancelling, outcome recording, and analytics.
    """
    email = f"tier1_test_{random.randint(1000, 9999)}@example.com"
    password = "TestPassword123!"
    user_id, opportunity_id, version_id, _ = await seed_user_and_opportunity(
        email, password, "TechCorp", "techcorp.com"
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # Login
        login_resp = await client.post(
            "/api/v2/auth/login", json={"email": email, "password": password}
        )
        assert login_resp.status_code == 200
        tokens = login_resp.json()
        headers = {"Authorization": f"Bearer {tokens['access_token']}"}

        # Start temporal testing environment
        async with await WorkflowEnvironment.start_time_skipping() as env:
            # Set global temporal service client to the testing client
            TemporalWorkflowService.set_client(env.client)

            # Start worker
            async with Worker(
                env.client,
                task_queue="application-queue",
                workflows=[ApplicationExecutionWorkflow],
                activities=[
                    activities.prepare_application_materials,
                    activities.submit_to_ats_api,
                    activities.submit_deterministic_form,
                    activities.submit_browser_fallback,
                    activities.record_workflow_checkpoint,
                    activities.handle_workflow_execution_failure,
                    activities.record_successful_submission,
                ],
            ):
                # Trigger workflow via API POST request
                payload = {
                    "opportunity_id": opportunity_id,
                    "resume_version_id": version_id,
                    "ats_type": "GREENHOUSE",
                    "board_token": "techcorp",
                    "job_id": "12345",
                    "company_domain": "techcorp.com",
                    "application_url": "https://techcorp.com/apply/12345",
                }
                
                # Mock actual HTTP request to Greenhouse API board to prevent network outbound
                mock_submit_res = {"success": True, "status_code": 201, "confirmation_id": "conf-ats-123"}
                with patch("app.services.ats_integration_service.ATSIntegrationService.submit", return_value=mock_submit_res):
                    trigger_resp = await client.post(
                        "/api/v2/applications/workflows/trigger",
                        json=payload,
                        headers=headers,
                    )
                    assert trigger_resp.status_code == 202
                    res_data = trigger_resp.json()
                    application_id = res_data["application_id"]
                    workflow_id = res_data["workflow_id"]

                    # Wait for workflow completion on temporal environment
                    handle = env.client.get_workflow_handle(workflow_id)
                    result = await handle.result()
                    assert result["status"] == "COMPLETED"
                    assert result["method"] == "ATS_API"

                # Verify Job Application state in DB
                async with AsyncSessionLocal() as session:
                    app_stmt = select(JobApplication).where(JobApplication.id == application_id)
                    app_res = await session.execute(app_stmt)
                    job_app = app_res.scalar_one()
                    assert job_app.status == "applied"
                    assert job_app.source == "ATS_API"
                    assert job_app.submitted_at is not None

                # Verify workflow execution logs status API endpoint
                status_resp = await client.get(
                    f"/api/v2/workflows/executions/{workflow_id}",
                    headers=headers,
                )
                assert status_resp.status_code == 200
                status_data = status_resp.json()
                assert status_data["status"] == "COMPLETED"

                # Verify execution log traces endpoint (checkpoints)
                logs_resp = await client.get(
                    f"/api/v2/applications/{application_id}/logs",
                    headers=headers,
                )
                assert logs_resp.status_code == 200
                logs_data = logs_resp.json()
                assert logs_data["status"] == "PROCESSING"
                assert len(logs_data["logs"]) > 0

                # Verify manual cancel request works (returns 202)
                cancel_resp = await client.post(
                    f"/api/v2/workflows/executions/{workflow_id}/cancel",
                    headers=headers,
                )
                assert cancel_resp.status_code == 202

                # Verify outcome memory recording (transition status to rejected)
                outcome_resp = await client.post(
                    f"/api/v2/applications/{application_id}/outcome",
                    json={
                        "new_status": "REJECTED",
                        "rejection_reason": "Failed system design interview",
                        "rejection_stage": "SYSTEM_DESIGN",
                    },
                    headers=headers,
                )
                assert outcome_resp.status_code == 200
                outcome_data = outcome_resp.json()
                assert outcome_data["final_outcome"] == "REJECTED"
                assert outcome_data["rejection_stage"] == "SYSTEM_DESIGN"
                # Assert prediction error (predicted fit 80.0 vs actual 0.0) -> 80.0
                assert outcome_data["prediction_error"] == 80.0

                # Verify dashboard outcome metrics endpoint compiles analytics
                analytics_resp = await client.get(
                    "/api/v2/applications/outcomes/analytics",
                    headers=headers,
                )
                assert analytics_resp.status_code == 200
                analytics_data = analytics_resp.json()
                assert analytics_data["total_applications"] == 1
                assert analytics_data["ghost_rate"] == 0.0


@pytest.mark.asyncio
async def test_e2e_workflow_tier2_success():
    """
    Test Tier 2: Deterministic form execution submission.
    Tier 1 fails, Tier 2 executes Workday/iCIMS form matching schema successfully.
    """
    rand_id = random.randint(1000, 9999)
    email = f"tier2_test_{rand_id}@example.com"
    password = "TestPassword123!"
    domain = f"aerocorp_{rand_id}.myworkdayjobs.com"
    _, opportunity_id, version_id, _ = await seed_user_and_opportunity(
        email, password, "AeroCorp", domain
    )

    # Register Workday Form Schema for domain
    await DeterministicFormExecutionService.register_schema(
        platform_provider="WORKDAY",
        company_domain=domain,
        fields_schema={
            "personal_details": {
                "first_name_selector": "input#fname",
                "last_name_selector": "input#lname",
                "email_selector": "input#email",
            },
            "work_experience": {
                "job_title_selector": "input#title",
                "employer_selector": "input#employer",
            }
        }
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        login_resp = await client.post(
            "/api/v2/auth/login", json={"email": email, "password": password}
        )
        headers = {"Authorization": f"Bearer {login_resp.json()['access_token']}"}

        async with await WorkflowEnvironment.start_time_skipping() as env:
            TemporalWorkflowService.set_client(env.client)

            async with Worker(
                env.client,
                task_queue="application-queue",
                workflows=[ApplicationExecutionWorkflow],
                activities=[
                    activities.prepare_application_materials,
                    activities.submit_to_ats_api,
                    activities.submit_deterministic_form,
                    activities.submit_browser_fallback,
                    activities.record_workflow_checkpoint,
                    activities.handle_workflow_execution_failure,
                    activities.record_successful_submission,
                ],
            ):
                payload = {
                    "opportunity_id": opportunity_id,
                    "resume_version_id": version_id,
                    "ats_type": "GREENHOUSE",
                    "board_token": "aerocorp",
                    "job_id": "456",
                    "company_domain": domain,
                    "application_url": f"https://{domain}/apply/456",
                }

                # Mock Tier 1 API to fail, triggering Tier 2 escalation
                mock_submit_fail = {"success": False, "status_code": 500, "error_message": "ATS endpoint down"}
                with patch("app.services.ats_integration_service.ATSIntegrationService.submit", return_value=mock_submit_fail):
                    trigger_resp = await client.post(
                        "/api/v2/applications/workflows/trigger",
                        json=payload,
                        headers=headers,
                    )
                    assert trigger_resp.status_code == 202
                    res_data = trigger_resp.json()
                    application_id = res_data["application_id"]
                    workflow_id = res_data["workflow_id"]

                    handle = env.client.get_workflow_handle(workflow_id)
                    result = await handle.result()
                    assert result["status"] == "COMPLETED"
                    assert result["method"] == "FORM"

                # Assert execution logs contain Form logs in DB
                async with AsyncSessionLocal() as session:
                    stmt = select(FormExecutionLog).where(FormExecutionLog.application_id == application_id)
                    res = await session.execute(stmt)
                    logs = res.scalars().all()
                    assert len(logs) == 3
                    assert {log.step_name for log in logs} == {"PERSONAL_INFO", "WORK_EXPERIENCE", "SUBMIT"}


@pytest.mark.asyncio
async def test_e2e_workflow_tier3_success():
    """
    Test Tier 3: Visual fallback browser submission.
    Tier 1 fails, Tier 2 fails (no schema), Tier 3 executes Playwright simulation fallback successfully.
    """
    email = f"tier3_test_{random.randint(1000, 9999)}@example.com"
    password = "TestPassword123!"
    _, opportunity_id, version_id, _ = await seed_user_and_opportunity(
        email, password, "CyberCorp", "cybercorp.com"
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        login_resp = await client.post(
            "/api/v2/auth/login", json={"email": email, "password": password}
        )
        headers = {"Authorization": f"Bearer {login_resp.json()['access_token']}"}

        async with await WorkflowEnvironment.start_time_skipping() as env:
            TemporalWorkflowService.set_client(env.client)

            async with Worker(
                env.client,
                task_queue="application-queue",
                workflows=[ApplicationExecutionWorkflow],
                activities=[
                    activities.prepare_application_materials,
                    activities.submit_to_ats_api,
                    activities.submit_deterministic_form,
                    activities.submit_browser_fallback,
                    activities.record_workflow_checkpoint,
                    activities.handle_workflow_execution_failure,
                    activities.record_successful_submission,
                ],
            ):
                payload = {
                    "opportunity_id": opportunity_id,
                    "resume_version_id": version_id,
                    "ats_type": "GREENHOUSE",
                    "board_token": "cybercorp",
                    "job_id": "789",
                    "company_domain": "cybercorp.com",  # No schema exists for cybercorp.com
                    "application_url": "https://cybercorp.com/apply/789",
                }

                # Mock Tier 1 to fail, Tier 2 will automatically fail because no schema matches
                mock_submit_fail = {"success": False, "status_code": 500, "error_message": "ATS endpoint down"}
                with patch("app.services.ats_integration_service.ATSIntegrationService.submit", return_value=mock_submit_fail):
                    trigger_resp = await client.post(
                        "/api/v2/applications/workflows/trigger",
                        json=payload,
                        headers=headers,
                    )
                    assert trigger_resp.status_code == 202
                    res_data = trigger_resp.json()
                    application_id = res_data["application_id"]
                    workflow_id = res_data["workflow_id"]

                    handle = env.client.get_workflow_handle(workflow_id)
                    result = await handle.result()
                    assert result["status"] == "COMPLETED"
                    assert result["method"] == "BROWSER"

                # Assert execution logs contain Browser logs in DB
                async with AsyncSessionLocal() as session:
                    stmt = select(BrowserExecutionLog).where(BrowserExecutionLog.application_id == application_id)
                    res = await session.execute(stmt)
                    logs = res.scalars().all()
                    assert len(logs) == 6
                    assert logs[0].action_type == "NAVIGATE"
                    assert logs[2].action_type == "FILL_INPUT"
                    assert logs[2].value_entered == "Jane"
