# Feature Specification: Application Workflow

## 1. Purpose
The Application Workflow feature represents the core state machine coordinating the job application submission process in CareerPilot. It is responsible for orchestrating the multi-tiered execution strategy (ATS API Integration, Deterministic Form Execution, and Browser Fallback) after a user approves an application brief.

This workflow runs as a stateful Temporal workflow, managing transient failures, ensuring checkpoints are successfully recorded, logging audit steps, and updating the application pipeline in the user's dashboard.

---

## 2. User Value
Directly operates on the **Execution Layer** of the **Career Intelligence Compounding Loop**.
- **Compounding Loop Connection**: When a job application completes, it records the application context and outcome. This serves as the feedback loop that tells CareerPilot which resume variants, cover letters, and positioning angles convert into real-world interviews.
- **User Benefit**: Users can trigger one-click applications that automatically execute the most efficient submission route without manual copy-pasting, while maintaining visibility of the detailed execution logs and receipt confirmations.

---

## 3. Requirements
- **State Machine Definition**: Implement a robust workflow state machine with states: `PREPARING`, `ATS_SUBMISSION`, `FORM_SUBMISSION`, `BROWSER_SUBMISSION`, `VERIFYING`, `COMPLETED`, and `FAILED`.
- **Workflow Checkpoints**: Save execution checkpoints at each major transition state to ensure that if a worker crashes, the workflow can resume from the last completed activity.
- **Recovery Logic**: Implement recovery strategies, such as escalating to `Browser Fallback Execution` if direct `ATS API` or `Deterministic Form Execution` fail.
- **Audit Logs**: Maintain detailed database records of every transition, payload modification, and external API status code.
- **User Notifications**: Trigger system notifications (via email or app dashboard) when human attention is required or when submissions finish/fail.
- **APIs**: Expose REST endpoints to trigger executions, retrieve live state checks, and request manual retries on execution failures.

---

## 4. Database Changes
We need to track applications and their corresponding workflow executions in Postgres.

### Table: `job_applications`
Tracks the high-level job application state and link to opportunity details.

| Field Name | Data Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | UUID | PRIMARY KEY, DEFAULT gen_random_uuid() | Unique identifier. |
| `user_id` | UUID | FOREIGN KEY references `users(id)`, NOT NULL | Owner of the application. |
| `opportunity_id` | UUID | FOREIGN KEY references `opportunities(id)`, NOT NULL | The matched job posting. |
| `current_status` | VARCHAR(50) | NOT NULL | e.g., `DRAFT`, `QUEUED`, `PROCESSING`, `SUBMITTED`, `FAILED`, `REJECTED`, `INTERVIEWING`. |
| `resume_version_id` | UUID | FOREIGN KEY references `profile_versions(id)`, NOT NULL | The specific resume snapshot used. |
| `cover_letter_text` | TEXT | NULLABLE | Cover letter customized for this posting. |
| `custom_answers` | JSONB | NULLABLE | Normalised answers to the job's screening questions. |
| `workflow_id` | VARCHAR(255) | NULLABLE | Link to the Temporal workflow execution. |
| `submitted_at` | TIMESTAMPTZ | NULLABLE | Timestamp when submission completed. |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | Record creation time. |
| `updated_at` | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | Last update time. |

### Table: `application_workflow_checkpoints`
Saves checkpoint payloads for recovery purposes.

| Field Name | Data Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | UUID | PRIMARY KEY, DEFAULT gen_random_uuid() | Unique identifier. |
| `application_id` | UUID | FOREIGN KEY references `job_applications(id)`, NOT NULL | Target job application. |
| `current_state` | VARCHAR(50) | NOT NULL | State name where checkpoint was saved. |
| `checkpoint_data` | JSONB | NOT NULL | Intermediate state variables, inputs, and browser state tokens. |
| `saved_at` | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | Timestamp when saved. |

### Indexes
- `idx_job_applications_user_id` on `job_applications(user_id)`
- `idx_job_applications_status` on `job_applications(current_status)`
- `idx_app_checkpoints_app_id` on `application_workflow_checkpoints(application_id)`

---

## 5. API Endpoints

### Trigger Application Workflow
- **HTTP Method**: `POST`
- **Route**: `/api/v2/applications/workflows/trigger`
- **Request Body (JSON)**:
```json
{
  "opportunity_id": "456ea3c7-1122-3344-5566-778899aabbcc",
  "resume_version_id": "567ea3c7-1122-3344-5566-778899aabbcc",
  "cover_letter_text": "I am writing to express my interest...",
  "custom_answers": {
    "salary_expectation": "140,000 USD",
    "authorized_to_work": "Yes"
  }
}
```
- **Response Payload (JSON)**:
```json
{
  "application_id": "890ea3c7-1122-3344-5566-778899aabbcc",
  "status": "QUEUED",
  "workflow_id": "app-wf-890ea3c7-1122-3344",
  "created_at": "2026-06-09T02:04:18Z"
}
```
- **HTTP Status Codes**:
  - `202 Accepted`: Workflow successfully queued.
  - `400 Bad Request`: Invalid payload parameters.
  - `401 Unauthorized`: Missing or invalid JWT.

### Fetch Application Execution Logs
- **HTTP Method**: `GET`
- **Route**: `/api/v2/applications/{application_id}/logs`
- **Path Parameters**:
  - `application_id` (string): Target application UUID.
- **Response Payload (JSON)**:
```json
{
  "application_id": "890ea3c7-1122-3344-5566-778899aabbcc",
  "status": "PROCESSING",
  "logs": [
    {
      "timestamp": "2026-06-09T02:04:20Z",
      "state": "PREPARING",
      "message": "Enriched user profile and assembled application materials."
    },
    {
      "timestamp": "2026-06-09T02:04:22Z",
      "state": "ATS_SUBMISSION",
      "message": "ATS API not available for target company. Escalating to form filler."
    },
    {
      "timestamp": "2026-06-09T02:04:25Z",
      "state": "FORM_SUBMISSION",
      "message": "Starting deterministic form parser for Workday platform."
    }
  ]
}
```
- **HTTP Status Codes**:
  - `200 OK`: Successful retrieval.
  - `401 Unauthorized`: Invalid JWT.
  - `404 Not Found`: Application ID not found.

---

## 6. Domain Models

```python
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, Dict, Any, List

class JobApplicationBase(BaseModel):
    opportunity_id: str
    resume_version_id: str
    cover_letter_text: Optional[str] = None
    custom_answers: Optional[Dict[str, Any]] = None

class JobApplicationCreate(JobApplicationBase):
    pass

class JobApplicationResponse(JobApplicationBase):
    id: str
    user_id: str
    current_status: str
    workflow_id: Optional[str] = None
    submitted_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True

class ApplicationLogEntry(BaseModel):
    timestamp: datetime
    state: str
    message: str
```

---

## 7. Services

### Class: `ApplicationWorkflowService`
Responsible for orchestration policies, checking readiness, saving state updates, and triggering fallback mechanics.

- **Method**: `queue_application`
  - **Inputs**:
    - `user_id` (str): Requester ID.
    - `data` (JobApplicationCreate): Application details.
  - **Return Type**: `JobApplicationResponse`
  - **Responsibilities**:
    - Creates database records in `job_applications`.
    - Generates unique `workflow_id`.
    - Invokes `TemporalWorkflowService` to spin up `ApplicationExecutionWorkflow`.
    - Updates application status to `QUEUED`.

- **Method**: `record_checkpoint`
  - **Inputs**:
    - `application_id` (str): Target application UUID.
    - `state` (str): Current workflow execution step.
    - `checkpoint_payload` (Dict[str, Any]): Intermediate state context.
  - **Return Type**: `None`
  - **Responsibilities**:
    - Inserts a new row in `application_workflow_checkpoints` for state tracking and error recovery.

- **Method**: `handle_execution_failure`
  - **Inputs**:
    - `application_id` (str): Target application.
    - `failed_state` (str): Step where it failed.
    - `error` (str): Failure details.
  - **Return Type**: `None`
  - **Responsibilities**:
    - Updates application status in `job_applications` to `FAILED`.
    - Saves failure log details.
    - Publishes `application.failed` event.

---

## 8. Events

### Event: `application.submitted`
- **Producer**: `ApplicationWorkflow` upon successful confirmation extraction.
- **Consumer**: `outcome-memory-system`, `weekly-digest-service`
- **Payload Schema**:
```json
{
  "event_id": "evt_app_sub_001",
  "event_type": "application.submitted",
  "timestamp": "2026-06-09T02:05:00Z",
  "payload": {
    "application_id": "890ea3c7-1122-3344-5566-778899aabbcc",
    "user_id": "9b1deb09-1122-3344-5566-778899aabbcc",
    "opportunity_id": "456ea3c7-1122-3344-5566-778899aabbcc",
    "submission_method": "FORM",
    "confirmation_number": "WD-198276A"
  }
}
```

### Event: `application.failed`
- **Producer**: `ApplicationWorkflow` on unrecoverable error.
- **Consumer**: `observability-service`
- **Payload Schema**:
```json
{
  "event_id": "evt_app_fail_001",
  "event_type": "application.failed",
  "timestamp": "2026-06-09T02:06:00Z",
  "payload": {
    "application_id": "890ea3c7-1122-3344-5566-778899aabbcc",
    "failed_state": "FORM_SUBMISSION",
    "error_message": "Required field 'work_authorization' selector not found."
  }
}
```

---

## 9. Background Jobs
No standalone cron is required, as the workflow is event-driven. However, Temporal workflow timers are used to sleep and wait for human inputs if a custom answer verification step is required, timing out after 48 hours.

---

## 10. Acceptance Criteria
- **Scenario**: Application is triggered and runs via ATS API.
  - **Given**: A user has approved an application brief.
  - **When**: The user calls the trigger endpoint.
  - **Then**: The system launches the workflow, determines ATS API is available, submits successfully, updates `job_applications` status to `SUBMITTED`, and emits an `application.submitted` event.
- **Scenario**: Application fails at ATS stage and falls back.
  - **Given**: ATS API fails with a 500 error.
  - **When**: The workflow catches the error.
  - **Then**: It saves the state, triggers the `FORM` tier, completes the form, and marks the submission as successful.

---

## 11. Edge Cases
- **Missing Required Questionnaire Answer**: If a form asks a question not covered by the user's profile context.
  - **Resolution**: The workflow pauses, registers a human-in-the-loop task, sends a notification, and waits for the user to answer the field before resuming execution.
- **Duplicate Application Detected**: The system queries the ATS/website before submission. If the user has already applied, the workflow completes with status `COMPLETED` and records "Already Applied" in the log details.

---

## 12. Test Requirements
- **Unit Tests**: Test the state transition logic in isolation.
- **Integration Tests**: Verify database transaction commits for checkpoints and logs under mocked Temporal runs.
- **Workflow Tests**: Validate correct execution routing: `ATS API` -> Failure -> `Deterministic Form` -> Success.

---

## 13. Dependencies
- **[F4.1: Temporal Infrastructure](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/feature-specs/temporal-infrastructure.md)**: Manages background execution reliability.
- **[F1.2: Authentication & Identity Context](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/feature-specs/authentication-identity-context.md)**: Resolves user ownership and credentials.
- **[F3.7: Human-in-the-Loop Review](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/feature-specs/human-in-the-loop-review.md)**: Provides the user-approved application brief payload.
- **[F4.3: ATS API Integrations](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/feature-specs/ats-api-integrations.md)**: First-choice execution API layer.
- **[F4.4: Deterministic Form Execution](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/feature-specs/deterministic-form-execution.md)**: Second-choice execution parser.
- **[F4.5: Browser Fallback Execution](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/feature-specs/browser-fallback-execution.md)**: Last-resort browser filler.

---
