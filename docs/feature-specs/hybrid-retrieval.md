# Feature Specification: Hybrid Retrieval (F3.6)

## 1. Purpose
Hybrid Retrieval is a core performance-critical platform service that implements a multi-stage search pipeline. Per the [Implementation Doctrine](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/IMPLEMENTATION_DOCTRINE.md), single-stage retrieval is prohibited. Hybrid Retrieval combines keyword-based searches (BM25 via PostgreSQL Full-Text Search) with dense semantic vector searches (via Qdrant Vector Database) to capture both exact matches (e.g., specific library names like "FastAPI") and conceptual alignments (e.g., "backend developer with high-throughput API experience"). The candidates from both streams are merged using Reciprocal Rank Fusion (RRF) and re-scored via a Cross-Encoder reranking model (e.g., Cohere or self-hosted BGE-Reranker) before delivery to the agents.

---

## 2. User Value
Hybrid Retrieval ensures that recommendations are highly precise and relevant. Standard keyword search misses jobs that describe matching roles using synonyms. Conversely, pure vector search occasionally misses exact technical keyword requirements (like "Go" or "Kubernetes"). By fusing both methods, CareerPilot finds highly aligned hidden opportunities, reducing false positives and ensuring the Intelligence Agent evaluates the best matching positions in the market.

---

## 3. Requirements
* **PostgreSQL BM25 Engine**: Configure database indexes (`gin(to_tsvector('english', description))`) on job postings and profile tables to enable high-speed keyword retrieval.
* **Qdrant Vector Database Integration**: Configure a Qdrant collection containing dense embeddings representing job postings and candidate profiles.
* **Embedding Generation Pipeline**: Setup an embedding service that converts raw text into vector representation utilizing a consistent model (e.g., `text-embedding-3-small` or local `bge-small-en-v1.5`).
* **Reciprocal Rank Fusion (RRF)**: Implement RRF algorithm to merge rankings from BM25 and Qdrant. Use standard parameter constant `k = 60`.
* **Reranking Pipeline**: Hook up a Cross-Encoder model (`BAAI/bge-reranker-large` or Cohere Rerank API) to run secondary relevance evaluation on top-K merged results.
* **Retrieval APIs**: Build interfaces for agents to query the hybrid pipeline and retrieve the final, ranked list of jobs or profiles.
* **Observability & Metrics**: Expose retrieval latencies (p95 < 400ms), index dimensions, and cache efficiency metrics.

---

## 4. Database & Vector Store Changes

### PostgreSQL Table Extensions
Update `job_postings` table to support full-text search.
```sql
-- Assuming job_postings table exists from F1.5
ALTER TABLE job_postings ADD COLUMN search_vector tsvector;

CREATE INDEX idx_job_postings_search_vector ON job_postings USING GIN (search_vector);

-- Trigger to automatically update search_vector when title or description changes
CREATE OR REPLACE FUNCTION job_postings_trigger_func() RETURNS trigger AS $$
begin
  new.search_vector :=
    setweight(to_tsvector('english', coalesce(new.title,'')), 'A') ||
    setweight(to_tsvector('english', coalesce(new.description,'')), 'B');
  return new;
end
$$ LANGUAGE plpgsql;

CREATE TRIGGER tsvectorupdate BEFORE INSERT OR UPDATE
ON job_postings FOR EACH ROW EXECUTE FUNCTION job_postings_trigger_func();
```

### Qdrant Vector Store Collection
* **Collection Name**: `job_postings_vectors`
* **Configuration**:
  * Vector Size: 1536 (or matching embedding provider model)
  * Distance Metric: Cosine similarity
* **Payload Fields**:
  * `job_id` (UUID string matching `job_postings.id`)
  * `title` (string)
  * `company_name` (string)
  * `skills` (list of strings)
  * `location` (string)

---

## 5. API Endpoints

### POST `/api/v1/retrieval/search`
Perform a hybrid search for job postings matching a query or candidate profile.
* **Request Payload**:
  ```json
  {
    "query": "Kubernetes and Go developer with API design background",
    "user_id": "4a2b9c3d-1234-5678-9101-abcdef123456",
    "limit": 10,
    "rerank_top_k": 30
  }
  ```
* **Response Body (200 OK)**:
  ```json
  {
    "query": "Kubernetes and Go developer with API design background",
    "results": [
      {
        "job_id": "job_11223344-5566-7788-9900-aabbccddeeff",
        "title": "Senior Platform Engineer",
        "company_name": "Stripe",
        "score": 0.9234, -- reranked cross-encoder score
        "retrieval_sources": ["vector", "bm25"]
      }
    ]
  }
  ```

---

## 6. Domain Models

```python
from pydantic import BaseModel, Field
from typing import List, Optional
from uuid import UUID

class RetrievalCandidate(BaseModel):
    job_id: UUID
    title: str
    company_name: str
    bm25_rank: Optional[int] = None
    vector_rank: Optional[int] = None
    rrf_score: Optional[float] = None
    final_score: float = Field(description="The final score output by the Cross-Encoder reranker.")
    retrieval_sources: List[str] = Field(description="List containing retrieval paths, e.g. ['vector', 'bm25']")

class HybridRetrievalRequest(BaseModel):
    query: str
    user_id: Optional[UUID] = None
    limit: int = 10
    rerank_top_k: int = 30
```

---

## 7. Services

### `HybridRetrievalService`
* **Method**: `generate_embeddings(text: str) -> List[float]`
  * Converts query or candidate text into embedding vectors.
* **Method**: `search(request: HybridRetrievalRequest) -> List[RetrievalCandidate]`
  * Coordinates the multi-stage pipeline:
    1. Executes vector search against Qdrant (`qdrant_client.search`).
    2. Executes Full-Text Search against PostgreSQL.
    3. Merges result indices using Reciprocal Rank Fusion.
    4. Submits top `rerank_top_k` results to the Cross-Encoder model.
    5. Returns top `limit` sorted candidates.

---

## 8. Events
No events are generated directly during query retrieval to avoid slowing performance. However, async synchronization events are emitted during record inserts.

### `retrieval.index.updated`
* **Producer**: Ingestion Worker
* **Consumer**: ObservabilityPlatform
* **Payload**:
  ```json
  {
    "event_id": "evt_ret_idx_01",
    "timestamp": "2026-06-09T02:04:18Z",
    "job_id": "job_11223344-5566-7788-9900-aabbccddeeff",
    "status": "indexed_qdrant_and_postgres"
  }
  ```

---

## 9. Background Jobs
* **Job Name**: `vector_db_sync`
  * **Frequency**: Hourly (`0 * * * *`)
  * **Payload**: None
  * **Logic**: Scan `job_postings` table for records created or updated within the last hour. Verify Qdrant vectors exist for those records. Generate and upload missing embeddings.
  * **Retry Behavior**: Retry up to 3 times, with 1-minute backoffs.

---

## 10. Acceptance Criteria
* **AC 1**: Given a query, when Hybrid Search is executed, it must call both Qdrant vector retrieval and PostgreSQL full-text search.
* **AC 2**: The top candidates from both search streams must be merged utilizing Reciprocal Rank Fusion before passing to the reranker.
* **AC 3**: The total latency of the combined search and rerank pipeline must be less than 400ms for p95 requests.

---

## 11. Edge Cases
* **Zero Results from Vector Database**: If Qdrant is offline or returns empty lists, the service must gracefully fall back to full-text search (BM25) and log a warning, rather than returning a 500 error.
* **Special Character Queries**: Queries with special characters or SQL syntax must be sanitized before passing to PostgreSQL's `to_tsquery` function to prevent syntax exceptions.
* **Massive Query Strings**: If a user submits a huge text chunk (e.g., entire resume), the system must extract key nouns and verbs using the NLP extraction service before passing to BM25 to avoid overwhelming the parser.

---

## 12. Test Requirements
* **Unit Testing**:
  * Verify RRF ranking logic outputs correct order using static mock rankings.
  * Assert sanitization functions properly clean raw user inputs.
* **Integration Testing**:
  * Execute a mock search query asserting that candidates from PostgreSQL GIN indices and Qdrant local test vectors are aggregated correctly.
* **Agent/Workflow Evaluation**:
  * Assert Mean Reciprocal Rank (MRR@10) and Normalized Discounted Cumulative Gain (NDCG@10) match baseline benchmarks (e.g., MRR >= 0.70) on a test set of 100 queries.

---

## 13. Dependencies
* This feature depends on:
  * [career-profile-domain.md](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/feature-specs/career-profile-domain.md) (F1.3)
  * [job-market-data-foundation.md](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/feature-specs/job-market-data-foundation.md) (F1.5)
* This feature is a dependency for:
  * [research-agent.md](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/feature-specs/research-agent.md) (F3.3)
  * [intelligence-agent.md](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/feature-specs/intelligence-agent.md) (F3.4)
  * [gap-aware-retrieval.md](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/feature-specs/gap-aware-retrieval.md) (F7.2)
