from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field


class GraphNode(BaseModel):
    id: str
    label: str
    properties: dict[str, Any]


class GraphEdge(BaseModel):
    source_id: str
    target_id: str
    relationship_type: str
    properties: dict[str, Any]


class CareerPathStep(BaseModel):
    step_index: int
    source_role: str
    target_role: str
    avg_transition_time_months: float
    common_bridge_skills: list[str]
    confidence_score: float


class CareerPath(BaseModel):
    steps: list[CareerPathStep]
    path_probability: float


class CareerPathResponse(BaseModel):
    paths: list[CareerPath]


class RelatedSkillItem(BaseModel):
    skill_name: str
    relationship: str
    weight: float


class RelatedSkillsResponse(BaseModel):
    searched_skill: str
    related_skills: list[RelatedSkillItem]


class GraphSyncResponse(BaseModel):
    task_id: str
    status: str
    message: str
