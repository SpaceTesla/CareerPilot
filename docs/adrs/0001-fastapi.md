# ADR 0001: FastAPI as Core Web Application API Framework

## Status
Accepted

## Context
CareerPilot is designed as a continuous career intelligence platform. As detailed in the [Master Design Document (careerpilot_v2.md)](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/careerpilot_v2.md), the system operates on a data compounding loop requiring high-performance network communication, real-time background processing, and integration with complex AI orchestrators.

The technical constraints and product objectives for the web API layer are:
1. **Python Ecosystem Dominance:** The backend requires direct integration with Python-based AI, machine learning, and natural language processing libraries, specifically LangGraph for multi-agent workflows, spaCy for entity extraction, scikit-learn for outcome calibration, and MLflow for experiment tracking. Therefore, the web framework must be Python-based.
2. **Asynchronous I/O Performance:** The core application frequently performs I/O-bound operations, including querying PostgreSQL, reading/writing vector embeddings in Qdrant, interacting with Redis caching and rate-limiting instances, coordinating background tasks via Celery, and calling external large language model (LLM) APIs (OpenAI, Anthropic). A framework with first-class `async/await` support is essential to prevent event loop blocking and optimize throughput.
3. **Data Validation and Type Safety:** The multi-agent architecture operates on typed states (e.g., `CareerPilotState`) and requires structured inputs/outputs. Standardizing data parsing and validation at the HTTP boundary prevents malformed payloads from polluting downstream agent pipelines.
4. **Developer Velocity:** As an early-stage project (outlined in the [Dependency Graph (DEPENDENCY_GRAPH.md)](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/DEPENDENCY_GRAPH.md)), rapid iteration on the API contracts, interactive testing, and automated API documentation (OpenAPI/Swagger) are critical to maintaining engineering speed.

## Decision
We will use **FastAPI** as the core web application API framework. It will serve as the gateway and routing layer for all services, exposing the RESTful interface under the `/api/v2/*` namespace as specified in the [Master Design Document](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/careerpilot_v2.md) and [Backlog](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/backlog.md).

FastAPI will be utilized in the following capacity:
* **Asynchronous Routing:** All API routes interacting with external networks or datastores (PostgreSQL, Qdrant, Redis, LLM endpoints) will be defined using `async def` and execute on the native Python event loop.
* **Pydantic V2 for Validation:** Pydantic models will act as the single source of truth for request payload validation, query parameter parsing, and response serialization. All domain-specific entity DTOS (Data Transfer Objects) will inherit from Pydantic's `BaseModel`.
* **Dependency Injection (DI) System:** FastAPI’s built-in dependency injection system will manage component lifecycles, such as database sessions (SQLAlchemy `AsyncSession`), HTTP clients (`httpx.AsyncClient`), caching instances, and authenticated user contexts (JWT payload decoding and user retrieval).
* **OpenAPI Auto-Generation:** Interactive Swagger and ReDoc documentation will be auto-generated at `/docs` and `/redoc` in the development environment to facilitate rapid frontend integration.

## Alternatives Considered

### Django / Django REST Framework (DRF)
* **Why Evaluated:** Django is a highly mature, "batteries-included" Python framework featuring a robust Object-Relational Mapper (ORM), built-in admin panel, and session management.
* **Why Rejected:** Django is historically synchronous. While asynchronous views and ORM calls have been introduced in recent versions, async is not native to its core architecture. Running async operations, such as concurrent LLM calls or multi-agent routing within views, requires wrapping sync functions, which introduces overhead and complexity. Furthermore, DRF relies on serializers that are significantly slower and less modern than Pydantic V2.

### Flask
* **Why Evaluated:** Flask is a micro-framework that offers maximum flexibility and a minimal footprint, ideal for small microservices.
* **Why Rejected:** Flask is inherently synchronous and lacks built-in data validation and auto-documentation. Implementing input/output validation requires third-party dependencies (like Marshmallow or Webargs) and manual boilerplate. Offloading Flask I/O-bound operations requires complex WSGI configurations (like Gevent or uWSGI thread pooling), which do not match the simplicity and performance of native ASGI.

### Node.js (NestJS / Express) or Go (Gin / Fiber)
* **Why Evaluated:** Node.js and Go offer exceptional performance, lightweight runtimes, and native concurrency models (event loop / goroutines).
* **Why Rejected:** Adopting Node.js or Go as the primary API layer would result in a split-language stack: Go/Node.js for the API and Python for the AI/agent workloads. This division increases operational complexity, demands maintaining duplicate model definitions (e.g., Go structs vs. Python Pydantic models), and adds serialization/gRPC overhead between the API and the agent workers. Keeping the entire codebase in Python preserves unified domain models, decreases latency, and maximizes developer velocity.

## Consequences
* **High-Throughput ASGI Runtimes:** The application runs on Uvicorn or Hypercorn, taking full advantage of async database drivers and non-blocking I/O.
* **Consistent Data Contracts:** Pydantic schemas enforce type safety from the API boundary down to the service layer.
* **Self-Documenting Codebase:** Changes to Pydantic models and API signatures are automatically reflected in Swagger docs, preventing documentation drift.
* **Lack of Strict Project Layout:** FastAPI does not dictate a project structure. To prevent directory sprawl and architectural drift, we must strictly enforce the bounded context layout defined in the [Implementation Doctrine (IMPLEMENTATION_DOCTRINE.md)](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/IMPLEMENTATION_DOCTRINE.md).
* **Async Library Requirements:** Any library utilized within the main request-response cycle must support async execution. Using blocking synchronous libraries (e.g., standard `requests` instead of `httpx`, or sync DB connections) will block the ASGI loop and severely degrade performance.

## Tradeoffs

### Flexiblity vs. Structural Discipline
By choosing a micro-framework like FastAPI over a structured framework like Django, we trade rigid built-in architecture for total flexibility. The risk of codebase erosion is high. We mitigate this trade-off by establishing explicit domain ownership boundaries (Identity, Career Profile, Market Intelligence, Intelligence Synthesis, Execution, Strategy) and enforcing code styling/linting rules at the CI level.

### Concurrency Performance vs. Async Code Complexity
FastAPI’s async capabilities allow the API to handle thousands of concurrent requests with low memory footprints. However, writing asynchronous Python code is more complex and error-prone than synchronous code (e.g., managing async generator cleanups, database session leaks, and handling CPU-bound tasks). We accept this operational overhead because of the massive volume of concurrent network requests required by external LLM calling, Web scraping, and worker dispatching. Any CPU-bound task (e.g., NLP extraction, pdf parsing, ML scoring) must be explicitly offloaded to Celery background tasks or thread pools to prevent event loop starvation.
