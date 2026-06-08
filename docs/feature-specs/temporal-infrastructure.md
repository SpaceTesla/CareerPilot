# Feature Specification: Temporal Infrastructure

## 1. Purpose
The Temporal Infrastructure feature establishes a highly reliable, stateful, and distributed orchestration engine for CareerPilot. It handles long-running, asynchronous, and complex workflows that span multiple systems and services (e.g., job application automation, profile syncing, and daily market intelligence aggregation).

By utilizing Temporal, the system guarantees execution durability, transactional consistency across external APIs, and resilient retry mechanisms. It prevents partial failures, orphaned API requests, and untracked job application states.

---

## 2. User Value
Directly supports the execution layer of the **Career Intelligence Compounding Loop**. 
- **Compounding Loop Connection**: When a user decides to apply for a recommended role, the submission must succeed deterministically. If an application fails halfway due to network dropouts or external API issues, Temporal ensures it resumes from its last known-good state. 
- **User Benefit**: Users get a reliable, hands-off job application submission experience, with real-time status updates and guarantees that no application is lost in transit.

---

## 3. Requirements
- **Deploy Temporal Cluster**: Run a production-ready Temporal cluster (hosted locally/Docker for dev, cloud/managed for production) with a PostgreSQL persistence backend.
- **Worker Configuration**: Implement separate worker processes configured to poll specific task queues (`application-queue`, `profile-sync-queue`, `intelligence-queue`).
- **Workflow State Management**: Implement structured workflow files defining execution paths for multi-step career tasks.
- **Workflow Retries**: Implement exponential backoff retry policies for all external API calls and browser execution attempts, ensuring transient errors do not fail the workflow.
- **Workflow Monitoring**: Integrate Temporal Web UI, Prometheus metrics, and OpenTelemetry tracing to track workflow health and activity execution durations.
- **Workflow Alerting**: Set up Prometheus/Grafana alerting rules for workflow execution timeouts, long-running activities, and high activity failure rates.
- **Audit Trails**: Capture every workflow event and transaction state and write execution metadata to the local PostgreSQL database for query speed.

---

## 4. Database Changes
Temporal maintains its own internal database schemas for workflow history. To expose workflow states to CareerPilot APIs, we record metadata in a dedicated audit table.

### Table: `workflow_execution_logs`
Tracks execution state metadata for query performance and user visibility.

| Field Name | Data Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | UUID | PRIMARY KEY, DEFAULT gen_random_uuid() | Unique identifier for the log record. |
| `user_id` | UUID | FOREIGN KEY references `users(id)`, NULLABLE | User associated with the workflow. |
| `workflow_id` | VARCHAR(255) | UNIQUE, NOT NULL | Temporal's unique business workflow identifier. |
| `run_id` | VARCHAR(255) | NOT NULL | Temporal's execution run identifier. |
| `workflow_type` | VARCHAR(100) | NOT NULL | e.g., `ApplicationExecutionWorkflow`, `ProfileSyncWorkflow`. |
| `status` | VARCHAR(50) | NOT NULL | e.g., `RUNNING`, `COMPLETED`, `FAILED`, `CANCELLED`, `TERMINATED`. |
| `task_queue` | VARCHAR(100) | NOT NULL | Queue name the workflow is running on. |
| `input_payload` | JSONB | NOT NULL | Input parameters passed to start the workflow. |
| `output_payload` | JSONB | NULLABLE | Output data returned by the workflow upon completion. |
| `error_details` | JSONB | NULLABLE | Error trace or message if status is FAILED. |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | Workflow start time. |
| `updated_at` | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | Last state change timestamp. |

### Indexes
- `idx_workflow_logs_user_id` on `workflow_execution_logs(user_id)`
- `idx_workflow_logs_workflow_id` on `workflow_execution_logs(workflow_id)`
- `idx_workflow_logs_status` on `workflow_execution_logs(status)`

### Alembic Migration Details
The migration will script the creation of the `workflow_execution_logs` table, its foreign key constraint referencing the `users` table, and the respective query optimization indexes.

---

## 5. API Endpoints

### Get Workflow Status
- **HTTP Method**: `GET`
- **Route**: `/api/v2/workflows/executions/{workflow_id}`
- **Path Parameters**:
  - `workflow_id` (string): The unique workflow identifier.
- **Response Headers**:
  - `Content-Type: application/json`
- **Response Payload (JSON)**:
```json
{
  "workflow_id": "app-sub-9b1deb09-1122-3344",
  "run_id": "8f375a00-1122-4455-88aa-8f0a81b",
  "workflow_type": "ApplicationExecutionWorkflow",
  "status": "RUNNING",
  "task_queue": "application-queue",
  "current_activity": "SubmitGreenhouseApplication",
  "attempt": 2,
  "created_at": "2026-06-09T02:00:00Z",
  "updated_at": "2026-06-09T02:02:15Z"
}
```
- **HTTP Status Codes**:
  - `200 OK`: Successful retrieval.
  - `401 Unauthorized`: Missing or invalid JWT credentials.
  - `404 Not Found`: Workflow ID does not exist in logs.

### Cancel Workflow
- **HTTP Method**: `POST`
- **Route**: `/api/v2/workflows/executions/{workflow_id}/cancel`
- **Path Parameters**:
  - `workflow_id` (string): The unique workflow identifier.
- **Request Body**: None.
- **Response Payload (JSON)**:
```json
{
  "workflow_id": "app-sub-9b1deb09-1122-3344",
  "message": "Cancellation request submitted successfully.",
  "cancelled_at": "2026-06-09T02:02:30Z"
}
```
- **HTTP Status Codes**:
  - `202 Accepted`: Cancellation initiated.
  - `401 Unauthorized`: Missing or invalid JWT credentials.
  - `404 Not Found`: Workflow ID not active or found.

---

## 6. Domain Models

```python
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, Any, Dict

class WorkflowExecutionBase(BaseModel):
    workflow_id: str = Field(..., description="Temporal business workflow ID")
    run_id: str = Field(..., description="Temporal run ID")
    workflow_type: str = Field(..., description="Type of workflow class")
    status: str = Field(..., description="Current state of workflow execution")
    task_queue: str = Field(..., description="Queue name worker polls from")

class WorkflowExecutionCreate(WorkflowExecutionBase):
    user_id: Optional[str] = None
    input_payload: Dict[str, Any]

class WorkflowExecutionUpdate(BaseModel):
    status: str
    output_payload: Optional[Dict[str, Any]] = None
    error_details: Optional[Dict[str, Any]] = None

class WorkflowExecutionResponse(WorkflowExecutionBase):
    id: str
    user_id: Optional[str]
    input_payload: Dict[str, Any]
    output_payload: Optional[Dict[str, Any]] = None
    error_details: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True
```

---

## 7. Services

### Class: `TemporalWorkflowService`
Responsible for interacting with the Temporal Client SDK to start, query, cancel, and audit workflows.

- **Method**: `start_workflow`
  - **Inputs**:
    - `workflow_name` (str): Class name of target Temporal workflow.
    - `workflow_id` (str): Unique business-defined workflow identifier.
    - `task_queue` (str): Target worker queue.
    - `input_data` (Dict[str, Any]): Inputs for workflow instantiation.
    - `user_id` (Optional[str]): Database ID of the user requesting execution.
  - **Return Type**: `WorkflowExecutionResponse`
  - **Responsibilities**:
    - Calls `temporal_client.start_workflow()`.
    - Creates a new record in `workflow_execution_logs` with status `RUNNING`.
    - Returns details of the started execution.

- **Method**: `cancel_workflow`
  - **Inputs**:
    - `workflow_id` (str): Target workflow identifier.
  - **Return Type**: `None`
  - **Responsibilities**:
    - Gets workflow handle from `temporal_client.get_workflow_handle()`.
    - Calls `handle.cancel()`.
    - Updates local `workflow_execution_logs` record status to `CANCELLED`.

- **Method**: `sync_workflow_status`
  - **Inputs**:
    - `workflow_id` (str): Target workflow ID.
    - `run_id` (str): Target run ID.
  - **Return Type**: `str` (the updated status)
  - **Responsibilities**:
    - Queries Temporal system for the execution status.
    - Synchronizes the state directly into the `workflow_execution_logs` DB record.

---

## 8. Events

### Event: `workflow.started`
- **Producer**: `TemporalWorkflowService.start_workflow`
- **Consumer**: `observability-service`
- **Payload Schema**:
```json
{
  "event_id": "evt_123456789",
  "event_type": "workflow.started",
  "timestamp": "2026-06-09T02:00:00Z",
  "payload": {
    "workflow_id": "app-sub-9b1deb09-1122-3344",
    "run_id": "8f375a00-1122-4455-88aa-8f0a81b",
    "workflow_type": "ApplicationExecutionWorkflow",
    "user_id": "9b1deb09-1122-3344-5566-778899aabbcc"
  }
}
```

### Event: `workflow.completed`
- **Producer**: Temporal Workflow Execution interceptors/listeners
- **Consumer**: `outcome-memory-system`, `observability-service`
- **Payload Schema**:
```json
{
  "event_id": "evt_987654321",
  "event_type": "workflow.completed",
  "timestamp": "2026-06-09T02:05:00Z",
  "payload": {
    "workflow_id": "app-sub-9b1deb09-1122-3344",
    "run_id": "8f375a00-1122-4455-88aa-8f0a81b",
    "workflow_type": "ApplicationExecutionWorkflow",
    "user_id": "9b1deb09-1122-3344-5566-778899aabbcc",
    "duration_seconds": 300
  }
}
```

---

## 9. Background Jobs
Temporal replaces standard cron servers for stateful background automation. The infrastructure hosts:
- **System Synchronization Cron**: A recurring Temporal Schedule running every 24 hours to execute `IntelligenceSyncWorkflow` (syncs macro trends, market data, and recalibrates peer cohorts).
- **Execution Retry Behaviors**: Managed inside activities. If an API request fails with a rate limit (HTTP 429), the activity throws a retryable exception configured with backoff matching the `Retry-After` header.

---

## 10. Acceptance Criteria
- **Scenario**: A background task triggers an application.
  - **Given**: A configured Temporal worker is active and polling the `application-queue`.
  - **When**: `TemporalWorkflowService` starts `ApplicationExecutionWorkflow` with valid parameters.
  - **Then**: An execution record is written to `workflow_execution_logs` with status `RUNNING`, and the Temporal worker executes the activity sequence successfully.
- **Scenario**: API execution experiences a temporary timeout.
  - **Given**: An activity is executing an external HTTP request.
  - **When**: The external service times out (HTTP 504).
  - **Then**: Temporal catches the exception and schedules a retry according to the exponential backoff policy (up to 5 attempts) before failing.

---

## 11. Edge Cases
- **Temporal Server Disconnection**: If the app backend loses connectivity to the Temporal cluster, the gateway service writes to a fallback Redis buffer. Once connections resume, the buffer drains, launching the workflows.
- **Zombie Workflows**: Workflows that get stuck in an execution loop due to code bugs. Prevented by setting global workflow timeout parameters (e.g., maximum 30 minutes for any individual job application execution).
- **Worker Crash Mid-Activity**: If a worker node goes down during form filling, Temporal detects the missing heartbeat, schedules the activity on another available worker, and resumes processing.

---

## 12. Test Requirements
- **Unit Tests**: Test the Pydantic data validation schemas and the mapping logic within the service layer.
- **Integration Tests**: Verify that the `TemporalWorkflowService` successfully communicates with a test Temporal server (using `temporalio.testing.WorkflowEnvironment`).
- **Workflow Tests**: Mock external activity boundaries to assert that the workflow executes its path steps in the correct order under success and failure states.

---

## 13. Dependencies
- **[F1.1: Project Setup & Architecture](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/feature-specs/project-setup-architecture.md)**: Provides base database structures and FastAPI initialization rules.

---
