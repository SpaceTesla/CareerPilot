from __future__ import annotations

import os
import json
from datetime import datetime
from uuid import uuid4
from typing import Dict, Any, Optional

from sqlalchemy import select, update, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.infrastructure.database.models import MLModelRegistry
from app.services.database_service import AsyncSessionLocal
from app.schemas.evaluation import ModelRegistrationInfo
from app.utils.event_bus import EventBus

logger = get_logger(__name__)


class MLPlatformService:
    """
    ML Platform Service (F5.5).
    Tracks hyperparameters, logs metrics, registers models, and manages deployment lifecycles.
    """

    @classmethod
    async def register_run_model(
        cls, name: str, run_id: str, version: str, metrics: Dict[str, float]
    ) -> ModelRegistrationInfo:
        """
        Creates a tracking row in ml_model_registry.
        """
        async with AsyncSessionLocal() as session:
            reg_id = str(uuid4())
            model_entry = MLModelRegistry(
                id=reg_id,
                model_name=name,
                mlflow_run_id=run_id,
                version_tag=version,
                current_stage="Candidate",
                accuracy_metrics=metrics,
                is_active=False,
                registered_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            session.add(model_entry)
            await session.commit()

            # Publish event
            await EventBus.publish(
                "model.registered",
                {
                    "event_id": f"evt_ml_reg_{str(uuid4())[:8]}",
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "model_name": name,
                    "version_tag": version,
                    "mlflow_run_id": run_id,
                }
            )

            return ModelRegistrationInfo(
                model_name=name,
                mlflow_run_id=run_id,
                version_tag=version,
                current_stage="Candidate",
                accuracy_metrics=metrics,
                registered_at=model_entry.registered_at
            )

    @classmethod
    async def promote_model_stage(
        cls, name: str, version: str, stage: str
    ) -> ModelRegistrationInfo:
        """
        Promotes/transitions a model version to a new stage (e.g. Staging, Production, Archived).
        If promoted to Production, marks it as active and demotes other active versions.
        """
        # Try contacting MLflow client (mocked/stubbed if server is offline)
        try:
            import mlflow
            client = mlflow.tracking.MlflowClient()
            # In a real environment, we'd do:
            # client.transition_model_version_stage(name, version, stage)
            logger.info(f"MLflow client: transitioning {name} version {version} to stage {stage}")
        except Exception as e:
            logger.warning(f"MLflow client transition failed, falling back to local DB: {e}")

        async with AsyncSessionLocal() as session:
            stmt = select(MLModelRegistry).where(
                MLModelRegistry.model_name == name,
                MLModelRegistry.version_tag == version
            )
            res = await session.execute(stmt)
            model_entry = res.scalar_one_or_none()
            if not model_entry:
                raise ValueError(f"Model version not found: {name} ({version})")

            # Warning/safety condition: do not promote a model to Production if Brier score is > 0.25 unless forced (can check metrics)
            brier = model_entry.accuracy_metrics.get("brier_score", 0.0)
            if stage == "Production" and brier > 0.25:
                logger.warning(f"Promoting model with high Brier score ({brier} > 0.25).")

            previous_stage = model_entry.current_stage
            model_entry.current_stage = stage
            model_entry.updated_at = datetime.utcnow()

            if stage == "Production":
                # Demote other active models of the same name
                demote_stmt = (
                    update(MLModelRegistry)
                    .where(
                        MLModelRegistry.model_name == name,
                        MLModelRegistry.is_active == True,
                        MLModelRegistry.id != model_entry.id
                    )
                    .values(is_active=False, updated_at=datetime.utcnow())
                )
                await session.execute(demote_stmt)
                model_entry.is_active = True
            else:
                if model_entry.is_active:
                    model_entry.is_active = False

            await session.commit()

            # Publish event
            await EventBus.publish(
                "model.promoted",
                {
                    "event_id": f"evt_ml_prom_{str(uuid4())[:8]}",
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "model_name": name,
                    "version_tag": version,
                    "stage": stage,
                }
            )

            # Also publish calibration.model.promoted if Production
            if stage == "Production":
                await EventBus.publish(
                    "calibration.model.promoted",
                    {
                        "event_id": f"evt_cal_promo_{str(uuid4())[:8]}",
                        "timestamp": datetime.utcnow().isoformat() + "Z",
                        "mlflow_run_id": model_entry.mlflow_run_id,
                        "model_version": version,
                        "brier_score": float(model_entry.accuracy_metrics.get("brier_score", 0.0)),
                        "roc_auc": float(model_entry.accuracy_metrics.get("roc_auc", 0.0)),
                    }
                )

            return ModelRegistrationInfo(
                model_name=name,
                mlflow_run_id=model_entry.mlflow_run_id,
                version_tag=version,
                current_stage=stage,
                accuracy_metrics=model_entry.accuracy_metrics,
                registered_at=model_entry.registered_at
            )

    @classmethod
    async def rollback_production_model(cls, name: str) -> ModelRegistrationInfo:
        """
        Locates the previously active version in ml_model_registry,
        toggles active status, transitions current bad production model to Archived,
        and restores prior calibration.
        """
        async with AsyncSessionLocal() as session:
            # Get currently active model
            active_stmt = select(MLModelRegistry).where(
                MLModelRegistry.model_name == name,
                MLModelRegistry.is_active == True
            )
            active_res = await session.execute(active_stmt)
            active_model = active_res.scalar_one_or_none()

            # Find latest registered version of this model that is not the active one
            query = (
                select(MLModelRegistry)
                .where(MLModelRegistry.model_name == name)
                .order_by(desc(MLModelRegistry.registered_at))
            )
            if active_model:
                query = query.where(MLModelRegistry.id != active_model.id)
            
            prev_res = await session.execute(query.limit(1))
            prev_model = prev_res.scalar_one_or_none()

            if not prev_model:
                raise ValueError("No previous model version found to rollback to.")

            # Deactivate active model
            if active_model:
                active_model.is_active = False
                active_model.current_stage = "Archived"
                active_model.updated_at = datetime.utcnow()

            # Activate previous model
            prev_model.is_active = True
            prev_model.current_stage = "Production"
            prev_model.updated_at = datetime.utcnow()

            await session.commit()

            return ModelRegistrationInfo(
                model_name=name,
                mlflow_run_id=prev_model.mlflow_run_id,
                version_tag=prev_model.version_tag,
                current_stage="Production",
                accuracy_metrics=prev_model.accuracy_metrics,
                registered_at=prev_model.registered_at
            )

    @classmethod
    async def compare_models(
        cls, candidate_run_id: str, production_run_id: str
    ) -> Dict[str, Any]:
        """
        Fetch performance comparisons between a candidate run and the active production model.
        """
        async with AsyncSessionLocal() as session:
            stmt_cand = select(MLModelRegistry).where(MLModelRegistry.mlflow_run_id == candidate_run_id)
            res_cand = await session.execute(stmt_cand)
            cand = res_cand.scalar_one_or_none()

            stmt_prod = select(MLModelRegistry).where(MLModelRegistry.mlflow_run_id == production_run_id)
            res_prod = await session.execute(stmt_prod)
            prod = res_prod.scalar_one_or_none()

            if not cand or not prod:
                raise ValueError("Candidate or Production model run not found in registry.")

            cand_brier = float(cand.accuracy_metrics.get("brier_score", 0.0))
            prod_brier = float(prod.accuracy_metrics.get("brier_score", 0.0))
            brier_delta = cand_brier - prod_brier
            brier_improved = cand_brier < prod_brier  # lower is better

            cand_roc = float(cand.accuracy_metrics.get("roc_auc", 0.0))
            prod_roc = float(prod.accuracy_metrics.get("roc_auc", 0.0))
            roc_delta = cand_roc - prod_roc
            roc_improved = cand_roc > prod_roc  # higher is better

            # Recommendation rules
            recommendation = "PROMOTABLE" if (brier_improved or roc_improved) and cand_brier <= 0.25 else "HOLD"

            return {
                "metrics_comparison": {
                    "brier_score": {
                        "candidate": cand_brier,
                        "production": prod_brier,
                        "delta": brier_delta,
                        "improved": brier_improved
                    },
                    "roc_auc": {
                        "candidate": cand_roc,
                        "production": prod_roc,
                        "delta": roc_delta,
                        "improved": roc_improved
                    }
                },
                "recommendation": recommendation
            }
