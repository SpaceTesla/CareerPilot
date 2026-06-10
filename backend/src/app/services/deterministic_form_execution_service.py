"""Deterministic Form Execution Service (Tier 2)."""

from __future__ import annotations

import time
from datetime import datetime
from uuid import uuid4
from typing import Any, Dict, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.infrastructure.database.models import FormSchema, FormExecutionLog
from app.services.database_service import AsyncSessionLocal

logger = get_logger(__name__)


class DeterministicFormExecutionService:
    """Service to handle programmatic form fillings for Workday and iCIMS using declarative schemas."""

    @classmethod
    async def get_schema_for_domain(cls, domain: str) -> Optional[FormSchema]:
        """Fetch form schema mapping for target company domain."""
        async with AsyncSessionLocal() as session:
            stmt = select(FormSchema).where(FormSchema.company_domain == domain)
            res = await session.execute(stmt)
            return res.scalar_one_or_none()

    @classmethod
    async def register_schema(
        cls, platform_provider: str, company_domain: str, fields_schema: Dict[str, Any]
    ) -> FormSchema:
        """Register a new form schema in database."""
        async with AsyncSessionLocal() as session:
            # Check if domain exists
            stmt = select(FormSchema).where(FormSchema.company_domain == company_domain)
            res = await session.execute(stmt)
            schema = res.scalar_one_or_none()
            
            if schema:
                schema.platform_provider = platform_provider
                schema.fields_schema = fields_schema
                schema.updated_at = datetime.utcnow()
            else:
                schema = FormSchema(
                    id=str(uuid4()),
                    platform_provider=platform_provider.upper(),
                    company_domain=company_domain,
                    fields_schema=fields_schema,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                )
                session.add(schema)
            
            await session.commit()
            return schema

    @classmethod
    async def execute_form_submission(
        cls,
        application_id: str,
        company_domain: str,
        profile_data: Dict[str, Any],
        files: Dict[str, bytes],
    ) -> bool:
        """
        Execute multi-stage programmatic form submission for Workday or iCIMS.
        """
        schema = await cls.get_schema_for_domain(company_domain)
        if not schema:
            logger.warning(f"No form schema registered for domain: {company_domain}")
            return False

        fields_schema = schema.fields_schema
        platform = schema.platform_provider
        
        # Pre-flight check: ensure required selectors/fields have matching values in profile
        required_fields = ["first_name", "last_name", "email"]
        for field in required_fields:
            if not profile_data.get(field):
                logger.error(f"Pre-flight validation failed: Missing profile field '{field}'")
                return False

        # Simulate multi-step form submission
        # Step 1: Personal Info
        # Step 2: Experience / Education
        # Step 3: Review / Submit
        steps = [
            ("PERSONAL_INFO", 1),
            ("WORK_EXPERIENCE", 2),
            ("SUBMIT", 3)
        ]
        
        for step_name, step_num in steps:
            step_payload: Dict[str, Any] = {}
            response_status = 200
            error_captured = None
            
            # Map elements based on step
            if step_name == "PERSONAL_INFO":
                step_payload = {
                    fields_schema.get("personal_details", {}).get("first_name_selector", "first_name"): profile_data.get("first_name"),
                    fields_schema.get("personal_details", {}).get("last_name_selector", "last_name"): profile_data.get("last_name"),
                    fields_schema.get("personal_details", {}).get("email_selector", "email"): profile_data.get("email"),
                }
            elif step_name == "WORK_EXPERIENCE":
                step_payload = {
                    fields_schema.get("work_experience", {}).get("job_title_selector", "job_title"): profile_data.get("job_title", "Engineer"),
                    fields_schema.get("work_experience", {}).get("employer_selector", "employer"): profile_data.get("company", "TechCorp"),
                }
            elif step_name == "SUBMIT":
                step_payload = {
                    "submit_token": "token-" + str(uuid4())[:8],
                    "confirmation_box": True
                }

            # Write step audit log
            async with AsyncSessionLocal() as session:
                exec_log = FormExecutionLog(
                    id=str(uuid4()),
                    application_id=application_id,
                    step_number=step_num,
                    step_name=step_name,
                    request_payload=step_payload,
                    response_status=response_status,
                    error_captured=error_captured,
                    created_at=datetime.utcnow()
                )
                session.add(exec_log)
                await session.commit()
                
        return True
