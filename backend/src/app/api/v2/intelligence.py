from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_user
from app.infrastructure.database.models import User
from app.schemas.intelligence import CareerHealthScoreResponse, PositionDeltaResponse
from app.services.database_service import DatabaseService
from app.services.career_health_service import CareerHealthService
from app.services.position_delta_service import PositionDeltaService

router = APIRouter(prefix="/intelligence", tags=["intelligence"])


@router.get("/health-score", response_model=CareerHealthScoreResponse)
async def get_health_score(
    current_user: User = Depends(get_current_user),  # noqa: B008
    db: AsyncSession = Depends(DatabaseService.get_session),  # noqa: B008
):
    """Fetch or compute the latest Career Health Score."""
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )
    health = await CareerHealthService.compute_health_score(db, current_user.id)
    if not health:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Career goals not set; cannot compute health score.",
        )
    return health


@router.get("/delta", response_model=PositionDeltaResponse)
async def get_position_delta(
    current_user: User = Depends(get_current_user),  # noqa: B008
    db: AsyncSession = Depends(DatabaseService.get_session),  # noqa: B008
):
    """Fetch or compute the latest position/skills gaps delta."""
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )
    delta = await PositionDeltaService.calculate_position_delta(db, current_user.id)
    if not delta:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Career goals not set; cannot compute position delta.",
        )
    return delta
