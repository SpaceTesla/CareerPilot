# CareerPilot Multi-Agent Architecture Specification

This document details the multi-agent system orchestration designed for CareerPilot v2. It defines the schemas, inputs, outputs, states, decision trees, failure logic, and contract interfaces for all 5 load-bearing agents, complying with [ADR 0007 (LangGraph)](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/adrs/0007-langgraph.md) and [ADR 0008 (Agent Architecture)](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/adrs/0008-agent-architecture.md).

---

## Global Agent State: `CareerPilotState`

All agents in the system read and write to a unified, strongly-typed state machine defined using Pydantic.

```python
class CareerPilotState(BaseModel):
    # Context Identifiers
    user_id: UUID
    thread_id: UUID
    active_job_id: Optional[UUID] = None

    # Active Data Snapshots
    user_profile: Optional[Dict[str, Any]] = None
    user_goals: Optional[Dict[str, Any]] = None
    target_job: Optional[Dict[str, Any]] = None

    # Agent Communication Layer
    last_active_agent: Optional[str] = None
    routing_decision: Optional[str] = None
    agent_logs: List[Dict[str, Any]] = []

    # Intermediate Synthesis Outputs
    company_research: Optional[Dict[str, Any]] = None
    health_score: Optional[Dict[str, Any]] = None
    position_delta: Optional[Dict[str, Any]] = None
    opportunity_score: Optional[Dict[str, Any]] = None

    # Human Approval Gates
    human_approved_brief: Optional[Dict[str, Any]] = None
    human_feedback: Optional[str] = None

    # Execution Tracking
    submission_status: Optional[str] = None
    execution_logs: List[str] = []

    # Loop Guard
    hop_count: int = 0
```

---

## 1. Supervisor Agent

The Supervisor is the hub orchestrator that manages routing states, increments loop guards, logs planning runs, and halts execution when human gates are triggered.

### 1.1 Specifications

- **Responsibilities:** Orchestrate the control loop flow, verify user profile completeness, route requests to Spoke Agents, manage loop guards, and coordinate Human-in-the-Loop review gates.
- **Inputs:** Incoming user request/prompt, current `CareerPilotState` snapshot.
- **Outputs:** Next routing target node, planning rationale.
- **State Schema:** Writes directly to `routing_decision`, updates `hop_count` (+1 per turn), logs decisions to `agent_logs`.
- **Decision Points:**
  - _If `hop_count >= 15`:_ Route to `error_handler` (halt to prevent infinite loops).
  - _If profile or goals are missing:_ Route to `research_agent` to request parser sync.
  - _If target job details are not researched:_ Route to `research_agent`.
  - _If scores/delta are not synthesized:_ Route to `intelligence_agent`.
  - _If application execution is requested but `human_approved_brief` is missing:_ Route to `human_gate` (pause workflow).
  - _If application execution is approved:_ Route to `execution_agent`.
  - _If execution has finished:_ Route to `end`.
- **Failure Handling:** Triggers hard failures if LangGraph saver writes block. Fallbacks to a safe manual route back to the user if the LLM output is malformed or invalid.
- **Evaluation Criteria:** Routing accuracy vs. golden path trajectories (Goal: 100%), hop efficiency (minimizing redundant node hops).

### 1.2 Prompt & Tool Contracts

- **System Prompt Contract:**
  ```text
  Role: Principal Router and Planner
  Context: You are orchestrating the execution loop for user {user_id}.
  Task: Inspect the current CareerPilotState and output the next logical step.
  Rules:
  - Never bypass the human gate before execution.
  - If goals/profile are uncalculated, always run Intelligence Agent first.
  - Output must strictly conform to the JSON schema.
  ```
- **Response JSON Schema:**
  ```json
  {
    "type": "object",
    "properties": {
      "next_node": {
        "type": "string",
        "enum": [
          "research_agent",
          "intelligence_agent",
          "execution_agent",
          "human_gate",
          "end"
        ]
      },
      "reasoning": { "type": "string" }
    },
    "required": ["next_node", "reasoning"]
  }
  ```
- **Tool Contracts:** None (Pure orchestrator).

---

## 2. Research Agent

Specialized spoke agent responsible for gathering, extracting, and normalizing company and job market context.

### 2.1 Specifications

- **Responsibilities:** Extract structured requirements (skills, experience years) from unstructured job descriptions, retrieve company profiles (hiring velocities, funding), and calculate attractiveness scores.
- **Inputs:** `active_job_id`, `target_job` text.
- **Outputs:** Structured company research data, normalized requirement lists.
- **State Schema:** Updates `company_research`, appends logs to `agent_logs`.
- **Decision Points:**
  - _If company data is cached in PostgreSQL:_ Retrieve cached entity; skip search.
  - _If company details are missing/stale:_ Execute `search_web` and `get_company_details` tools.
- **Failure Handling:** If search APIs time out or fail, falls back to parsing job description texts via regex/heuristics to gather basic company names and locations.
- **Evaluation Criteria:** Skill extraction F1-score (Goal: >=0.92), company profile completeness.

### 2.2 Prompt & Tool Contracts

- **System Prompt Contract:**
  ```text
  Role: Lead Market Intelligence Researcher
  Task: Analyze job description {target_job} and company metadata. Extract the core requirements.
  Rules:
  - Map all extracted skills to normalized skill aliases.
  - Calculate experience bounds precisely.
  - Output structured JSON profile.
  ```
- **Tool Contracts:**
  - `search_web(query: str) -> List[Dict[str, str]]`: Queries search engines for company signals.
  - `get_company_details(domain: str) -> Dict[str, Any]`: Fetches corporate registration/funding metadata.

---

## 3. Intelligence Agent

The core compiler spoke that synthesizes profiles, goals, and market telemetry to generate scores, deltas, and career roadmaps.

### 3.1 Specifications

- **Responsibilities:** Calculate Career Health Score parameters, extract prioritized Position Delta gaps, calculate job opportunity matches, and synthesize explanations.
- **Inputs:** `user_profile`, `user_goals`, `company_research`, `target_job`.
- **Outputs:** Computed composite scores, delta lists, fit rationale.
- **State Schema:** Updates `health_score`, `position_delta`, and `opportunity_score`.
- **Decision Points:**
  - _If target salary exceeds market percentiles:_ Decrement `compensation_alignment_score` and add to detractor drivers list.
  - _If critical skills are missing from profile:_ Generate missing skill delta entries ranked by market trend velocity.
- **Failure Handling:** If computation inputs are incomplete, uses base defaults (e.g. 50.0 score) and raises a warnings flag to prevent application crashes.
- **Evaluation Criteria:** Correlation between computed opportunity score and real interview callback outcomes (Goal: Pearson r >= 0.60).

### 3.2 Prompt & Tool Contracts

- **System Prompt Contract:**
  ```text
  Role: Principal Intelligence Synthesizer
  Task: Review user profile against target goals and market data.
  Rules:
  - Ground all insights in concrete evidence (no empty health scores).
  - Prioritize the top 3 position delta items based on velocity trends.
  - Produce detailed, friendly explanations.
  ```
- **Tool Contracts:**
  - `get_skill_trends(skill_ids: List[UUID]) -> Dict[UUID, Dict[str, Any]]`: Returns velocity/frequency telemetry.
  - `get_compensation_benchmarks(role: str, location: str) -> Dict[str, Any]`: Returns salary percentiles.

---

## 4. Execution Agent

The actions coordinator spoke that interfaces with ATS APIs and browser automations.

### 4.1 Specifications

- **Responsibilities:** Execute application submissions across Tier 1 (APIs), Tier 2 (Form Schemas), or Tier 3 (Playwright).
- **Inputs:** `user_profile`, `human_approved_brief` (cover letter, customized answers).
- **Outputs:** Submission outcome status, audit logs, error logs, execution receipts.
- **State Schema:** Updates `submission_status`, appends execution traces to `execution_logs`.
- **Decision Points:**
  - _If job ATS supports API (Greenhouse/Lever/Ashby):_ Execute via API (`submit_ats_api` tool).
  - _If API unsupported but schema available:_ Execute via form payload mapping (`fill_form_schema` tool).
  - _If standard schemas fail or are missing:_ Execute browser fallback flow (`execute_playwright_script` tool).
- **Failure Handling:** If API submissions fail with transient errors (e.g. 503), retries up to 3 times with exponential backoff. If permanent error, immediately falls back to Tier 2/3.
- **Evaluation Criteria:** Execution success rate (Goal: >=92%), 0% silent failures, form completion audits.

### 4.2 Prompt & Tool Contracts

- **System Prompt Contract:**
  ```text
  Role: Application Execution Coordinator
  Task: Submit user profile to target company ATS.
  Rules:
  - Always use the user-approved form answers.
  - Log every step, failure, and fallback trigger.
  - If fallback occurs, record a full execution trace.
  ```
- **Tool Contracts:**
  - `submit_ats_api(ats_type: str, payload: Dict[str, Any]) -> Response`: Submits profile via ATS API.
  - `fill_form_schema(schema_id: UUID, data: Dict[str, Any]) -> Response`: Generates and posts form inputs.
  - `execute_playwright_script(url: str, selectors: Dict[str, str], data: Dict[str, Any]) -> Dict[str, Any]`: Playwright script execution.

---

## 5. Evaluation Agent

The quality control agent that acts in the background to validate outputs.

### 5.1 Specifications

- **Responsibilities:** Evaluate the relevance and accuracy of Spoke Agent outputs, detect hallucinations, and run regressions checks.
- **Inputs:** Target agent outputs, context source documents, evaluation criteria metrics.
- **Outputs:** Binary evaluation rating (PASS/FAIL), numerical quality score, rationale logs.
- **State Schema:** Appends evaluation logs to `agent_logs` (does not overwrite business scores).
- **Decision Points:**
  - _If agent response contains facts missing from source context:_ Mark as FAIL (hallucination detected).
  - _If explanation fails grammar or formatting constraints:_ Route back to target node for repair.
- **Failure Handling:** If the evaluation model times out, defaults to a FAIL rating and alerts the system logger to flag potential performance issues.
- **Evaluation Criteria:** Evaluation alignment with human grading (Goal: Cohen's kappa >= 0.80).

### 5.2 Prompt & Tool Contracts

- **System Prompt Contract:**
  ```text
  Role: Strict Quality Control Judge (temperature=0)
  Task: Compare the agent's generated report against the input context.
  Rules:
  - Assess faithfulness: Are all assertions backed by the context?
  - Assess relevance: Does the answer address the user's specific request?
  - Output binary check results and detailed rating scores.
  ```
- **Response JSON Schema:**
  ```json
  {
    "type": "object",
    "properties": {
      "rating": { "type": "string", "enum": ["PASS", "FAIL"] },
      "faithfulness_score": {
        "type": "number",
        "minimum": 0.0,
        "maximum": 1.0
      },
      "relevance_score": { "type": "number", "minimum": 0.0, "maximum": 1.0 },
      "rationale": { "type": "string" }
    },
    "required": ["rating", "faithfulness_score", "relevance_score", "rationale"]
  }
  ```
- **Tool Contracts:**
  - `fetch_golden_datasets(dataset_id: UUID) -> List[Dict[str, Any]]`: Returns QA pairs.
  - `log_evaluation_results(metrics: Dict[str, Any]) -> None`: Logs run statistics.
