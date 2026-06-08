# Feature Specification: Compensation Intelligence (F2.6)

## 1. Purpose
The `Compensation Intelligence` feature extracts, normalizes, and aggregates pay ranges and equity packages from job postings and verified candidate offers. It computes granular percentile-based salary benchmarks (P25, P50, P75) by role, geography, and specific technical skills. This provides an analytical source of truth for current labor pricing.

---

## 2. User Value
Software engineers struggle to obtain reliable, real-time compensation data. Existing platforms often rely on outdated, self-reported, or broad averages. 
Compensation Intelligence addresses this by surfacing real, current offer details and listing prices, adjusted for location and skill set (e.g., showing a candidate the premium for adding "Rust" or "Kubernetes" to their stack). 
In the **Career Intelligence Compounding Loop** (from [careerpilot_v2.md](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/careerpilot_v2.md)), this data is critical. It determines the "Compensation Alignment" component of the Career Health Score and ensures users only apply to roles matching their market value.

---

## 3. Requirements
- **Compensation Schema**: Design data models capable of storing annual salaries, hourly rates, equity ranges, and bonus structures across multiple currencies.
- **Salary Extraction Pipeline**: Build regex-based parsing patterns and LLM filters to extract salary bounds from job postings (e.g. "$150,000 - $190,000/yr" or "£60/hour").
- **Compensation Range Normalization**: Convert hourly rates to annual equivalents (assuming 2,000 hours per year) and clean up outliers.
- **Location Normalization**: Map custom location fields ("NY", "New York City", "Manhattan") to canonical cities, countries, and regional cost-of-living (COL) tier groups (e.g. Tier 1: SF/NY, Tier 2: Austin/Seattle, Tier 3: Remote).
- **Benchmark Calculator**: Run weekly aggregation jobs to group compensation records by role type, location, and key skills.
- **Percentile Calculations**: Compute statistical distributions (P25, P50, P75) for salary clusters with a minimum sample size constraint ($N \ge 5$) to protect anonymity and maintain relevance.
- **Compensation APIs**: Support queries by role, location, and skills, returning percentile data.
- **Caching Layer**: Cache frequently queried benchmarks in Redis.
- **Benchmark Evaluation Tests**: Quality check pipeline to filter out corrupted listings and verify calculations.

---

## 4. Database Changes

Maintains raw extraction records and materialized benchmark tables.

### Schema Definitions

#### Table: `compensation_records`
Holds raw, cleaned data points.
- `id`: `UUID` (PK, default `uuid_generate_v4()`)
- `job_posting_id`: `UUID` (FK referencing `job_postings.id`, ON DELETE CASCADE, Nullable)
- `source_type`: `VARCHAR(50)` (e.g., "JOB_POSTING", "USER_OFFER_VERIFIED")
- `min_salary`: `DECIMAL(12, 2)` (Raw minimum value)
- `max_salary`: `DECIMAL(12, 2)` (Raw maximum value)
- `currency`: `VARCHAR(3)` (ISO 4217, e.g. "USD", "GBP", "EUR")
- `payment_interval`: `VARCHAR(50)` (e.g., "ANNUAL", "HOURLY", "MONTHLY")
- `computed_annual_min`: `DECIMAL(12, 2)` (Normalized annual USD minimum, Indexed)
- `computed_annual_max`: `DECIMAL(12, 2)` (Normalized annual USD maximum, Indexed)
- `equity_min`: `DECIMAL(12, 2)` (Stock/option grant value in USD, Nullable)
- `equity_max`: `DECIMAL(12, 2)` (Nullable)
- `location_normalized`: `VARCHAR(150)` (Indexed)
- `col_tier`: `VARCHAR(50)` (Cost-of-living tier, e.g. "TIER_1")
- `created_at`: `TIMESTAMP WITH TIME ZONE` (default `now()`)

#### Table: `compensation_benchmarks`
Materialized summary aggregates updated periodically.
- `id`: `UUID` (PK, default `uuid_generate_v4()`)
- `role_type`: `VARCHAR(100)` (Indexed)
- `location_normalized`: `VARCHAR(150)` (Indexed)
- `skill_id`: `UUID` (FK referencing `skills_taxonomy.id`, ON DELETE CASCADE, Nullable, Indexed)
- `p25_salary`: `DECIMAL(12, 2)`
- `p50_salary`: `DECIMAL(12, 2)`
- `p75_salary`: `DECIMAL(12, 2)`
- `sample_size`: `INTEGER`
- `updated_at`: `TIMESTAMP WITH TIME ZONE` (default `now()`)

### Indexes & Migrations
- `idx_comp_records_geo_salary`: Combined index on `(location_normalized, computed_annual_max)`.
- `idx_comp_benchmarks_lookup`: Composite index on `(role_type, location_normalized, skill_id)`.
- **Alembic Migration**: `create_compensation_intelligence_tables.py` creating the schemas and tables.

---

## 5. API Endpoints

### `GET /api/v2/market/compensation`
Retrieves percentile benchmarks based on search filters.
- **Authentication**: Required (JWT, Scope: `user`)
- **Query Parameters**:
  - `role_type`: "Backend Engineer" (Required)
  - `location`: "San Francisco, CA" or "Remote" (Optional)
  - `skill_ids`: Comma-separated list of UUIDs (Optional)
- **Response (200 OK)**:
```json
{
  "query": {
    "role_type": "Backend Engineer",
    "location": "San Francisco, CA",
    "skills": ["Python"]
  },
  "benchmarks": {
    "p25_salary": 165000.00,
    "p50_salary": 195000.00,
    "p75_salary": 230000.00,
    "currency": "USD",
    "sample_size": 42,
    "updated_at": "2026-06-09T01:00:00Z"
  },
  "skill_premiums": [
    {
      "skill_name": "Kubernetes",
      "p50_premium_percentage": 0.08,
      "p50_premium_value": 15600.00
    }
  ]
}
```

### `GET /api/v2/market/compensation/stats`
Retrieves high-level market compensation trend insights.
- **Authentication**: Required (JWT, Scope: `user`)
- **Response (200 OK)**:
```json
{
  "market_trends": {
    "quarterly_drift_percentage": 0.012,
    "highest_paying_skills": [
      { "skill_name": "Rust", "avg_salary": 215000.00 },
      { "skill_name": "LangGraph", "avg_salary": 208000.00 }
    ],
    "hottest_markets": [
      { "location": "Remote", "avg_salary": 185000.00 },
      { "location": "New York, NY", "avg_salary": 192000.00 }
    ]
  }
}
```

---

## 6. Domain Models

```python
from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from typing import Optional, List

class SkillPremium(BaseModel):
    skill_name: str
    p50_premium_percentage: float
    p50_premium_value: float

class SalaryBenchmark(BaseModel):
    p25_salary: float
    p50_salary: float
    p75_salary: float
    currency: str = Field("USD", max_length=3)
    sample_size: int
    updated_at: datetime

class CompensationQueryResponse(BaseModel):
    query: dict
    benchmarks: SalaryBenchmark
    skill_premiums: List[SkillPremium]
```

---

## 7. Services

### `CompensationExtractionService`
Extracts raw salary strings from job texts.
- `extract_salary(job_id: UUID, text: str) -> Optional[dict]`: Runs regex parses. Identifies numbers, intervals, and currencies.
- `normalize_range(raw_min: float, raw_max: float, interval: str, currency: str) -> dict`: Converts intervals to annual figures and converts non-USD currencies using external exchange rates.

### `LocationNormalizationService`
Normalizes geographic locations.
- `normalize_location(location_str: str) -> dict`: Standardizes names and maps them to cost-of-living tiers (TIER_1, TIER_2, etc.).

### `BenchmarkCalculatorService`
Runs statistical models on stored compensation records.
- `recalculate_benchmarks() -> None`: Queries `compensation_records`, computes P25, P50, and P75 percentiles, and populates `compensation_benchmarks`.

---

## 8. Events

### Event: `market.compensation_benchmark.updated`
- **Producer**: `BenchmarkCalculatorService`
- **Consumer**: `intelligence-synthesis-service`
- **Payload Schema**:
```json
{
  "event_id": "ab12cd34-ef56-78gh-90ij-klmnopqrstuv",
  "event_type": "market.compensation_benchmark.updated",
  "timestamp": "2026-06-09T01:00:00Z",
  "payload": {
    "role_type": "Backend Engineer",
    "location": "San Francisco, CA",
    "p50_salary": 195000.00,
    "sample_size": 42
  }
}
```

---

## 9. Background Jobs
- **`scheduled_compensation_aggregation_job`**: Runs weekly. Iterates over `compensation_records` to compute rolling salary benchmarks and updates the `compensation_benchmarks` table.
- **`exchange_rate_refresh_job`**: Daily task updates the currency translation index from a public bank API.

---

## 10. Acceptance Criteria

### Salary Extraction Scenario
- **Given**: A newly crawled job description contains: "Salary range: $140,000 to $180,000 per year plus equity."
- **When**: The `CompensationExtractionService` processes the text.
- **Then**: It extracts min=140000, max=180000, currency="USD", interval="ANNUAL", writes to `compensation_records`, and calculates normalized bounds.

### Outlier Filtering Scenario
- **Given**: A job description contains: "Salary: $100 - $200,000,000 per year."
- **When**: The normalization pipeline checks the range.
- **Then**: It identifies the maximum bounds as an outlier (greater than $1,000,000 limit) and drops the record, logging a schema validation warning.

---

## 11. Edge Cases
- **Exaggerated Ranges**: Some jobs state: "Salary: $50,000 - $350,000". If the ratio of Max to Min salary exceeds $3.0$, flag the posting for review and exclude it from baseline benchmark calculations to avoid skewing percentiles.
- **Currency Translations**: For roles based in London offering "£80,000", translate value to USD using current daily exchange rates, preserving the original currency key for audit trails.
- **Lack of Local Data**: If SF has 50 samples but Boise, ID has only 2, return regional state aggregates or COL Tier aggregates instead of Boise-only data.

---

## 12. Test Requirements
- **Regex Parsing Unit Tests**: Test the parser against 50 different variations of salary text formats (ranges, hourly rates, word formatting) to verify parsing accuracy.
- **Math Distribution Tests**: Assert that computed percentiles mathematically match expected results on a fixed test vector.

---

## 13. Dependencies
- **Direct Blockers**:
  - [Multi-Source Job Ingestion (F2.1)](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/feature-specs/multi-source-job-ingestion.md)
- **Downstream Beneficiaries**:
  - [Opportunity Intelligence (F2.7)](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/feature-specs/opportunity-intelligence.md)
  - [Intelligence Agent (F3.4)](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/DEPENDENCY_GRAPH.md)
