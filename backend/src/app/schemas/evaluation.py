from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional, Tuple
from uuid import UUID
from datetime import datetime

class EvalDatasetItem(BaseModel):
    id: UUID
    component_name: str
    input_payload: Dict[str, Any]
    expected_output: Dict[str, Any]

class EvalRunMetrics(BaseModel):
    total_tests: int
    passed: int
    failed: int
    overall_accuracy: float = Field(ge=0.0, le=1.0)
    average_latency_ms: float

class EvaluationReport(BaseModel):
    eval_run_id: UUID
    status: str
    metrics: EvalRunMetrics
    regression_detected: bool
    error_summary: Optional[str] = None

class AgentEvaluationResult(BaseModel):
    passed: bool = Field(description="True if all scores are above minimum thresholds and safety checks passed.")
    faithfulness_score: float = Field(ge=0.0, le=1.0, description="Measures factual alignment with input sources.")
    relevance_score: float = Field(ge=0.0, le=1.0, description="Measures target query satisfaction.")
    schema_compliance_score: float = Field(ge=0.0, le=1.0, description="Measures adherence to schema types.")
    critical_failures: List[str] = Field(default_factory=list)
    rejection_feedback: Optional[str] = Field(None, description="Detailed instruction to route back to worker node for repair.")

class CalibrationInferenceRequest(BaseModel):
    raw_fit_score: float = Field(description="Raw heuristic score from F3.4")
    features: Dict[str, float] = Field(description="Extracted feature variables for calibration scaling.")

class CalibrationInferenceResponse(BaseModel):
    model_version: str
    raw_fit_score: float
    calibrated_probability: float = Field(ge=0.0, le=1.0)
    confidence_interval: Tuple[float, float]

class CohortPeerGap(BaseModel):
    skill: str
    peer_adoption_rate: float = Field(ge=0.0, le=1.0)
    priority: str

class UserPercentiles(BaseModel):
    salary: float = Field(ge=0.0, le=100.0)
    skills_count: float = Field(ge=0.0, le=100.0)
    interview_rate: float = Field(ge=0.0, le=100.0)

class BenchmarkReport(BaseModel):
    user_id: UUID
    cohort_name: str
    member_count: int
    median_salary: float
    my_percentiles: UserPercentiles
    actionable_gaps: List[CohortPeerGap]

class ModelRegistrationInfo(BaseModel):
    model_name: str
    mlflow_run_id: str
    version_tag: str
    current_stage: str = Field(description="Stage: 'Candidate', 'Staging', 'Production', 'Archived'")
    accuracy_metrics: Dict[str, Any]
    registered_at: datetime

class ModelPromotionRequest(BaseModel):
    model_name: str
    version_tag: str
    target_stage: str
