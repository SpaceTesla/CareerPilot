from __future__ import annotations

import json
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.models import CareerProfile, UploadedResume
from app.schemas.profile import ProfileUpdate
from app.services.profile_service import ProfileService


class ProfileSyncService:
    """
    Orchestrates gate-controlled synchronization of parsed resume text
    into the active career profile.
    """

    @staticmethod
    async def sync_resume(
        db: AsyncSession, user_id: UUID, resume_id: UUID, override_data: ProfileUpdate
    ) -> CareerProfile:
        """
        Commits the parsed/overridden resume details into the active profile.
        Marks the UploadedResume as synced, triggers profile versioning,
        and returns the updated profile.
        """
        # Fetch the uploaded resume and verify it belongs to the user's career profile
        stmt = (
            select(UploadedResume)
            .join(CareerProfile)
            .where(
                UploadedResume.id == str(resume_id),
                CareerProfile.user_id == str(user_id),
            )
        )
        res = await db.execute(stmt)
        uploaded_resume = res.scalar_one_or_none()

        if not uploaded_resume:
            raise HTTPException(
                status_code=404,
                detail="Uploaded resume not found or access denied.",
            )

        # Update the active career profile with the override data (new ProfileVersion)
        updated_profile = await ProfileService.update_profile(
            db=db, user_id=user_id, data=override_data
        )

        # Mark resume as synced and save the final payload
        uploaded_resume.is_synced = True
        # Convert Pydantic model to a clean JSON-compatible dictionary
        uploaded_resume.parsed_payload = json.loads(override_data.model_dump_json())

        await db.flush()

        return updated_profile
