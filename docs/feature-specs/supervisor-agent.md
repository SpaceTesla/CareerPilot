# Feature Specification: Supervisor Agent (F3.2)

## 1. Purpose
The Supervisor Agent is the primary orchestrator of the LangGraph multi-agent execution loop. It functions as the router, planner, and coordinator, processing incoming user requests (e.g., job analysis, resume tailoring, strategy generation), delegating specialized tasks to downstream nodes (Research Agent, Intelligence Agent), and enforcing human approval gates before executing high-impact external actions. The Supervisor maintains the high-level plan, validates execution outputs, and determines when a request is fulfilled.

---

## 2. User Value
The Supervisor Agent guarantees safety, reliability, and precision in CareerPilot. Rather than blindly executing AI-generated resumes or application submissions, the Supervisor implements strict approval gates. This gives users absolute control over what is submitted on their behalf, while automating the heavy lifting of gathering context, comparing opportunities, and structuring the inputs.

---

## 3. Requirements
* **Orchestration & Routing**: Analyze user queries to construct a dynamic execution plan. Dynamically route execution between the Research Agent, Intelligence Agent, and human approval gates based on graph state.
* **Human Approval Gates**: Intercept state execution when high-impact actions (e.g., submitting applications, modifying base profiles) are recommended. Persist the state, mark the session as paused, and emit an event to request human validation.
* **Supervisor Prompts**: Define structured system prompts guiding the Supervisor's routing and planning behavior, enforcing structured output format (JSON matching schema).
* **Decision Logging**: Log every routing choice, reasoning step, and state mutation in a dedicated `agent_decision_logs` table for explainability and training.
* **Failure Recovery Logic**: Detect agent node failures, rate limits, or low-confidence outputs, and execute fallback transitions (e.g., rerouting to another tool, falling back to a simpler heuristic, or querying the user).
* **Routing Analytics**: Track metrics on which agents are called, average hops per query, and routing accuracy.

---

## 4. Database Changes
The Supervisor Agent requires detailed logs of its decision-making steps.

### PostgreSQL Tables

#### `agent_decision_logs`
Tracks every routing choice, planning step, and reasoning process.
```sql
CREATE TABLE agent_decision_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    thread_id VARCHAR(255) NOT NULL REFERENCES agent_sessions(thread_id) ON DELETE CASCADE,
    run_id UUID NOT NULL,
    current_node VARCHAR(100) NOT NULL,
    routing_decision VARCHAR(100) NOT NULL, -- e.g. research_agent, intelligence_agent, human_gate, end
    reasoning_explanation TEXT NOT NULL,
    state_snapshot_before JSONB NOT NULL,
    state_snapshot_after JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX idx_decision_logs_thread_id ON agent_decision_logs(thread_id);
CREATE INDEX idx_decision_logs_run_id ON agent_decision_logs(run_id);
```

### Alembic Migration Plan
1. Create `agent_decision_logs` table.
2. Link `thread_id` to `agent_sessions(thread_id)` with cascading deletes.
3. Apply indexes on `thread_id` and `run_id`.

---

## 5. API Endpoints

### POST `/api/v1/supervisor/approve`
Approve or reject a pending decision on a thread.
* **Request Payload**:
  ```json
  {
    "thread_id": "thread_8f3b2a1c_user_4a2b9c3d",
    "decision_id": "dec_8899aabbcc",
    "approved": true,
    "user_notes": "Looks good, proceed with application."
  }
  ```
* **Response Body (200 OK)**:
  ```json
  {
    "status": "resumed",
    "next_node": "execution_node",
    "message": "Thread execution resumed successfully"
  }
  ```

### GET `/api/v1/supervisor/sessions/{thread_id}/decisions`
Fetch the complete routing and planning decision trace for a session.
* **Response Body (200 OK)**:
  ```json
  {
    "thread_id": "thread_8f3b2a1c_user_4a2b9c3d",
    "decisions": [
      {
        "id": "a1b2c3d4-5678-9101-1121-314151617181",
        "current_node": "supervisor",
        "routing_decision": "research_agent",
        "reasoning_explanation": "User requested analysis on Netflix. Initiating corporate data search.",
        "created_at": "2026-06-09T02:04:18Z"
      },
      {
        "id": "e5f6g7h8-9101-1121-3141-516171819202",
        "current_node": "supervisor",
        "routing_decision": "intelligence_agent",
        "reasoning_explanation": "Research complete. Computing fit score and delta mapping.",
        "created_at": "2026-06-09T02:05:00Z"
      }
    ]
  }
  ```

---

## 6. Domain Models

```python
from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from typing import List, Optional

class RoutingDecision(BaseModel):
    next_node: str = Field(description="The key of the node to route to. Allowed: 'research_agent', 'intelligence_agent', 'human_gate', 'end'.")
    reasoning: str = Field(description="Structured explanation for this routing path decision.")
    required_context: List[str] = Field(description="List of fields required in state before executing next node.")

class DecisionLogEntry(BaseModel):
    id: UUID
    thread_id: str
    run_id: UUID
    current_node: str
    routing_decision: str
    reasoning_explanation: str
    created_at: datetime
```

---

## 7. Services

### `SupervisorOrchestrationService`
* **Method**: `route_next(state: CareerPilotState) -> RoutingDecision`
  * Runs the Supervisor planning LLM with structured outputs to resolve the next node in the graph.
* **Method**: `log_decision(thread_id: str, run_id: UUID, current_node: str, decision: RoutingDecision, state_before: dict, state_after: dict) -> None`
  * Persists decision metrics to `agent_decision_logs`.
* **Method**: `apply_human_gate(thread_id: str) -> None`
  * Pauses graph execution, raises the state lock, and triggers notifications.

---

## 8. Events

### `agent.supervisor.routed`
* **Producer**: `SupervisorOrchestrationService`
* **Consumer**: `ObservabilityPlatform`, `InteractionMemory`
* **Payload**:
  ```json
  {
    "thread_id": "thread_8f3b2a1c_user_4a2b9c3d",
    "run_id": "bbccdd11-2233-4455-6677-8899aabbccdd",
    "from_node": "supervisor",
    "to_node": "research_agent",
    "reasoning": "Searching JSearch database for current hiring trends at Netflix."
  }
  ```

### `agent.supervisor.gate_triggered`
* **Producer**: `SupervisorOrchestrationService`
* **Consumer**: Notification Service, API Router
* **Payload**:
  ```json
  {
    "thread_id": "thread_8f3b2a1c_user_4a2b9c3d",
    "reason": "Execution paused. Review of personalized resume required.",
    "approval_url": "https://careerpilot.io/app/review/thread_8f3b2a1c_user_4a2b9c3d"
  }
  ```

---

## 9. Background Jobs
No standalone background tasks are required for routing. However, standard timeout mechanisms configured in [langgraph-foundation.md](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/feature-specs/langgraph-foundation.md) (F3.1) apply to Supervisor states.

---

## 10. Acceptance Criteria
* **AC 1**: Given an incoming query, when the Supervisor evaluates the state, it must produce a routing decision conforming strictly to the `RoutingDecision` schema (no raw strings).
* **AC 2**: Given a routing transition, when an exception occurs in a worker node (e.g., Research Agent fails), the Supervisor must intercept the failure and attempt a structured fallback path rather than crashing the thread.
* **AC 3**: Given a transition targeting an external submission, when the Supervisor triggers a human gate, the thread state must transition to `paused_for_approval` and require an API invocation to resume.

---

## 11. Edge Cases
* **Infinite Execution Loops**: If the Supervisor keeps routing between Research and Intelligence agents iteratively, the graph must enforce a maximum execution hop limit (e.g., 8 hops) and terminate with an error.
* **Low-Confidence Outputs**: If the LLM generates a routing node that doesn't exist, the supervisor framework must catch the parsing exception and fall back to the `human_gate` to prevent illegal operations.
* **Concurrent Resumes**: If a user submits two approval calls for the same paused execution thread simultaneously, the API must use a pessimistic write lock on the `agent_sessions` row to prevent double-resuming.

---

## 12. Test Requirements
* **Unit Testing**:
  * Assert Supervisor prompt parser handles malformed or incomplete JSON formats gracefully.
  * Verify that `agent_decision_logs` are accurately captured for every transition.
* **Integration Testing**:
  * Execute a complete multi-step routing flow including nodes for Research, Intelligence, and Approval Gates to ensure correct edge conditions.
* **Agent/Workflow Evaluation**:
  * Perform evaluation runs to check supervisor routing correctness. Out of 100 test prompts, the Supervisor must route to the appropriate domain agent > 95% of the time.

---

## 13. Dependencies
* This feature depends on:
  * [langgraph-foundation.md](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/feature-specs/langgraph-foundation.md) (F3.1)
  * [authentication-identity-context.md](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/feature-specs/authentication-identity-context.md) (F1.2)
* This feature is a dependency for:
  * [human-in-the-loop-review.md](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/feature-specs/human-in-the-loop-review.md) (F3.7)
  * [career-strategy-reviews.md](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/feature-specs/career-strategy-reviews.md) (F7.4)
