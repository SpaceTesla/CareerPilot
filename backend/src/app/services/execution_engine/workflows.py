"""Temporal workflow coordinating the multi-tiered job application submission engine."""

from __future__ import annotations

from datetime import timedelta
from typing import Any, Dict
from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    import app.services.execution_engine.activities as activities


@workflow.defn
class ApplicationExecutionWorkflow:
    """Temporal workflow managing the Three-Tier job application submission process."""

    @workflow.run
    async def run(self, input_payload: Dict[str, Any]) -> Dict[str, Any]:
        application_id = input_payload.get("application_id", "")
        ats_type = input_payload.get("ats_type")
        board_token = input_payload.get("board_token")
        job_id = input_payload.get("job_id")
        company_domain = input_payload.get("company_domain", "")
        application_url = input_payload.get("application_url", "")
        cover_letter = input_payload.get("cover_letter_text")
        custom_answers = input_payload.get("custom_answers")

        # Retry policy for HTTP operations
        retry_policy = RetryPolicy(
            initial_interval=timedelta(seconds=1),
            backoff_coefficient=2.0,
            maximum_interval=timedelta(seconds=10),
            maximum_attempts=3,
        )

        # Step 1: PREPARING state
        current_state = "PREPARING"
        await workflow.execute_activity(
            activities.record_workflow_checkpoint,
            {
                "application_id": application_id,
                "state": current_state,
                "payload": {"status": "preparing_materials"},
            },
            start_to_close_timeout=timedelta(seconds=10),
        )

        materials = await workflow.execute_activity(
            activities.prepare_application_materials,
            application_id,
            start_to_close_timeout=timedelta(seconds=30),
        )
        
        profile_data = materials["profile_data"]
        resume_bytes = materials["resume_bytes"]
        resume_filename = materials["resume_filename"]

        # Step 2: Attempt Tier 1 - ATS API Submission
        if ats_type and board_token and job_id:
            current_state = "ATS_SUBMISSION"
            await workflow.execute_activity(
                activities.record_workflow_checkpoint,
                {
                    "application_id": application_id,
                    "state": current_state,
                    "payload": {"ats_type": ats_type, "job_id": job_id},
                },
                start_to_close_timeout=timedelta(seconds=10),
            )

            try:
                ats_res = await workflow.execute_activity(
                    activities.submit_to_ats_api,
                    {
                        "ats_type": ats_type,
                        "board_token": board_token,
                        "job_id": job_id,
                        "profile_data": profile_data,
                        "resume_bytes": resume_bytes,
                        "resume_filename": resume_filename,
                        "cover_letter": cover_letter,
                        "custom_answers": custom_answers,
                        "application_id": application_id,
                    },
                    start_to_close_timeout=timedelta(seconds=45),
                    retry_policy=retry_policy,
                )
                
                if ats_res.get("success"):
                    # Success
                    await workflow.execute_activity(
                        activities.record_successful_submission,
                        {"application_id": application_id, "method": "ATS_API"},
                        start_to_close_timeout=timedelta(seconds=20),
                    )
                    return {
                        "status": "COMPLETED",
                        "method": "ATS_API",
                        "response": ats_res,
                    }
                else:
                    workflow.logger.warn(f"ATS API submission failed: {ats_res.get('error_message')}. Escalating to Form Submission.")
            except Exception as e:
                workflow.logger.error(f"ATS API submission threw exception: {e}. Escalating to Form Submission.")

        # Step 3: Attempt Tier 2 - Deterministic Form Submission
        if company_domain:
            current_state = "FORM_SUBMISSION"
            await workflow.execute_activity(
                activities.record_workflow_checkpoint,
                {
                    "application_id": application_id,
                    "state": current_state,
                    "payload": {"company_domain": company_domain},
                },
                start_to_close_timeout=timedelta(seconds=10),
            )

            try:
                form_success = await workflow.execute_activity(
                    activities.submit_deterministic_form,
                    {
                        "application_id": application_id,
                        "company_domain": company_domain,
                        "profile_data": profile_data,
                        "resume_bytes": resume_bytes,
                    },
                    start_to_close_timeout=timedelta(seconds=60),
                    retry_policy=retry_policy,
                )
                
                if form_success:
                    await workflow.execute_activity(
                        activities.record_successful_submission,
                        {"application_id": application_id, "method": "FORM"},
                        start_to_close_timeout=timedelta(seconds=20),
                    )
                    return {
                        "status": "COMPLETED",
                        "method": "FORM",
                    }
                else:
                    workflow.logger.warn("Form Submission failed. Escalating to Browser Fallback.")
            except Exception as e:
                workflow.logger.error(f"Form Submission threw exception: {e}. Escalating to Browser Fallback.")

        # Step 4: Attempt Tier 3 - Browser Fallback Submission
        current_state = "BROWSER_SUBMISSION"
        await workflow.execute_activity(
            activities.record_workflow_checkpoint,
            {
                "application_id": application_id,
                "state": current_state,
                "payload": {"application_url": application_url},
            },
            start_to_close_timeout=timedelta(seconds=10),
        )

        try:
            browser_success = await workflow.execute_activity(
                activities.submit_browser_fallback,
                {
                    "application_id": application_id,
                    "application_url": application_url,
                    "profile_data": profile_data,
                    "resume_bytes": resume_bytes,
                },
                start_to_close_timeout=timedelta(seconds=120),
            )
            
            if browser_success:
                await workflow.execute_activity(
                    activities.record_successful_submission,
                    {"application_id": application_id, "method": "BROWSER"},
                    start_to_close_timeout=timedelta(seconds=20),
                )
                return {
                    "status": "COMPLETED",
                    "method": "BROWSER",
                }
            else:
                raise RuntimeError("Browser fallback submission failed.")
        except Exception as e:
            workflow.logger.error(f"Browser fallback execution failed: {e}")
            await workflow.execute_activity(
                activities.handle_workflow_execution_failure,
                {
                    "application_id": application_id,
                    "failed_state": current_state,
                    "error": str(e),
                },
                start_to_close_timeout=timedelta(seconds=20),
            )
            return {
                "status": "FAILED",
                "error": str(e),
            }


@workflow.defn
class WeeklyDigestWorkflow:
    """Temporal workflow that runs weekly, generates, and sends digests to users."""

    @workflow.run
    async def run(self, input_payload: Dict[str, Any]) -> Dict[str, Any]:
        user_id = input_payload.get("user_id")

        # Compile digest
        digest_res = await workflow.execute_activity(
            activities.generate_digest_activity,
            user_id,
            start_to_close_timeout=timedelta(seconds=60),
        )

        # Send digest email
        send_res = await workflow.execute_activity(
            activities.send_digest_email_activity,
            digest_res["digest_id"],
            start_to_close_timeout=timedelta(seconds=60),
        )

        return {
            "status": "COMPLETED",
            "digest_id": digest_res["digest_id"],
            "sent_successfully": send_res
        }


@workflow.defn
class MonthlyReviewWorkflow:
    """Temporal workflow that triggers monthly strategy reviews for a user."""

    @workflow.run
    async def run(self, input_payload: Dict[str, Any]) -> Dict[str, Any]:
        user_id = input_payload.get("user_id")

        # Initiate review activity
        review_id = await workflow.execute_activity(
            activities.initiate_strategy_review_activity,
            user_id,
            start_to_close_timeout=timedelta(seconds=60),
        )

        return {
            "status": "COMPLETED",
            "review_id": review_id
        }
