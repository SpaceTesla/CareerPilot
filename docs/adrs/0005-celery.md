# ADR 0005: Celery for Lightweight Asynchronous Background Workers

## Status
Accepted

## Context
CareerPilot is a continuous career intelligence platform that processes vast amounts of unstructured data. As defined in the [Master Design Document (careerpilot_v2.md)](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/careerpilot_v2.md) and the [Implementation Doctrine (IMPLEMENTATION_DOCTRINE.md)](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/IMPLEMENTATION_DOCTRINE.md), the system operates on a continuous feedback loop where profile updates, market signals, and application outcomes compound over time.

This model introduces several resource-intensive, I/O-bound, and CPU-bound operations that cannot run synchronously within the FastAPI ASGI event loop. Doing so would block Uvicorn workers, degrade API response times, and reduce overall platform throughput. These operations include:
1. **Multi-Source Job Ingestion:** Extracting listings from third-party APIs (e.g., JSearch, Adzuna) and web-scraped targets.
2. **Deduplication and Normalization:** Running Natural Language Processing (NLP) models (e.g., spaCy) to extract skills, standardise job titles, and resolve duplicate postings.
3. **Embedding Generation:** Transforming raw text into vector embeddings and storing them in the Qdrant vector database.
4. **Peer Cohort Benchmarking:** Running statistical aggregates across thousands of user profiles to calculate compensation brackets and skill distributions.
5. **Notification and Digest Delivery:** Compiling personalized weekly digests and executing high-volume email/push notification pipelines.
6. **Resume Parsing and Profile Extraction:** Parsing incoming PDF/Word resumes to extract experience matrices, skills, and histories.

We require an asynchronous task execution system that is:
- **Low Latency:** Minimal overhead when scheduling and executing fire-and-forget tasks.
- **Python-Native:** Directly compatible with our ML, NLP, and vector database client packages.
- **Queue-Prioritized:** Able to route tasks to specialized worker instances based on resource needs (e.g., CPU-heavy normalization vs. network-bound ingestion).
- **Scalable:** Capable of horizontal scaling across separate containerized worker instances.

## Decision
We will use **Celery** (backed by **Redis** as a message broker) as our primary framework for lightweight, stateless, asynchronous background processing. 

### Implementation Strategy
Celery will be configured and deployed as follows:
* **Broker & Backend:** Redis will serve as the message broker (`redis://`) and task result backend. Task states will be stored in Redis with a strict 24-hour Time-to-Live (TTL) to prevent memory growth. Critical results (e.g., parsed resume JSON) will be written directly to PostgreSQL instead of Celery's result backend.
* **Separation of Queues:** Workers will poll from dedicated queues to isolate resource constraints:
  - `ingestion-queue`: Reserved for network-bound job scrapers and API integrations.
  - `nlp-queue`: Dedicated to CPU-bound tasks such as normalization, skill extraction, and embedding generation (run on GPU/high-CPU nodes).
  - `notifications-queue`: Used for transactional emails, SMS, and dashboard notification fan-out.
  - `default-queue`: For general, short-lived tasks.
* **Serialization:** We will enforce `json` as the default serialization format (`CELERY_TASK_SERIALIZER = "json"`) for safety, explicitly disabling `pickle` to prevent arbitrary code execution vulnerabilities.
* **Task Idempotency:** All tasks will be designed to be idempotent. In the event of a worker crash or message redelivery, rerunning a task (e.g., inserting a duplicate job listing) will not corrupt database state.
* **Monitoring & Observability:** We will deploy Flower in our staging and production environments to monitor queue lengths, worker health, and task execution logs. Worker metrics will be exported via Prometheus integration.

## Alternatives Considered

### RQ (Redis Queue)
* **Why Evaluated:** RQ is a lightweight Python-based background queue backed by Redis, offering a simpler API and lower setup friction than Celery.
* **Why Rejected:** RQ is single-threaded per worker process and lacks native support for complex scheduling patterns like chords, chains, and task groups. Furthermore, RQ does not support alternative brokers (such as RabbitMQ, should we migrate in the future) and does not offer built-in rate-limiting at the worker configuration level, which is necessary to stay within third-party API rate limits.

### Temporal (for ALL asynchronous tasks)
* **Why Evaluated:** Since Temporal is selected for long-running durable workflows, we could theoretically execute all background tasks as Temporal activities or workflows.
* **Why Rejected:** Temporal is a heavyweight orchestration engine designed for durable state, workflow history persistence, and human-in-the-loop coordination. Using Temporal for rapid, high-frequency, stateless tasks (like generating an embedding vector or sending a single email notification) introduces unnecessary latency, database write-amplification, and networking overhead. Using Celery for stateless, sub-second tasks keeps execution fast and cost-effective.

### FastAPI Native BackgroundTasks
* **Why Evaluated:** FastAPI provides a native `BackgroundTasks` class that executes functions in the background after returning an HTTP response.
* **Why Rejected:** FastAPI's `BackgroundTasks` run within the same ASGI process. For CPU-bound operations like NLP normalization, embedding generation, or mass JSON calculations, this blocks the single-threaded Python event loop and ruins API concurrency. Additionally, native background tasks have no persistence mechanism; if the FastAPI container crashes, all queued tasks are lost forever.

## Consequences
* **Decoupled API Execution:** FastAPI can instantly offload processing workloads, returning `202 Accepted` to the client and keeping web UI interaction smooth.
* **Resource Optimization:** We can scale high-memory workers (e.g., NLP/embedding nodes utilizing GPU hardware) independently of lightweight API containers.
* **Operational Dependency:** Introducing Celery requires maintaining Redis as a message broker. Redis persistence policies must be carefully tuned (RDB/AOF configuration) to avoid message loss during restarts.
* **Shared Code Dependency:** Since Celery workers must import task definitions, workers and API nodes must share access to the core repository or work from a unified Docker image containing the entire codebase.

## Tradeoffs

### Operational Complexity vs. Horizontal Scalability
Deploying Celery introduces additional microservices (Redis broker, Celery worker nodes, Celery Beat scheduler, and Flower monitoring) to the infrastructure setup in [Dependency Graph (DEPENDENCY_GRAPH.md)](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/DEPENDENCY_GRAPH.md). This increases Docker Compose and Kubernetes configuration complexity. We trade this operational overhead for the ability to handle massive, concurrent background workloads without degrading the user experience.

### Architectural Split (Celery vs. Temporal)
By using both Celery and Temporal, we introduce a dual-async architecture. Developers must decide when a background task belongs in Celery vs. Temporal:
- **Rule of Thumb:** Celery is chosen for stateless, short-lived (< 5 minutes), single-step, fire-and-forget tasks (e.g., PDF parsing, embedding generation, push notifications). Temporal is chosen for stateful, long-running, multi-step, human-in-the-loop processes (e.g., job application tracking, multi-day user onboarding, weekly schedule executions). While this split increases the developer learning curve, it optimizes system performance and operational costs.
