# Feature Specification: Resume Import & Profile Sync

## 1. Purpose
This feature automates candidate onboarding by extracting structured professional profiles from uploaded unstructured resume documents (PDF, DOCX). It provides binary text extraction, text normalization pipelines, LLM-based structured profiling prompt injection, and a profile sync flow that updates the core profile domain tables. It also generates confidence metrics for the extraction results, enabling users to verify and correct details before committing them.

For the structural foundations of user profiles, see [career-profile-domain.md](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/feature-specs/career-profile-domain.md). For broader product context, refer to [careerpilot_v2.md](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/careerpilot_v2.md).

## 2. User Value
Onboarding onto career sites is notoriously tedious, often requiring users to upload a resume and then manually re-enter their entire work history. By delivering an intelligent parser, CareerPilot reduces this friction to a single drag-and-drop file upload. This instantly populates the user's Profile Context, generating immediate value through their Career Health Score without manual data entry.

## 3. Requirements
- **Multi-Format Extraction**: Support text extraction from PDF (using pdfplumber/PyPDF) and DOCX (using python-docx).
- **Text Normalization**: Clean and normalize extracted text (remove double spaces, resolve non-UTF-8 characters, standard headers reconstruction).
- **LLM Structured Extraction**: Use structured outputs from LLMs (e.g. OpenAI's `response_format` or Pydantic validation) to map raw text into structured schema blocks (skills, experiences, education, projects).
- **Confidence Scoring**: Compute a numeric confidence score (0.0 to 1.0) based on parsing accuracy, missing dates, and LLM self-evaluations.
- **Sync Workflow (Gate)**: Store parsed profiles in a temporary workspace, presenting them to the user for review before updating the active career profile tables.

## 4. Database Changes

### `uploaded_resumes`
Stores the file metadata and raw/parsed extraction buffers before syncing.
- `id`: `UUID` (Primary Key, Default: `uuid_generate_v4()`)
- `profile_id`: `UUID` (Foreign Key referencing `career_profiles.id` ON DELETE CASCADE, Indexed, Not Null)
- `file_name`: `VARCHAR(255)` (Not Null)
- `file_size`: `INTEGER` (Not Null) - Size in bytes
- `content_type`: `VARCHAR(100)` (Not Null)
- `raw_text`: `TEXT` (Not Null) - Extracted clean text content
- `parsed_payload`: `JSONB` (Nullable) - JSON matching the structure of `ProfileUpdate`
- `confidence_score`: `NUMERIC(3, 2)` (Nullable) - Score between 0.00 and 1.00
- `is_synced`: `BOOLEAN` (Default: `False`, Not Null)
- `created_at`: `TIMESTAMP WITH TIME ZONE` (Default: `NOW()`, Not Null)

### Indexes and Migrations
- Foreign key index on `uploaded_resumes.profile_id`.
- Alembic migration `V2026_06_09_0002_create_resume_tables.py` will handle creation.

## 5. API Endpoints

### `POST /api/v2/profile/upload`
Uploads a resume file, extracts raw text, runs LLM parsing, saves metadata, and returns the parsed payload with confidence details.
- **Request Content Type**: `multipart/form-data`
- **Request Parameters**:
  - `file`: Binary file (PDF or DOCX, max size 5MB)
- **Response Body (200 OK)**:
  ```json
  {
    "resume_id": "c138fd90-e5bf-4078-abf7-41804fcd7c12",
    "confidence_score": 0.89,
    "parsed_data": {
      "headline": "Senior Software Engineer",
      "summary": "Full stack developer with focus on python backend services.",
      "location": "Boston, MA",
      "skills": [
        {
          "skill_name": "Python",
          "years_experience": 4.5,
          "proficiency": "EXPERT"
        }
      ],
      "experiences": [
        {
          "company_name": "Acme Inc",
          "job_title": "Backend Engineer",
          "start_date": "2022-01-15",
          "end_date": "2026-05-30",
          "description": "Built asynchronous worker systems using Celery.",
          "is_current": false
        }
      ],
      "education": [],
      "projects": []
    }
  }
  ```

### `POST /api/v2/profile/sync-resume`
Applies the approved parsed data snapshot to the active profile context, triggering a new version.
- **Request Headers**: JWT Bearer Token
- **Request Body**:
  ```json
  {
    "resume_id": "c138fd90-e5bf-4078-abf7-41804fcd7c12",
    "override_data": {
      "headline": "Senior Backend Engineer",
      "summary": "Full stack developer with focus on python backend services.",
      "location": "Boston, MA",
      "skills": [
        {
          "skill_name": "Python",
          "years_experience": 5.0,
          "proficiency": "EXPERT"
        }
      ],
      "experiences": [
        {
          "company_name": "Acme Inc",
          "job_title": "Backend Engineer",
          "start_date": "2022-01-15",
          "end_date": "2026-05-30",
          "description": "Built asynchronous worker systems using Celery.",
          "is_current": false
        }
      ],
      "education": [],
      "projects": []
    }
  }
  ```
- **Response Body (200 OK)**:
  ```json
  {
    "status": "success",
    "profile_version": 2,
    "message": "Career profile synced successfully."
  }
  ```

## 6. Domain Models

### Pydantic Schemas

```python
from pydantic import BaseModel, Field
from uuid import UUID
from typing import Optional
from decimal import Decimal
from careerpilot.schemas.profile import ProfileUpdate # Imports fields from profile schema

class ResumeUploadResponse(BaseModel):
    resume_id: UUID
    confidence_score: Decimal = Field(..., max_digits=3, decimal_places=2)
    parsed_data: ProfileUpdate

class ResumeSyncRequest(BaseModel):
    resume_id: UUID
    override_data: ProfileUpdate
```

## 7. Services

### `ResumeExtractorService`
- **Responsibilities**: Validates file types, reads raw bytes, uses helper packages to output plain text, and runs normalization algorithms.
- **Methods**:
  - `extract_text(file_bytes: bytes, file_name: str) -> str`: Decides on parser (PDF vs DOCX) and returns raw text string.
  - `normalize_text(text: str) -> str`: Strips whitespace, standardizes headers, sanitizes text input.

### `LLMParserService`
- **Responsibilities**: Formulates prompts, coordinates LLM API calls, enforces schema-compliant JSON structures, and calculates confidence.
- **Methods**:
  - `parse_resume_text(normalized_text: str) -> tuple[dict, float]`: Connects to LLM provider using structured tools outputs. Returns the parsed JSON payload and confidence metrics.

### `ProfileSyncService`
- **Responsibilities**: Orchestrates the sync workflow, updating profile tables and marking the resume as synced.
- **Methods**:
  - `sync(user_id: UUID, resume_id: UUID, final_data: ProfileUpdate) -> int`: Invokes `ProfileService.update_profile` within a database transaction, updates `uploaded_resumes` `is_synced` status to true. Returns new profile version ID.

## 8. Events

- **`resume.uploaded`**:
  - **Producer**: `/api/v2/profile/upload` route handler.
  - **Consumers**: None (for synchronous API); if scaled to async, a background extraction worker consumes this.
  - **Payload**:
    ```json
    {
      "event_id": "761da69d-2101-4475-be7a-b9c1bc32c668",
      "event_type": "resume.uploaded",
      "timestamp": "2026-06-09T02:04:18Z",
      "data": {
        "resume_id": "c138fd90-e5bf-4078-abf7-41804fcd7c12",
        "file_name": "resume.pdf",
        "file_size": 204800
      }
    }
    ```
- **`profile.synced`**:
  - **Producer**: `ProfileSyncService.sync`
  - **Consumers**: `CareerHealthScoreEngine`, `PositionDeltaEngine`.
  - **Payload**:
    ```json
    {
      "event_id": "b3e0988c-ff5d-45db-953e-2b1d3032bdcc",
      "event_type": "profile.synced",
      "timestamp": "2026-06-09T02:04:18Z",
      "data": {
        "user_id": "e229c9bb-36db-4876-b9a6-d6b797cc963a",
        "resume_id": "c138fd90-e5bf-4078-abf7-41804fcd7c12",
        "profile_version": 2
      }
    }
    ```

## 9. Background Jobs
No background cron jobs are run. The parsing is done synchronously inside the FastAPI request loop (with standard gateway timeout configs set to 30s to accommodate LLM latency).

## 10. Acceptance Criteria

- **Scenario: PDF Parsing Execution**
  - **Given** a valid UTF-8 text-based PDF resume,
  - **When** calling `POST /api/v2/profile/upload`,
  - **Then** return HTTP 200 with extracted entities, matching experience dates and names, and save metadata.
- **Scenario: Unsupported File Upload**
  - **Given** a `.png` file,
  - **When** calling upload endpoint,
  - **Then** return HTTP 400 Bad Request indicating invalid extension.
- **Scenario: Synced Profile**
  - **Given** a parsed resume output,
  - **When** calling `POST /api/v2/profile/sync-resume` with user updates,
  - **Then** write changes to `career_profiles` and child entities, mark the upload record `is_synced: true`, and trigger profile version creation.

## 11. Edge Cases
- **Image-Only (Scanned) PDFs**: If the PDF extractor returns fewer than 50 characters of text, the system aborts execution and returns an HTTP 422 Unprocessable Entity error: "Scanned or empty document detected. Please provide a text-based resume."
- **LLM Timeout**: If the LLM call times out (e.g. over 15s), the API returns HTTP 504 Gateway Timeout. A future iteration will fall back to an async Celery worker routing state.
- **Encrypted/Password Protected Files**: If the file is encrypted, the extraction library throws a decryption error. The system catches this, returns HTTP 400 with "File is encrypted or password-protected".

## 12. Test Requirements
- **Unit Tests**:
  - Test binary readers (`pdfplumber` and `docx` integrations) using fixture files.
  - Test text normalization helper (removes control characters, standardizes vertical spacing).
- **Integration Tests**:
  - Mock the LLM service responses to verify the full parsing flow from API upload to database storage.
  - Assert that calling Sync on an already-synced resume ID returns an HTTP 409 Conflict.

## 13. Dependencies
This feature depends on [career-profile-domain.md](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/feature-specs/career-profile-domain.md).
There are no Epic 1 features that depend directly on this feature. It serves as an onboarding input shortcut to the profile tables.
