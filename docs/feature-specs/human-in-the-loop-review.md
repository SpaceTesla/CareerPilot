# Feature Specification: Human-in-the-Loop Review (F3.7)

## 1. Purpose
Human-in-the-Loop (HITL) Review provides the security and editing mechanisms required for high-impact actions in CareerPilot. Following the [Implementation Doctrine](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/IMPLEMENTATION_DOCTRINE.md), agents may recommend actions, but humans must approve them. When the Supervisor Agent schedules an execution task (e.g., submitting a customized resume or form answers to Greenhouse/Lever), it pauses the active thread and generates an approval request. Users can review the draft, make edits directly to the proposed application content (the "edit-and-resubmit" flow), and authorize the action. This feature bridges the gap between agent recommendation and execution.

---

## 2. User Value
Human-in-the-Loop Review builds user confidence by guaranteeing that the platform will never submit job applications or contact hiring managers without explicit human review. Users maintain control over how their professional brand is presented, with the ability to modify AI-generated answers or resumes to ensure they are 100% accurate, while saving hours on drafting and form-filling.

---

## 3. Requirements
* **Approval Request Schema**: Define structured data models for tracking approval status (pending, approved, rejected, edited), payload details, and audit history.
* **Approval Workflow Integration**: Hook into the LangGraph state machine execution, pausing thread traversal when the supervisor triggers a gate node and generating an approval request.
* **Edit-and-Resubmit Flow**: Provide the API endpoints and models to allow users to patch proposed resume modifications, cover letter contents, or form field answers before resuming.
* **Approval Audit Logs**: Write every approval, rejection, and modification delta to a secure audit table to guarantee transparency and provide training data for model calibration.
* **Notifications**: Trigger notification events when approvals are requested, letting users know their attention is required.
* **Workflow Analytics**: Calculate metrics on approval queue latencies, edit frequencies, rejection rates, and user engagement times.

---

## 4. Database Changes
We require tables to store the approval requests and audit histories.

### PostgreSQL Tables

#### `agent_approval_requests`
Stores pending, approved, and rejected execution briefs that require human sign-off.
```sql
CREATE TABLE agent_approval_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    thread_id VARCHAR(255) NOT NULL REFERENCES agent_sessions(thread_id) ON DELETE CASCADE,
    action_type VARCHAR(100) NOT NULL, -- e.g. submit_job_application, modify_profile_skills
    payload JSONB NOT NULL, -- contains proposed fields, resumes, and text answers
    status VARCHAR(50) NOT NULL DEFAULT 'pending', -- pending, approved, rejected, edited
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX idx_approval_requests_user ON agent_approval_requests(user_id);
CREATE INDEX idx_approval_requests_status ON agent_approval_requests(status);
```

#### `agent_approval_audit_logs`
Tracks modifications, actions, timestamps, and active user overrides.
```sql
CREATE TABLE agent_approval_audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    approval_request_id UUID NOT NULL REFERENCES agent_approval_requests(id) ON DELETE CASCADE,
    actor_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    action_taken VARCHAR(50) NOT NULL, -- approved, rejected, modified
    changes_made JSONB, -- stores diff of modifications (before vs after)
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX idx_approval_audit_request ON agent_approval_audit_logs(approval_request_id);
```

### Alembic Migration Plan
1. Create `agent_approval_requests` table with status indexes.
2. Create `agent_approval_audit_logs` table.
3. Configure cascading deletes and link foreign keys appropriately.

---

## 5. API Endpoints

### GET `/api/v1/approvals/pending`
Retrieve list of approval requests requiring action for the active user.
* **Response Body (200 OK)**:
  ```json
  [
    {
      "id": "app_9988aa11-bb22-33cc-44dd-556677889900",
      "thread_id": "thread_8f3b2a1c_user_4a2b9c3d",
      "action_type": "submit_job_application",
      "payload": {
        "job_title": "Senior Platform Engineer",
        "company_name": "Stripe",
        "resume_url": "https://s3.amazonaws.com/resumes/4a2b9c3d_custom.pdf",
        "proposed_answers": {
          "why_netflix": "I am passionate about high-throughput infrastructure..."
        }
      },
      "status": "pending",
      "created_at": "2026-06-09T02:04:18Z"
  }
  ]
  ```

### POST `/api/v1/approvals/{approval_id}/action`
Process a user decision (approve, reject, or edit-and-resubmit).
* **Request Payload**:
  ```json
  {
    "action": "approved", -- approved, rejected, modified
    "edited_payload": {
      "proposed_answers": {
        "why_netflix": "I am passionate about high-throughput infrastructure and building billing ledgers..."
      }
    }
  }
  ```
* **Response Body (200 OK)**:
  ```json
  {
    "approval_id": "app_9988aa11-bb22-33cc-44dd-556677889900",
    "status": "approved",
    "workflow_status": "resumed",
    "message": "Approval processed. LangGraph thread execution has resumed."
  }
  ```

---

## 6. Domain Models

```python
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
from uuid import UUID
from datetime import datetime

class ApprovalRequestPayload(BaseModel):
    job_title: str
    company_name: str
    resume_url: str
    proposed_answers: Dict[str, str] = Field(default_factory=dict)
    additional_metadata: Dict[str, Any] = Field(default_factory=dict)

class ApprovalActionRequest(BaseModel):
    action: str = Field(description="Action must be 'approved', 'rejected', or 'modified'")
    edited_payload: Optional[Dict[str, Any]] = None

class ApprovalSummary(BaseModel):
    id: UUID
    thread_id: str
    action_type: str
    payload: ApprovalRequestPayload
    status: str
    created_at: datetime
```

---

## 7. Services

### `HumanInTheLoopService`
* **Method**: `create_approval_request(user_id: UUID, thread_id: str, action: str, payload: dict) -> UUID`
  * Registers a new request in `agent_approval_requests`, flags status as `pending`, and pauses execution thread.
* **Method**: `process_approval_action(approval_id: UUID, actor_id: UUID, action: str, edited_payload: Optional[dict] = None) -> dict`
  * Updates the status of the request. If edits are present, calculates diff, records to `agent_approval_audit_logs`, merges modifications into the thread state, and unlocks/resumes the LangGraph thread via the Supervisor Agent.

---

## 8. Events

### `agent.approval.requested`
* **Producer**: `HumanInTheLoopService`
* **Consumer**: Notification Service (Email/Slack/Web Push)
* **Payload**:
  ```json
  {
    "event_id": "evt_app_req_01",
    "timestamp": "2026-06-09T02:04:18Z",
    "approval_request_id": "app_9988aa11-bb22-33cc-44dd-556677889900",
    "user_id": "4a2b9c3d-1234-5678-9101-abcdef123456",
    "company_name": "Stripe",
    "action_type": "submit_job_application"
  }
  ```

### `agent.approval.processed`
* **Producer**: `HumanInTheLoopService`
* **Consumer**: `OutcomeCalibration`, `ObservabilityPlatform`
* **Payload**:
  ```json
  {
    "event_id": "evt_app_proc_02",
    "timestamp": "2026-06-09T02:05:30Z",
    "approval_request_id": "app_9988aa11-bb22-33cc-44dd-556677889900",
    "action_taken": "approved",
    "was_modified": true
  }
  ```

---

## 9. Background Jobs
No recurring background tasks are needed for this feature. When a request is approved, execution resumes synchronously or pushes to the queue immediately.

---

## 10. Acceptance Criteria
* **AC 1**: Given a paused LangGraph thread, when the user queries `/api/v1/approvals/pending`, they must see the correct payload and metadata for the paused node.
* **AC 2**: Given an approval request, when the user action is `approved`, the system must update the database, append to audit logs, and trigger the resumption of the graph thread.
* **AC 3**: Given an approval request, when the user edits proposed answers and submits, the system must write the differences to `agent_approval_audit_logs` and merge the edits into the thread execution state.

---

## 11. Edge Cases
* **Double Submission**: If a user double-clicks the approve button, the second API call must return HTTP 409 Conflict, verifying the status has already transitioned away from `pending`.
* **Stale Thread State**: If the LangGraph session expired or was deleted while waiting for approval, the review submission must gracefully inform the user and reconstruct the state from the last available checkpoint.
* **Malformed Edits**: If the user submits edit fields that fail form validation rules (e.g., leaving a mandatory email field blank), the system must reject the action, return HTTP 422, and keep the approval status `pending`.

---

## 12. Test Requirements
* **Unit Testing**:
  * Verify diff builder logic correctly identifies added, modified, or deleted fields and formats the audit logs cleanly.
  * Assert validation schema intercepts malformed action requests.
* **Integration Testing**:
  * Create approval requests, apply user actions with custom payload changes, and verify state modifications and audit log rows exist in the DB.
* **Agent/Workflow Evaluation**:
  * Run mock human interaction loops to confirm that resumed thread state contains the modified fields rather than original agent-generated fields.

---

## 13. Dependencies
* This feature depends on:
  * [supervisor-agent.md](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/feature-specs/supervisor-agent.md) (F3.2)
* This feature is a dependency for:
  * [application-workflow.md](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/feature-specs/application-workflow.md) (F4.2)
