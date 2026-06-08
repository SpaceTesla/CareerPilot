# ADR 0007: LangGraph as the Core Multi-Agent Orchestration Framework

## Status
Accepted

## Context
CareerPilot relies on a multi-agent system to process profile data, perform market intelligence scans, and execute job applications. As specified in the [Implementation Doctrine (IMPLEMENTATION_DOCTRINE.md)](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/IMPLEMENTATION_DOCTRINE.md) and the [Master Design Document (careerpilot_v2.md)](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/careerpilot_v2.md), we must avoid prompt-only systems and unstructured conversational loops. The system requires that agents:
1. **Operate on Typed State:** Agents must read and modify a structured, typed schema (`CareerPilotState`) to ensure data consistency, static contract enforcement, and reliable transitions.
2. **Produce Structured Outputs:** LLM outputs must be parsed into defined schema structures (Pydantic models) rather than free-form text.
3. **Support State Checkpoint Persistence:** The state of an agent execution thread must be saved at every transition step, allowing the graph to pause for Human-in-the-Loop review gates and resume after approval.
4. **Provide Full Observability:** Every LLM prompt, token expenditure, and node routing decision must be traceable for latency optimization, prompt tuning, and regression detection.

Popular multi-agent frameworks often treat agent collaboration as open-ended, natural language conversation loops. This makes it extremely difficult to enforce deterministic state schemas, prevent infinite execution loops, or implement robust database checkpointing. We need a framework that treats agents as structured state machines, where nodes represent execution steps or agent tasks, and edges define state routing.

## Decision
We will use **LangGraph** as our core multi-agent state orchestration framework. LangGraph provides a cyclical graph execution model that allows us to construct structured agent systems as state machines.

### Implementation Strategy
* **State Definition:** The graph state will be represented by a typed Pydantic class `CareerPilotState`, defined in the [LangGraph Foundation Spec (langgraph-foundation.md)](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/feature-specs/langgraph-foundation.md). This schema serves as the single source of truth for the entire run, containing fields like `user_profile`, `retrieved_jobs`, `research_signals`, `intelligence_report`, and `audit_trail`.
* **State Graph Configuration:** We will define our agents as nodes in a LangGraph `StateGraph`. The graph topology will include:
  - Specialized agent nodes (Supervisor, Research, Intelligence, Execution).
  - Conditional routing edges controlled by the Supervisor Agent.
  - System boundary nodes for database queries, vector retrieval, and human approval gates.
* **Database Checkpointing (PostgresSaver):** We will configure LangGraph's database checkpoint manager (`PostgresSaver`) to persist the execution state of every thread into our local PostgreSQL database (within tables `agent_sessions` and `agent_checkpoints`). This ensures that if a workflow is paused for user review, or if a backend node crashes, the agent thread can resume from the exact same node and state.
* **Observability Integration:** We will integrate LangGraph with **Langfuse** (utilizing OpenTelemetry) to capture step-by-step traces, prompt variants, latency, and LLM token usage. This allows us to debug routing decisions and run evaluation tests on agent performance.
* **Type-Safe Routing:** All routing decisions made by agent nodes must return structured models matching Pydantic schemas (e.g., `RoutingDecision`), which are validated at runtime.

## Alternatives Considered

### CrewAI
* **Why Evaluated:** CrewAI is a popular, high-level framework for defining hierarchical and sequential agent teams.
* **Why Rejected:** CrewAI is highly opinionated and abstracts away the underlying execution flow. It is built on the concept of agents communicating through natural language prompts, making it difficult to enforce a strict, typed state schema (`CareerPilotState`) at the code level. This abstraction limits our ability to control precise execution paths, handle low-level error recoveries, or implement custom database-backed checkpoint savers.

### AutoGen
* **Why Evaluated:** AutoGen is Microsoft's framework for multi-agent conversation, enabling complex problem solving through interactive agent chats.
* **Why Rejected:** AutoGen is designed around unstructured chat-based loops. Managing state transitions, enforcing schemas, and implementing durable state persistence requires overriding the framework's internal message-handling classes. It lacks a clean, declarative state-machine abstraction (like LangGraph's `StateGraph`), which is necessary for CareerPilot's deterministic and explainable routing requirements.

### Custom Python State Machine (Vanilla Code)
* **Why Evaluated:** Writing a custom control loop in Python that executes a series of agent classes and manages state in local dictionaries.
* **Why Rejected:** While writing vanilla Python gives us full control, we would have to build our own implementation of thread checkpoint persistence, fork/join graph processing, retry middleware, and tracing integrations. Using LangGraph provides these production-ready components out of the box, saving significant development time while still giving us low-level control over the state machine.

## Consequences
* **Deterministic Execution:** The graph structure ensures that agent routing is bounded and predictable, eliminating the risk of unstructured agents going off-topic or looping indefinitely.
* **Durable Sessions:** User interactions with agents can span days (e.g., waiting for resume reviews). The database-backed checkpointing makes it simple to resume these threads.
* **Observability by Default:** Developers can visually trace every step of an agent run in the Langfuse dashboard, simplifying debugging and prompt optimization.
* **Development Overhead:** Adding new agents or modifying the routing behavior requires compiling the `StateGraph` and updating state transitions, which is more structured and verbose than free-form agent scripts.

## Tradeoffs

### Predictable Routing vs. Agent Autonomy
By choosing LangGraph, we trade agent autonomy (the ability of LLMs to dynamically formulate their own tools and execution loops on the fly) for predictable, state-machine-controlled execution. For CareerPilot, predictability and explainability are paramount. We must be able to guarantee that the agent system always calls the Research Agent before the Intelligence Agent, and always pauses at the Human Approval Gate before submission. LangGraph's structured graph routing aligns perfectly with these safety constraints.

### Ecosystem Lock-in vs. Engineering Velocity
Centering our agent architecture around LangGraph couples us to the LangChain ecosystem. We accept this dependency because LangGraph solves the hard engineering problems of state management, checkpointing, and thread control. To protect the codebase from future library changes, we will decouple the core agent business logic (such as scraping APIs, database queries, and raw LLM wrappers) into separate services and tools, using LangGraph nodes strictly for orchestration and routing.
