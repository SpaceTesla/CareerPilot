# Feature Specification: Advanced Deduplication (F2.2)

## 1. Purpose
The `Advanced Deduplication` feature compares raw job postings ingested from multiple sources (JSearch, Adzuna, direct crawlers) and matches them to prevent duplicate job records in the core database. It identifies postings that represent the same physical position at the same company and aggregates them under a single primary job record, maintaining an audit trail of duplicate source postings.

---

## 2. User Value
When a job seeker uses traditional job boards, they are often overwhelmed by identical listings posted multiple times (by recruiters, job boards, and direct ATS feeds). 
Advanced Deduplication ensures users have a clean, unique list of opportunities. It prevents double-applications (e.g., submitting once via JSearch and once via Greenhouse) and ensures that CareerPilot's aggregate statistical metrics—such as the Career Health Score and market trend salary percentiles—are calculated using clean, unique data.

---

## 3. Requirements
- **Title Similarity Scoring**: Normalize titles (lowercase, remove seniority tags like "Sr.", "Junior", "II", "III" during comparison) and compute similarity using Jaccard similarity of token sets or Levenshtein distance.
- **Company Similarity Scoring**: Clean and match company names (resolving suffixes like "Inc.", "LLC", "Corp" and consulting entity-matching aliases).
- **Description Similarity Scoring**: Compute description similarity using MinHash LSH (Locality Sensitive Hashing) or TF-IDF cosine similarity. For high-confidence matching, utilize dense vector similarity queries in Qdrant.
- **Deduplication Scoring Model**: A weighted composite scoring engine:
  $$\text{Score} = (W_{\text{title}} \times S_{\text{title}}) + (W_{\text{company}} \times S_{\text{company}}) + (W_{\text{desc}} \times S_{\text{desc}})$$
  Where $W_{\text{title}} = 0.3$, $W_{\text{company}} = 0.3$, and $W_{\text{desc}} = 0.4$.
- **Duplicate Clustering**: Group identical postings into clusters and elect a single "Primary" posting.
- **Merge Strategy Engine**: Define rule-based hierarchy to merge fields: direct ATS feeds (Greenhouse/Lever) have the highest priority, followed by API feeds, then general board aggregators.
- **Dedupe Review Tooling APIs**: Support manual review override endpoints for operators to verify edge-case duplicates flagged with marginal scores (0.75 - 0.85).
- **Dedupe Metrics**: Record rate of duplication per source, daily duplicates merged, and system precision/recall.
- **Audit Logging**: Trace all merges, recording original source fields, timestamps, and active decisions.

---

## 4. Database Changes

Modifications are applied to the core `job_postings` table, and new tables are introduced for auditing and manual resolution queue.

### Schema Definitions

#### Table Alterations: `job_postings`
Add deduplication fields to track status and merge relationships:
- `merged_into_id`: `UUID` (Nullable, self-referencing FK to `job_postings.id` ON DELETE SET NULL)
- `dedupe_fingerprint`: `VARCHAR(64)` (Nullable, sha256 representation of cleaned title + company + description snippet)
- `is_primary`: `BOOLEAN` (default `true`)

#### Table: `job_duplicates`
Stores evaluation pairs flagged as highly similar, pending manual review or auto-resolved.
- `id`: `UUID` (PK, default `uuid_generate_v4()`)
- `primary_job_id`: `UUID` (FK referencing `job_postings.id`, ON DELETE CASCADE)
- `duplicate_job_id`: `UUID` (FK referencing `job_postings.id`, ON DELETE CASCADE)
- `confidence_score`: `DECIMAL(4, 3)` (Value between 0.000 and 1.000)
- `title_similarity`: `DECIMAL(4, 3)`
- `company_similarity`: `DECIMAL(4, 3)`
- `description_similarity`: `DECIMAL(4, 3)`
- `status`: `VARCHAR(50)` (e.g., "AUTO_MERGED", "PENDING_REVIEW", "APPROVED", "REJECTED")
- `reviewed_by`: `UUID` (FK referencing `users.id`, Nullable)
- `created_at`: `TIMESTAMP WITH TIME ZONE` (default `now()`)
- `resolved_at`: `TIMESTAMP WITH TIME ZONE` (Nullable)

#### Table: `dedupe_audit_logs`
Historical log of merge transactions for pipeline transparency.
- `id`: `UUID` (PK, default `uuid_generate_v4()`)
- `action`: `VARCHAR(50)` (e.g., "MERGE", "SPLIT", "IGNORE")
- `primary_job_id`: `UUID` (FK referencing `job_postings.id`)
- `merged_job_id`: `UUID`
- `merge_details`: `JSONB` (Stores snapshot of values merged: title, url, description length)
- `created_at`: `TIMESTAMP WITH TIME ZONE` (default `now()`)

### Indexes & Migrations
- `idx_job_postings_fingerprint`: Hash index on `dedupe_fingerprint` for $O(1)$ lookup matching.
- `idx_job_duplicates_status`: B-Tree index on `status` to retrieve pending queue items.
- **Alembic Migration**: `add_deduplication_fields_and_tables.py` to add new columns to `job_postings` and create `job_duplicates` and `dedupe_audit_logs` tables.

---

## 5. API Endpoints

### `GET /api/v2/market/dedupe/duplicates`
Returns list of potential duplicates flagged for manual review (confidence score between threshold limits, e.g., 0.75 and 0.85).
- **Authentication**: Required (JWT, Scope: `admin` or `operator`)
- **Query Parameters**:
  - `status`: "PENDING_REVIEW" (default)
  - `limit`: `INTEGER` (default 50)
- **Response (200 OK)**:
```json
{
  "pending_duplicates": [
    {
      "duplicate_pair_id": "9a1b8c7d-e2f3-4a5b-6c7d-8e9f01234567",
      "confidence_score": 0.812,
      "primary_job": {
        "id": "1a2b3c4d-5e6f-7a8b-9c0d-1e2f3g4h5i6j",
        "title": "Staff Software Engineer, Platform",
        "company_name": "Google LLC",
        "source": "greenhouse",
        "location": "Mountain View, CA"
      },
      "duplicate_job": {
        "id": "7a8b9c0d-1e2f-3g4h-5i6j-7k8l9m0n1o2p",
        "title": "Staff Backend Engineer (Platform)",
        "company_name": "Google",
        "source": "jsearch",
        "location": "Mountain View, CA"
      },
      "similarities": {
        "title": 0.85,
        "company": 0.95,
        "description": 0.75
      }
    }
  ]
}
```

### `POST /api/v2/market/dedupe/resolve`
Approves or rejects a merge proposal.
- **Authentication**: Required (JWT, Scope: `admin` or `operator`)
- **Request Payload**:
```json
{
  "duplicate_pair_id": "9a1b8c7d-e2f3-4a5b-6c7d-8e9f01234567",
  "action": "APPROVE" 
}
```
- **Response (200 OK)**:
```json
{
  "duplicate_pair_id": "9a1b8c7d-e2f3-4a5b-6c7d-8e9f01234567",
  "status": "APPROVED",
  "primary_job_id": "1a2b3c4d-5e6f-7a8b-9c0d-1e2f3g4h5i6j",
  "merged_job_id": "7a8b9c0d-1e2f-3g4h-5i6j-7k8l9m0n1o2p",
  "message": "Jobs successfully merged."
}
```

---

## 6. Domain Models

```python
from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from typing import Optional, Dict

class SimilarityMetrics(BaseModel):
    title: float = Field(..., ge=0.0, le=1.0)
    company: float = Field(..., ge=0.0, le=1.0)
    description: float = Field(..., ge=0.0, le=1.0)

class DuplicateJobPair(BaseModel):
    duplicate_pair_id: UUID
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    primary_job_id: UUID
    duplicate_job_id: UUID
    similarities: SimilarityMetrics
    status: str
    created_at: datetime
    resolved_at: Optional[datetime] = None

class DedupeResolutionRequest(BaseModel):
    duplicate_pair_id: UUID
    action: str = Field(..., regex="^(APPROVE|REJECT)$")
```

---

## 7. Services

### `DeduplicationService`
Orchestrates comparison of incoming postings against currently active postings.
- `deduplicate_raw_posting(raw_job_id: UUID) -> Optional[UUID]`: Executes matching pipelines. Returns primary ID if merged, or `None` if verified unique.
- `generate_fingerprint(title: str, company: str, description: str) -> str`: Cleans inputs and hashes them into a stable string format.
- `cluster_duplicates(batch_job_ids: list[UUID]) -> None`: Runs batch clustering calculations on new ingest packages.

### `SimilarityScoringEngine`
Pure functional engine for similarity calculations.
- `calculate_title_similarity(t1: str, t2: str) -> float`: Tokenizes strings, strips stop words, calculates Levenshtein/Jaccard similarity.
- `calculate_company_similarity(c1: str, c2: str) -> float`: Looks up known aliases (e.g. "Meta" -> "Facebook") and cleans corporate extensions.
- `calculate_description_similarity(d1: str, d2: str) -> float`: Computes Cosine similarity of TF-IDF vectors or utilizes Qdrant dense embedding cosine scores.

### `MergeStrategyEngine`
Executes database updates.
- `merge_records(primary_id: UUID, duplicate_id: UUID) -> None`: Updates `merged_into_id` and `is_primary` flags. Transfers and merges list fields (e.g., appending external source URLs).

---

## 8. Events

### Event: `market.jobs.merged`
- **Producer**: `MergeStrategyEngine`
- **Consumer**: `qdrant-index-worker`, `intelligence-synthesis-service`, `search-index-update-job`
- **Payload Schema**:
```json
{
  "event_id": "6a2b8c9d-d2e1-4c60-a2b1-5e7e8fa1b98f",
  "event_type": "market.jobs.merged",
  "timestamp": "2026-06-09T02:10:00Z",
  "payload": {
    "primary_job_id": "1a2b3c4d-5e6f-7a8b-9c0d-1e2f3g4h5i6j",
    "merged_job_id": "7a8b9c0d-1e2f-3g4h-5i6j-7k8l9m0n1o2p",
    "source_merged": "jsearch",
    "primary_source": "greenhouse"
  }
}
```

---

## 9. Background Jobs
- **`batch_deduplication_cleanup_job`**: Runs hourly. Selects unprocessed rows from `raw_job_postings`, computes similarity clusters against database records, and applies auto-merges for scores > 0.85. Marginal cases are routed to the review queue.
- **`fingerprint_backfill_job`**: One-off/adhoc job to generate `dedupe_fingerprint` hashes for historical job data in `job_postings`.

---

## 10. Acceptance Criteria

### Auto-Merge Validation Scenario
- **Given**: A primary job posting for "Senior Software Engineer" at "Acme Corp" exists.
- **When**: A new raw job posting is ingested for "Sr. Software Engineer" at "Acme Corporation" with a 95% identical description.
- **Then**: The similarity score is calculated at 0.92, `is_primary` is set to `false` on the new posting, its `merged_into_id` is updated to point to the primary job, and a `market.jobs.merged` event is published.

### Marginal Case Review Queue Scenario
- **Given**: A primary job posting exists for "Backend Developer" at "Stripe" (New York Office).
- **When**: A new posting is crawled for "Backend Developer" at "Stripe" (Remote - US) with a 85% similar description.
- **Then**: The similarity score evaluates to 0.78 (due to location mismatch but identical description). The job is NOT auto-merged; instead, an entry is added to `job_duplicates` with status `PENDING_REVIEW` to trigger human review.

---

## 11. Edge Cases
- **Expired Postings**: A company reposts the same job description 6 months later. If the active job is marked filled/closed, the new job should not be merged into the old one. It must remain a new active posting.
- **Remote vs. Local Postings**: The same job details are posted for San Francisco, Austin, and Remote. They are distinct openings. The location matching logic must block auto-merges when geo-regions differ unless one is specifically labeled "Anywhere/Remote" and the company consolidates remote hiring.
- **API Timeout on Vector Lookup**: If Qdrant is unresponsive, fallback to PostgreSQL-only MinHash LSH checks to continue deduplication without blocking ingestion workers.

---

## 12. Test Requirements
- **Precision/Recall Evaluation Suite**: Maintain a test dataset of 200 manually labeled duplicates/non-duplicates. The deduplication scoring engine must hit a target threshold of **98% Precision** (no false merges) and **90% Recall**.
- **Performance/Scaling Testing**: Run similarity comparisons for a batch of 10,000 raw postings against a target database of 100,000 jobs. Verify average latency per job remains under 150ms.

---

## 13. Dependencies
- **Direct Blockers**:
  - [Multi-Source Job Ingestion (F2.1)](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/feature-specs/multi-source-job-ingestion.md)
- **Downstream Beneficiaries**:
  - [Company Intelligence (F2.4)](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/feature-specs/company-intelligence.md)
  - [Ghost Posting Detection (F2.5)](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/feature-specs/ghost-posting-detection.md)
  - [Opportunity Intelligence (F2.7)](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/feature-specs/opportunity-intelligence.md)
