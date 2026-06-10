"""ATS (Applicant Tracking System) API Submission Service."""

from __future__ import annotations

import time
from datetime import datetime
from uuid import uuid4
from typing import Any, Dict, Optional
import httpx

from app.core.logging import get_logger
from app.infrastructure.database.models import ATSAuditLog
from app.services.database_service import AsyncSessionLocal

logger = get_logger(__name__)


class ATSIntegrationService:
    """Service to handle direct API applications to Greenhouse, Lever, and Ashby boards."""

    @classmethod
    async def submit(
        cls,
        ats_type: str,
        board_token: str,
        job_id: str,
        profile_data: Dict[str, Any],
        resume_bytes: bytes,
        resume_filename: str = "resume.pdf",
        cover_letter_text: Optional[str] = None,
        custom_answers: Optional[Dict[str, Any]] = None,
        application_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Map candidate profile data to ATS specific formats and execute direct API POST submission.
        """
        ats_type = ats_type.upper()
        start_time = time.perf_counter()
        
        request_url = ""
        request_headers: Dict[str, str] = {"User-Agent": "CareerPilot/v2"}
        request_body: Dict[str, Any] = {}
        files: Dict[str, Any] = {}
        
        # Combine names if needed
        first_name = profile_data.get("first_name", "")
        last_name = profile_data.get("last_name", "")
        full_name = f"{first_name} {last_name}".strip()
        email = profile_data.get("email", "")
        phone = profile_data.get("phone", "")
        
        if ats_type == "GREENHOUSE":
            # Greenhouse Public Board Apply Endpoint
            request_url = f"https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs/{job_id}/apply"
            
            # Construct multi-part data
            request_body = {
                "first_name": first_name,
                "last_name": last_name,
                "email": email,
            }
            if phone:
                request_body["phone"] = phone
            
            # Map custom answers to Greenhouse format (typically question_{id})
            if custom_answers:
                for k, v in custom_answers.items():
                    request_body[k] = str(v)
            
            files = {
                "resume": (resume_filename, resume_bytes, "application/pdf")
            }
            if cover_letter_text:
                request_body["cover_letter_text"] = cover_letter_text
                
        elif ats_type == "LEVER":
            # Lever Apply Endpoint
            request_url = f"https://api.lever.co/v1/jobs/{job_id}/apply"
            
            request_body = {
                "name": full_name,
                "email": email,
            }
            if phone:
                request_body["phone"] = phone
            if cover_letter_text:
                request_body["comments"] = cover_letter_text
                
            # Custom questions mapping
            if custom_answers:
                for k, v in custom_answers.items():
                    request_body[k] = str(v)
                    
            files = {
                "resume": (resume_filename, resume_bytes, "application/pdf")
            }
            
        elif ats_type == "ASHBY":
            # Ashby Job Board Endpoint (typically JSON or multipart)
            request_url = f"https://api.ashbyhq.com/v1/vacancies/{job_id}/apply"
            
            request_body = {
                "name": full_name,
                "email": email,
                "resumeUrl": "https://storage.careerpilot.io/resumes/mock_resume.pdf"
            }
            if phone:
                request_body["phone"] = phone
            if cover_letter_text:
                request_body["coverLetterText"] = cover_letter_text
            if custom_answers:
                request_body["customAnswers"] = custom_answers
                
            request_headers["Content-Type"] = "application/json"
            
        else:
            return {
                "success": False,
                "status_code": 400,
                "error_message": f"Unsupported ATS type: {ats_type}",
                "raw_response": "",
                "latency_ms": 0
            }

        response_status = 200
        response_body = "Mock success response"
        
        # Perform actual HTTP call if not running in purely local mock mode
        # (For integration testing, we can mock this or let the tests intercept it)
        try:
            async with httpx.AsyncClient() as client:
                if ats_type == "ASHBY":
                    # Send JSON
                    res = await client.post(request_url, json=request_body, headers=request_headers, timeout=30.0)
                else:
                    # Send multipart
                    res = await client.post(request_url, data=request_body, files=files, headers=request_headers, timeout=30.0)
                
                response_status = res.status_code
                response_body = res.text
        except Exception as e:
            logger.error(f"HTTP call failed for {ats_type} submission: {e}")
            response_status = 500
            response_body = f"Connection failed: {str(e)}"

        latency_ms = int((time.perf_counter() - start_time) * 1000)
        success = (200 <= response_status < 300)
        
        # Log to ats_audit_logs if application_id is provided
        if application_id:
            async with AsyncSessionLocal() as session:
                audit_log = ATSAuditLog(
                    id=str(uuid4()),
                    application_id=application_id,
                    ats_type=ats_type,
                    request_url=request_url,
                    request_headers=request_headers,
                    request_body={k: (str(v) if k != "resume_bytes" else "<binary>") for k, v in request_body.items()},
                    response_status=response_status,
                    response_body=response_body[:1000],  # Truncate large responses
                    latency_ms=latency_ms,
                    created_at=datetime.utcnow(),
                )
                session.add(audit_log)
                await session.commit()
                
        return {
            "success": success,
            "status_code": response_status,
            "confirmation_id": "conf-" + str(uuid4())[:8] if success else None,
            "error_message": response_body if not success else None,
            "raw_response": response_body,
            "latency_ms": latency_ms
        }
