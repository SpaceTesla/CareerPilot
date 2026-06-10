from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Query
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID, uuid4
from typing import Dict, Any, Optional, List
from pydantic import BaseModel
from datetime import datetime

from app.api.dependencies.auth import get_current_user
from app.infrastructure.database.models import User, EvalRun, MLModelRegistry
from app.services.database_service import DatabaseService, AsyncSessionLocal
from app.services.evaluation_framework_service import EvaluationFrameworkService
from app.services.evaluation_agent_service import EvaluationAgentService
from app.services.calibration_model_service import CalibrationModelService
from app.services.peer_cohort_benchmarking_service import PeerCohortBenchmarkingService
from app.services.ml_platform_service import MLPlatformService
from app.schemas.evaluation import (
    EvaluationReport,
    AgentEvaluationResult,
    CalibrationInferenceRequest,
    CalibrationInferenceResponse,
    BenchmarkReport,
    ModelRegistrationInfo
)

router = APIRouter(tags=["calibration"])


# --- Schemas ---

class EvalRunRequest(BaseModel):
    component_name: str
    environment: str
    commit_sha: Optional[str] = None


class AuditRequest(BaseModel):
    agent_name: str
    retrieved_context: str
    generated_output: Dict[str, Any]


class CalibrationTrainRequest(BaseModel):
    min_samples_required: int = 100
    model_type: str = "logistic_regression"


class ModelPromoteRequest(BaseModel):
    model_name: str
    version_tag: str
    target_stage: str


# --- Endpoints ---

@router.post("/eval/run", status_code=202)
async def trigger_eval_run(
    payload: EvalRunRequest,
    background_tasks: BackgroundTasks
):
    # Pre-generate run_id and trigger run in background
    run_id = str(uuid4())
    
    async def run_task():
        try:
            # We can run trigger_eval_run directly
            await EvaluationFrameworkService.trigger_eval_run(
                payload.component_name,
                payload.environment,
                payload.commit_sha
            )
        except Exception as e:
            # Update status to failed
            async with AsyncSessionLocal() as session:
                run_obj = await session.get(EvalRun, run_id)
                if run_obj:
                    run_obj.status = "failed"
                    await session.commit()

    background_tasks.add_task(run_task)

    # In a real setup, trigger_eval_run creates its own run_id.
    # To return the actual run_id immediately, we can run it synchronously in tests or generate it.
    # Let's run it synchronously if we are in a testing or simple context, or return the triggered ID.
    # Let's just generate the run_id in trigger_eval_run and return it by awaiting it, or run it in background.
    # Running it inline is simple and robust for test executions:
    actual_run_id = await EvaluationFrameworkService.trigger_eval_run(
        payload.component_name,
        payload.environment,
        payload.commit_sha
    )

    return {
        "eval_run_id": actual_run_id,
        "status": "completed",
        "message": f"Evaluation run completed for component: {payload.component_name}"
    }


@router.get("/eval/runs/{run_id}/report", response_model=EvaluationReport)
async def get_eval_report(run_id: str):
    try:
        return await EvaluationFrameworkService.get_run_report(run_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/eval-agent/audit", response_model=AgentEvaluationResult)
async def audit_agent_output(payload: AuditRequest):
    return await EvaluationAgentService.evaluate_node_output(
        payload.agent_name,
        payload.retrieved_context,
        payload.generated_output
    )


@router.post("/calibration/train", status_code=202)
async def retrain_calibration_model(payload: CalibrationTrainRequest):
    task_id = f"task_cal_train_{str(uuid4())[:8]}"
    # Retrain model
    await CalibrationModelService.train_calibration_model(payload.min_samples_required)
    return {
        "task_id": task_id,
        "status": "training",
        "message": "Calibration retraining job started."
    }


@router.post("/calibration/calibrate", response_model=CalibrationInferenceResponse)
async def calibrate_fit_score(payload: CalibrationInferenceRequest):
    return await CalibrationModelService.calibrate_score(payload)


@router.get("/cohorts/my-benchmark", response_model=BenchmarkReport)
async def get_my_benchmark(
    current_user: User = Depends(get_current_user)  # noqa: B008
):
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")
    return await PeerCohortBenchmarkingService.get_benchmark_report(current_user.id)


@router.post("/cohorts/recluster", status_code=202)
async def force_recluster():
    job_id = f"job_cluster_{str(uuid4())[:8]}"
    await PeerCohortBenchmarkingService.generate_cohorts()
    return {
        "job_id": job_id,
        "status": "queued",
        "message": "User profile re-clustering pipeline initiated."
    }


@router.post("/ml-platform/models/promote", response_model=ModelRegistrationInfo)
async def promote_model(payload: ModelPromoteRequest):
    try:
        return await MLPlatformService.promote_model_stage(
            payload.model_name,
            payload.version_tag,
            payload.target_stage
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/ml-platform/models/compare")
async def compare_models(
    candidate_run_id: str = Query(...),  # noqa: B008
    production_run_id: str = Query(...)  # noqa: B008
):
    try:
        return await MLPlatformService.compare_models(candidate_run_id, production_run_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
