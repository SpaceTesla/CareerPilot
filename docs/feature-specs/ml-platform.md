# Feature Specification: ML Platform (F5.5)

## 1. Purpose
The ML Platform is an infrastructure and model management service that provides experiment tracking, model registry, and lifecycle deployment controls for CareerPilot's machine learning components. Centered on a self-hosted MLflow deployment, it allows engineers to log training parameters, metrics (Brier score, ROC-AUC), and model artifacts (pickled scikit-learn models, calibration plots) during training cycles. It provides systematic promotion pathways (from Candidate to Staging to Active/Production) and instant rollback support if performance degradation is detected.

---

## 2. User Value
The ML Platform powers the reliability of CareerPilot's outcome predictions. By ensuring that only rigorously tested, version-controlled models are promoted to production, the platform prevents prediction errors or bias from affecting users. It guarantees that any updates to scoring mechanisms are backed by transparent metrics, protecting users from bad recommendations or corrupted calibration outputs.

---

## 3. Requirements
* **MLflow Server Setup**: Deploy and configure a self-hosted MLflow tracking server using PostgreSQL as the backend store and S3 (or MinIO) as the artifact store.
* **Experiment Tracking**: Provide utility clients to log hyperparameter training runs, datasets, and output graphs (e.g., ROC curves, calibration curves).
* **Model Registry Integration**: Standardize naming conventions for model artifacts, registering trained calibration models in the MLflow model registry.
* **Model Promotion Workflow**: Provide automated APIs/scripts to transition model versions through lifecycle states (`Staging`, `Production`, `Archived`).
* **Model Rollback Support**: Enable instant model rollbacks, allowing developers to flag a previous version as active via the API, restoring previous prediction performance.
* **Model Metrics Collection**: Extract historical run metrics to compile model performance comparison reports.
* **Monitoring & Alerts**: Monitor MLflow server status and track resource footprint metrics.

---

## 4. Database Changes
While MLflow manages its own PostgreSQL schema (which resides in a dedicated `mlflow` schema namespace or a separate database instance), the CareerPilot main schema registers deployed model states.

### PostgreSQL Tables

#### `ml_model_registry`
Local reference table matching MLflow registered models to CareerPilot deployment states.
```sql
CREATE TABLE ml_model_registry (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    model_name VARCHAR(150) NOT NULL, -- e.g. fit_probability_calibrator
    mlflow_run_id VARCHAR(100) NOT NULL,
    version_tag VARCHAR(50) NOT NULL,
    current_stage VARCHAR(50) NOT NULL, -- Candidate, Staging, Production, Archived
    accuracy_metrics JSONB NOT NULL, -- logs brier_score, roc_auc, F1-score
    is_active BOOLEAN NOT NULL DEFAULT FALSE,
    registered_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT uq_name_version UNIQUE (model_name, version_tag)
);

CREATE INDEX idx_model_registry_stage ON ml_model_registry(model_name, current_stage);
```

### Alembic Migration Plan
1. Create `ml_model_registry` table in the main database.
2. Add unique constraint on `(model_name, version_tag)`.
3. Add search indexes on current model stage and name keys.

---

## 5. API Endpoints

### POST `/api/v1/ml-platform/models/promote`
Transition a model version to a new lifecycle stage.
* **Request Payload**:
  ```json
  {
    "model_name": "fit_probability_calibrator",
    "version_tag": "v2.1.0",
    "target_stage": "Production"
  }
  ```
* **Response Body (200 OK)**:
  ```json
  {
    "model_name": "fit_probability_calibrator",
    "version_tag": "v2.1.0",
    "previous_stage": "Staging",
    "current_stage": "Production",
    "status": "active",
    "message": "Model version v2.1.0 promoted to Production. Active inference updated."
  }
  ```

### GET `/api/v1/ml-platform/models/compare`
Fetch performance comparisons between a candidate run and the active production model.
* **Query Parameters**:
  * `candidate_run_id` (string): MLflow run ID of candidate model.
  * `production_run_id` (string): MLflow run ID of active production model.
* **Response Body (200 OK)**:
  ```json
  {
    "metrics_comparison": {
      "brier_score": {
        "candidate": 0.0821,
        "production": 0.0910,
        "delta": -0.0089, -- candidate is better (lower)
        "improved": true
      },
      "roc_auc": {
        "candidate": 0.7620,
        "production": 0.7410,
        "delta": 0.0210,
        "improved": true
      }
    },
    "recommendation": "PROMOTABLE"
  }
  ```

---

## 6. Domain Models

```python
from pydantic import BaseModel, Field
from typing import Dict, Any
from datetime import datetime

class ModelRegistrationInfo(BaseModel):
    model_name: str
    mlflow_run_id: str
    version_tag: str
    current_stage: str = Field(description="Stage: 'Candidate', 'Staging', 'Production', 'Archived'")
    accuracy_metrics: Dict[str, float]
    registered_at: datetime

class ModelPromotionRequest(BaseModel):
    model_name: str
    version_tag: str
    target_stage: str
```

---

## 7. Services

### `MLPlatformService`
* **Method**: `register_run_model(name: str, run_id: str, version: str, metrics: dict) -> ModelRegistrationInfo`
  * Creates a tracking row in `ml_model_registry` mirroring an MLflow model creation.
* **Method**: `promote_model_stage(name: str, version: str, stage: str) -> ModelRegistrationInfo`
  * Contacts MLflow client API (`MlflowClient.transition_model_version_stage`) to update registry status. Updates the local `ml_model_registry` table, sets `is_active = True` if stage is `Production`, and demotes other versions.
* **Method**: `rollback_production_model(name: str) -> ModelRegistrationInfo`
  * Locates the previously active version in `ml_model_registry`, toggles active status, transitions current bad production model to `Archived`, and restores prior calibration coefficients.

---

## 8. Events

### `model.registered`
* **Producer**: `MLPlatformService`
* **Consumer**: ObservabilityPlatform
* **Payload**:
  ```json
  {
    "event_id": "evt_ml_reg_01",
    "timestamp": "2026-06-09T02:04:18Z",
    "model_name": "fit_probability_calibrator",
    "version_tag": "v2.1.0",
    "mlflow_run_id": "run_99881122"
  }
  ```

### `model.promoted`
* **Producer**: `MLPlatformService`
* **Consumer**: `CalibrationModelService`, Notification Service
* **Payload**:
  ```json
  {
    "event_id": "evt_ml_prom_02",
    "timestamp": "2026-06-09T02:05:00Z",
    "model_name": "fit_probability_calibrator",
    "version_tag": "v2.1.0",
    "stage": "Production"
  }
  ```

---

## 9. Background Jobs
None. Model registry updates and promotions are event-triggered via API calls or training workflows.

---

## 10. Acceptance Criteria
* **AC 1**: Given a completed calibration training run, the client must successfully write parameters, curves, and model weights to the MLflow server.
* **AC 2**: Given a promotion command to `Production`, the service must update MLflow stage tags and update `is_active` in `ml_model_registry` to redirect inference workloads.
* **AC 3**: Given a rollback command, the system must demote the active model version and restore the previous `Production` version in less than 5 seconds.

---

## 11. Edge Cases
* **S3/MinIO Outage**: If the S3 artifact store is offline, model registry actions must pause and queue a background sync task, keeping the currently active production model file loaded in local RAM cache to ensure inference continuity.
* **Version Tag Conflict**: If a developer attempts to register an already existing version tag, the client API must raise a validation exception rather than overwriting historical run records.
* **Promotion to Production of Worse Model**: If a user attempts to promote a model that has a worse Brier score (> 0.25) than the currently active version, the API must return a warning and require an explicit confirmation flag (`force_promotion=true`).

---

## 12. Test Requirements
* **Unit Testing**:
  * Verify client helper functions construct correct MLflow tracking URLs and headers.
  * Assert model comparisons calculate correct metric differences.
* **Integration Testing**:
  * Connect to a local MLflow mock Docker container, create an experiment, log mock run parameters, register model, and promote to production.
* **Agent/Workflow Evaluation**:
  * Verify that model version tags are accurately injected into the metadata of calibration inference calls for auditing.

---

## 13. Dependencies
* This feature depends on:
  * [project-setup-architecture.md](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/feature-specs/project-setup-architecture.md) (F1.1)
* This feature is a dependency for:
  * [outcome-calibration.md](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/feature-specs/outcome-calibration.md) (F5.3)
