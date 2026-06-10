from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_user
from app.infrastructure.database.models import User
from app.schemas.auth import (
    CareerGoalsResponse,
    CareerGoalsUpdate,
    UserPreferencesResponse,
    UserPreferencesUpdate,
)
from app.services.database_service import DatabaseService
from app.services.identity_service import IdentityService
from app.services.dashboard_service import DashboardAggregationService

router = APIRouter(prefix="/identity", tags=["identity"])


@router.get("/preferences", response_model=UserPreferencesResponse)
async def get_preferences(
    current_user: User = Depends(get_current_user),  # noqa: B008
    db: AsyncSession = Depends(DatabaseService.get_session),  # noqa: B008
):
    """
    Fetches the current user's preferences.
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )
    pref = await IdentityService.get_preferences(db, current_user.id)
    return pref


@router.put("/preferences", response_model=UserPreferencesResponse)
async def update_preferences(
    pref_in: UserPreferencesUpdate,
    current_user: User = Depends(get_current_user),  # noqa: B008
    db: AsyncSession = Depends(DatabaseService.get_session),  # noqa: B008
):
    """
    Updates the current user's preferences.
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )
    pref = await IdentityService.update_preferences(db, current_user.id, pref_in)
    return pref


@router.get("/goals", response_model=CareerGoalsResponse)
async def get_goals(
    current_user: User = Depends(get_current_user),  # noqa: B008
    db: AsyncSession = Depends(DatabaseService.get_session),  # noqa: B008
):
    """
    Fetches the current user's career goals.
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )
    goals = await IdentityService.get_goals(db, current_user.id)
    return goals


@router.put("/goals", response_model=CareerGoalsResponse)
async def update_goals(
    goals_in: CareerGoalsUpdate,
    current_user: User = Depends(get_current_user),  # noqa: B008
    db: AsyncSession = Depends(DatabaseService.get_session),  # noqa: B008
):
    """
    Updates the current user's career goals.
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )
    goals = await IdentityService.update_goals(db, current_user.id, goals_in)
    await DashboardAggregationService.invalidate_cache(current_user.id)
    return goals
