# ADR 0006: Temporal.io for Durable Workflow Orchestration

## Status
Accepted

## Context
CareerPilot's execution layer is responsible for submitting job applications, synchronization pipelines, and weekly intelligence generation. As detailed in the [Application Workflow Feature Spec (application-workflow.md)](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/feature-specs/application-workflow.md) and the [Master Design Document (careerpilot_v2.md)](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/careerpilot_v2.md), these processes are complex, stateful, and run over long periods (from minutes to days). 

In particular, the `ApplicationWorkflow` involves a multi-tiered execution strategy (ATS API Integration -> Deterministic Form Execution -> Browser Fallback) that:
1. Interacts with unreliable external APIs and web interfaces that can timeout or fail mid-execution.
2. Needs to checkpoint intermediate states (such as browser session tokens or form progression data) to recover without repeating expensive steps.
3. Must enforce **Human Approval Gates** (as outlined in the [Human-in-the-Loop Review Spec](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/feature-specs/human-in-the-loop-review.md)), pausing execution to wait for a user to approve a resume layout or answer a custom screening question, then resuming from the exact point of interruption.
4. Requires long-term scheduling (e.g., daily market trend scraping, weekly career intelligence aggregates) that remains resilient across service restarts and host failures.

Standard asynchronous task queues like Celery lack the ability to persist execution history, handle state checkpoints, or halt processing to wait for external human signals. Writing a custom orchestrator using database tables and polled cron jobs invites race conditions, complex locking logic, and significant technical debt. We require a specialized framework designed to guarantee workflow durability, fault tolerance, and human-in-the-loop coordination.

## Decision
We will use **Temporal.io** as the core durable workflow orchestration engine for CareerPilot. The system will leverage the Temporal Python SDK to implement workflows and activities, executing them on dedicated worker processes.

### Implementation Strategy
* **Cluster Deployment:** We will run a Temporal cluster utilizing a PostgreSQL database backend for persistence. In development, this runs via Docker Compose; in production, we will utilize a managed Temporal Cloud instance or a self-hosted cluster on Kubernetes.
* **Workflow Definitions:** All long-running, multi-step orchestration processes will be written as Temporal Workflows:
  - `ApplicationExecutionWorkflow`: Coordinates the submission of resume materials, managing transitions between the ATS API, form parsers, and browser executors.
  - `ProfileSyncWorkflow`: Triggered on user profile changes to sync embeddings, evaluate data models, and update indexes.
  - `IntelligenceSyncWorkflow`: A daily scheduled workflow that refreshes macro trends and cohort benchmarks.
  - `DigestWorkflow`: A weekly scheduled workflow that compiles and fires the career intelligence digest.
* **Activity Decoupling:** All side-effecting operations (database writes, HTTP requests, LLM queries, browser sessions) will be isolated within Temporal Activities. Activities will be configured with explicit retry policies (e.g., exponential backoff, maximum attempts, timeouts) to handle transient failures automatically.
* **Human-in-the-Loop Gates (Signals):** When the workflow encounters a step requiring human review (e.g., verifying custom application answers), it will transition its internal status, emit a `workflow.gate_triggered` event, and block using `workflow.wait_condition` or a signal channel. The workflow will resume immediately when the API gateway sends a Temporal Signal (e.g., `ApproveResumeSignal`), or fail gracefully if a 48-hour timeout expires.
* **Status Auditing:** To prevent API consumers from directly querying the Temporal cluster (which has high history serialization overhead), the service layer will write execution updates to a native `workflow_execution_logs` PostgreSQL table, as specified in the [Temporal Infrastructure Spec (temporal-infrastructure.md)](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/feature-specs/temporal-infrastructure.md).

## Alternatives Considered

### AWS Step Functions
* **Why Evaluated:** AWS Step Functions is a fully managed cloud orchestrator that supports state machines, error retries, and human task integration.
* **Why Rejected:** AWS Step Functions locks CareerPilot into AWS infrastructure, preventing us from running the system locally for development or deploying on alternative clouds. Additionally, defining workflows in Amazon States Language (ASL) or JSON/YAML is verbose, lacks static type-checking, and is difficult to unit test compared to Temporal's standard Python code.

### Argo Workflows
* **Why Evaluated:** Argo is a Kubernetes-native workflow engine that runs each execution step in a separate Docker container, making it highly isolated and scalable.
* **Why Rejected:** Argo is optimized for batch-processing DAGs and data pipelines (similar to Apache Airflow) rather than application-level microservice orchestration. The latency for spinning up containers for each step is too high for interactive user applications, and managing human approvals or real-time signals requires complex external workarounds.

### Custom PostgreSQL State Machine Engine
* **Why Evaluated:** Building a custom engine by tracking workflow states in a `workflows` table, using Celery for task steps, and running a daemon process to poll for timeouts and transitions.
* **Why Rejected:** Writing custom distributed state management logic is notoriously complex. Developers must solve edge cases like handling worker crashes mid-transaction, avoiding double-execution of non-idempotent steps, and managing concurrent lock contentions. Adopting Temporal allows us to offload these distributed system complexities to a proven, battle-tested platform.

## Consequences
* **Guaranteed Execution:** If a worker process crashes mid-submission, the Temporal cluster detects the heart-beat failure and automatically reassigns the workflow state to another active worker, resuming from the last checkpoint.
* **Immutable Audit History:** The Temporal Web UI and history logs provide a step-by-step trace of every execution, including inputs, outputs, and failures. This is highly useful for debugging and explaining execution paths to users.
* **Deterministic Programming Constraints:** Temporal workflows must be deterministic. Developers cannot use direct I/O, network requests, random number generators, or standard system clocks (e.g., `time.sleep` or `datetime.utcnow`) inside workflow code. All such operations must be deferred to activities. Violating this constraint triggers workflow non-determinism panics.
* **Operational Footprint:** Temporal introduces multiple infrastructure components (Frontend, Matching, History, and Worker services, plus Elasticsearch for advanced visibility). This adds to the deployment footprint and monitoring requirements.

## Tradeoffs

### Operational Complexity vs. System Reliability
The addition of a Temporal cluster to our backend infrastructure, as outlined in [Dependency Graph (DEPENDENCY_GRAPH.md)](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/DEPENDENCY_GRAPH.md), increases initial setup and monitoring overhead. We accept this trade-off because the reliability of job applications is our highest business priority. A single lost or double-submitted application damages user trust; Temporal's guarantees eliminate this class of failures.

### Code Constraints vs. Orchestration Power
Writing workflows under Temporal's determinism rules requires specialized training for the engineering team. However, the ability to write workflow logic in native Python (using standard loops, condition checks, and try/except blocks) is far more productive and maintainable than writing ASL JSON files or managing complex state-polling database tables.
