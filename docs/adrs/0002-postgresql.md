# ADR 0002: PostgreSQL as Primary Relational Database

## Status
Accepted

## Context
CareerPilot’s architecture hinges on a relational data model that connects users, profiles, market data, and historical outcomes. As specified in the [Master Design Document (careerpilot_v2.md)](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/careerpilot_v2.md) and the [Implementation Doctrine (IMPLEMENTATION_DOCTRINE.md)](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/IMPLEMENTATION_DOCTRINE.md), the system of record must store:
* **User Identity and Preferences:** Authentication data, credentials, and settings.
* **Career Profiles:** Deeply structured user information including experience timelines, normalized skills, education history, and projects. Profiles must support versioning (`profile_versions`) to track user progression.
* **Job Market Data:** Ingested job postings, company directories, historical compensation bounds, and skill categories.
* **Execution & Outcome Memory:** The central database for tracking application workflows, audit logs, and outcomes (interviews, offers, rejections) which form the foundation of the platform's data moat.
* **Agent Execution Logs:** Auditable decision-making traces from the LangGraph supervisor and execution agents.

To support these structures, the datastore must satisfy the following technical requirements:
1. **Strict Relational Integrity:** Deep connections exist between profiles, jobs, companies, applications, and outcomes. Foreign key constraints, cascade rules, and check constraints are required to prevent data corruption.
2. **ACID Transactions:** When a user updates their profile or syncs a new resume, multiple tables (skills, experiences, education) must update atomically. Partial saves or orphaned records are unacceptable.
3. **Semi-Structured Data Support:** Job boards use disparate structures, and Application Tracking Systems (ATS) expose varied form schemas (e.g., Workday custom fields). The database must handle both highly structured fields (e.g., UUIDs, timestamps, decimals) and variable JSON data without requiring frequent schema migrations.
4. **Keyword-Based Text Search:** The hybrid retrieval pipeline (specified in [IMPLEMENTATION_DOCTRINE.md](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/IMPLEMENTATION_DOCTRINE.md)) requires high-performance BM25-equivalent keyword matching on job postings and profiles to combine with vector search.

## Decision
We will use **PostgreSQL** as the primary system of record relational database. 

PostgreSQL will be utilized in the following capacity:
* **Relational Schema Design:** Implemented with strict foreign keys, unique constraints, and indices on query lookups (e.g., `user_id`, `company_id`, `job_posting_id`).
* **JSONB for Semi-Structured Columns:** Custom ATS form schemas, raw API responses from ingestion sources, and agent execution trace payloads will be stored in `JSONB` columns, enabling indexable, queryable, and schema-less flexibility where needed.
* **Full-Text Search (FTS):** We will leverage Postgres’s native `tsvector` and `tsquery` engine alongside GIN (Generalized Inverted Index) indices to provide the keyword search layer (BM25) for our hybrid retrieval stack.
* **Materialized Views:** For time-intensive analytical aggregations, such as the Daily Skill Trend velocity scores (F1.6) and company hiring velocity stats, we will use Materialized Views refreshed asynchronously via Celery background workers.
* **Alembic Migrations:** Database migrations will be version-controlled using Alembic, ensuring that all changes to models are trackable and deployable across development, testing, and production environments.

## Alternatives Considered

### MongoDB (NoSQL)
* **Why Evaluated:** MongoDB is a document-oriented database offering dynamic schemas, which easily matches the varying structures of resumes and job postings.
* **Why Rejected:** MongoDB does not natively enforce the relational constraints required by CareerPilot. Representing deep connections (e.g., linking a specific user experience to a normalized skill, which is linked to a job posting, which is linked to an application outcome) requires application-level joins, leading to complex and slow queries. Furthermore, transactions spanning multiple documents, while supported, are less performant and harder to manage than in a SQL native.

### MySQL
* **Why Evaluated:** MySQL is a mature, high-performance relational database with excellent write speeds and a vast ecosystem.
* **Why Rejected:** PostgreSQL offers superior support for JSONB operations (including containment and existence operators, and GIN indexing on JSON keys), which are critical for parsing custom ATS forms. Additionally, PostgreSQL's Full-Text Search capabilities are more advanced than MySQL’s, and Postgres provides superior support for window functions, Common Table Expressions (CTEs), and advanced data types (like UUIDs and arrays) which are frequently used throughout our profile and trend engines.

### SQLite
* **Why Evaluated:** SQLite is a self-contained, serverless database requiring zero configuration, ideal for testing and simple local deployments.
* **Why Rejected:** SQLite is unsuitable for a production environment featuring concurrent web servers, Celery workers, and Temporal activity loops. SQLite locks the entire database on writes, causing write-contention errors and bottlenecking concurrent ingestion pipelines.

## Consequences
* **Guaranteed Relational Integrity:** Enforced at the database engine level, ensuring profiles and application outcomes never enter orphaned or corrupt states.
* **Flexible Hybrid Storage:** The blend of structured SQL columns and flexible JSONB documents allows developers to adapt to changing ATS and scraper formats without migration overhead.
* **Unified Database Stack:** Utilizing PostgreSQL's native full-text search engine avoids the operational and cost overhead of running a separate Elasticsearch cluster in the early phases.
* **Migration Overhead:** Schema modifications require writing, testing, and applying Alembic migrations, which can slow down early-stage changes compared to schema-less databases.
* **Performance Maintenance at Scale:** As job posting and log tables scale to millions of rows, aggressive index optimization, partition strategies, and vacuuming cycles must be implemented to maintain low query latencies.

## Tradeoffs

### Schema Strictness vs. Ingestion Flexibility
We trade the absolute writing speed and schema-less ease of NoSQL for data integrity and structural consistency. The ingestion pipeline must perform normalization (matching raw job titles and skills to standard entities) before inserting records into Postgres. This design requires more upfront engineering effort in the ingestion service but guarantees that downstream analytics, health scoring, and matching agents operate on clean, valid, and relational data.

### Relational Storage vs. Write Telemetry Bloat
Storing agent execution logs, decision states, and audit trails directly in PostgreSQL guarantees auditability and easy debugging. However, it exposes the database to rapid table growth and write-amplification. We trade storage efficiency for complete system auditability. To prevent performance degradation, we store transient session data and rate limits in Redis, and apply partition schemes or archival strategies on historical agent logs and transaction traces.
