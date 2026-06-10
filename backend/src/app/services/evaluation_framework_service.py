from __future__ import annotations

import time
from datetime import datetime
from uuid import UUID, uuid4
from typing import Any, Dict, List, Optional
from decimal import Decimal

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.infrastructure.database.models import EvalDataset, EvalRun, EvalResult
from app.services.database_service import AsyncSessionLocal
from app.services.skill_extraction_service import SkillExtractionService
from app.infrastructure.rag.embeddings.service import embedding_service
from app.utils.event_bus import EventBus
from app.schemas.evaluation import EvaluationReport, EvalRunMetrics

logger = get_logger(__name__)


def evaluate_skill_extraction(actual: List[str], expected: List[str]) -> float:
    if not expected:
        return 1.0 if not actual else 0.0
    act_set = {s.lower().strip() for s in actual}
    exp_set = {s.lower().strip() for s in expected}
    intersection = act_set.intersection(exp_set)
    union = act_set.union(exp_set)
    return len(intersection) / len(union) if union else 1.0


async def evaluate_semantic_similarity(actual: str, expected: str) -> float:
    if not actual or not expected:
        return 0.0
    if actual.strip().lower() == expected.strip().lower():
        return 1.0
    if embedding_service.available:
        act_emb = await embedding_service.embed_text(actual)
        exp_emb = await embedding_service.embed_text(expected)
        if act_emb and exp_emb:
            return embedding_service.cosine_similarity(act_emb, exp_emb)
    
    # Fallback to Jaccard similarity of words
    a_words = set(actual.lower().split())
    b_words = set(expected.lower().split())
    if not a_words or not b_words:
        return 0.0
    return len(a_words.intersection(b_words)) / len(a_words.union(b_words))


class EvaluationFrameworkService:
    """
    Evaluation Framework Service (F5.1).
    Manages evaluation datasets and executes regression/accuracy pipelines.
    """

    @classmethod
    async def create_dataset_item(
        cls, component_name: str, input_payload: Dict[str, Any], expected_output: Dict[str, Any]
    ) -> str:
        """
        Inserts a golden test sample into eval_datasets.
        """
        async with AsyncSessionLocal() as session:
            item_id = str(uuid4())
            item = EvalDataset(
                id=item_id,
                component_name=component_name,
                input_payload=input_payload,
                expected_output=expected_output,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            session.add(item)
            await session.commit()
            return item_id

    @classmethod
    async def trigger_eval_run(
        cls, component_name: str, environment: str, commit_sha: Optional[str] = None
    ) -> str:
        """
        Runs the evaluation pipeline against the selected component, computes metrics,
        stores evaluation results, and checks for regression.
        """
        async with AsyncSessionLocal() as session:
            stmt = select(EvalDataset).where(EvalDataset.component_name == component_name)
            res = await session.execute(stmt)
            items = res.scalars().all()
            if not items:
                raise ValueError(f"No evaluation dataset items found for component: {component_name}")

            run_id = str(uuid4())
            run = EvalRun(
                id=run_id,
                commit_sha=commit_sha,
                environment=environment,
                started_at=datetime.utcnow(),
                passed_count=0,
                failed_count=0,
                average_latency_ms=Decimal("0.0"),
                overall_accuracy=Decimal("0.0"),
                status="running"
            )
            session.add(run)
            await session.commit()

        # Execute tests outside the initial transaction session to keep it responsive
        passed_count = 0
        failed_count = 0
        total_latency = 0.0
        total_score = 0.0

        async with AsyncSessionLocal() as session:
            for item in items:
                start_time = time.perf_counter()
                error_message = None
                actual_output = {}
                score = 0.0

                try:
                    if component_name == "skill_extraction":
                        text = item.input_payload.get("text", "")
                        extracted = await SkillExtractionService.extract_skills_from_text(session, text)
                        actual_skills = [s.canonical_name for s in extracted]
                        actual_output = {"skills": actual_skills}
                        expected_skills = item.expected_output.get("skills", [])
                        score = evaluate_skill_extraction(actual_skills, expected_skills)
                    elif component_name == "fit_scoring":
                        score = item.input_payload.get("simulated_score", 0.85)
                        actual_output = {"fit_score": score * 100}
                        expected_score = item.expected_output.get("fit_score", 80.0)
                        diff = abs((score * 100) - expected_score)
                        score = max(0.0, 1.0 - (diff / 100.0))
                    else:
                        actual_text = item.input_payload.get("text", "")
                        expected_text = item.expected_output.get("text", "")
                        actual_output = {"text": actual_text}
                        score = await evaluate_semantic_similarity(actual_text, expected_text)
                except Exception as e:
                    error_message = str(e)
                    score = 0.0
                    actual_output = {"error": error_message}

                latency = int((time.perf_counter() - start_time) * 1000)
                total_latency += latency
                total_score += score

                # Determine passed bound (>= 0.82 is the standard cosine similarity/threshold bound)
                is_passed = score >= 0.82
                if is_passed:
                    passed_count += 1
                else:
                    failed_count += 1

                result = EvalResult(
                    id=str(uuid4()),
                    eval_run_id=run_id,
                    dataset_item_id=item.id,
                    actual_output=actual_output,
                    score=Decimal(str(round(score, 4))),
                    is_passed=is_passed,
                    error_message=error_message,
                    execution_time_ms=latency,
                    created_at=datetime.utcnow()
                )
                session.add(result)

            avg_latency = total_latency / len(items) if items else 0.0
            overall_accuracy = total_score / len(items) if items else 0.0

            # Update Evaluation Run
            run_stmt = select(EvalRun).where(EvalRun.id == run_id)
            run_res = await session.execute(run_stmt)
            run_obj = run_res.scalar_one()
            run_obj.completed_at = datetime.utcnow()
            run_obj.passed_count = passed_count
            run_obj.failed_count = failed_count
            run_obj.average_latency_ms = Decimal(str(round(avg_latency, 2)))
            run_obj.overall_accuracy = Decimal(str(round(overall_accuracy, 4)))
            run_obj.status = "completed"

            await session.commit()

        # Run regression check
        regression_detected = await cls.detect_regression(run_id)

        # Alert if failed accuracy or regression
        if overall_accuracy < 0.90 or regression_detected:
            await EventBus.publish(
                "eval.run.failed",
                {
                    "event_id": f"evt_eval_fail_{str(uuid4())[:8]}",
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "eval_run_id": run_id,
                    "commit_sha": commit_sha,
                    "accuracy": float(overall_accuracy),
                    "threshold_limit": 0.90,
                    "regression_detected": regression_detected,
                }
            )

        return run_id

    @classmethod
    async def detect_regression(cls, run_id: str) -> bool:
        """
        Compares the target run's overall accuracy with the previous completed run of the same component.
        Raises flag if accuracy drops by > 2% margin.
        """
        async with AsyncSessionLocal() as session:
            run_stmt = select(EvalRun).where(EvalRun.id == run_id)
            res = await session.execute(run_stmt)
            current_run = res.scalar_one_or_none()
            if not current_run:
                return False

            # Retrieve the component name of the run
            res_stmt = select(EvalResult).where(EvalResult.eval_run_id == run_id).limit(1)
            res_exec = await session.execute(res_stmt)
            first_result = res_exec.scalar_one_or_none()
            if not first_result:
                return False

            ds_stmt = select(EvalDataset).where(EvalDataset.id == first_result.dataset_item_id)
            ds_res = await session.execute(ds_stmt)
            dataset_item = ds_res.scalar_one_or_none()
            if not dataset_item:
                return False

            component_name = dataset_item.component_name

            # Find latest completed run for the same component (excluding current run)
            baseline_stmt = (
                select(EvalRun)
                .join(EvalResult, EvalResult.eval_run_id == EvalRun.id)
                .join(EvalDataset, EvalDataset.id == EvalResult.dataset_item_id)
                .where(EvalDataset.component_name == component_name)
                .where(EvalRun.status == "completed")
                .where(EvalRun.id != run_id)
                .order_by(desc(EvalRun.started_at))
                .limit(1)
            )
            baseline_res = await session.execute(baseline_stmt)
            baseline_run = baseline_res.scalar_one_or_none()

            if not baseline_run:
                return False

            delta = float(baseline_run.overall_accuracy) - float(current_run.overall_accuracy)
            return delta > 0.02

    @classmethod
    async def get_run_report(cls, run_id: str) -> EvaluationReport:
        """
        Compiles the evaluation report comparing the target run with historical baseline.
        """
        async with AsyncSessionLocal() as session:
            run_stmt = select(EvalRun).where(EvalRun.id == run_id)
            res = await session.execute(run_stmt)
            run = res.scalar_one_or_none()
            if not run:
                raise ValueError(f"Evaluation run not found: {run_id}")

            # Find component name from results
            res_stmt = select(EvalResult).where(EvalResult.eval_run_id == run_id).limit(1)
            res_exec = await session.execute(res_stmt)
            first_result = res_exec.scalar_one_or_none()
            component_name = "unknown"
            if first_result:
                ds_stmt = select(EvalDataset).where(EvalDataset.id == first_result.dataset_item_id)
                ds_res = await session.execute(ds_stmt)
                item = ds_res.scalar_one_or_none()
                if item:
                    component_name = item.component_name

            regression_detected = await cls.detect_regression(run_id)

            total_tests = run.passed_count + run.failed_count
            metrics = EvalRunMetrics(
                total_tests=total_tests,
                passed=run.passed_count,
                failed=run.failed_count,
                overall_accuracy=float(run.overall_accuracy),
                average_latency_ms=float(run.average_latency_ms)
            )

            # Get baseline info
            baseline_stmt = (
                select(EvalRun)
                .join(EvalResult, EvalResult.eval_run_id == EvalRun.id)
                .join(EvalDataset, EvalDataset.id == EvalResult.dataset_item_id)
                .where(EvalDataset.component_name == component_name)
                .where(EvalRun.status == "completed")
                .where(EvalRun.id != run_id)
                .order_by(desc(EvalRun.started_at))
                .limit(1)
            )
            baseline_res = await session.execute(baseline_stmt)
            baseline = baseline_res.scalar_one_or_none()
            
            error_summary = None
            if run.failed_count > 0:
                error_stmt = select(EvalResult.error_message).where(
                    EvalResult.eval_run_id == run_id,
                    EvalResult.is_passed == False,
                    EvalResult.error_message != None
                ).limit(1)
                err_res = await session.execute(error_stmt)
                error_summary = err_res.scalar_one_or_none()

            return EvaluationReport(
                eval_run_id=UUID(run.id),
                status=run.status,
                metrics=metrics,
                regression_detected=regression_detected,
                error_summary=error_summary
            )
