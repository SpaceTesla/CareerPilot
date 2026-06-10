from __future__ import annotations

import json
from decimal import Decimal
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_user
from app.infrastructure.database.models import ProfileVersion, UploadedResume, User
from app.schemas.profile import (
    ProfileResponse,
    ProfileUpdate,
    ProfileVersionResponse,
    ResumeSyncRequest,
    ResumeUploadResponse,
)
from app.services.database_service import DatabaseService
from app.services.llm_parser_service import LLMParserService
from app.services.profile_service import ProfileService
from app.services.profile_sync_service import ProfileSyncService
from app.services.resume_extractor_service import ResumeExtractorService
from app.services.dashboard_service import DashboardAggregationService

router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("", response_model=ProfileResponse)
async def get_profile(
    current_user: User = Depends(get_current_user),  # noqa: B008
    db: AsyncSession = Depends(DatabaseService.get_session),  # noqa: B008
):
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )
    profile = await ProfileService.get_by_user_id(db, UUID(current_user.id))
    return profile


@router.put("", response_model=ProfileResponse)
async def update_profile(
    data: ProfileUpdate,
    current_user: User = Depends(get_current_user),  # noqa: B008
    db: AsyncSession = Depends(DatabaseService.get_session),  # noqa: B008
):
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )
    profile = await ProfileService.update_profile(db, UUID(current_user.id), data)
    await DashboardAggregationService.invalidate_cache(current_user.id)
    return profile


@router.get("/versions", response_model=list[ProfileVersionResponse])
async def get_versions(
    current_user: User = Depends(get_current_user),  # noqa: B008
    db: AsyncSession = Depends(DatabaseService.get_session),  # noqa: B008
):
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )
    profile = await ProfileService.get_by_user_id(db, UUID(current_user.id))
    stmt = (
        select(ProfileVersion)
        .where(ProfileVersion.profile_id == profile.id)
        .order_by(ProfileVersion.version_number.desc())
    )
    res = await db.execute(stmt)
    versions = res.scalars().all()
    return versions


@router.post("/versions/{version_number}/restore", response_model=ProfileResponse)
async def restore_version(
    version_number: int,
    current_user: User = Depends(get_current_user),  # noqa: B008
    db: AsyncSession = Depends(DatabaseService.get_session),  # noqa: B008
):
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )
    profile = await ProfileService.restore_version(
        db, UUID(current_user.id), version_number
    )
    await DashboardAggregationService.invalidate_cache(current_user.id)
    return profile


@router.post("/upload", response_model=ResumeUploadResponse)
async def upload_resume(
    file: UploadFile = File(...),  # noqa: B008
    current_user: User = Depends(get_current_user),  # noqa: B008
    db: AsyncSession = Depends(DatabaseService.get_session),  # noqa: B008
):
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    file_bytes = await file.read()
    raw_text = ResumeExtractorService.extract_text(file_bytes, file.filename)
    normalized_text = ResumeExtractorService.normalize_text(raw_text)

    if len(normalized_text.strip()) < 50:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "Extracted text is too short. "
                "The file might be empty or a scanned image/PDF."
            ),
        )

    parsed_data, confidence_score = await LLMParserService.parse_resume_text(
        normalized_text
    )

    profile = await ProfileService.get_by_user_id(db, UUID(current_user.id))

    uploaded_resume = UploadedResume(
        id=str(uuid4()),
        profile_id=profile.id,
        file_name=file.filename,
        file_size=len(file_bytes),
        content_type=file.content_type,
        raw_text=normalized_text,
        parsed_payload=json.loads(parsed_data.model_dump_json()),
        confidence_score=Decimal(str(round(confidence_score, 2))),
        is_synced=False,
    )
    db.add(uploaded_resume)
    await db.flush()

    return ResumeUploadResponse(
        resume_id=UUID(uploaded_resume.id),
        confidence_score=uploaded_resume.confidence_score,
        parsed_data=parsed_data,
    )


@router.post("/sync-resume", response_model=ProfileResponse)
async def sync_resume(
    request: ResumeSyncRequest,
    current_user: User = Depends(get_current_user),  # noqa: B008
    db: AsyncSession = Depends(DatabaseService.get_session),  # noqa: B008
):
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    profile = await ProfileSyncService.sync_resume(
        db=db,
        user_id=UUID(current_user.id),
        resume_id=request.resume_id,
        override_data=request.override_data,
    )
    await DashboardAggregationService.invalidate_cache(current_user.id)
    return profile
