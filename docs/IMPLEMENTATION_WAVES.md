# CareerPilot Implementation Waves Roadmap

This document outlines the sequential implementation strategy for the CareerPilot platform. In accordance with the [Master Design Document](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/careerpilot_v2.md) and [Implementation Doctrine](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/IMPLEMENTATION_DOCTRINE.md), tasks are grouped into 10 independently completable and testable waves.

---

```
Wave Sequence Flow:
[Wave 1: Foundation] ➔ [Wave 2: Auth] ➔ [Wave 3: Profile] ➔ [Wave 4: Market Ingestion]
                                                                        │
                                                                        ▼
[Wave 8: Calibration] ◄─ [Wave 7: Execution] ◄─ [Wave 6: Agents] ◄─ [Wave 5: Score Engine]
        │
        ▼
[Wave 9: Hardening] ➔ [Wave 10: Post-MVP Scale]
```

---

## Wave 1: Project Foundation

### 1. Features Included

- **F1.1: Project Setup & Architecture** (Platform Context)

### 2. Tasks Included

- Initialize monorepo structure.
- Configure FastAPI application skeleton.
- Configure PostgreSQL connection layer (asyncpg + connection pool).
- Configure Alembic migrations.
- Configure Docker development environment.
- Configure environment variable management.
- Create base domain package structure.
- Create API versioning structure (`/api/v2`).
- Configure JSON logging framework.
- Create health check endpoints.

### 3. Estimated Effort

- **Effort:** 1.0 Engineer-Week
- **Rationale:** Baseline configuration of repo, CI configs, database adapters, and Docker.

### 4. Dependencies

- None.

### 5. Definition of Done

- FastAPI application runs in Docker container.
- `GET /api/v2/health` returns status `200 OK`.
- Alembic can execute a blank migration successfully.
- Linter and formatting checks pass.

---

## Wave 2: Authentication

### 1. Features Included

- **F1.2: Authentication & Identity Context** (Identity Context)

### 2. Tasks Included

- Create users table migration.
- Create authentication domain models.
- Implement email/password authentication (bcrypt).
- Implement JWT access token generation.
- Implement JWT refresh token flow (with database-tracked hashes).
- Create current user middleware.
- Create user preferences schema.
- Create career goals schema.
- Create auth API endpoints (`POST /auth/register`, `POST /auth/login`, `POST /auth/refresh`).
- Add authentication test suite.

### 3. Estimated Effort

- **Effort:** 1.0 Engineer-Week
- **Rationale:** Secure auth implementation, token validation middleware, and user db migration tables.

### 4. Dependencies

- Wave 1 (Project Foundation).

### 5. Definition of Done

- Authentication endpoints pass unit and integration test suites.
- Requests to protected routes with invalid/expired tokens return `401 Unauthorized`.
- Alembic user tables migrations are completed.

---

## Wave 3: Career Profile

### 1. Features Included

- **F1.3: Career Profile Domain**
- **F1.4: Resume Import & Profile Sync**

### 2. Tasks Included

- Design career profile database schema.
- Create profile versioning schema.
- Create skill, experience, education, and project schemas.
- Implement profile repository layer.
- Implement profile service layer.
- Create profile CRUD APIs.
- Add profile validation rules.
- Build resume upload endpoint.
- Implement PDF & DOCX resume extraction.
- Create resume text normalization pipeline.
- Create structured profile extraction prompts.
- Build skill, experience, and education extraction pipelines.
- Build profile confidence scoring.
- Implement profile sync workflow.

### 3. Estimated Effort

- **Effort:** 2.0 Engineer-Weeks
- **Rationale:** Domain repository mappings, PDF parsers, and LLM-based structured extraction pipeline.

### 4. Dependencies

- Wave 2 (Authentication).

### 5. Definition of Done

- User can upload a PDF resume via `POST /api/v2/profile/sync`.
- LLM correctly parses work history, extracting skills and generating structured JSON profile data.
- Unit tests check version backups and rollbacks.

---

## Wave 4: Job Market Data & Ingestion

### 1. Features Included

- **F1.5: Job Market Data Foundation**
- **F1.6: Skill Trend Engine V1**
- **F2.1: Multi-Source Job Ingestion**
- **F2.2: Advanced Deduplication**
- **F2.3: NLP Skill Extraction**
- **F2.6: Compensation Intelligence**

### 2. Tasks Included

- Create job posting schema, normalized skills schema, and company schema.
- Create job ingestion worker framework.
- Implement job posting, skill, and company normalization logic.
- Create job deduplication service.
- Create ingestion audit logs and market data admin APIs.
- Design skill trends schema and build daily trend aggregation job.
- Compute skill frequency and velocity metrics.
- Create trend materialized views and refresh worker.
- Implement trend API endpoints and caching.
- Integrate JSearch, Adzuna, and Greenhouse/Lever crawler services.
- Design deduplication scoring model (title, company, description).
- Build duplicate clustering and merge strategy engine.
- Build skill taxonomy and integrate spaCy pipeline.
- Build salary extraction pipeline, normalize compensation ranges, and build percentiles.

### 3. Estimated Effort

- **Effort:** 3.5 Engineer-Weeks
- **Rationale:** Multi-API integration schedules, Celery task broker, deduplication scoring engines, and NLP taxonomy models.

### 4. Dependencies

- Wave 1 (Project Foundation).

### 5. Definition of Done

- Celery workers run in background, scraping jobs daily.
- Deduplication drops duplicates, merging metadata records.
- Ingested postings resolve skill requirements against `normalized_skills` table.

---

## Wave 5: Intelligence Synthesis & Dashboard

### 1. Features Included

- **F1.7: Career Health Score Engine V1**
- **F1.8: Position Delta Engine**
- **F1.9: Career Dashboard**
- **F2.4: Company Intelligence**
- **F2.5: Ghost Posting Detection**
- **F2.7: Opportunity Intelligence**

### 2. Tasks Included

- Design health score schema and repository.
- Implement skill alignment, positioning, and activity health components.
- Implement score weighting engine and explanation generator.
- Create health score API.
- Create position delta schema and target role model.
- Implement profile vs. target comparison engine.
- Build missing skill detection and importance ranking.
- Generate evidence-backed recommendations and prioritize top-3 deltas.
- Create position delta API.
- Create dashboard API aggregator endpoint and widgets (health, delta, insights).
- Create dashboard frontend page mockups/skeleton states.
- Build company profile aggregation and hiring velocity metrics.
- Design ghost posting signal model (posting age vs. hiring velocity).
- Create opportunity scoring schema.
- Build profile-role matching engine (skills, experience, salary, attractiveness).

### 3. Estimated Effort

- **Effort:** 3.0 Engineer-Weeks
- **Rationale:** Algorithmic scoring engines, delta priorities, and dashboard aggregate API caching.

### 4. Dependencies

- Wave 3 (Career Profile), Wave 4 (Job Ingestion).

### 5. Definition of Done

- Dashboard endpoint (`GET /api/v2/dashboard`) returns aggregated health scores, position delta lists, and opportunity matches.
- Health scores explain driver metrics (e.g. why the score increased).

---

## Wave 6: Agent System

### 1. Features Included

- **F3.1: LangGraph Foundation**
- **F3.2: Supervisor Agent**
- **F3.3: Research Agent**
- **F3.4: Intelligence Agent**
- **F3.5: Interaction Memory**
- **F3.6: Hybrid Retrieval**
- **F3.7: Human-in-the-Loop Review**

### 2. Tasks Included

- Define `CareerPilotState` schema.
- Create state persistence layer (PostgreSQL-backed `PostgresSaver`).
- Configure LangGraph runtime and graph execution framework.
- Implement graph checkpoints, retry logics, and metrics.
- Define supervisor prompts, routing logic, and human approval gates.
- Create supervisor APIs and decision logs.
- Define company research workflow and role requirement extraction.
- Define intelligence workflow (health scores, deltas, opportunity ranks).
- Build explanation synthesis and evidence attribution.
- Design interaction memory schema and Qdrant semantic memory collection.
- Configure Qdrant cluster and build embedding generation pipeline.
- Implement vector retrieval + BM25 retrieval + Cross-Encoder reranker.
- Create approval request schema and review UI/APIs.

### 3. Estimated Effort

- **Effort:** 4.0 Engineer-Weeks
- **Rationale:** Complex state-machine configurations, multi-agent router pipelines, and dense embedding indexing.

### 4. Dependencies

- Wave 5 (Intelligence Synthesis).

### 5. Definition of Done

- LangGraph agents successfully execute user threads.
- Agent execution traces map directly to Langfuse dashboards.
- The human approval gate pauses execution and persists state.

---

## Wave 7: Execution Engine

### 1. Features Included

- **F4.1: Temporal Infrastructure**
- **F4.2: Application Workflow**
- **F4.3: ATS API Integrations**
- **F4.4: Deterministic Form Execution**
- **F4.5: Browser Fallback Execution**
- **F4.6: Outcome Memory System**

### 2. Tasks Included

- Deploy Temporal environment and configure worker processes.
- Create workflow project structure and metrics.
- Design application workflow state machine.
- Implement workflow checkpoints and recovery logic.
- Integrate Greenhouse, Lever, and Ashby API clients.
- Create Workday and iCIMS form schema engines and mapping systems.
- Configure Playwright framework.
- Create browser execution service and form detection engines.
- Create outcome memory schema and repository.
- Implement outcome recording API.

### 3. Estimated Effort

- **Effort:** 4.0 Engineer-Weeks
- **Rationale:** Setting up Temporal clusters, handling non-standard web forms, and writing robust Playwright visual fallbacks.

### 4. Dependencies

- Wave 1 (Project Foundation), Wave 6 (Agent System).

### 5. Definition of Done

- Temporal workflows execute Greenhouse, Lever, and Workday applications.
- Playwright falls back gracefully when API/form schemas fail, capturing visual screenshots.
- Outcome events are written to the database to update `outcome_memories`.

---

## Wave 8: Intelligence Calibration

### 1. Features Included

- **F5.1: Evaluation Framework**
- **F5.2: Evaluation Agent**
- **F5.3: Outcome Calibration**
- **F5.4: Peer Cohort Benchmarking**
- **F5.5: ML Platform**

### 2. Tasks Included

- Create eval dataset schema and eval results schema.
- Build eval execution framework and dashboards.
- Implement CI evaluation execution and regression detection.
- Define evaluation workflows and output scoring pipelines.
- Create training dataset builder and feature engineering pipeline.
- Train logistic regression calibration model (scikit-learn).
- Create peer cohort schema, group user profiles via K-Means, and aggregate percentiles.
- Deploy MLflow, configure experiment tracking, and model registries.

### 3. Estimated Effort

- **Effort:** 3.0 Engineer-Weeks
- **Rationale:** Setting up MLflow, modeling callback probabilities with logistic regression, and clustering cohorts.

### 4. Dependencies

- Wave 6 (Agent System), Wave 7 (Execution Engine).

### 5. Definition of Done

- Evaluations run in CI/CD pipeline, catching regressions.
- Calibration models are versioned and stored in MLflow.
- `GET /api/v2/market/opportunities` returns calibration probability percentiles.

---

## Wave 9: Production Hardening

### 1. Features Included

- **F6.1: Observability Platform**
- **F6.2: Metrics & Monitoring**
- **F6.3: Reliability Engineering**
- **F6.4: Load & Performance Testing**
- **F6.5: Architecture Documentation**

### 2. Tasks Included

- Configure OpenTelemetry tracing across FastAPI, Celery, and Temporal.
- Deploy Prometheus and Grafana.
- Create business and system monitoring dashboards.
- Define service SLOs and error budgets.
- Add circuit breakers and rate limiting.
- Configure Locust and run load tests.
- Write Architecture Decision Records (ADRs) and onboarding manuals.

### 3. Estimated Effort

- **Effort:** 2.0 Engineer-Weeks
- **Rationale:** Metrics setups, performance tuning, and documentation validation.

### 4. Dependencies

- Wave 8 (Intelligence Calibration).

### 5. Definition of Done

- Grafana monitors show live traces, error budgets, and database connection pool levels.
- System handles 10x baseline traffic under Locust load simulations.
- All ADRs and deployment manuals are compiled.

---

## Wave 10: Future Scale Features (Post-MVP)

### 1. Features Included

- **F7.1: Knowledge Graph**
- **F7.2: Gap-Aware Retrieval**
- **F7.3: Weekly Digest System**
- **F7.4: Career Strategy Reviews**

### 2. Tasks Included

- Deploy Neo4j database and design graph schemas (role/skill/company nodes).
- Build graph ingestion pipeline.
- Implement graph-based traversal algorithms.
- Create adjacent opportunity scoring.
- Build weekly digest generation workflow and email scheduler.
- Build monthly strategy review workflow (LangGraph + Temporal scheduler).

### 3. Estimated Effort

- **Effort:** 3.0 Engineer-Weeks
- **Rationale:** Configuring Neo4j clusters, graph-traversal queries, and digest email integrations.

### 4. Dependencies

- Wave 8 (Intelligence Calibration).

### 5. Definition of Done

- Skill delta calculations traversals execute via Neo4j.
- Weekly digests and monthly reviews execute on background schedules.
