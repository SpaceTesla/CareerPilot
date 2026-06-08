# Feature Specification: NLP Skill Extraction (F2.3)

## 1. Purpose
The `NLP Skill Extraction` feature parses unstructured text (job descriptions and user resumes) to identify and extract professional skills, technologies, and certifications. It resolves textual variations and spelling differences to canonical skill entities stored in a central system taxonomy. This structural data forms the semantic foundation for skill-based matching and market analysis across CareerPilot.

---

## 2. User Value
For users, skill descriptions in profiles and job ads are highly fragmented. One posting might require "ReactJS," another "React.js," and a third "React". 
This feature normalizes these representations into a single canonical skill node: `React`. 
In the **Career Intelligence Compounding Loop** (defined in [careerpilot_v2.md](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/careerpilot_v2.md)), accurate skill extraction enables the [Position Delta Engine (F1.8)](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/DEPENDENCY_GRAPH.md) to calculate exact technical gaps between a user's profile and their target roles without failing due to syntax discrepancies or vocabulary mismatches.

---

## 3. Requirements
- **Skill Taxonomy**: Maintain a central hierarchical dictionary of skills, categorizing them into frameworks, languages, databases, tools, paradigms, and soft skills.
- **spaCy NLP Pipeline**: Integrate a specialized spaCy Named Entity Recognition (NER) pipeline or custom entity ruler trained to extract technical terms from raw text blocks.
- **LLM-Based Extraction Fallback**: For complex context validation (e.g., distinguishing between "experienced in Go" and "willing to go to office"), utilize structured LLM JSON outputs for edge cases.
- **Skill Confidence Scoring**: Score extracted skills based on grammatical positioning, frequency, and source validation (e.g., a skill explicitly listed under a "Requirements" header yields a higher confidence score than one in a "Nice-to-Have" list).
- **Skill Alias Resolution**: Automatically resolve synonyms and acronyms (e.g. "Amazon Web Services" -> "AWS", "MS Sql Server" -> "Microsoft SQL Server").
- **Technology Normalization**: Group related technologies (e.g., version control "Git" handles references to "GitHub" or "GitLab" where appropriate, while keeping entities distinct when necessary).
- **Evaluation Dataset**: Establish a golden dataset of 100 job descriptions and 50 resumes with manually annotated skills to measure extraction accuracy.
- **Extraction Benchmarking Suite**: Automatic evaluation runner that calculates pipeline F1-score against the golden dataset upon code modification.
- **Extraction Metrics**: Monitor the number of unknown skills, extraction latency, pipeline throughput, and LLM token usage.
- **Extraction Admin Tools**: Admin interface endpoints to curate unknown extracted tokens, merge aliases, and append new nodes to the taxonomy.

---

## 4. Database Changes

The schema models the central taxonomy, skill-posting relationships, and user-profile skill linkages.

### Schema Definitions

#### Table: `skills_taxonomy`
The primary authority table for valid, standardized skills.
- `id`: `UUID` (PK, default `uuid_generate_v4()`)
- `canonical_name`: `VARCHAR(100)` (Unique, Indexed, e.g. "React", "Python", "Kubernetes")
- `category`: `VARCHAR(50)` (e.g. "Language", "Framework", "Database", "Infrastructure", "Methodology")
- `subcategory`: `VARCHAR(50)` (Nullable, e.g. "Frontend", "Backend", "NoSQL", "DevOps")
- `aliases`: `VARCHAR(150)[]` (Array of synonyms/variations: `['ReactJS', 'React.js', 'React-JS']`)
- `popularity_score`: `DECIMAL(5, 2)` (Calculated daily frequency percentage, default `0.00`)
- `created_at`: `TIMESTAMP WITH TIME ZONE` (default `now()`)
- `updated_at`: `TIMESTAMP WITH TIME ZONE` (default `now()`)

#### Table: `job_posting_skills`
Maps extracted skills back to the core job posting.
- `id`: `UUID` (PK, default `uuid_generate_v4()`)
- `job_posting_id`: `UUID` (FK referencing `job_postings.id`, ON DELETE CASCADE)
- `skill_id`: `UUID` (FK referencing `skills_taxonomy.id`, ON DELETE CASCADE)
- `extraction_method`: `VARCHAR(50)` (e.g., "SPACY_NER", "RULE_RULER", "LLM_FALLBACK")
- `confidence_score`: `DECIMAL(4, 3)` (0.000 to 1.000)
- `context_sentence`: `TEXT` (Snippet containing the extracted skill for contextual proof)
- `created_at`: `TIMESTAMP WITH TIME ZONE` (default `now()`)

#### Table: `profile_skills`
Tracks a user's verified skills extracted from their resume or manually added.
- `id`: `UUID` (PK, default `uuid_generate_v4()`)
- `profile_id`: `UUID` (FK referencing `career_profiles.id`, ON DELETE CASCADE)
- `skill_id`: `UUID` (FK referencing `skills_taxonomy.id`, ON DELETE CASCADE)
- `extraction_method`: `VARCHAR(50)`
- `confidence_score`: `DECIMAL(4, 3)`
- `years_of_experience`: `INTEGER` (Inferred from resume history, Nullable)
- `last_used_at`: `DATE` (Inferred from experience timeline, Nullable)
- `created_at`: `TIMESTAMP WITH TIME ZONE` (default `now()`)

#### Table: `skill_relationships`
Describes relationship links inside the taxonomy to power graph lookups.
- `parent_skill_id`: `UUID` (FK referencing `skills_taxonomy.id`, ON DELETE CASCADE)
- `child_skill_id`: `UUID` (FK referencing `skills_taxonomy.id`, ON DELETE CASCADE)
- `relationship_type`: `VARCHAR(50)` (e.g., "COMPATIBLE_WITH", "SPECIALIZATION_OF", "DEPENDS_ON")
- `confidence_score`: `DECIMAL(4, 3)`
- Primary Key is composite: `(parent_skill_id, child_skill_id)`

### Indexes & Migrations
- `idx_skills_taxonomy_name`: Unique index on `canonical_name`.
- `idx_job_skills_mapping`: Composite index on `(job_posting_id, skill_id)` to speed up matching queries.
- `idx_profile_skills_mapping`: Composite index on `(profile_id, skill_id)`.
- **Alembic Migration**: `create_nlp_skill_extraction_tables.py` creating the tables and indexes.

---

## 5. API Endpoints

### `POST /api/v2/market/skills/extract`
Parses raw text to identify skills. Used on resumes and raw postings.
- **Authentication**: Required (JWT, Scope: `user` or `admin`)
- **Request Payload**:
```json
{
  "text": "We are seeking a backend developer experienced with Python, FastAPI, and Postgres. Familiarity with AWS and Kubernetes is a plus."
}
```
- **Response (200 OK)**:
```json
{
  "extracted_skills": [
    {
      "canonical_name": "Python",
      "category": "Language",
      "confidence_score": 1.0,
      "context_sentence": "We are seeking a backend developer experienced with Python, FastAPI, and Postgres.",
      "alias_resolved_from": "Python"
    },
    {
      "canonical_name": "FastAPI",
      "category": "Framework",
      "confidence_score": 0.98,
      "context_sentence": "We are seeking a backend developer experienced with Python, FastAPI, and Postgres.",
      "alias_resolved_from": "FastAPI"
    },
    {
      "canonical_name": "PostgreSQL",
      "category": "Database",
      "confidence_score": 0.95,
      "context_sentence": "We are seeking a backend developer experienced with Python, FastAPI, and Postgres.",
      "alias_resolved_from": "Postgres"
    }
  ]
}
```

### `POST /api/v2/market/skills/alias/resolve`
Resolves custom text strings to their taxonomy targets.
- **Authentication**: Required (JWT, Scope: `admin` or `operator`)
- **Request Payload**:
```json
{
  "raw_skill_name": "ReactJS"
}
```
- **Response (200 OK)**:
```json
{
  "raw_skill_name": "ReactJS",
  "resolved": true,
  "skill": {
    "id": "e2f3a4b5-6c7d-8e9f-0123-456789abcdef",
    "canonical_name": "React",
    "category": "Framework",
    "aliases": ["ReactJS", "React.js"]
  }
}
```

### `GET /api/v2/market/skills/eval/report`
Fetches precision, recall, and F1 statistics calculated against the golden test set.
- **Authentication**: Required (JWT, Scope: `admin`)
- **Response (200 OK)**:
```json
{
  "evaluation_timestamp": "2026-06-09T01:00:00Z",
  "overall_f1_score": 0.925,
  "precision": 0.941,
  "recall": 0.910,
  "by_category": {
    "Language": 0.97,
    "Framework": 0.93,
    "Database": 0.95,
    "Infrastructure": 0.88
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

class CanonicalSkill(BaseModel):
    id: UUID
    canonical_name: str
    category: str
    subcategory: Optional[str] = None
    aliases: List[str]
    popularity_score: float

class ExtractedSkill(BaseModel):
    canonical_name: str
    category: str
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    context_sentence: str
    alias_resolved_from: str

class SkillExtractionRequest(BaseModel):
    text: str
```

---

## 7. Services

### `SkillExtractionService`
Orchestrates pipeline execution, managing spaCy NER models and routing to LLMs when ambiguity limits confidence.
- `extract_skills_from_text(text: str) -> list[ExtractedSkill]`: Passes text to spaCy, resolves taxonomy tags, evaluates confidence, and processes unmatched tokens.
- `process_llm_fallback(text: str, ambiguous_tokens: list[str]) -> list[ExtractedSkill]`: Uses structured LLM prompt mapping to categorize and confirm ambiguous phrases.

### `TaxonomyResolutionService`
Keeps lookups fresh.
- `resolve_alias(raw_string: str) -> Optional[CanonicalSkill]`: Normalizes input strings (regex cleaning, lowercasing) and performs dictionary checks.
- `add_new_skill(name: str, category: str, aliases: list[str]) -> CanonicalSkill`: Appends details to `skills_taxonomy` and invalidates cached lookup objects.

### `SkillBenchmarkService`
Compares current models.
- `run_benchmark() -> dict`: Executes the pipeline on `eval_datasets`, compares output lists to labeled values, and updates validation logs.

---

## 8. Events

### Event: `market.skill.extracted`
- **Producer**: `SkillExtractionService`
- **Consumer**: `skill-trend-engine`, `intelligence-synthesis-service`
- **Payload Schema**:
```json
{
  "event_id": "4b3c2d1e-0f1e-2d3c-4b5a-6f7e8d9c0b1a",
  "event_type": "market.skill.extracted",
  "timestamp": "2026-06-09T02:02:10Z",
  "payload": {
    "source_type": "JOB_POSTING",
    "source_id": "1a2b3c4d-5e6f-7a8b-9c0d-1e2f3g4h5i6j",
    "skills": [
      {
        "skill_id": "e2f3a4b5-6c7d-8e9f-0123-456789abcdef",
        "canonical_name": "React",
        "confidence": 0.99
      }
    ]
  }
}
```

---

## 9. Background Jobs
- **`batch_job_skills_extraction_job`**: Daily cron processing newly scraped job postings that lack extracted skill records.
- **`batch_profile_skills_extraction_job`**: Triggered on profile creation or resume upload to parse experiences.
- **`taxonomy_popularity_refresh_job`**: Runs weekly. Aggregates occurrence frequency of skills across the active jobs database to update `popularity_score` in the taxonomy.

---

## 10. Acceptance Criteria

### High-Confidence NER Extraction Scenario
- **Given**: The skills taxonomy contains "Python" and "PostgreSQL" (with alias "Postgres").
- **When**: The extraction pipeline processes the text: "Experienced Python backend engineer using Postgres."
- **Then**: It extracts "Python" and "PostgreSQL" with confidence > 0.90, maps them to their taxonomy IDs, and outputs the context sentences.

### Ambiguity Resolution (Go vs. go) Scenario
- **Given**: The taxonomy contains the language "Go" (with alias "Golang").
- **When**: The pipeline processes: "Candidates must be willing to go to Chicago office."
- **Then**: The spaCy rule-matcher identifies "go" as a verb, flags it as low-confidence/non-entity, filters it out, and avoids mapping a "Go" programming language requirement to the job posting.

---

## 11. Edge Cases
- **Common Word Overlap**: Words like "Spring" (Java framework) or "Chef" (infrastructure tool) are common nouns. Grammatical parsing must verify part-of-speech context (e.g. capitalizing or checking if surrounding words refer to other software like "Java", "Hibernate" or "Puppet") to set confidence levels.
- **Brand New Technologies**: If a newly released tool (e.g., "Mojo" or "Bun") appears in JDs, it won't exist in the taxonomy. The extraction engine flags it as "UNCLASSIFIED_TECH" with a confidence score and dumps it to a queue for admin verification rather than throwing errors.
- **Hyphen/Spacing Discrepancies**: "Node.js", "NodeJS", "Node JS" must all normalize to the same canonical Node.js record. This requires robust regex stripping (removing spaces, periods, dashes) during alias matching.

---

## 12. Test Requirements
- **F1 Accuracy Test**: Build unit tests verifying that the NLP service retains > 0.90 F1 score on the validation suite.
- **Alias Loop Protection**: Ensure taxonomy updates do not permit cyclic aliases (e.g., alias of "React" is "ReactJS", and alias of "ReactJS" is "React").

---

## 13. Dependencies
- **Direct Blockers**:
  - [Job Market Data Foundation (F1.5)](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/DEPENDENCY_GRAPH.md)
- **Downstream Beneficiaries**:
  - [Company Intelligence (F2.4)](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/feature-specs/company-intelligence.md)
  - [Ghost Posting Detection (F2.5)](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/feature-specs/ghost-posting-detection.md)
  - [Opportunity Intelligence (F2.7)](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/feature-specs/opportunity-intelligence.md)
  - [Knowledge Graph (F7.1)](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/feature-specs/knowledge-graph.md)
