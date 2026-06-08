# Feature Specification: LangGraph Foundation (F3.1)

## 1. Purpose
LangGraph Foundation establishes the core multi-agent state-machine runtime for CareerPilot. It provides a standardized framework to define, execute, persist, and observe complex agent workflows. It translates high-level career strategy and market intelligence objectives into a structured execution graph of specialized nodes and conditional edges. By managing the graph state (`CareerPilotState`) across asynchronous executions, checkpointing graph history for user resumes and approvals, and integrating with observability engines (Langfuse/OpenTelemetry), this foundation enables robust, multi-turn AI reasoning loops.

---

## 2. User Value
The LangGraph Foundation is the engine behind the Career Intelligence Compounding Loop. By structuring agents as deterministic state-machine graphs instead of raw, conversational LLM wrappers, the platform ensures that recommendations (such as job alignment analyses or skill gap mitigations) are repeatable, explainable, and trace-backed. Users benefit from highly contextualized, multi-step research and analysis that can pause for human approval and resume without losing context.

---

## 3. Requirements
* **State Management**: Implement a typed `CareerPilotState` representing the execution context, including user profile snapshots, query details, retrieved job listings, extracted skill vectors, agent decisions, and audit paths.
* **Graph Structure**: Establish the default supervisor-led graph execution flow, supporting node dispatching, sub-graph runs, and state joins.
* **State Persistence (Checkpointing)**: Configure a PostgreSQL-backed checkpoint manager (`PostgresSaver`) in LangGraph to save thread execution snapshots at every transition, allowing long-running agents to resume after human gates.
* **Observability & Tracing**: Integrate Langfuse to trace LLM calls, token usages, latency, prompt templates, and agent routing logs.
* **Error Handling & Retries**: Build a robust retry mechanism at the node level utilizing exponential backoff for LLM API outages.
* **Metrics & Monitoring**: Export graph-level metrics (e.g., node latency, token cost per run, graph failure rates) via standard Prometheus telemetry hooks.
* **Testing Harness**: Build mock environments and fixtures to run graphs deterministically in test environments without calling live LLMs.

---

## 4. Database Changes
We require tables to store session states, checkpoint data (for LangGraph's runtime), and detailed execution runs for audit and analysis.

### PostgreSQL Tables

#### `agent_sessions`
Stores metadata about a distinct user session or thread run.
```sql
CREATE TABLE agent_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    thread_id VARCHAR(255) UNIQUE NOT NULL,
    current_status VARCHAR(50) NOT NULL DEFAULT 'active', -- active, paused_for_approval, completed, failed
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX idx_agent_sessions_user_id ON agent_sessions(user_id);
CREATE INDEX idx_agent_sessions_thread_id ON agent_sessions(thread_id);
```

#### `agent_checkpoints`
Backs the LangGraph `PostgresSaver` to persist graph state between node executions.
```sql
CREATE TABLE agent_checkpoints (
    thread_id VARCHAR(255) NOT NULL REFERENCES agent_sessions(thread_id) ON DELETE CASCADE,
    checkpoint_id VARCHAR(255) NOT NULL,
    parent_id VARCHAR(255),
    checkpoint BYTEA NOT NULL, -- serialized state binary
    metadata JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    PRIMARY KEY (thread_id, checkpoint_id)
);

CREATE INDEX idx_agent_checkpoints_lookup ON agent_checkpoints(thread_id, checkpoint_id DESC);
```

#### `agent_runs`
Tracks telemetry and outputs of an individual graph execution invocation.
```sql
CREATE TABLE agent_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    thread_id VARCHAR(255) NOT NULL REFERENCES agent_sessions(thread_id) ON DELETE CASCADE,
    trigger_source VARCHAR(100) NOT NULL, -- user_prompt, scheduler, manual_resume
    start_time TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    end_time TIMESTAMP WITH TIME ZONE,
    tokens_used INTEGER DEFAULT 0 NOT NULL,
    estimated_cost NUMERIC(10, 6) DEFAULT 0.000000 NOT NULL,
    success BOOLEAN DEFAULT TRUE NOT NULL,
    error_message TEXT
);
```

### Alembic Migration Plan
1. Create `agent_sessions` table with indexes on `user_id` and `thread_id`.
2. Create `agent_checkpoints` table to support LangGraph `PostgresSaver`.
3. Create `agent_runs` table with a foreign key to `agent_sessions`.
4. Apply indices on foreign keys and compound check-pointing lookups.

---

## 5. API Endpoints

### POST `/api/v1/agents/session`
Initiate an agent session/thread for a user.
* **Request Payload**:
  ```json
  {
    "user_id": "4a2b9c3d-1234-5678-9101-abcdef123456"
  }
  ```
* **Response Body (201 Created)**:
  ```json
  {
    "session_id": "8f3b2a1c-9988-7766-5544-33221100aabb",
    "thread_id": "thread_8f3b2a1c_user_4a2b9c3d",
    "status": "active",
    "created_at": "2026-06-09T02:00:00Z"
  }
  ```

### POST `/api/v1/agents/run`
Execute the LangGraph workflow on a specific thread.
* **Request Payload**:
  ```json
  {
    "thread_id": "thread_8f3b2a1c_user_4a2b9c3d",
    "user_message": "Analyze my resume alignment with Senior AI Architect roles in New York.",
    "bypass_human_gate": false
  }
  ```
* **Response Body (202 Accepted)**:
  ```json
  {
    "run_id": "bbccdd11-2233-4455-6677-8899aabbccdd",
    "thread_id": "thread_8f3b2a1c_user_4a2b9c3d",
    "status": "processing",
    "message": "Graph execution started in background"
  }
  ```

### GET `/api/v1/agents/session/{thread_id}/state`
Get the current state snapshot for a given thread.
* **Response Body (200 OK)**:
  ```json
  {
    "thread_id": "thread_8f3b2a1c_user_4a2b9c3d",
    "status": "paused_for_approval",
    "next_nodes": ["human_review_gate"],
    "state": {
      "user_profile": {
        "id": "4a2b9c3d-1234-5678-9101-abcdef123456",
        "skills": ["Python", "Machine Learning", "FastAPI"]
      },
      "retrieved_jobs": [],
      "research_signals": {},
      "routing_decision": "research_agent"
    }
  }
  ```

---

## 6. Domain Models

```python
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from uuid import UUID
from datetime import datetime

class UserProfileSnapshot(BaseModel):
    id: UUID
    skills: List[str]
    experience_years: float
    target_roles: List[str]
    target_salary_min: Optional[int] = None

class JobDocument(BaseModel):
    job_id: str
    title: str
    company_name: str
    description: str
    inferred_skills: List[str]
    relevance_score: float

class CareerPilotState(BaseModel):
    thread_id: str
    user_id: UUID
    user_profile: UserProfileSnapshot
    user_input_query: str
    retrieved_jobs: List[JobDocument] = Field(default_factory=list)
    research_signals: Dict[str, Any] = Field(default_factory=dict)
    intelligence_report: Optional[Dict[str, Any]] = None
    next_node_override: Optional[str] = None
    approved_by_user: bool = False
    audit_trail: List[str] = Field(default_factory=list)
```

---

## 7. Services

### `GraphStateService`
* **Method**: `get_state(thread_id: str) -> CareerPilotState`
  * Fetches the current LangGraph state snapshot from PostgresSaver.
* **Method**: `update_state(thread_id: str, state_update: Dict[str, Any]) -> CareerPilotState`
  * Overrides or pushes state values into the active graph thread.

### `GraphExecutionService`
* **Method**: `compile_graph() -> CompiledGraph`
  * Assembles nodes (Supervisor, Research, Intelligence) and builds conditional edges.
* **Method**: `run_graph_async(thread_id: str, input_state: Dict[str, Any]) -> str`
  * Triggers background execution using a Celery/Temporal task worker. Returns `run_id`.
* **Method**: `resume_graph(thread_id: str, approval_status: bool) -> str`
  * Resumes a graph paused at a human-in-the-loop review gate.

---

## 8. Events

### `agent.graph.started`
* **Producer**: `GraphExecutionService`
* **Consumer**: `ObservabilityPlatform`, `InteractionMemory`
* **Payload**:
  ```json
  {
    "event_id": "evt_11223344",
    "timestamp": "2026-06-09T02:04:18Z",
    "thread_id": "thread_8f3b2a1c_user_4a2b9c3d",
    "user_id": "4a2b9c3d-1234-5678-9101-abcdef123456",
    "query": "Analyze my resume alignment with Senior AI Architect roles"
  }
  ```

### `agent.graph.paused`
* **Producer**: LangGraph Runtime Node (`human_review_gate`)
* **Consumer**: Notification Service, User API
* **Payload**:
  ```json
  {
    "event_id": "evt_55667788",
    "timestamp": "2026-06-09T02:05:00Z",
    "thread_id": "thread_8f3b2a1c_user_4a2b9c3d",
    "gate_reason": "User approval needed for resume customization"
  }
  ```

### `agent.graph.completed`
* **Producer**: `GraphExecutionService`
* **Consumer**: `OutcomeCalibration`, `ObservabilityPlatform`
* **Payload**:
  ```json
  {
    "event_id": "evt_99001122",
    "timestamp": "2026-06-09T02:06:12Z",
    "thread_id": "thread_8f3b2a1c_user_4a2b9c3d",
    "execution_time_ms": 114000,
    "tokens_spent": 12500,
    "success": true
  }
  ```

---

## 9. Background Jobs
* **Job Name**: `agent_run_timeout_monitor`
  * **Frequency**: Every 10 minutes (`*/10 * * * *`)
  * **Payload**: None
  * **Logic**: Scan `agent_runs` for execution status `processing` that has been running for > 15 minutes. Terminate, write error trace, mark status as `failed`, and emit alerting event.
  * **Retry Behavior**: Standard Celery backoff retry (3 attempts, 30s base delay).

---

## 10. Acceptance Criteria
* **AC 1**: Given an active user session, when executing a LangGraph run, the system must write initial, intermediate checkpoints to the `agent_checkpoints` table.
* **AC 2**: Given a graph paused for user approval, when the user updates the approval flag, the graph must successfully resume execution from the exact checkpoint and complete downstream nodes.
* **AC 3**: All LLM calls and transitions within the graph execution must be logged and visible in Langfuse dashboard within 5 seconds of node completion.

---

## 11. Edge Cases
* **Database Connection Loss during Checkpointing**: Graph nodes must implement local in-memory retries (up to 3 times) before raising a critical system error to prevent losing active execution states.
* **Token Limit Exceeded**: If the LLM context window is exceeded, the state engine must truncate historical messages or trigger the memory summarization node before retrying the failed node.
* **Asynchronous Timeout**: If external APIs called by the Research Agent fail or hang, the supervisor node must gracefully abort execution, record the timeout, and transition to a user-notified failure state.

---

## 12. Test Requirements
* **Unit Testing**:
  * Verify state-machine validation logic (e.g., ensuring invalid transitions trigger exceptions).
  * Mock `PostgresSaver` and verify checkpoint state serialization/deserialization.
* **Integration Testing**:
  * Execute a mock LangGraph lifecycle from start node, through human approval gate, to end node using a SQLite/PostgreSQL test database.
* **Agent/Workflow Evaluation**:
  * Execute graph scenarios against deterministic LLM mock outputs to verify correct routing paths based on predefined mock conditions.

---

## 13. Dependencies
* This feature depends on [project-setup-architecture.md](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/feature-specs/project-setup-architecture.md) (F1.1) to configure the base databases and environment settings.
* This feature is a dependency for:
  * [supervisor-agent.md](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/feature-specs/supervisor-agent.md) (F3.2)
  * [research-agent.md](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/feature-specs/research-agent.md) (F3.3)
  * [intelligence-agent.md](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/feature-specs/intelligence-agent.md) (F3.4)
  * [interaction-memory.md](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/feature-specs/interaction-memory.md) (F3.5)
  * [evaluation-agent.md](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/feature-specs/evaluation-agent.md) (F5.2)
