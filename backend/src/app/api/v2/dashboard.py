from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_user
from app.infrastructure.database.models import User
from app.schemas.intelligence import DashboardResponse, AnalyticsEventCreate
from app.services.database_service import DatabaseService
from app.services.dashboard_service import DashboardAggregationService, AnalyticsService

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("", response_model=DashboardResponse)
async def get_dashboard(
    force_refresh: bool = False,
    current_user: User = Depends(get_current_user),  # noqa: B008
):
    """Get the aggregated dashboard widgets, utilizing Redis cache."""
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )
    return await DashboardAggregationService.get_dashboard_payload(
        current_user.id, force_refresh=force_refresh
    )


@router.post("/analytics", status_code=status.HTTP_201_CREATED)
async def log_analytics_event(
    event_in: AnalyticsEventCreate,
    current_user: User = Depends(get_current_user),  # noqa: B008
    db: AsyncSession = Depends(DatabaseService.get_session),  # noqa: B008
):
    """Log an interaction or click event in the dashboard."""
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )
    event = await AnalyticsService.log_dashboard_event(
        db,
        current_user.id,
        event_in.event_type,
        event_in.widget_name,
        event_in.metadata_json,
    )
    return {"status": "success", "event_id": event.id}
