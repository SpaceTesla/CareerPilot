# ADR 0008: Supervisor-Coordinated Multi-Agent Topology

## Status
Accepted

## Context
CareerPilot is designed around a continuous career intelligence compounding loop. Operating this loop requires executing distinct, complex AI-driven tasks:
1. **Researching** companies, job postings, hiring trends, and market signals (Research Agent).
2. **Analyzing** resume alignment, calculating the `CareerHealthScore`, mapping the `PositionDelta`, and benchmarking peer cohorts (Intelligence Agent).
3. **Submitting** job applications, executing deterministic form filler pipelines, and handling browser automation (Execution Agent).
4. **Evaluating** output data for regressions, hallucinations, and safety compliance (Evaluation Agent).

We need an agent architecture that coordinates these specialized tasks while satisfying the constraints in the [Implementation Doctrine (IMPLEMENTATION_DOCTRINE.md)](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/IMPLEMENTATION_DOCTRINE.md):
- Enforce strict type validation across execution transitions.
- Intercept workflows for **Human Approval Gates** prior to high-impact external actions (like submitting applications).
- Log complete, explainable decision traces for every step.

If we design this as a **Single-Agent System** where one LLM has access to all tools (search, database, browser, scoring), the prompt size and tool descriptions scale rapidly. This leads to context window bloat, tool selection errors, parameter hallucinations, high latency, and high cost.

If we design this as an **Unstructured Peer-to-Peer Agent Chat** (where agents communicate directly in a flat room), the system is prone to infinite loops, unpredictable routing behaviors, state corruption, and difficulty in intercepting executions for human verification. 

We require a structured multi-agent topology that isolates task responsibilities, maintains deterministic routing, and enforces centralized coordination.

## Decision
We will implement a **Supervisor-Coordinated Multi-Agent Topology** (Hub-and-Spoke model) built on top of LangGraph.

```
                    ┌─────────────────────────┐
                    │     SUPERVISOR AGENT    │◀───┐
                    │          (Hub)          │    │
                    │                         │    │
                    │  Plans execution paths  │    │
                    │  Routes dynamically     │    │
                    │  Manages human gates    │    │
                    └────────────┬────────────┘    │
                                 │                 │ Returns control
        ┌────────────────────────┼─────────────────┼────────────────────────┐
        │                        │                 │                        │
  ┌─────▼──────┐           ┌─────▼──────┐    ┌─────┴──────┐           ┌─────▼──────┐
  │  RESEARCH  │           │INTELLIGENCE│    │ EXECUTION  │           │ EVALUATION │
  │   AGENT    │           │   AGENT    │    │   AGENT    │           │   AGENT    │
  │  (Spoke)   │           │  (Spoke)   │    │  (Spoke)   │           │ (Cross-cut)│
  │            │           │            │    │            │           │            │
  │ Company +  │           │ Health     │    │ Application│           │ Evaluates  │
  │ role intel │           │ Score, fit │    │ submission │           │ reasoning  │
  │ JSearch API│           │ delta map  │    │ automation │           │ & output   │
  └────────────┘           └────────────┘    └────────────┘           └────────────┘
```

### Topology Architecture
1. **Supervisor Agent (The Hub):** The central router and planner. It receives the user prompt, reads the current `CareerPilotState`, and determines the next node to execute. It does not perform research or compute metrics directly. Instead, it decides if we need to route to the `ResearchAgent`, `IntelligenceAgent`, `ExecutionAgent`, pause at a `HumanGate`, or terminate (`End`). It is forced to produce a structured JSON output matching the `RoutingDecision` schema.
2. **Research Agent (Spoke):** Specialized in query construction, API calls, and corporate profile scraping. It writes parsed market signals and job descriptions into the state.
3. **Intelligence Agent (Spoke):** Specialized in data benchmarking, statistical comparison, and scoring. It calculates alignment delta metrics and explains health score drops.
4. **Execution Agent (Spoke):** Specialized in automation. It triggers the Temporal application workflows and records submission statuses.
5. **Evaluation Agent (Cross-Cutting):** An independent supervisor-facing node that reviews the inputs, intermediate prompts, and final outputs of the spokes to check for compliance, formatting issues, or hallucinations.
6. **State-Mediated Communication:** Spokes are decoupled. A spoke agent is prohibited from invoking or sending messages to another spoke agent directly. When a spoke finishes its task, it writes its structured output to the `CareerPilotState` and returns control to the Supervisor. This ensures all transitions are mediated by the central coordinator.

### Coordination and Audit Log
Every routing choice, planning reasoning, and state snapshot is persisted to the `agent_decision_logs` database table. This provides a transparent audit trace showing why the Supervisor routed to a specific agent and what information was updated.

## Alternatives Considered

### Single Agent with Tool Calling (ReAct Pattern)
* **Why Evaluated:** A single massive agent configuration equipped with all API tools (web search, profile DB, vector DB, scoring service, application triggers).
* **Why Rejected:** As the feature backlog grew, the single prompt became bloated with dozens of tool schemas. The LLM frequently hallucinated tool parameters, chose the wrong tools, and suffered from high cognitive load (resulting in low reasoning accuracy). The API costs were unsustainable because the entire tool list was processed on every single interaction turn.

### Chained / Sequential Pipeline
* **Why Evaluated:** A static, linear pipeline where data flows sequentially: User Input -> Research Node -> Intelligence Node -> Execution Node -> End.
* **Why Rejected:** Too rigid. A sequential flow cannot adapt to different user intents. For instance, if a user simply asks: "What is my current positioning delta?" the system should not run search scrapers or trigger application submissions. Additionally, if the Intelligence Agent detects that research data is incomplete, a sequential pipeline cannot loop back to the Research Agent with a refined query to gather more details.

### Peer-to-Peer Collaborative Chat (Choreographed Topology)
* **Why Evaluated:** Flat topology where agents communicate directly (e.g., the Research Agent finishes and triggers the Intelligence Agent, which then triggers the Execution Agent).
* **Why Rejected:** Flat topologies are hard to manage and trace. Implementing a human approval gate requires inserting pause-and-resume logic inside every individual agent. State tracking becomes messy since any agent can modify any variable. The hub-and-spoke supervisor model isolates the state transitions and control flow into a single coordinator node, simplifying human gates and debugging.

## Consequences
* **Task Specialization:** Developers can write, prompt-engineer, and test individual spoke agents in isolation. Changes to the Research Agent's prompt do not affect the routing logic of the Supervisor or the scoring logic of the Intelligence Agent.
* **Granular Model Selection:** We can route tasks to different LLMs based on complexity. We can use a fast, cost-effective model (e.g., GPT-4o-mini or Claude 3.5 Haiku) for the Supervisor routing decisions and simple formatting, while using a powerful model (e.g., GPT-4o or Claude 3.5 Sonnet) for the Intelligence Agent's reasoning.
* **Traceable Reasoning:** The `agent_decision_logs` table provides complete step-by-step transparency into why a particular career analysis path was followed, fulfilling our "explainability first" doctrine requirement.
* **Routing Latency:** The hub-and-spoke model adds an extra LLM call for each supervisor transition, increasing overall request latency.

## Tradeoffs

### Modularity vs. Latency
Establishing a multi-agent hub-and-spoke hierarchy introduces extra network hops. For example, a complete analysis run might require: Supervisor -> Research -> Supervisor -> Intelligence -> Supervisor -> End, resulting in three supervisor planning calls and two spoke execution calls. This increases latency compared to a single-agent system. We accept this trade-off because the modular approach yields significantly higher routing accuracy, reduces parameter hallucinations, and provides the structured checkpoints needed to support human approval gates.

### Routing Dependency vs. System Flexibility
The system's success depends heavily on the routing capabilities of the Supervisor Agent. If the Supervisor misinterprets a state and enters an infinite loop or routes to the wrong agent, the execution fails. We mitigate this risk by:
1. Enforcing strict JSON validation on the Supervisor's routing schema.
2. Setting a hard cap on graph execution hops (e.g., maximum 8 transitions per run).
3. Implementing regression testing using our Evaluation Agent to catch routing failures during continuous integration.
