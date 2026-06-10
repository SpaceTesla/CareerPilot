from __future__ import annotations

from datetime import datetime
from typing import Any
from pydantic import BaseModel, ConfigDict


class CareerHealthScoreResponse(BaseModel):
    score: float
    skill_alignment_score: float
    market_positioning_score: float
    activity_health_score: float
    compensation_alignment_score: float
    profile_completeness_score: float
    primary_insight: str
    top_driver: str
    top_detractor: str
    computed_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PositionDeltaResponse(BaseModel):
    target_role: str
    missing_skills: list[dict[str, Any]]
    top_3_prioritized_gaps: list[dict[str, Any]]
    recommendation_summary: str
    computed_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OpportunitySpotlightResponse(BaseModel):
    job_id: str
    title: str
    company_name: str
    location: str
    compensation_min: float | None = None
    compensation_max: float | None = None
    fit_score: float
    skill_fit_score: float
    experience_fit_score: float
    compensation_fit_score: float
    company_attractiveness_score: float
    explanation: dict[str, Any]


class DashboardResponse(BaseModel):
    health_score: CareerHealthScoreResponse | None = None
    position_delta: PositionDeltaResponse | None = None
    opportunity_spotlight: list[OpportunitySpotlightResponse] = []


class AnalyticsEventCreate(BaseModel):
    event_type: str
    widget_name: str | None = None
    metadata_json: dict[str, Any] = {}
