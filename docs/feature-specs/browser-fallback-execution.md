# Feature Specification: Browser Fallback Execution

## 1. Purpose
The Browser Fallback Execution feature is the third and final tier of the CareerPilot Three-Tier Execution Engine. If a target job application cannot be submitted via direct ATS APIs (Tier 1) or Deterministic Form POSTs (Tier 2) due to custom captchas, complex JavaScript widgets, or out-of-date schemas, the system escalates the application to this fallback module.

It launches a headless browser instance using Playwright, navigates to the application URL, scans the page DOM, dynamically matches input fields to the candidate's profile context, fills the form fields, clicks the submit controls, and captures screenshots at each step for verification and audit trails.

---

## 2. User Value
Directly operates on the **Execution Layer** of the **Career Intelligence Compounding Loop**.
- **Compounding Loop Connection**: By capturing visual screenshots and saving HTML structures during browser execution failures, the system generates debug telemetry. This telemetry is reviewed during ML platform calibration to update API templates or deterministic form schemas, increasing future automation rates.
- **User Benefit**: Candidates are protected from application dropouts. Even if a target company is using a highly custom careers portal, CareerPilot is capable of executing the application visual-first, returning screenshots as proof of submission.

---

## 3. Requirements
- **Playwright Configuration**: Deploy a headless browser wrapper service (running Chromium/Webkit/Firefox) with proxy support, stealth plugins (to bypass bot-detection), and custom resource limitations.
- **Form Detection Engine**: Build a rule-based selector crawler that detects inputs by scanning labels, placeholders, aria-labels, and nearest-neighbor text nodes.
- **Field Filling Engine**: Programmatically interact with complex UI fields (dropdown selects, date pickers, radio lists, file upload inputs).
- **Screenshot & DOM Capture**: Capture high-resolution page screenshots and archive the target page HTML after each key action.
- **Action Retries**: Implement smart UI-wait policies (e.g., waiting for elements to be visible, stable, or clickable) and page-reload retries on transient network timeouts.
- **Audit Logs**: Record every browser event, click, keystroke, and selector match in a structured database table.
- **Escalation Trigger**: Implement a clean interface for the `Application Workflow` to handoff execution to this tier with clear status flags.

---

## 4. Database Changes

### Table: `browser_execution_logs`
Tracks sequential browser actions, selectors targeted, and files saved during automated browser execution.

| Field Name | Data Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | UUID | PRIMARY KEY, DEFAULT gen_random_uuid() | Unique identifier. |
| `application_id` | UUID | FOREIGN KEY references `job_applications(id)`, NOT NULL | Parent application. |
| `step_index` | INTEGER | NOT NULL | Sequential index of the step (1, 2, 3...). |
| `action_type` | VARCHAR(50) | NOT NULL | `NAVIGATE`, `DETECT_FIELD`, `FILL_INPUT`, `CLICK`, `SUBMIT`. |
| `target_selector` | VARCHAR(255) | NULLABLE | CSS Selector or XPath targeted. |
| `value_entered` | VARCHAR(255) | NULLABLE | Masked value typed (if any). |
| `screenshot_path` | VARCHAR(512) | NULLABLE | File storage path of the captured step screenshot. |
| `html_archive_path` | VARCHAR(512) | NULLABLE | File storage path of the archived HTML DOM source. |
| `status` | VARCHAR(50) | NOT NULL | `SUCCESS`, `WARNING`, `FAILED`. |
| `error_details` | TEXT | NULLABLE | Playwright execution error traces. |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | Timestamp of step execution. |

### Indexes
- `idx_browser_logs_app_id` on `browser_execution_logs(application_id)`

---

## 5. API Endpoints
Executed asynchronously inside Temporal worker processes. The API endpoints provide read access to debug assets.

### Fetch Browser Step Details & Screenshots
- **HTTP Method**: `GET`
- **Route**: `/api/v2/applications/{application_id}/browser-logs`
- **Path Parameters**:
  - `application_id` (string): Target application UUID.
- **Response Payload (JSON)**:
```json
{
  "application_id": "890ea3c7-1122-3344-5566-778899aabbcc",
  "steps": [
    {
      "step_index": 1,
      "action_type": "NAVIGATE",
      "target_selector": "https://careers.example.com/jobs/apply",
      "screenshot_url": "/api/v2/applications/890ea3c7/browser-logs/steps/1/screenshot",
      "status": "SUCCESS",
      "created_at": "2026-06-09T02:04:20Z"
    },
    {
      "step_index": 2,
      "action_type": "FILL_INPUT",
      "target_selector": "input#first-name",
      "screenshot_url": "/api/v2/applications/890ea3c7/browser-logs/steps/2/screenshot",
      "status": "SUCCESS",
      "created_at": "2026-06-09T02:04:22Z"
    }
  ]
}
```
- **HTTP Status Codes**:
  - `200 OK`: Details found.
  - `401 Unauthorized`: Invalid JWT.
  - `404 Not Found`: Application has no browser logs.

### Fetch Step Screenshot Image
- **HTTP Method**: `GET`
- **Route**: `/api/v2/applications/{application_id}/browser-logs/steps/{step_index}/screenshot`
- **Path Parameters**:
  - `application_id` (string): Application UUID.
  - `step_index` (integer): Index of the screenshot step.
- **Response Headers**:
  - `Content-Type: image/png`
- **Response Body**: Raw binary data of the PNG image.
- **HTTP Status Codes**:
  - `200 OK`: Image returned.
  - `404 Not Found`: Image file not found in storage.

---

## 6. Domain Models

```python
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

class BrowserActionBase(BaseModel):
    step_index: int
    action_type: str
    target_selector: Optional[str] = None
    status: str
    created_at: datetime

class BrowserActionLogResponse(BrowserActionBase):
    id: str
    application_id: str
    value_entered: Optional[str] = None
    screenshot_url: Optional[str] = None
    html_archive_url: Optional[str] = None
    error_details: Optional[str] = None
```

---

## 7. Services

### Class: `BrowserFallbackExecutionService`
Manages the lifetime of Playwright page objects, selector matching heuristics, and action replay.

- **Method**: `execute_fallback`
  - **Inputs**:
    - `application_id` (str): Target application record key.
    - `application_url` (str): Destination application page URL.
    - `profile_data` (Dict[str, Any]): Applicant profile attributes.
    - `resume_path` (str): Local path to candidate's resume PDF.
  - **Return Type**: `bool` (indicating success or failure)
  - **Responsibilities**:
    - Instantiates a clean, sandboxed Playwright browser context using `playwright-stealth` configurations.
    - Navigates to `application_url` and waits for DOM stabilization (up to 15 seconds).
    - Inspects page elements: executes dynamic field detection to identify input selectors.
    - Iterates through required fields: enters profile details, uploads the resume file, and updates `browser_execution_logs` with step details and S3-uploaded screenshots.
    - Locates the submit control: clicks the button and waits for navigation or confirmation dialogs.
    - Inspects post-submit page content to confirm the success text matches (e.g., "Application Received").
    - Closes context cleanly and returns outcome status.

---

## 8. Events
Observability events are emitted at the `ApplicationWorkflow` layer.

---

## 9. Background Jobs
No periodic background crons. Work runs on demand within Temporal workers.

---

## 10. Acceptance Criteria
- **Scenario**: Form field inputs are correctly mapped and filled.
  - **Given**: A careers page with fields for "Full Name" and "Resume".
  - **When**: `BrowserFallbackExecutionService` runs against the page URL.
  - **Then**: Playwright successfully identifies the inputs, inputs candidate data, uploads the PDF file, takes a screenshot, and submits the form.
- **Scenario**: Captcha is encountered.
  - **Given**: The form contains a reCAPTCHA iframe.
  - **When**: The submission process encounters the widget.
  - **Then**: The engine halts, logs the roadblock to `browser_execution_logs` with status `FAILED`, and raises a `CaptchaDetectedException` to trigger human-in-the-loop fallback escalation.

---

## 11. Edge Cases
- **Infinite Page Load / Hang**: The target server is slow, leaving the page loading indefinitely.
  - **Resolution**: Playwright context options are configured with a strict `page.goto` timeout of 30 seconds. On timeout, it retries once; if it fails again, it raises a terminal exception.
- **Shadow DOM Inputs**: Inputs are encapsulated inside shadow roots, making normal CSS selector queries fail.
  - **Resolution**: The detection engine utilizes deep-selector engines (`page.locator('xpath=...')` or custom JavaScript crawler evaluation injected into the page context) to locate shadow elements.

---

## 12. Test Requirements
- **Unit Tests**: Validate the heuristic element finder algorithms against static mock HTML files containing various forms.
- **Integration Tests**: Execute submissions against locally hosted mock forms to verify that files are successfully uploaded, values are entered in inputs, and screenshots are generated.

---

## 13. Dependencies
- **[F1.1: Project Setup & Architecture](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/feature-specs/project-setup-architecture.md)**: Standardizes base DB interactions.

---
