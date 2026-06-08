# Feature Specification: Deterministic Form Execution

## 1. Purpose
The Deterministic Form Execution feature represents the second tier of the CareerPilot Three-Tier Execution Engine. It targets enterprise job portals that do not offer open candidate-facing APIs (such as Workday, iCIMS, and Taleo). Rather than using slow, resource-heavy browser automation, this engine scrapes the application form structure, maps the HTML form inputs to normalized user profile attributes, and submits the form programmatically via network requests (HTTP POST multipart/form-data) using a pre-cached JSON form schema.

This provides a middle-ground execution path: significantly faster and more reliable than browser automation, yet capable of navigating proprietary enterprise job portals.

---

## 2. User Value
Directly operates on the **Execution Layer** of the **Career Intelligence Compounding Loop**.
- **Compounding Loop Connection**: Enterprise platforms (Workday/iCIMS) host the largest volume of high-quality corporate jobs, but their manual application process is notoriously repetitive. Programmatic form execution automates this step reliably. If the target form layout changes, the system flags the difference to update the schema, improving future automation rates.
- **User Benefit**: Candidates can apply to roles on complex corporate portals within seconds. They avoid the tedious manual process of re-entering employment details and answering the same diversity questions repeatedly.

---

## 3. Requirements
- **Workday Schema Engine**: Parse, map, and execute multi-page submissions on Workday job portals by simulating sequential HTTP POST steps.
- **iCIMS Schema Engine**: Standardize the multi-page iframe structure used by iCIMS to map fields correctly.
- **Form Mapping System**: Create a declarative schema registry matching CSS selectors, XPath expressions, or input `name` properties to normalized candidate fields.
- **Field Normalization Layer**: Automatically map variations of field labels (e.g., "Given Name", "First Name", "fname", "forename") to the user's base database fields.
- **Validation Engine**: Pre-validate that all required fields on the target form are present in the user profile before initiating submission.
- **Programmatic Submission Engine**: Construct and transmit multi-page HTTP POST requests representing form completion tokens and payloads.
- **Error Recovery**: Automatically handoff execution to the `Browser Fallback Execution` engine if a validation error or field parsing error occurs during form submission.

---

## 4. Database Changes

### Table: `form_schemas`
Stores structured templates for forms mapped by target company or platform provider.

| Field Name | Data Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | UUID | PRIMARY KEY, DEFAULT gen_random_uuid() | Unique identifier. |
| `platform_provider` | VARCHAR(50) | NOT NULL | `WORKDAY`, `ICIMS`, `TALEO`, `OTHER`. |
| `company_domain` | VARCHAR(255) | UNIQUE, NOT NULL | e.g., `acme.myworkdayjobs.com`. |
| `fields_schema` | JSONB | NOT NULL | Mapping of selectors/names to profile properties. |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | Record creation. |
| `updated_at` | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | Last update. |

### Table: `form_execution_logs`
Tracks sequential HTTP requests made during multi-page form executions.

| Field Name | Data Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | UUID | PRIMARY KEY, DEFAULT gen_random_uuid() | Unique identifier. |
| `application_id` | UUID | FOREIGN KEY references `job_applications(id)`, NOT NULL | Parent application. |
| `step_number` | INTEGER | NOT NULL | Multi-page form step index (e.g., 1, 2, 3). |
| `step_name` | VARCHAR(100) | NOT NULL | e.g., `PERSONAL_INFO`, `WORK_EXPERIENCE`, `SUBMIT`. |
| `request_payload` | JSONB | NOT NULL | Data transmitted at this step. |
| `response_status` | INTEGER | NOT NULL | HTTP status code returned. |
| `error_captured` | TEXT | NULLABLE | Validation errors returned in the HTTP response. |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | Step start time. |

### Indexes
- `idx_form_schemas_domain` on `form_schemas(company_domain)`
- `idx_form_execs_app_id` on `form_execution_logs(application_id)`

---

## 5. API Endpoints
These modules are executed asynchronously inside Temporal workers. However, system administrator endpoints allow management of target schemas.

### Register Form Schema
- **HTTP Method**: `POST`
- **Route**: `/api/v2/admin/form-schemas`
- **Request Body (JSON)**:
```json
{
  "platform_provider": "WORKDAY",
  "company_domain": "acme.myworkdayjobs.com",
  "fields_schema": {
    "personal_details": {
      "first_name_selector": "input[name='firstName']",
      "last_name_selector": "input[name='lastName']",
      "email_selector": "input[name='email']"
    },
    "work_experience": {
      "job_title_selector": "input[data-automation-id='jobTitle']",
      "employer_selector": "input[data-automation-id='employer']"
    }
  }
}
```
- **Response Payload (JSON)**:
```json
{
  "schema_id": "789ea3c7-1122-3344-5566-778899aabbcc",
  "company_domain": "acme.myworkdayjobs.com",
  "status": "ACTIVE"
}
```
- **HTTP Status Codes**:
  - `201 Created`: Schema successfully stored.
  - `400 Bad Request`: Schema validation error.
  - `401 Unauthorized`: Not authenticated.
  - `403 Forbidden`: Admin privileges required.

---

## 6. Domain Models

```python
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Dict, Any, Optional

class FormSchemaBase(BaseModel):
    platform_provider: str = Field(..., description="Target ATS Portal Type")
    company_domain: str = Field(..., description="Target corporate domain")
    fields_schema: Dict[str, Any] = Field(..., description="Map of selectors to profile variables")

class FormSchemaCreate(FormSchemaBase):
    pass

class FormSchemaResponse(FormSchemaBase):
    id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True

class FormSubmissionPayload(BaseModel):
    application_id: str
    company_domain: str
    profile_data: Dict[str, Any]
    files: Dict[str, bytes]
```

---

## 7. Services

### Class: `DeterministicFormExecutionService`
Coordinates the mapping, validation, and multi-step HTTP routing to execute submissions on Workday and iCIMS portals.

- **Method**: `execute_form_submission`
  - **Inputs**:
    - `payload` (FormSubmissionPayload): Applicant metadata and files.
  - **Return Type**: `bool` (indicating success or failure)
  - **Responsibilities**:
    - Fetches the active schema mapping from `form_schemas` using the target company domain.
    - Runs the pre-flight checks: ensures all required fields in the schema exist in `profile_data`.
    - Instantiates the specific provider execution controller (e.g., `WorkdayFormEngine`).
    - Loops through form stages: generates the appropriate multi-part network request payload, transmits the request, parses the HTTP response, and writes status logs to `form_execution_logs`.
    - Extracts confirmation details from the final step's HTTP response.
    - If any stage fails, throws a `FormExecutionException` to prompt the workflow orchestrator to fall back.

---

## 8. Events
Observability and failure events are published at the `ApplicationWorkflow` level.

---

## 9. Background Jobs
No periodic cron tasks. Actions run on demand inside Temporal activities.

---

## 10. Acceptance Criteria
- **Scenario**: Form schema matches page layout and completes successfully.
  - **Given**: A registered form schema exists for `acme.myworkdayjobs.com`.
  - **When**: `DeterministicFormExecutionService` executes a submission.
  - **Then**: All sequential HTTP POST steps return status code 200, the final page confirms submission, and a success boolean is returned.
- **Scenario**: Pre-flight validation fails.
  - **Given**: The target schema requires a field `zip_code` which is missing from the candidate's profile.
  - **When**: The validation step is performed.
  - **Then**: The service blocks execution immediately and returns a validation error without making network calls.

---

## 11. Edge Cases
- **Dynamic Multi-page CSRF Tokens**: Workday generates anti-CSRF request tokens on page 1 that must be extracted and returned in the header of page 2.
  - **Resolution**: The execution service implements HTML page parsing (via BeautifulSoup) at each stage to search for hidden inputs named `_csrf` or similar, carrying them forward into the headers of subsequent requests.
- **Session Expiration during Multi-stage Forms**: The target portal times out if page actions take longer than 5 minutes.
  - **Resolution**: The Temporal activity wrapper enforces a maximum timeout of 3 minutes per step, failing quickly to trigger clean retries or fallback mechanisms.

---

## 12. Test Requirements
- **Unit Tests**: Test the field mapper logic using mock HTML forms and matching them against output data models.
- **Integration Tests**: Execute submissions against locally hosted Mock Workday/iCIMS endpoints to verify correct CSRF propagation and multi-stage HTTP routing behavior.

---

## 13. Dependencies
- **[F1.1: Project Setup & Architecture](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/feature-specs/project-setup-architecture.md)**: Standardizes DB access and networking.

---
