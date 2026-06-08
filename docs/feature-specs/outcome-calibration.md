# Feature Specification: Outcome Calibration (F5.3)

## 1. Purpose
Outcome Calibration is a central component of CareerPilot's technical defensibility, closing the career intelligence loop. In early phases, the Intelligence Agent generates heuristic fit scores. Outcome Calibration replaces these raw scores with empirical probabilities of securing an interview. It matches historical predicted fit scores against actual application outcomes (recorded in the Outcome Memory System). Using scikit-learn models (such as Platt scaling/Logistic Regression) tracked on MLflow, it trains a calibration model. At inference time, it translates raw fit scores into a calibrated probability percentage (e.g., "This role has an 18% interview probability for your cohort, which is 3x the baseline average").

---

## 2. User Value
Outcome Calibration shifts CareerPilot from an opinionated recommender to a data-backed career advisor. Users no longer get arbitrary "92% matches." Instead, they see realistic probabilities of getting an interview based on actual outcomes from similar users in their peer cohort. This manages expectations and provides clear, quantitative evidence showing that completing suggested profile updates actually increases callback probabilities (e.g., "Adding Kubernetes increases your estimated callback chance from 8% to 22%").

---

## 3. Requirements
* **Training Dataset Builder**: Build queries to join `agent_intelligence_reports`, `outcome_memories` (real outcomes), and profile data into structured training sets.
* **Feature Engineering Pipeline**: Convert raw attributes (overall fit score, position delta count, company hiring velocity, experience years, industry match) into numerical vector records.
* **Model Training & Baseline**: Train a Platt scaling model (Logistic Regression over raw scores) using scikit-learn to map fit scores to binary outcome targets (interview secured: true/false).
* **Calibration Inference Service**: Provide a low-latency model server class that loads the active calibration model from MLflow registry and adjusts raw fit scores on the fly.
* **Model Versioning & MLflow Registry**: Log model hyperparameters, calibration curves, Brier scores, ROC-AUC, and binary files to the MLflow platform.
* **Prediction Monitoring**: Log calibrated probability predictions alongside the final realized outcome to continuously track model drift.
* **Retraining Job**: Schedule automated runs to update the calibration model parameters as new outcome memory records accumulate.

---

## 4. Database Changes

### PostgreSQL Tables

#### `calibration_models`
Tracks deployed versions of calibration models linked to MLflow run identifiers.
```sql
CREATE TABLE calibration_models (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    model_name VARCHAR(150) NOT NULL DEFAULT 'fit_probability_calibrator',
    mlflow_run_id VARCHAR(100) UNIQUE NOT NULL,
    mlflow_model_version VARCHAR(50) NOT NULL,
    brier_score NUMERIC(6, 5) NOT NULL,
    roc_auc NUMERIC(6, 5) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT FALSE,
    deployed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX idx_calibration_models_active ON calibration_models(is_active) WHERE is_active = TRUE;
```

#### `calibrated_predictions_log`
Tracks predictions, calibration values, and actual outcomes for drift measurement.
```sql
CREATE TABLE calibrated_predictions_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    job_id UUID NOT NULL, -- references job_postings(id)
    calibration_model_id UUID REFERENCES calibration_models(id) ON DELETE SET NULL,
    raw_fit_score NUMERIC(5, 2) NOT NULL,
    calibrated_probability NUMERIC(5, 4) NOT NULL, -- value between 0.0000 and 1.0000
    actual_outcome VARCHAR(50), -- e.g. interview, rejected, offer, ghosted (from outcome memory)
    realized_target BOOLEAN, -- True if interview/offer occurred, False if rejected
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX idx_calibrated_predictions_user ON calibrated_predictions_log(user_id);
```

### Alembic Migration Plan
1. Create `calibration_models` table to manage deployments.
2. Create `calibrated_predictions_log` to capture calibration inputs and outcomes.
3. Apply active-model query filter optimization indexes.

---

## 5. API Endpoints

### POST `/api/v1/calibration/train`
Trigger a background model training run using accumulated outcome records.
* **Request Payload**:
  ```json
  {
    "min_samples_required": 100,
    "model_type": "logistic_regression"
  }
  ```
* **Response Body (202 Accepted)**:
  ```json
  {
    "task_id": "task_cal_train_09",
    "status": "training",
    "message": "Calibration retraining job started."
  }
  ```

### POST `/api/v1/calibration/calibrate`
Evaluate raw fit scores and output probability estimations.
* **Request Payload**:
  ```json
  {
    "raw_fit_score": 85.50,
    "features": {
      "experience_years": 4.5,
      "skill_gap_count": 2,
      "company_hiring_velocity": 2.0
    }
  }
  ```
* **Response Body (200 OK)**:
  ```json
  {
    "model_version": "v2.1.0",
    "raw_fit_score": 85.50,
    "calibrated_probability": 0.1425, -- 14.25% chance of securing interview
    "confidence_interval": [0.115, 0.170]
  }
  ```

---

## 6. Domain Models

```python
from pydantic import BaseModel, Field
from typing import Dict, Any, Tuple
from uuid import UUID

class CalibrationInferenceRequest(BaseModel):
    raw_fit_score: float = Field(description="Raw heuristic score from F3.4")
    features: Dict[str, float] = Field(description="Extracted feature variables for calibration scaling.")

class CalibrationInferenceResponse(BaseModel):
    model_version: str
    raw_fit_score: float
    calibrated_probability: float = Field(ge=0.0, le=1.0)
    confidence_interval: Tuple[float, float]
```

---

## 7. Services

### `CalibrationModelService`
* **Method**: `train_calibration_model(min_samples: int) -> dict`
  * Reads data from `outcome_memories` and `agent_intelligence_reports`. Splits into training/validation sets. Fits a scikit-learn calibration model. Evaluates using Brier score and ROC-AUC. Logs parameters to MLflow. Returns the run metrics.
* **Method**: `calibrate_score(request: CalibrationInferenceRequest) -> CalibrationInferenceResponse`
  * Loads active model weights from local cache or MLflow registry, calculates calibrated probability, and formats response.
* **Method**: `promote_model(mlflow_run_id: str) -> None`
  * Marks the target model as active in `calibration_models` and demotes previous models.

---

## 8. Events

### `calibration.model.promoted`
* **Producer**: `CalibrationModelService`
* **Consumer**: ObservabilityPlatform, API Routers
* **Payload**:
  ```json
  {
    "event_id": "evt_cal_promo_01",
    "timestamp": "2026-06-09T02:04:18Z",
    "mlflow_run_id": "run_99881122",
    "model_version": "v2.1.0",
    "brier_score": 0.0821,
    "roc_auc": 0.7620
  }
  ```

---

## 9. Background Jobs
* **Job Name**: `periodic_calibration_retraining`
  * **Frequency**: Weekly on Sunday at 03:00 AM (`0 3 * * 0`)
  * **Payload**: None
  * **Logic**: Scan database for new outcomes. If count of new outcome records since last deployment is > 50, run `train_calibration_model` and alert developers of new metrics.
  * **Retry Behavior**: Standard celery backoff retry (up to 3 times).

---

## 10. Acceptance Criteria
* **AC 1**: Given a raw fit score, the calibration inference API must return a probability strictly bounded between 0.0 and 1.0.
* **AC 2**: The Brier Score (measure of calibration quality) of any newly trained model must be lower than 0.25 (lower is better, a score of 0.25 represents a random 50% guess).
* **AC 3**: A newly trained model must be logged to the MLflow platform before it can be activated in the database.

---

## 11. Edge Cases
* **Cold Start (Insufficient Outcome Data)**: In early stages, we have zero outcomes. The inference service must fall back to a baseline sigmoid function mapping `(raw_score / 100.0) * cohort_base_rate` until 100 real-world outcome points are recorded.
* **Feature Drift**: If target job market profiles shift, the model might overpredict. The background job must compute monthly prediction drift (comparing predicted probabilities vs actual interview frequencies) and alert engineers if drift exceeds 15% margin.
* **MLflow Platform Offline**: If MLflow is unreachable during training or startup, the calibration service must load the last successfully cached model files from local disk storage.

---

## 12. Test Requirements
* **Unit Testing**:
  * Verify Platt scaling logic executes mathematically correct probability mappings.
  * Assert dataset builder successfully filters out records missing realized targets.
* **Integration Testing**:
  * Run model fit, register in mock MLflow workspace, deploy to local PostgreSQL database, and run sample inference.
* **Agent/Workflow Evaluation**:
  * Validate that calibrated predictions show a positive correlation coefficient (Brier score <= 0.15, ROC-AUC >= 0.70) against validation subsets.

---

## 13. Dependencies
* This feature depends on:
  * [outcome-memory-system.md](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/feature-specs/outcome-memory-system.md) (F4.6)
  * [intelligence-agent.md](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/feature-specs/intelligence-agent.md) (F3.4)
  * [evaluation-framework.md](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/feature-specs/evaluation-framework.md) (F5.1)
  * [ml-platform.md](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/feature-specs/ml-platform.md) (F5.5)
* This feature is a dependency for:
  * [architecture-documentation.md](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/feature-specs/architecture-documentation.md) (F6.5)
