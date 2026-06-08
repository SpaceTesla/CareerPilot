# Feature Specification: ATS API Integrations

## 1. Purpose
The ATS API Integrations feature is the primary and most efficient tier of the CareerPilot Three-Tier Execution Engine. When executing an application, the system abstracts the differences between major Applicant Tracking Systems (ATS)—specifically Greenhouse, Lever, and Ashby—and attempts to submit the candidate's structured profile data and files directly to their public job application endpoints using high-speed, structured HTTP requests.

This programmatic submission method bypasses the need for UI rendering, resulting in high reliability, reduced resource consumption, and immediate API-driven confirmation.

---

## 2. User Value
Directly supports the execution layer of the **Career Intelligence Compounding Loop**.
- **Compounding Loop Connection**: Rapid, programmatic submissions generate immediate API confirmation hashes and structure. This provides clean timestamping and metadata formatting for the Outcome Memory System, enabling precise conversion tracking.
- **User Benefit**: Applications are submitted in milliseconds with 100% data formatting accuracy. The candidate receives immediate verification that their application is in the employer's database without waiting for web browsers to load.

---

## 3. Requirements
- **ATS Abstraction Layer**: Build a unified interface to process applicant submissions regardless of the target ATS system.
- **Greenhouse Board API Integration**: Implement client to POST multi-part application payloads to `https://api.greenhouse.io/v1/boards/{board_token}/jobs/{job_id}/apply`.
- **Lever Apply API Integration**: Implement client to POST multi-part payloads to `https://api.lever.co/v1/jobs/{job_id}/apply`.
- **Ashby Job Board API Integration**: Implement client to POST structured JSON payloads to Ashby's candidate submission endpoints.
- **Authentication Handling**: Manage authentication mechanisms for target companies requiring API authorization or candidate-facing token checks.
- **Error Handling & Mapping**: Capture and standardize raw ATS API error codes (e.g., duplicate email, validation failed, missing files) into CareerPilot system errors.
- **Audit Logging**: Store every HTTP request, response header, response payload, and roundtrip duration for debug purposes.
- **Metrics Integration**: Emit Prometheus counters for submission successes and failures partitioned by ATS type.

---

## 4. Database Changes

### Table: `ats_audit_logs`
Logs detailed HTTP transaction details for direct API submissions.

| Field Name | Data Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | UUID | PRIMARY KEY, DEFAULT gen_random_uuid() | Unique identifier. |
| `application_id` | UUID | FOREIGN KEY references `job_applications(id)`, NOT NULL | Target job application. |
| `ats_type` | VARCHAR(50) | NOT NULL | `GREENHOUSE`, `LEVER`, `ASHBY`. |
| `request_url` | TEXT | NOT NULL | HTTP URL targeted. |
| `request_headers` | JSONB | NOT NULL | Request headers (sensitive tokens masked). |
| `request_body` | JSONB | NOT NULL | Parsed form fields or JSON payload sent. |
| `response_status` | INTEGER | NOT NULL | HTTP status code returned (e.g., 200, 400, 500). |
| `response_body` | TEXT | NULLABLE | Raw response content. |
| `latency_ms` | INTEGER | NOT NULL | Execution roundtrip duration. |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | Event timestamp. |

### Indexes
- `idx_ats_logs_app_id` on `ats_audit_logs(application_id)`
- `idx_ats_logs_status` on `ats_audit_logs(response_status)`

---

## 5. API Endpoints
These integrations are backend services invoked by Temporal workers. There are no public user-facing endpoints. However, an internal administration endpoint is provided for testing connectors.

### Admin/Test ATS Submission
- **HTTP Method**: `POST`
- **Route**: `/api/v2/admin/ats/test-submit`
- **Request Body (JSON)**:
```json
{
  "ats_type": "GREENHOUSE",
  "board_token": "acme",
  "job_id": "123456",
  "profile_data": {
    "first_name": "Jane",
    "last_name": "Doe",
    "email": "jane.doe@example.com",
    "resume_url": "https://storage.careerpilot.io/resumes/jane_resume.pdf"
  }
}
```
- **Response Payload (JSON)**:
```json
{
  "success": true,
  "status_code": 200,
  "payload_sent": {},
  "raw_response": "{\"success\": \"Application created.\"}",
  "latency_ms": 345
}
```
- **HTTP Status Codes**:
  - `200 OK`: Successful test submission.
  - `400 Bad Request`: Validation failure on candidate profile.
  - `401 Unauthorized`: Not authenticated.
  - `403 Forbidden`: User is not a system administrator.

---

## 6. Domain Models

```python
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

class CandidateSubmissionPayload(BaseModel):
    first_name: str
    last_name: str
    email: str
    phone: Optional[str] = None
    resume_bytes: bytes = Field(..., description="Binary content of the resume PDF")
    resume_filename: str = Field("resume.pdf")
    cover_letter_text: Optional[str] = None
    linkedin_url: Optional[str] = None
    github_url: Optional[str] = None
    custom_answers: Dict[str, Any] = Field(default_factory=dict)

class ATSSubmissionResult(BaseModel):
    success: bool
    status_code: int
    confirmation_id: Optional[str] = None
    error_message: Optional[str] = None
    raw_response: str
    latency_ms: int
```

---

## 7. Services

### Class: `ATSIntegrationService`
Acts as the central gateway implementing the strategy pattern. It detects the target ATS, delegates to the correct client, and audits the results.

- **Method**: `submit`
  - **Inputs**:
    - `ats_type` (str): Type of ATS.
    - `board_token` (str): Target company board sub-identifier.
    - `job_id` (str): Specific vacancy code.
    - `payload` (CandidateSubmissionPayload): Enriched applicant data.
    - `application_id` (str): Reference database key for logging.
  - **Return Type**: `ATSSubmissionResult`
  - **Responsibilities**:
    - Instantiates correct connector (`GreenhouseConnector`, `LeverConnector`, or `AshbyConnector`).
    - Maps the generalized `CandidateSubmissionPayload` to the ATS-specific multipart/JSON structure.
    - Executes the HTTP request with timeout protection (30s).
    - Measures roundtrip latency.
    - Writes execution logs to `ats_audit_logs`.
    - Returns standardized `ATSSubmissionResult` to the caller.

---

## 8. Events
ATS Integration components publish observability metrics rather than standalone domain events. The events are handled at the `ApplicationWorkflow` layer.

---

## 9. Background Jobs
No scheduled cron jobs exist. Work runs purely on demand inside Temporal activities.

---

## 10. Acceptance Criteria
- **Scenario**: Successful Greenhouse API application submission.
  - **Given**: Valid applicant data and an active job board vacancy token.
  - **When**: `ATSIntegrationService.submit` is called for `GREENHOUSE`.
  - **Then**: An HTTP multipart request is sent to Greenhouse API, returns status code 200, and returns `success=True` with a confirmation ID.
- **Scenario**: Submission fails due to duplicate email.
  - **Given**: The candidate has previously applied for this role.
  - **When**: Submitting to Lever API.
  - **Then**: Lever returns status code 400 with a duplicate email error, and the service maps this to a system error `DUPLICATE_APPLICATION`.

---

## 11. Edge Cases
- **WAF / Cloudflare Rate Limiting**: The destination board is protected by Cloudflare and blocks raw Python HTTP clients.
  - **Resolution**: Custom headers (e.g., mimicking modern browser User-Agents) are appended. If blocking persists, the connector raises a retryable exception to handoff execution to `Browser Fallback Execution`.
- **Form Field Validation Changes**: The employer changes field formats on the ATS page, causing the API POST to reject the input with validation errors.
  - **Resolution**: The service logs the response body, marks the submission as failed with a validation error flag, and triggers the `Deterministic Form Execution` engine to scrape and parse the updated form schema.

---

## 12. Test Requirements
- **Unit Tests**: Verify the mappings of Pydantic model payloads to HTTP multipart payloads for each individual connector class.
- **Integration Tests**: Run the submission code against mocked HTTP servers (using `responses` or `pytest-mock`) returning typical success/error patterns for Greenhouse, Lever, and Ashby.

---

## 13. Dependencies
- **[F1.1: Project Setup & Architecture](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/feature-specs/project-setup-architecture.md)**: Establishes HTTP client structures.

---
