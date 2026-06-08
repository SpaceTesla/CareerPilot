# Feature Specification: Evaluation Framework (F5.1)

## 1. Purpose
The Evaluation Framework is an observability and quality assurance service designed to continuously measure the accuracy, drift, and performance of CareerPilot's intelligence engines and agents. It manages golden evaluation datasets (collections of ground-truth test cases representing ideal profile-to-job matches, skill extractions, and resume customisations) and executes automated evaluation runs. By running LLM-as-a-judge tests, structural comparisons, and heuristic validators inside the CI/CD pipeline, the framework catches performance regressions before code changes are merged.

---

## 2. User Value
The Evaluation Framework acts as the quality assurance anchor for the Career Intelligence Compounding Loop. Users receive highly reliable recommendations because the underlying agent templates, prompt instructions, and calibration models are continuously verified against a standardized benchmark. It prevents "prompt drift" (where fixing a bug for one user breaks recommendations for thousands of others) and ensures consistent scoring accuracy.

---

## 3. Requirements
* **Evaluation Dataset Schema**: Build database models to store test items containing user inputs, job descriptions, expected outcomes, and acceptable similarity thresholds.
* **Evaluation Results & Runs Schema**: Log the result of every test item execution, tracking LLM scoring details, token costs, processing times, and accuracy scores.
* **CI Execution Integration**: Provide a CLI test runner that executes evaluation runs inside Github Actions/CI, returning non-zero exit codes when accuracy metrics fall below threshold bounds.
* **Regression Detection**: Compare current evaluation run scores against historical baselines using standard statistical tests to detect regression.
* **Alerting**: Emit events and notification triggers when an active branch introduces regression or when live performance metrics drift.
* **Reporting APIs**: Expose REST endpoints to trigger ad-hoc evaluations, retrieve historical performance charts, and review failed test logs.

---

## 4. Database Changes

### PostgreSQL Tables

#### `eval_datasets`
Stores ground-truth test scenarios, inputs, and expected outputs.
```sql
CREATE TABLE eval_datasets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    component_name VARCHAR(100) NOT NULL, -- e.g. skill_extraction, fit_scoring, resume_tailoring
    input_payload JSONB NOT NULL, -- inputs like raw profile text, job details
    expected_output JSONB NOT NULL, -- expected skills list, target score range
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX idx_eval_datasets_component ON eval_datasets(component_name);
```

#### `eval_runs`
Tracks distinct evaluation run execution metadata.
```sql
CREATE TABLE eval_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    commit_sha VARCHAR(100),
    environment VARCHAR(50) NOT NULL, -- ci, staging, local, production
    started_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    completed_at TIMESTAMP WITH TIME ZONE,
    passed_count INTEGER DEFAULT 0 NOT NULL,
    failed_count INTEGER DEFAULT 0 NOT NULL,
    average_latency_ms NUMERIC(10, 2) DEFAULT 0.00 NOT NULL,
    overall_accuracy NUMERIC(5, 4) DEFAULT 0.0000 NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'running' -- running, completed, failed
);

CREATE INDEX idx_eval_runs_status ON eval_runs(status);
```

#### `eval_results`
Stores the detail of each test case execution within an evaluation run.
```sql
CREATE TABLE eval_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    eval_run_id UUID NOT NULL REFERENCES eval_runs(id) ON DELETE CASCADE,
    dataset_item_id UUID NOT NULL REFERENCES eval_datasets(id) ON DELETE CASCADE,
    actual_output JSONB NOT NULL,
    score NUMERIC(5, 4) NOT NULL, -- score normalized between 0.0000 and 1.0000
    is_passed BOOLEAN NOT NULL DEFAULT TRUE,
    error_message TEXT,
    execution_time_ms INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX idx_eval_results_run ON eval_results(eval_run_id);
```

### Alembic Migration Plan
1. Create `eval_datasets` table with a component filter index.
2. Create `eval_runs` table tracking commits and environments.
3. Create `eval_results` table linking datasets and runs.
4. Set up index constraints to speed up evaluation regression checks.

---

## 5. API Endpoints

### POST `/api/v1/eval/run`
Trigger a new evaluation run for a target component.
* **Request Payload**:
  ```json
  {
    "component_name": "fit_scoring",
    "environment": "ci",
    "commit_sha": "a1b2c3d4e5f6g7h8"
  }
  ```
* **Response Body (202 Accepted)**:
  ```json
  {
    "eval_run_id": "9f8e7d6c-5b4a-3c2d-1e0f-998877665544",
    "status": "queued",
    "message": "Evaluation run initialized for component: fit_scoring"
  }
  ```

### GET `/api/v1/eval/runs/{run_id}/report`
Fetch the detailed report and regression checks for a completed run.
* **Response Body (200 OK)**:
  ```json
  {
    "eval_run_id": "9f8e7d6c-5b4a-3c2d-1e0f-998877665544",
    "component_name": "fit_scoring",
    "status": "completed",
    "metrics": {
      "total_tests": 120,
      "passed": 118,
      "failed": 2,
      "overall_accuracy": 0.9833,
      "average_latency_ms": 312.45
    },
    "regression_detected": false,
    "baseline_comparison": {
      "baseline_run_id": "11223344-5566-7788-9900-aabbccddeeff",
      "baseline_accuracy": 0.9750,
      "delta": 0.0083
    }
  }
  ```

---

## 6. Domain Models

```python
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
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
```

---

## 7. Services

### `EvaluationFrameworkService`
* **Method**: `create_dataset_item(component: str, inputs: dict, expected: dict) -> UUID`
  * Inserts a golden test sample into `eval_datasets`.
* **Method**: `trigger_eval_run(component: str, env: str, commit: str) -> UUID`
  * Initializes an evaluation session, spins up concurrent runner workers, matches inputs against active agents, compares actual output with expected target, logs results, and computes aggregate metrics.
* **Method**: `detect_regression(run_id: UUID) -> bool`
  * Evaluates current performance versus historical baseline runs for the same component. Raises flag if accuracy falls by > 2% margin.

---

## 8. Events

### `eval.run.failed`
* **Producer**: `EvaluationFrameworkService`
* **Consumer**: ObservabilityPlatform, Slack Alert Service
* **Payload**:
  ```json
  {
    "event_id": "evt_eval_fail_01",
    "timestamp": "2026-06-09T02:04:18Z",
    "eval_run_id": "9f8e7d6c-5b4a-3c2d-1e0f-998877665544",
    "commit_sha": "a1b2c3d4e5f6g7h8",
    "accuracy": 0.7410,
    "threshold_limit": 0.9000,
    "regression_detected": true
  }
  ```

---

## 9. Background Jobs
* **Job Name**: `eval_regression_report_builder`
  * **Frequency**: Asynchronous webhook trigger (triggered via GitHub actions CI run).
  * **Payload**: `{"eval_run_id": "9f8e7d6c-5b4a-3c2d-1e0f-998877665544"}`
  * **Logic**: Compiles run telemetry, compares with production baselines, compiles markdown report files, posts summaries to PR hooks, and shuts down test pods.
  * **Retry Behavior**: Retry up to 2 times with a 30s delay on API post failures.

---

## 10. Acceptance Criteria
* **AC 1**: Given an active codebase pull-request, when the CI pipeline executes, it must trigger a regression evaluation run across all golden test items.
* **AC 2**: Given an evaluation run, when the overall accuracy drops below the configured component threshold (e.g., 90%), the runner must output a failure status code (1) to block the build.
* **AC 3**: Every evaluation result must be logged to `eval_results` with execution latency and score data points.

---

## 11. Edge Cases
* **Rate Limiting During CI Execution**: Running hundreds of LLM calls in CI can trigger 429 errors. The framework runner must apply a token bucket rate limiter to throttle API calls and implement backoff retries.
* **Hallucinatory Eval Criteria**: Simple string matching will fail correct semantic variants. The framework must use cosine similarity thresholding (>= 0.82) on embeddings for free-text evaluations instead of exact string checks.
* **Empty Dataset**: If a new component has no dataset records in `eval_datasets`, the framework must raise a validation exception rather than returning a default "passed" status.

---

## 12. Test Requirements
* **Unit Testing**:
  * Assert accuracy calculation algorithms (e.g., precision, recall, Cosine similarity checks) work accurately.
  * Assert regression detection functions correctly handle baseline comparison margins.
* **Integration Testing**:
  * Run a minimal mock evaluation execution containing 2 test items against a local DB and verify output metrics.
* **Agent/Workflow Evaluation**:
  * Bootstrap the golden dataset with 100 test items per key module (Resume customisation, Fit scoring, Skill extraction) to establish MVP performance lines.

---

## 13. Dependencies
* This feature depends on:
  * [project-setup-architecture.md](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/feature-specs/project-setup-architecture.md) (F1.1)
* This feature is a dependency for:
  * [evaluation-agent.md](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/feature-specs/evaluation-agent.md) (F5.2)
  * [outcome-calibration.md](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/feature-specs/outcome-calibration.md) (F5.3)
