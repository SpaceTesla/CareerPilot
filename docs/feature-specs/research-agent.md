# Feature Specification: Research Agent (F3.3)

## 1. Purpose
The Research Agent is a specialized node in the CareerPilot agent network. Its role is to execute deep investigations into target companies, industries, and specific job descriptions. It extracts latent requirements (e.g., hidden tech stacks, soft requirements, interview styles), compiles organizational signals (e.g., hiring velocity, executive departures, product launches), and constructs comprehensive, source-attributed company intelligence profiles. By replacing raw keyword matching with deep structural understanding, this agent provides context to the downstream scoring and tailoring engines.

---

## 2. User Value
The Research Agent fuels the Career Intelligence Compounding Loop by transforming raw, superficial job listings into rich, multi-dimensional profiles. Instead of guessing why they aren't getting callbacks, users receive granular context, such as: "This team is migrating from PyTorch to JAX; emphasizing your JAX experience will close the 15% positioning gap." It ensures every recommendations is backed by verified data points (source attribution) rather than general LLM hallucination.

---

## 3. Requirements
* **Company Research Workflow**: Implement a structured workflow that coordinates hybrid searches against cached job listings, company reports, and web index APIs.
* **Role Requirement Extraction**: Extract hard technical skills, domain certifications, soft-skill requirements, and organizational structure clues from job descriptions.
* **Market Signal Synthesis**: Integrate company hiring velocity indices (from Company Intelligence F2.4) and ghost posting indicators (F2.5) to assess company health.
* **Structured Research Outputs**: Ensure the agent outputs data conforming to a strict schema, classifying requirements into "Critical", "Preferred", and "Bonus".
* **Source Attribution**: Map every extracted requirement or company velocity indicator to a specific source URL, cached document ID, or job posting metadata record.
* **Research Memory Storage**: Persist compiled company profiles in the `research_memories` table to bypass LLM searches for future queries on the same firm.
* **Research APIs**: Expose endpoints to query cached research, execute ad-hoc company analyses, and retrieve structured signal metrics.
* **Scoring & Evaluation**: Implement a calibration scoring protocol for research quality (e.g., comparing extracted skills against human annotations).

---

## 4. Database Changes
We require tables to store compiled research profiles and mapping logs.

### PostgreSQL Tables

#### `research_memories`
Stores structured, cached intelligence reports about companies and roles.
```sql
CREATE TABLE research_memories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_name VARCHAR(255) NOT NULL,
    company_domain VARCHAR(255),
    role_category VARCHAR(150), -- e.g. platform-engineer, ml-scientist
    structured_data JSONB NOT NULL, -- contains requirements, signals, tech stack
    raw_sources JSONB NOT NULL, -- list of source URLs, docs, metadata
    confidence_score NUMERIC(3, 2) NOT NULL DEFAULT 1.00,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE UNIQUE INDEX idx_research_memories_lookup ON research_memories(company_name, role_category);
CREATE INDEX idx_research_memories_expires ON research_memories(expires_at);
```

### Alembic Migration Plan
1. Create `research_memories` table with unique constraint on `(company_name, role_category)`.
2. Add index on `expires_at` for background cleanup.
3. Configure JSONB indices on `structured_data` keys if query speed dictates.

---

## 5. API Endpoints

### GET `/api/v1/research/company/{company_name}`
Fetch compiled intelligence report for a company.
* **Query Parameters**:
  * `role_category` (string, optional): Filter by department or engineering vertical.
* **Response Body (200 OK)**:
  ```json
  {
    "company_name": "Netflix",
    "company_domain": "netflix.com",
    "role_category": "ml-engineer",
    "confidence_score": 0.94,
    "structured_data": {
      "tech_stack": ["Python", "JAX", "Kubernetes", "Ray"],
      "hiring_velocity": "high",
      "estimated_growth_yoy": 12.5,
      "requirements": {
        "critical": ["Distributed Systems", "Ray Core", "Deep Learning Fundamentals"],
        "preferred": ["Streaming pipelines", "Flink"],
        "bonus": ["Previous ad-tech experience"]
      }
    },
    "raw_sources": [
      {
        "source_type": "job_description",
        "reference_id": "job_99881122",
        "url": "https://netflix.jobs/role-123",
        "verified_at": "2026-06-09T01:00:00Z"
      }
    ],
    "updated_at": "2026-06-09T02:04:18Z"
  }
  ```

### POST `/api/v1/research/analyze`
Trigger an ad-hoc deep research task for a company/role combination.
* **Request Payload**:
  ```json
  {
    "company_name": "Stripe",
    "job_description_raw": "Looking for a staff engineer to build our core API platform. Experience with Ruby, Go, and high throughput is required...",
    "bypass_cache": false
  }
  ```
* **Response Body (202 Accepted)**:
  ```json
  {
    "task_id": "task_res_778899",
    "status": "queued",
    "message": "Deep company intelligence gathering initiated."
  }
  ```

---

## 6. Domain Models

```python
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from uuid import UUID
from datetime import datetime

class ResearchSource(BaseModel):
    source_type: str = Field(description="Type of source: 'job_posting', 'news_article', 'sec_filing', 'company_page'")
    reference_id: Optional[str] = None
    url: Optional[str] = None
    snippet: Optional[str] = None
    verified_at: datetime

class RequirementsMap(BaseModel):
    critical: List[str] = Field(description="Must-have competencies or tools.")
    preferred: List[str] = Field(description="Strong positive indicators.")
    bonus: List[str] = Field(description="Nice-to-have or peripheral skills.")

class CompanySignals(BaseModel):
    hiring_velocity: str = Field(description="Hiring pace: 'stagnant', 'moderate', 'high'")
    tech_stack: List[str] = Field(description="Verified technologies used by the team.")
    organizational_notes: Optional[str] = None

class ResearchReport(BaseModel):
    company_name: str
    company_domain: Optional[str] = None
    role_category: str
    requirements: RequirementsMap
    signals: CompanySignals
    sources: List[ResearchSource]
    confidence_score: float = Field(ge=0.0, le=1.0)
```

---

## 7. Services

### `ResearchAgentService`
* **Method**: `research_opportunity(company_name: str, job_description: str) -> ResearchReport`
  * Executes the main research graph node. Checks `research_memories` cache, performs hybrid retrieval lookup on current company postings, runs LLM extraction, compiles sources, and generates confidence scores.
* **Method**: `cache_research(report: ResearchReport) -> None`
  * Saves or updates a serialized research profile in the `research_memories` database.
* **Method**: `invalidate_expired_memories() -> int`
  * Triggers database cleanup of cached research that has surpassed expiration timestamps.

---

## 8. Events

### `agent.research.completed`
* **Producer**: `ResearchAgentService`
* **Consumer**: `IntelligenceAgent`, `ObservabilityPlatform`
* **Payload**:
  ```json
  {
    "event_id": "evt_res_9901",
    "timestamp": "2026-06-09T02:04:18Z",
    "company_name": "Stripe",
    "role_category": "staff-platform-engineer",
    "critical_requirements_count": 5,
    "confidence_score": 0.89
  }
  ```

---

## 9. Background Jobs
* **Job Name**: `research_cache_cleaner`
  * **Frequency**: Daily at 01:00 AM (`0 1 * * *`)
  * **Payload**: None
  * **Logic**: Delete rows in `research_memories` where `expires_at < CURRENT_TIMESTAMP`. Set expiration interval to 14 days by default to capture fluctuating market data.
  * **Retry Behavior**: Standard celery worker retry (3 attempts, 5-minute delay).

---

## 10. Acceptance Criteria
* **AC 1**: Given a raw job description, when the Research Agent parses it, it must output a structured `ResearchReport` containing at least one verified `ResearchSource`.
* **AC 2**: Given a query for a company already researched within the last 14 days, the service must return the cached report from `research_memories` instead of performing new external API fetches.
* **AC 3**: Given an extracted skill, when presenting results to the user, the agent must output the source snippet where that skill was inferred.

---

## 11. Edge Cases
* **Zero Job Details (Blank/Short Descriptions)**: When a job description contains less than 200 characters, the agent must fallback to scraping the company's career page or inferring requirements based on the job title and company sector using hybrid retrieval.
* **Name Ambiguity (e.g., Apple vs. Apple Bank)**: The Research Agent must map target company domains utilizing URL lookups to ensure research is tied to the correct legal entity.
* **API Ingestion Rate Limiting**: If external research tools (search APIs, news indexers) return HTTP 429, the agent must immediately fall back to vector database caches of historical jobs for that firm.

---

## 12. Test Requirements
* **Unit Testing**:
  * Verify Pydantic schema parser handles missing source urls and incomplete source blocks.
  * Assert validation logic flags invalid confidence scores (e.g., > 1.0 or < 0.0).
* **Integration Testing**:
  * Test cache lookup, caching execution, and cache invalidation against a test database.
* **Agent/Workflow Evaluation**:
  * Run evaluation on 50 ground-truth job postings. The Research Agent must extract at least 80% of core technical competencies correctly (Precision >= 0.80, Recall >= 0.80).

---

## 13. Dependencies
* This feature depends on:
  * [langgraph-foundation.md](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/feature-specs/langgraph-foundation.md) (F3.1)
  * [company-intelligence.md](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/feature-specs/company-intelligence.md) (F2.4)
  * [hybrid-retrieval.md](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/feature-specs/hybrid-retrieval.md) (F3.6)
* This feature is a dependency for:
  * [intelligence-agent.md](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/feature-specs/intelligence-agent.md) (F3.4)
