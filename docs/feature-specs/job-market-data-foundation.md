# Feature Specification: Job Market Data Foundation

## 1. Purpose
This feature establishes the core "Market Model" for CareerPilot. It provides the database schemas, normalization engines, deduplication pipelines, ingestion audit logs, and admin endpoints for managing job postings, companies, and normalized skill taxonomies. This is the root repository for all external jobs, representing the ground truth of the market against which candidate profiles are evaluated.

For how this feeds into future epics (e.g. Multi-Source Ingestion, NLP Skill Extraction), see [DEPENDENCY_GRAPH.md](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/DEPENDENCY_GRAPH.md). For product conviction details, refer to [careerpilot_v2.md](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/careerpilot_v2.md).

## 2. User Value
A candidate's value is relative to the job market. To calculate how well-aligned a user is with the market (Health Score) and what gaps they need to fill (Position Delta), CareerPilot needs a clean, deduplicated, and normalized view of job descriptions, required skills, and salary benchmarks. This database ensures users see real, non-duplicated opportunities and reliable trends.

## 3. Requirements
- **Database Architecture**: Design schemas for Job Postings, Companies, Normalized Skills, and Ingestion Audit Logs.
- **Job Ingestion Framework**: Set up an async Celery worker structure that receives raw JSON job postings from external collection systems, resolving company records and deduplicating records.
- **Normalizers**:
  - **Company Normalizer**: Maps variations of company names (e.g., "Google LLC", "Google Inc.") to a single, unique `company` entity.
  - **Title Normalizer**: Maps raw job titles (e.g., "Sr. Python Dev", "Senior Backend Engineer - Python") to standardized roles.
- **Job Deduplication Service**: Flags and merges duplicate postings (same company, similar title, location, and post date within 7 days) by pointing duplicate rows to a single primary posting ID.
- **Skills Extraction & Normalization**: Maps raw string skills found in descriptions to a master taxonomy table.
- **Ingestion Audit Logging**: Persists statistics for every ingestion batch run (jobs attempted, inserted, duplicated, failed).

## 4. Database Changes

### `companies`
Central directory of employers.
- `id`: `UUID` (Primary Key, Default: `uuid_generate_v4()`)
- `name`: `VARCHAR(255)` (Unique, Indexed, Not Null) - Normalized name, e.g. "Google"
- `website`: `VARCHAR(255)` (Nullable)
- `logo_url`: `VARCHAR(512)` (Nullable)
- `sector`: `VARCHAR(100)` (Nullable)
- `size_range`: `VARCHAR(50)` (Nullable) - E.g. "100-500", "1000+"
- `created_at`: `TIMESTAMP WITH TIME ZONE` (Default: `NOW()`, Not Null)
- `updated_at`: `TIMESTAMP WITH TIME ZONE` (Default: `NOW()`, Not Null)

### `job_postings`
Unifying table for all ingested jobs.
- `id`: `UUID` (Primary Key, Default: `uuid_generate_v4()`)
- `company_id`: `UUID` (Foreign Key referencing `companies.id` ON DELETE RESTRICT, Indexed, Not Null)
- `title`: `VARCHAR(255)` (Indexed, Not Null) - Normalized title
- `raw_title`: `VARCHAR(255)` (Not Null) - Original title
- `location`: `VARCHAR(255)` (Not Null) - Normalized location
- `description`: `TEXT` (Not Null)
- `url`: `VARCHAR(1024)` (Indexed, Not Null)
- `compensation_min`: `NUMERIC(12, 2)` (Nullable)
- `compensation_max`: `NUMERIC(12, 2)` (Nullable)
- `currency`: `VARCHAR(10)` (Default: 'USD', Not Null)
- `source`: `VARCHAR(100)` (Not Null) - E.g. "ADZUNA", "JSEARCH", "GREENHOUSE"
- `source_id`: `VARCHAR(255)` (Unique, Indexed, Not Null) - Unique identifier from source
- `post_date`: `DATE` (Indexed, Not Null)
- `expiry_date`: `DATE` (Nullable)
- `is_active`: `BOOLEAN` (Default: `True`, Indexed, Not Null)
- `deduplicated_to_id`: `UUID` (Foreign Key referencing `job_postings.id` ON DELETE SET NULL, Indexed, Nullable) - References primary job posting if duplicate
- `created_at`: `TIMESTAMP WITH TIME ZONE` (Default: `NOW()`, Not Null)
- `updated_at`: `TIMESTAMP WITH TIME ZONE` (Default: `NOW()`, Not Null)

### `normalized_skills`
Global taxonomy list of standard technical and business skills.
- `id`: `UUID` (Primary Key, Default: `uuid_generate_v4()`)
- `name`: `VARCHAR(100)` (Unique, Indexed, Not Null) - E.g., "Kubernetes"
- `category`: `VARCHAR(100)` (Nullable) - E.g., "Infrastructure"
- `aliases`: `JSONB` (Default: `'[]'`, Not Null) - E.g. `["k8s", "kube", "k8s clustering"]`
- `created_at`: `TIMESTAMP WITH TIME ZONE` (Default: `NOW()`, Not Null)

### `job_postings_skills`
Join table connecting postings to required skills.
- `job_posting_id`: `UUID` (Foreign Key referencing `job_postings.id` ON DELETE CASCADE, Indexed, Not Null)
- `skill_id`: `UUID` (Foreign Key referencing `normalized_skills.id` ON DELETE RESTRICT, Indexed, Not Null)
- `raw_mention`: `VARCHAR(100)` (Nullable) - Original text extracted
- `created_at`: `TIMESTAMP WITH TIME ZONE` (Default: `NOW()`, Not Null)

### `ingestion_audit_logs`
Tracks pipeline health and ingestion statistics.
- `id`: `UUID` (Primary Key, Default: `uuid_generate_v4()`)
- `source`: `VARCHAR(100)` (Not Null)
- `job_count_attempted`: `INTEGER` (Not Null)
- `job_count_inserted`: `INTEGER` (Not Null)
- `job_count_duplicated`: `INTEGER` (Not Null)
- `job_count_failed`: `INTEGER` (Not Null)
- `log_details`: `JSONB` (Nullable) - Contains error traces or duplicate list ID pairs
- `created_at`: `TIMESTAMP WITH TIME ZONE` (Default: `NOW()`, Not Null)

### Indexes and Migrations
- Unique constraint on `companies.name`.
- Unique constraint on `job_postings.source_id`.
- Composite index on `job_postings(title, company_id, location)`.
- Alembic migration `V2026_06_09_0003_create_market_tables.py`.

## 5. API Endpoints

### `POST /api/v2/admin/market/ingest`
Admin endpoint to manually trigger raw job posting payload ingestion (used by spiders and tests).
- **Request Headers**: Admin API Key or JWT Admin role.
- **Request Body**:
  ```json
  {
    "source": "JSEARCH",
    "postings": [
      {
        "source_id": "js_129381",
        "company_name": "Google LLC",
        "title": "Sr. Software Engineer (Python)",
        "description": "We are seeking a Python developer with Kubernetes experience.",
        "location": "Mountain View, CA",
        "url": "https://careers.google.com/jobs/129381",
        "compensation_min": 175000.00,
        "compensation_max": 220000.00,
        "currency": "USD",
        "post_date": "2026-06-08"
      }
    ]
  }
  ```
- **Response Body (202 Accepted)**:
  ```json
  {
    "audit_log_id": "4eb9bf2c-38cd-47d3-96b6-d249f390022d",
    "status": "processing",
    "message": "Ingestion task queued successfully."
  }
  ```

### `GET /api/v2/market/postings`
Fetches active, normalized job postings. Supports basic filters for skills and normalized titles.
- **Query Parameters**:
  - `skills`: List of skill names (e.g. `Python,Kubernetes`)
  - `title`: Filter by normalized title substring
  - `limit`: default 20
  - `offset`: default 0
- **Response Body (200 OK)**:
  ```json
  {
    "total": 142,
    "items": [
      {
        "id": "7db091bb-000c-4828-9828-0902bd32a688",
        "company": {
          "name": "Google",
          "sector": "Technology"
        },
        "title": "Senior Software Engineer",
        "location": "Mountain View, CA",
        "compensation_min": 175000.00,
        "compensation_max": 220000.00,
        "post_date": "2026-06-08",
        "skills": ["Python", "Kubernetes"]
      }
    ]
  }
  ```

## 6. Domain Models

### Pydantic Schemas

```python
from pydantic import BaseModel, HttpUrl
from uuid import UUID
from datetime import date
from typing import List, Optional
from decimal import Decimal

class CompanyBase(BaseModel):
    name: str
    website: Optional[str] = None
    sector: Optional[str] = None

class CompanyResponse(CompanyBase):
    id: UUID
    class Config:
        from_attributes = True

class JobPostingBase(BaseModel):
    source_id: str
    title: str
    location: str
    description: str
    url: str
    compensation_min: Optional[Decimal] = None
    compensation_max: Optional[Decimal] = None
    currency: str = "USD"
    post_date: date

class JobPostingResponse(BaseModel):
    id: UUID
    company: CompanyResponse
    title: str  # Normalized
    raw_title: str
    location: str
    description: str
    url: str
    compensation_min: Optional[Decimal]
    compensation_max: Optional[Decimal]
    currency: str
    post_date: date
    skills: List[str] = []

    class Config:
        from_attributes = True
```

## 7. Services

### `JobIngestionService`
- **Responsibilities**: Receives raw crawls, creates/resolves unique `companies` entities, writes records to database, maps skills using string regex patterns (in V1), and tracks run in `ingestion_audit_logs`.
- **Methods**:
  - `ingest_batch(source: str, raw_payloads: List[dict]) -> UUID`: Runs batch inserts inside transactions, handles parsing errors gracefully without failing the entire batch, returns audit log UUID.

### `JobNormalizationService`
- **Responsibilities**: Implements dictionaries and regexes to normalize raw titles and raw locations.
- **Methods**:
  - `normalize_title(raw_title: str) -> str`: Standardizes inputs (e.g. maps "Sr. Backend" to "Senior Backend Engineer").
  - `resolve_skills(description: str) -> List[NormalizedSkill]`: Parses text against standard list and aliases, returning matched entities.

### `JobDeduplicationService`
- **Responsibilities**: Checks for duplicate records during batch ingestion.
- **Methods**:
  - `identify_duplicates(company_id: UUID, title: str, location: str, date: date) -> Optional[UUID]`: Returns the primary `job_posting.id` if a matching duplicate exists.

## 8. Events

- **`market.job_ingested`**:
  - **Producer**: `JobIngestionService` (fired per newly inserted job)
  - **Consumers**: `QdrantEmbeddingWorker` (generate vectors), `PositionDeltaEngine` (recalculate active deltas if necessary).
  - **Payload**:
    ```json
    {
      "event_id": "c61fd120-1b76-4be0-bb78-0d8bb32014a6",
      "event_type": "market.job_ingested",
      "timestamp": "2026-06-09T02:04:18Z",
      "data": {
        "job_posting_id": "7db091bb-000c-4828-9828-0902bd32a688",
        "company_name": "Google",
        "normalized_title": "Senior Software Engineer",
        "skills": ["Python", "Kubernetes"]
      }
    }
    ```
- **`market.ingestion_completed`**:
  - **Producer**: Celery Ingestion batch Task.
  - **Consumers**: `SkillTrendEngine` (re-run daily aggregations).
  - **Payload**:
    ```json
    {
      "event_id": "ab71efd3-90d4-4899-b1d1-08dcd3f218bb",
      "event_type": "market.ingestion_completed",
      "timestamp": "2026-06-09T02:04:18Z",
      "data": {
        "audit_log_id": "4eb9bf2c-38cd-47d3-96b6-d249f390022d",
        "source": "JSEARCH",
        "inserted_count": 89,
        "failed_count": 2
      }
    }
    ```

## 9. Background Jobs

### `celery_run_ingestion`
- **Trigger**: Cron, triggered daily at 01:00 AM.
- **Payload**: None.
- **Workflow**: Calls external APIs (like JSearch or Adzuna in subsequent features), pulls new listings matching key parameters (e.g. location, roles), passes payloads to `JobIngestionService.ingest_batch`.
- **Retry Behavior**: Retries 3 times, exponential backoff (delay 60s, multiplier 2).

## 10. Acceptance Criteria

- **Scenario: Normal Ingestion with Duplicate Detection**
  - **Given** two raw postings with identical company ("Google LLC"), title ("Sr. Python Developer"), location ("Mountain View, CA"), and date ("2026-06-09"),
  - **When** the ingestion pipeline processes both in a batch,
  - **Then** insert one active `job_postings` record, and insert the second record with `deduplicated_to_id` pointing to the first record, marking it inactive (`is_active: false`).
- **Scenario: Title Normalization Lookup**
  - **Given** raw titles "Sr Backend Engineer", "Lead Developer Backend", and "Senior Python Backend",
  - **When** calling the normalization service,
  - **Then** map all three to the standardized title string: "Senior Backend Engineer".
- **Scenario: Batch Ingestion Error Recovery**
  - **Given** a batch payload containing 10 jobs, where 1 job has a corrupt missing URL,
  - **When** executing `ingest_batch`,
  - **Then** insert 9 valid jobs successfully, log 1 failure in `ingestion_audit_logs`, and commit transaction.

## 11. Edge Cases
- **Varying Company Suffixes**: Company normalizer matches root substrings using Jaro-Winkler similarity or lookup maps (e.g., "Apple Corp" and "Apple Inc" map to the single company entity "Apple").
- **Missing Salary Fields**: If the crawled posting lacks compensation figures, the fields are kept null. Normalization engines skip salary computations for this posting rather than crashing.
- **Extreme Job Descriptions**: Job descriptions containing binary structures or spam lists are truncated at 20,000 characters during text normalization to protect database storage limits.

## 12. Test Requirements
- **Unit Tests**:
  - Test title normalization dictionary mappings.
  - Test regex matching parser against simulated job descriptions to assert correct skill extraction.
- **Integration Tests**:
  - Verify that parallel insertion tasks do not create duplicate company entries in the `companies` table.
  - Run end-to-end ingestion and verify audit logs count matches exact inputs.

## 13. Dependencies
This feature depends on [project-setup-architecture.md](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/feature-specs/project-setup-architecture.md).
Downward features that depend on this are:
- [skill-trend-engine-v1.md](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/feature-specs/skill-trend-engine-v1.md)
- [position-delta-engine.md](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/feature-specs/position-delta-engine.md)
