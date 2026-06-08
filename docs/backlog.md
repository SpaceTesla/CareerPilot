# Epic 1: Intelligence Foundation (Phase 1)

## Feature: Project Setup & Architecture

### Task

- Initialize monorepo structure
- Configure FastAPI application skeleton
- Configure PostgreSQL connection layer
- Configure Alembic migrations
- Configure Docker development environment
- Configure environment variable management
- Create base domain package structure
- Create API versioning structure (`/api/v2`)
- Configure logging framework
- Create health check endpoints

---

## Feature: Authentication & Identity Context

### Task

- Create users table migration
- Create authentication domain models
- Implement email/password authentication
- Implement JWT access token generation
- Implement JWT refresh token flow
- Create current user middleware
- Create user preferences schema
- Create career goals schema
- Create auth API endpoints
- Add authentication test suite

---

## Feature: Career Profile Domain

### Task

- Design career profile database schema
- Create profile versioning schema
- Create skill entity schema
- Create experience entity schema
- Create education entity schema
- Create project entity schema
- Implement profile repository layer
- Implement profile service layer
- Create profile CRUD APIs
- Add profile validation rules

---

## Feature: Resume Import & Profile Sync

### Task

- Build resume upload endpoint
- Implement PDF resume extraction
- Implement DOCX resume extraction
- Create resume text normalization pipeline
- Create structured profile extraction prompts
- Build skill extraction pipeline
- Build experience extraction pipeline
- Build education extraction pipeline
- Build profile confidence scoring
- Implement profile sync workflow

---

## Feature: Job Market Data Foundation

### Task

- Create job posting schema
- Create normalized skills schema
- Create company schema
- Create job ingestion worker framework
- Implement job posting normalization
- Implement skill normalization logic
- Implement company normalization logic
- Create job deduplication service
- Create ingestion audit logs
- Create market data admin APIs

---

## Feature: Skill Trend Engine V1

### Task

- Design skill trends schema
- Build daily trend aggregation job
- Compute skill frequency metrics
- Compute trend velocity metrics
- Create trend materialized views
- Create trend refresh worker
- Implement trend API endpoint
- Add trend caching layer
- Create trend unit tests
- Create trend integration tests

---

## Feature: Career Health Score Engine V1

### Task

- Design health score schema
- Create health score repository
- Implement skill alignment component
- Implement market positioning component
- Implement activity health component
- Implement compensation alignment component
- Implement profile completeness component
- Implement score weighting engine
- Implement score explanation generator
- Create health score API

---

## Feature: Position Delta Engine

### Task

- Create position delta schema
- Design target role model
- Implement profile vs target comparison engine
- Build missing skill detection
- Build skill importance ranking
- Generate evidence-backed recommendations
- Implement top-3 delta prioritization
- Create position delta API
- Add explanation generation
- Add position delta tests

---

## Feature: Career Dashboard

### Task

- Create dashboard API aggregator
- Build health score widget
- Build score change widget
- Build market insight widget
- Build position delta widget
- Build opportunity spotlight widget
- Implement dashboard caching
- Create dashboard frontend page
- Create loading/error states
- Add dashboard analytics

---

# Epic 2: Market Intelligence Depth (Phase 2)

## Feature: Multi-Source Job Ingestion

### Task

- Integrate JSearch ingestion
- Integrate Adzuna ingestion
- Build Greenhouse board crawler
- Build Lever board crawler
- Create ingestion scheduler
- Implement source health monitoring
- Add ingestion retry policies
- Build ingestion observability
- Create ingestion dashboard
- Add source comparison reports

---

## Feature: Advanced Deduplication

### Task

- Design deduplication scoring model
- Implement title similarity scoring
- Implement company similarity scoring
- Implement description similarity scoring
- Build duplicate clustering
- Create merge strategy engine
- Build dedupe review tooling
- Create dedupe metrics
- Add dedupe evaluation tests
- Create dedupe audit logs

---

## Feature: NLP Skill Extraction

### Task

- Build skill taxonomy
- Integrate spaCy pipeline
- Create skill extraction prompts
- Build skill confidence scoring
- Create skill alias resolution
- Implement technology normalization
- Create extraction evaluation dataset
- Build extraction benchmarking
- Add extraction metrics
- Create extraction admin tools

---

## Feature: Company Intelligence

### Task

- Create company intelligence schema
- Build company profile aggregation
- Implement hiring velocity calculations
- Implement hiring trend calculations
- Build company scoring engine
- Create company intelligence APIs
- Create company watchlist support
- Build company report generator
- Add company caching
- Add company intelligence tests

---

## Feature: Ghost Posting Detection

### Task

- Design ghost posting signal model
- Build posting age analysis
- Build hiring velocity correlation analysis
- Implement ghost score computation
- Create ghost posting database schema
- Create ghost posting APIs
- Add ghost posting dashboard
- Create ghost score explanations
- Add evaluation datasets
- Add monitoring metrics

---

## Feature: Compensation Intelligence

### Task

- Create compensation schema
- Build salary extraction pipeline
- Normalize compensation ranges
- Create compensation aggregation jobs
- Build benchmark calculator
- Implement percentile calculations
- Create compensation APIs
- Add location normalization
- Build compensation caching
- Add benchmark tests

---

## Feature: Opportunity Intelligence

### Task

- Create opportunity scoring schema
- Build profile-role matching engine
- Implement skill fit scoring
- Implement experience fit scoring
- Implement compensation fit scoring
- Implement company attractiveness scoring
- Create ranking pipeline
- Create opportunity API
- Add ranking explanations
- Add ranking tests

---

# Epic 3: Agent System (Phase 3)

## Feature: LangGraph Foundation

### Task

- Define CareerPilotState schema
- Create state persistence layer
- Configure LangGraph runtime
- Build graph execution framework
- Implement graph checkpoints
- Create graph observability
- Build graph testing harness
- Create graph evaluation fixtures
- Add graph retry logic
- Add graph metrics

---

## Feature: Supervisor Agent

### Task

- Define supervisor prompts
- Implement routing logic
- Build agent orchestration layer
- Implement human approval gates
- Build decision logging
- Create supervisor APIs
- Add supervisor evaluations
- Add failure recovery logic
- Build routing analytics
- Add supervisor tests

---

## Feature: Research Agent

### Task

- Define company research workflow
- Build role requirement extraction
- Build market signal synthesis
- Create structured research outputs
- Implement source attribution
- Create research memory storage
- Build research APIs
- Add evaluation datasets
- Add research scoring
- Add research tests

---

## Feature: Intelligence Agent

### Task

- Define intelligence workflow
- Integrate health score computation
- Integrate position delta generation
- Integrate opportunity scoring
- Integrate compensation benchmarking
- Build explanation synthesis
- Implement evidence attribution
- Create intelligence APIs
- Add intelligence evaluation suite
- Add intelligence tests

---

## Feature: Interaction Memory

### Task

- Design interaction memory schema
- Create memory repository
- Implement memory retrieval
- Implement memory storage
- Build memory summarization
- Create memory APIs
- Add memory expiration policies
- Build memory analytics
- Add memory tests
- Add memory observability

---

## Feature: Hybrid Retrieval

### Task

- Configure Qdrant cluster
- Build embedding generation pipeline
- Implement vector retrieval
- Implement BM25 retrieval
- Build retrieval fusion layer
- Implement reranking pipeline
- Create retrieval APIs
- Build retrieval evaluations
- Add retrieval metrics
- Add retrieval tests

---

## Feature: Human-in-the-Loop Review

### Task

- Create approval request schema
- Build approval workflow
- Create review UI
- Build edit-and-resubmit flow
- Create approval audit logs
- Add approval notifications
- Build approval APIs
- Add approval metrics
- Add approval tests
- Add workflow analytics

---

# Epic 4: Execution Engine (Phase 4)

## Feature: Temporal Infrastructure

### Task

- Deploy Temporal environment
- Configure worker processes
- Create workflow project structure
- Build workflow monitoring
- Create workflow metrics
- Implement workflow retries
- Build workflow dashboards
- Create workflow tests
- Add workflow alerts
- Document workflow patterns

---

## Feature: Application Workflow

### Task

- Design application workflow state machine
- Create application workflow schema
- Implement workflow checkpoints
- Build workflow recovery logic
- Create workflow audit logs
- Add workflow notifications
- Build workflow APIs
- Add workflow metrics
- Add workflow tests
- Create workflow documentation

---

## Feature: ATS API Integrations

### Task

- Integrate Greenhouse API
- Integrate Lever API
- Integrate Ashby API
- Build ATS abstraction layer
- Create ATS authentication handling
- Implement ATS error handling
- Create ATS audit logging
- Add ATS metrics
- Add ATS integration tests
- Create ATS documentation

---

## Feature: Deterministic Form Execution

### Task

- Create Workday schema engine
- Create iCIMS schema engine
- Build form mapping system
- Create field normalization layer
- Build validation engine
- Implement submission engine
- Add error recovery
- Add execution logging
- Add execution tests
- Create schema management tools

---

## Feature: Browser Fallback Execution

### Task

- Configure Playwright framework
- Create browser execution service
- Build form detection engine
- Build field filling engine
- Implement screenshot capture
- Add browser retries
- Add browser audit logs
- Add browser metrics
- Add browser tests
- Create fallback escalation logic

---

## Feature: Outcome Memory System

### Task

- Create outcome memory schema
- Build outcome repository
- Implement outcome recording API
- Build outcome validation logic
- Implement prediction error tracking
- Create follow-up scheduling logic
- Build outcome analytics
- Add outcome tests
- Add outcome observability
- Create outcome dashboards

---

# Epic 5: Intelligence Calibration (Phase 5)

## Feature: Evaluation Framework

### Task

- Create eval dataset schema
- Create eval results schema
- Build eval execution framework
- Create eval reporting APIs
- Build eval dashboards
- Implement CI evaluation execution
- Add regression detection
- Add eval alerts
- Create evaluation documentation
- Add evaluation tests

---

## Feature: Evaluation Agent

### Task

- Define evaluation workflows
- Build output scoring pipeline
- Implement regression detection logic
- Build evaluation reports
- Create evaluation APIs
- Add evaluation observability
- Create evaluation dashboards
- Add evaluation metrics
- Add evaluation tests
- Create evaluation documentation

---

## Feature: Outcome Calibration

### Task

- Create training dataset builder
- Build feature engineering pipeline
- Train logistic regression baseline
- Implement calibration inference service
- Build calibration evaluation metrics
- Create model versioning support
- Add prediction monitoring
- Create calibration APIs
- Add calibration tests
- Build calibration dashboards

---

## Feature: Peer Cohort Benchmarking

### Task

- Create peer cohort schema
- Build profile clustering pipeline
- Create cohort assignment logic
- Implement benchmark aggregation
- Build percentile computation
- Create cohort APIs
- Build cohort dashboards
- Add cohort analytics
- Add cohort tests
- Add cohort observability

---

## Feature: ML Platform

### Task

- Deploy MLflow
- Configure experiment tracking
- Build model registry integration
- Create model promotion workflow
- Add model metrics collection
- Build model comparison reports
- Create model rollback support
- Add MLflow monitoring
- Create MLflow documentation
- Add ML platform tests

---

# Epic 6: Production Hardening (Phase 6)

## Feature: Observability Platform

### Task

- Configure OpenTelemetry tracing
- Instrument FastAPI services
- Instrument Celery workers
- Instrument Temporal workflows
- Instrument agent execution
- Create trace dashboards
- Add distributed tracing tests
- Create observability documentation
- Add alerting rules
- Add observability health checks

---

## Feature: Metrics & Monitoring

### Task

- Deploy Prometheus
- Deploy Grafana
- Create business metric dashboards
- Create system metric dashboards
- Add interview conversion metrics
- Add execution success metrics
- Add health score trend metrics
- Create alert policies
- Add monitoring tests
- Document monitoring strategy

---

## Feature: Reliability Engineering

### Task

- Define service SLOs
- Create error budgets
- Build incident runbooks
- Add circuit breakers
- Add rate limiting
- Add graceful degradation paths
- Build chaos test scenarios
- Add reliability dashboards
- Add reliability tests
- Document reliability architecture

---

## Feature: Load & Performance Testing

### Task

- Configure Locust framework
- Create authentication load tests
- Create profile API load tests
- Create intelligence API load tests
- Create retrieval load tests
- Create workflow load tests
- Create dashboard load tests
- Build performance reports
- Add performance regression tests
- Document performance baselines

---

## Feature: Architecture Documentation

### Task

- Create system architecture diagrams
- Create domain architecture diagrams
- Create workflow diagrams
- Create agent architecture diagrams
- Create deployment diagrams
- Write ADRs for core decisions
- Write onboarding guide
- Write operations guide
- Write API documentation
- Create portfolio showcase documentation

---

# Epic 7: Future Scale Features (Post-MVP)

## Feature: Knowledge Graph

### Task

- Deploy Neo4j
- Design graph schema
- Create role nodes
- Create skill nodes
- Create company nodes
- Create career transition edges
- Build graph ingestion pipeline
- Create graph APIs
- Build graph analytics
- Add graph tests

---

## Feature: Gap-Aware Retrieval

### Task

- Design adjacent opportunity model
- Build cluster adjacency engine
- Implement graph-based traversal
- Create adjacent opportunity scoring
- Build recommendation explanations
- Create retrieval APIs
- Add retrieval evaluations
- Add retrieval analytics
- Add retrieval tests
- Add retrieval monitoring

---

## Feature: Weekly Digest System

### Task

- Create digest schema
- Build digest generation workflow
- Generate market insights section
- Generate health score section
- Generate position delta section
- Create digest delivery service
- Add digest preferences
- Add digest analytics
- Add digest tests
- Add digest monitoring

---

## Feature: Career Strategy Reviews

### Task

- Create strategy review schema
- Build monthly review workflow
- Generate strategic recommendations
- Build strategy history tracking
- Create review APIs
- Add review dashboards
- Add review analytics
- Add review notifications
- Add review tests
- Add review observability
