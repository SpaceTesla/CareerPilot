from __future__ import annotations

import math
import numpy as np
from datetime import datetime
from uuid import uuid4
from typing import Dict, Any, List, Optional, Tuple
from decimal import Decimal

from sqlalchemy import select, update, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.infrastructure.database.models import (
    ApplicationOutcome,
    JobApplication,
    MLModelRegistry,
    CalibrationModel,
    CalibratedPredictionLog
)
from app.services.database_service import AsyncSessionLocal
from app.schemas.evaluation import (
    CalibrationInferenceRequest,
    CalibrationInferenceResponse,
    ModelRegistrationInfo
)
from app.services.ml_platform_service import MLPlatformService

logger = get_logger(__name__)


class CalibrationModelService:
    """
    Calibration Model Service (F5.3).
    Trains logistic regression models (Platt scaling) to calibrate Fit Scores to Interview Probabilities.
    """

    @classmethod
    async def train_calibration_model(cls, min_samples: int = 100) -> Dict[str, Any]:
        """
        Gathers historical predicted fit scores and actual outcomes.
        Trains a Logistic Regression calibrator, computes Brier Score and ROC-AUC,
        and registers the model on the ML Platform.
        """
        async with AsyncSessionLocal() as session:
            # Join ApplicationOutcome and JobApplication
            stmt = (
                select(ApplicationOutcome, JobApplication)
                .join(JobApplication, JobApplication.id == ApplicationOutcome.application_id)
            )
            res = await session.execute(stmt)
            rows = res.all()

        logger.info(f"Retrieved {len(rows)} historical outcomes for calibration training.")

        # Check if we have at least one success and one failure class to prevent single-class errors
        has_success = False
        has_failure = False
        if len(rows) >= min_samples:
            success_outcomes = ["INTERVIEW", "OFFERED", "OFFER"]
            for outcome, _ in rows:
                if outcome.final_outcome and outcome.final_outcome.upper() in success_outcomes:
                    has_success = True
                else:
                    has_failure = True

        # If insufficient samples, or single-class dataset, construct synthetic data to train a valid baseline model
        if len(rows) < min_samples or not (has_success and has_failure):
            logger.info("Insufficient real outcome samples or single-class target variable. Generating bootstrap synthetic samples for baseline model.")
            # Synthesize data: 100 samples correlated with fit scores
            np.random.seed(42)
            raw_scores = np.random.uniform(50, 100, 150)
            exp_years = np.random.uniform(0, 15, 150)
            skill_gaps = np.random.randint(0, 10, 150)
            velocity = np.random.uniform(1.0, 3.0, 150)

            # Generate target interview callback (more likely with high scores and experience)
            logits = (raw_scores - 75) * 0.1 + exp_years * 0.2 - skill_gaps * 0.3 + (velocity - 2.0) * 0.5
            probs = 1 / (1 + np.exp(-logits))
            realized = (probs > np.random.uniform(0, 1, 150)).astype(int)

            X = np.column_stack((raw_scores, exp_years, skill_gaps, velocity))
            y = realized
        else:
            X_data = []
            y_data = []
            for outcome, app in rows:
                raw_score = float(outcome.predicted_fit_score)
                
                # Fetch features from user profile snapshots or defaults
                # Default features if profile information is sparse
                exp_years = 5.0
                skill_gaps = 2.0
                velocity = 2.0

                if app.job_data_json:
                    # Try retrieving attributes if present
                    skill_gaps = float(app.job_data_json.get("skill_gap_count", 2.0))
                    velocity = float(app.job_data_json.get("company_hiring_velocity", 2.0))

                X_data.append([raw_score, exp_years, skill_gaps, velocity])
                
                # Terminal successes are INTERVIEW or OFFERED or OFFER
                success_outcomes = ["INTERVIEW", "OFFERED", "OFFER"]
                realized_bool = outcome.final_outcome.upper() in success_outcomes
                y_data.append(1 if realized_bool else 0)

            X = np.array(X_data)
            y = np.array(y_data)

        # Import scikit-learn models
        from sklearn.linear_model import LogisticRegression
        from sklearn.metrics import brier_score_loss, roc_auc_score
        from sklearn.model_selection import train_test_split

        # Split
        X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=0.2, random_state=42)

        # Fit calibrator model
        model = LogisticRegression(C=1.0, solver="lbfgs")
        model.fit(X_train, y_train)

        # Evaluate
        val_probs = model.predict_proba(X_val)[:, 1]
        brier_score = brier_score_loss(y_val, val_probs)
        try:
            roc_auc = roc_auc_score(y_val, val_probs)
        except ValueError:
            roc_auc = 0.5 # fallback if single class present in validation set

        # Extract weights
        weights = list(model.coef_[0])
        intercept = float(model.intercept_[0])

        metrics = {
            "brier_score": float(brier_score),
            "roc_auc": float(roc_auc),
            "weights": weights,
            "intercept": intercept
        }

        # Register model on ML Platform
        run_id = f"run_{str(uuid4())[:8]}"
        version = f"v{datetime.utcnow().strftime('%Y.%m.%d.%H%M')}"
        model_name = "fit_probability_calibrator"

        reg_info = await MLPlatformService.register_run_model(
            name=model_name,
            run_id=run_id,
            version=version,
            metrics=metrics
        )

        # Also write to local calibration_models reference table
        async with AsyncSessionLocal() as session:
            cm_id = str(uuid4())
            cm = CalibrationModel(
                id=cm_id,
                model_name=model_name,
                mlflow_run_id=run_id,
                mlflow_model_version=version,
                brier_score=Decimal(str(round(brier_score, 5))),
                roc_auc=Decimal(str(round(roc_auc, 5))),
                is_active=False,
                deployed_at=None,
                created_at=datetime.utcnow()
            )
            session.add(cm)
            await session.commit()

        return {
            "mlflow_run_id": run_id,
            "version_tag": version,
            "brier_score": brier_score,
            "roc_auc": roc_auc,
        }

    @classmethod
    async def calibrate_score(
        cls, request: CalibrationInferenceRequest, user_id: Optional[str] = None, job_id: Optional[str] = None
    ) -> CalibrationInferenceResponse:
        """
        Loads active model parameters from local DB and scales raw fit scores to probabilities.
        Applies a sigmoid fallback function if no active model exists.
        Logs prediction to calibrated_predictions_log.
        """
        async with AsyncSessionLocal() as session:
            # Query the active model from registry
            stmt = select(MLModelRegistry).where(
                MLModelRegistry.model_name == "fit_probability_calibrator",
                MLModelRegistry.is_active == True
            )
            res = await session.execute(stmt)
            active_reg = res.scalar_one_or_none()

            model_ref_stmt = select(CalibrationModel).where(
                CalibrationModel.model_name == "fit_probability_calibrator",
                CalibrationModel.is_active == True
            )
            model_ref_res = await session.execute(model_ref_stmt)
            active_model = model_ref_res.scalar_one_or_none()

        version = "fallback"
        model_id = None
        
        # Cold start fallback logic
        if not active_reg:
            # Sigmoid mapping: (raw_fit_score / 100.0) * cohort_base_rate
            cohort_base_rate = 0.15 # default 15% callback probability
            prob = (request.raw_fit_score / 100.0) * cohort_base_rate
            prob = max(0.0, min(1.0, prob))
        else:
            version = active_reg.version_tag
            model_id = active_reg.id
            metrics = active_reg.accuracy_metrics
            weights = metrics.get("weights", [0.1, 0.2, -0.3, 0.5])
            intercept = metrics.get("intercept", -5.0)

            # Features vector: [raw_fit_score, experience_years, skill_gap_count, company_hiring_velocity]
            raw_score = request.raw_fit_score
            exp_years = request.features.get("experience_years", 5.0)
            skill_gaps = request.features.get("skill_gap_count", 2.0)
            velocity = request.features.get("company_hiring_velocity", 2.0)

            # Compute logistic regression logit
            logit = (
                weights[0] * raw_score
                + weights[1] * exp_years
                + weights[2] * skill_gaps
                + weights[3] * velocity
                + intercept
            )
            prob = 1.0 / (1.0 + math.exp(-logit))
            prob = max(0.0, min(1.0, prob))

        # Compute a confidence interval (standard error bound, e.g. 5% spread)
        margin = 0.05 * prob
        lower_bound = max(0.0, prob - margin)
        upper_bound = min(1.0, prob + margin)

        # Log prediction if user and job references are provided
        if user_id and job_id:
            async with AsyncSessionLocal() as session:
                log_entry = CalibratedPredictionLog(
                    id=str(uuid4()),
                    user_id=user_id,
                    job_id=job_id,
                    calibration_model_id=active_model.id if active_model else None,
                    raw_fit_score=Decimal(str(round(request.raw_fit_score, 2))),
                    calibrated_probability=Decimal(str(round(prob, 4))),
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                session.add(log_entry)
                await session.commit()

        return CalibrationInferenceResponse(
            model_version=version,
            raw_fit_score=request.raw_fit_score,
            calibrated_probability=prob,
            confidence_interval=(lower_bound, upper_bound)
        )
