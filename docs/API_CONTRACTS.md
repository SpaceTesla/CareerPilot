# CareerPilot API Contracts Specification

This document defines the formal OpenAPI-style API contracts for CareerPilot v2. All endpoints follow the domain boundaries and patterns established in the [Master Design Document](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/careerpilot_v2.md), [Implementation Doctrine](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/IMPLEMENTATION_DOCTRINE.md), and [ADRs](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/adrs/0001-fastapi.md).

---

## Global API Information

*   **API Version:** `2.0.0`
*   **Base URL:** `/api/v2`
*   **Default Headers:**
    *   `Content-Type: application/json`
    *   `Accept: application/json`
*   **Authentication Schemes:**
    *   `BearerAuth`: JSON Web Token (JWT) in the header format `Authorization: Bearer <JWT_ACCESS_TOKEN>`. See [Authentication Strategy ADR](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/adrs/0009-authentication-strategy.md) for details.

---

## 1. Standardized Error Contracts

All endpoint failures return a consistent JSON response conforming to the RFC 7807 Problem Details spec.

### Standard Error Schema (4xx/5xx)
```json
{
  "detail": "Error message explaining the failure details.",
  "error_code": "ERROR_CODE_SLUG",
  "timestamp": "2026-06-09T02:12:31Z",
  "path": "/api/v2/endpoint"
}
```

### Unprocessable Entity Schema (422 ValidationError)
Returned by FastAPI when input payload validation fails against Pydantic models.
```json
{
  "detail": [
    {
      "loc": ["body", "email"],
      "msg": "value is not a valid email address",
      "type": "value_error.email"
    }
  ]
}
```

---

## 2. API Endpoints

### 2.1 Authentication & Identity Domain

#### `POST /auth/register`
Creates a new user profile and goals wrapper.
*   **Authentication:** None
*   **Request Body:**
    ```json
    {
      "email": "user@example.com",
      "password": "SecurePassword123!"
    }
    ```
*   **Success Response (`201 Created`):**
    ```json
    {
      "user_id": "8fa8d390-c209-411a-8bb7-09d29486c91e",
      "email": "user@example.com",
      "created_at": "2026-06-09T02:12:31Z"
    }
    ```
*   **Errors:**
    *   `400 Bad Request` (`EMAIL_ALREADY_EXISTS`): The email is already registered.
    *   `422 Unprocessable Entity`: Password strength fails complexity rules.

---

#### `POST /auth/login`
Authenticates a user and issues token credentials.
*   **Authentication:** None
*   **Request Body:**
    ```json
    {
      "email": "user@example.com",
      "password": "SecurePassword123!"
    }
    ```
*   **Success Response (`200 OK`):**
    ```json
    {
      "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
      "refresh_token": "9a7f34c2-8419-482c-b5f7-d2e822019941",
      "token_type": "bearer",
      "expires_in": 900
    }
    ```
*   **Errors:**
    *   `401 Unauthorized` (`INVALID_CREDENTIALS`): Incorrect email or password.

---

#### `POST /auth/refresh`
Rotates and issues a new access token pair. See [Authentication Strategy ADR](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/adrs/0009-authentication-strategy.md) for session rotation details.
*   **Authentication:** None
*   **Request Body:**
    ```json
    {
      "refresh_token": "9a7f34c2-8419-482c-b5f7-d2e822019941"
    }
    ```
*   **Success Response (`200 OK`):**
    ```json
    {
      "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
      "refresh_token": "cfd86419-12a4-4f2e-a5b7-789a24cbf5e4",
      "token_type": "bearer",
      "expires_in": 900
    }
    ```
*   **Errors:**
    *   `401 Unauthorized` (`REFRESH_TOKEN_EXPIRED` / `REFRESH_TOKEN_INVALID`): Token has expired or is invalid.

---

#### `POST /auth/logout`
Revokes active refresh tokens and clears user session.
*   **Authentication:** None
*   **Request Body:**
    ```json
    {
      "refresh_token": "cfd86419-12a4-4f2e-a5b7-789a24cbf5e4"
    }
    ```
*   **Success Response (`204 No Content`):** Empty body.

---

### 2.2 Career Profile Domain

#### `GET /profile`
Retrieves the user's active career profile.
*   **Authentication:** `BearerAuth`
*   **Success Response (`200 OK`):**
    ```json
    {
      "profile_id": "7fa8e1b0-18e4-4d89-9a74-dcf019318b82",
      "version": 1,
      "skills": [
        {"name": "Python", "years_experience": 5.5, "proficiency": "expert"},
        {"name": "FastAPI", "years_experience": 2.0, "proficiency": "intermediate"}
      ],
      "experiences": [
        {
          "company": "Tech Corp",
          "role": "Senior Backend Engineer",
          "start_date": "2023-01-15",
          "end_date": null,
          "highlights": ["Designed core data pipeline processing 1M events/day."]
        }
      ],
      "education": [
        {
          "institution": "State University",
          "degree": "B.S. Computer Science",
          "graduation_year": 2020
        }
      ],
      "positioning_summary": "Experienced backend software engineer specializing in async python workflows.",
      "updated_at": "2026-06-09T02:12:31Z"
    }
    ```
*   **Errors:**
    *   `401 Unauthorized`: Token missing/expired.
    *   `404 Not Found` (`PROFILE_NOT_INITIALIZED`): User has not imported a resume yet.

---

#### `POST /profile/sync`
Uploads a raw resume document to execute extraction and profile sync.
*   **Authentication:** `BearerAuth`
*   **Request Content Type:** `multipart/form-data`
*   **Request Form Fields:**
    *   `file`: Binary file upload (PDF or DOCX allowed, max 5MB).
*   **Success Response (`202 Accepted`):**
    ```json
    {
      "task_id": "sync_task_8fa1b490d29141",
      "status": "PROCESSING",
      "message": "Resume parsing initiated. Check task status for completion."
    }
    ```
*   **Errors:**
    *   `400 Bad Request` (`INVALID_FILE_TYPE`): Uploaded file must be PDF or DOCX.
    *   `413 Payload Too Large`: File size exceeds limit.

---

#### `PUT /profile`
Manually overrides/updates details of the active career profile.
*   **Authentication:** `BearerAuth`
*   **Request Body:** Same schema structure as `GET /profile` response body.
*   **Success Response (`200 OK`):** Returns the updated profile schema.
*   **Errors:**
    *   `422 Unprocessable Entity`: Profile validation constraints failed.

---

#### `GET /profile/versions`
Retrieves history snapshots of the user's career profile versions.
*   **Authentication:** `BearerAuth`
*   **Success Response (`200 OK`):**
    ```json
    [
      {
        "version": 2,
        "updated_at": "2026-06-09T02:12:31Z",
        "change_reason": "Manual UI edit"
      },
      {
        "version": 1,
        "updated_at": "2026-06-08T15:20:00Z",
        "change_reason": "Initial Resume Upload"
      }
    ]
    ```

---

#### `POST /profile/versions/{version_id}/rollback`
Rollbacks the active profile version to a previous snapshot version.
*   **Authentication:** `BearerAuth`
*   **Path Parameters:**
    *   `version_id` (integer): Version index to rollback to.
*   **Success Response (`200 OK`):** Returns the rolled-back profile schema structure.
*   **Errors:**
    *   `404 Not Found` (`VERSION_NOT_FOUND`): Version index does not exist for the user.

---

### 2.3 Intelligence Synthesis Domain

#### `GET /intelligence/health-score`
Computes the current explaining metrics of the Career Health Score. See [spec](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/feature-specs/career-health-score-engine-v1.md) for weights.
*   **Authentication:** `BearerAuth`
*   **Success Response (`200 OK`):**
    ```json
    {
      "score": 78.5,
      "delta_7d": 1.2,
      "computed_at": "2026-06-09T02:12:31Z",
      "primary_insight": "Your alignment improved because LangGraph was verified in your profile.",
      "components": {
        "skill_alignment_score": 85.0,
        "market_positioning_score": 72.0,
        "activity_health_score": 90.0,
        "compensation_alignment_score": 68.0,
        "profile_completeness_score": 95.0
      },
      "drivers": [
        {"type": "positive", "impact": 4.5, "description": "High skill match for target Staff Backend Engineer roles."},
        {"type": "negative", "impact": -2.1, "description": "Compensation target exceeds current peer cohort 75th percentile."}
      ]
    }
    ```

---

#### `GET /intelligence/position-delta`
Retrieves prioritized gap actions relative to target roles.
*   **Authentication:** `BearerAuth`
*   **Success Response (`200 OK`):**
    ```json
    {
      "target_role": "Staff Platform Engineer",
      "missing_skills": [
        {
          "skill_name": "Kubernetes",
          "importance_rank": 1,
          "market_frequency": 0.74,
          "recommendation": "Deploy a service using Helm and add experience in a project block."
        },
        {
          "skill_name": "LangGraph",
          "importance_rank": 2,
          "market_frequency": 0.61,
          "recommendation": "Integrate a multi-agent routing topology in your portfolio repository."
        }
      ],
      "experience_gaps": [
        "Missing clear evidence of leading distributed system scaling migrations."
      ]
    }
    ```

---

### 2.4 Market Intelligence Domain

#### `GET /market/trends`
Queries global skill demand velocity trends.
*   **Authentication:** `BearerAuth`
*   **Query Parameters:**
    *   `role_category` (string, optional): Filter by role profile (e.g. `backend`, `frontend`, `ai-infra`).
*   **Success Response (`200 OK`):**
    ```json
    [
      {
        "skill_name": "LangGraph",
        "frequency_pct": 14.5,
        "growth_velocity_pct": 34.2,
        "demand_tier": "critical_growth"
      },
      {
        "skill_name": "Kubernetes",
        "frequency_pct": 52.1,
        "growth_velocity_pct": 2.1,
        "demand_tier": "stable_core"
      }
    ]
    ```

---

#### `GET /market/companies/{id}`
Returns aggregated telemetry for a tracked employer.
*   **Authentication:** `BearerAuth`
*   **Path Parameters:**
    *   `id` (UUID): Company record identifier.
*   **Success Response (`200 OK`):**
    ```json
    {
      "company_id": "9fa8d390-c209-411a-8bb7-09d29486c91e",
      "name": "Innovate AI",
      "hiring_velocity": "high",
      "open_postings_count": 24,
      "attractiveness_score": 88.5,
      "ghost_posting_index": 0.08,
      "company_signals": [
        {"type": "funding", "title": "Series B closed $40M", "date": "2026-05-10"},
        {"type": "attrition", "title": "Engineering management departures", "date": "2026-04-12"}
      ],
      "last_updated": "2026-06-09T02:12:31Z"
    }
    ```
*   **Errors:**
    *   `404 Not Found`: Company ID not recognized.

---

#### `GET /market/compensation`
Retrieves salary index percentile breakdowns for target configurations.
*   **Authentication:** `BearerAuth`
*   **Query Parameters:**
    *   `role` (string): e.g. `Senior Python Engineer`
    *   `location` (string): e.g. `San Francisco`
*   **Success Response (`200 OK`):**
    ```json
    {
      "role": "Senior Python Engineer",
      "location": "San Francisco",
      "col_tier": "T1",
      "percentiles": {
        "p25": 145000,
        "p50": 175000,
        "p75": 210000,
        "p90": 245000
      },
      "sample_size": 342,
      "source_type": "offer_outcomes_aggregated"
    }
    ```

---

#### `GET /market/opportunities`
Ranked feed of personalized matched jobs.
*   **Authentication:** `BearerAuth`
*   **Query Parameters:**
    *   `page` (integer, optional): Default `1`.
    *   `limit` (integer, optional): Default `20`.
*   **Success Response (`200 OK`):**
    ```json
    {
      "results": [
        {
          "posting_id": "4fa8e230-22d4-4f89-8a12-dcf019324a12",
          "title": "AI Platform Engineer",
          "company_name": "Innovate AI",
          "matching_score": 92.4,
          "salary_range": {"min": 180000, "max": 220000},
          "location": "San Francisco (Hybrid)",
          "skills_matched": ["Python", "FastAPI", "Qdrant"],
          "skills_missing": ["Kubernetes"],
          "reasons": [
            "Matches 90% of required tech stack.",
            "Compensation range aligns with your target P75 benchmark."
          ]
        }
      ],
      "total_count": 145
    }
    ```

---

### 2.5 Execution & Workflow Domain

#### `POST /execution/applications`
Initializes a multi-step job application execution sequence. See [Application Workflow specs](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/feature-specs/application-workflow.md).
*   **Authentication:** `BearerAuth`
*   **Request Body:**
    ```json
    {
      "posting_id": "4fa8e230-22d4-4f89-8a12-dcf019324a12",
      "override_resume_id": null
    }
    ```
*   **Success Response (`201 Created`):**
    ```json
    {
      "execution_id": "exec_7fa8e1b018e4d89a74",
      "workflow_id": "app_wf_4fa8e230-22d4-4f89-8a12",
      "status": "AWAITING_APPROVAL",
      "message": "Application brief generated. Awaiting human approval gate confirmation."
    }
    ```
*   **Errors:**
    *   `404 Not Found`: Posting ID does not exist.
    *   `409 Conflict` (`ACTIVE_EXECUTION_EXISTS`): An active submission is already in progress for this role.

---

#### `GET /execution/applications/{id}`
Returns Temporal workflow execution tracking and logs.
*   **Authentication:** `BearerAuth`
*   **Path Parameters:**
    *   `id` (string): Execution tracking ID.
*   **Success Response (`200 OK`):**
    ```json
    {
      "execution_id": "exec_7fa8e1b018e4d89a74",
      "status": "RUNNING",
      "current_stage": "FORM_FILLING",
      "tier_attempted": 2,
      "logs": [
        {"timestamp": "2026-06-09T02:12:31Z", "message": "API submission (Tier 1) unsupported. Falling back to Form Execution (Tier 2)."},
        {"timestamp": "2026-06-09T02:13:00Z", "message": "Parsed Workday form schema. Injecting profile mapping inputs."}
      ],
      "screenshot_url": null,
      "updated_at": "2026-06-09T02:13:02Z"
    }
    ```

---

#### `GET /execution/approvals`
Lists pending human approval briefs. See [Human Review specs](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/feature-specs/human-in-the-loop-review.md).
*   **Authentication:** `BearerAuth`
*   **Success Response (`200 OK`):**
    ```json
    [
      {
        "approval_id": "appr_9fa8d390c209411",
        "execution_id": "exec_7fa8e1b018e4d89a74",
        "job_title": "AI Platform Engineer",
        "company_name": "Innovate AI",
        "custom_resume_version": 2,
        "proposed_cover_letter": "I am excited to apply for the AI Platform Engineer role...",
        "form_answers": [
          {
            "field_label": "Years of experience with Kubernetes",
            "field_key": "kubernetes_years",
            "proposed_value": "2 years (via personal portfolio configurations)"
          }
        ]
      }
    ]
    ```

---

#### `POST /execution/approvals/{id}/submit`
Submits decision configurations approving or editing a generated brief.
*   **Authentication:** `BearerAuth`
*   **Path Parameters:**
    *   `id` (string): Approval identifier.
*   **Request Body:**
    ```json
    {
      "status": "approved",
      "edited_cover_letter": "I am excited to apply for the AI Platform Engineer role at Innovate AI...",
      "edited_form_answers": [
        {
          "field_key": "kubernetes_years",
          "value": "2 years"
        }
      ]
    }
    ```
*   **Success Response (`200 OK`):**
    ```json
    {
      "execution_id": "exec_7fa8e1b018e4d89a74",
      "status": "RESUMED",
      "message": "Workflow signal sent. Resuming submission execution."
    }
    ```
*   **Errors:**
    *   `404 Not Found`: Approval ID does not exist or has expired.
    *   `400 Bad Request` (`INVALID_DECISION`): Status must be 'approved' or 'rejected'.

---

#### `POST /execution/outcomes`
Manually records or updates the outcome of an application to close the calibration feedback loop.
*   **Authentication:** `BearerAuth`
*   **Request Body:**
    ```json
    {
      "execution_id": "exec_7fa8e1b018e4d89a74",
      "outcome": "interview_callback",
      "details": {
        "callback_date": "2026-06-12",
        "contact_person": "Jane Doe"
      }
    }
    ```
*   **Success Response (`200 OK`):**
    ```json
    {
      "outcome_id": "outc_7fa8e1b018e4d89",
      "execution_id": "exec_7fa8e1b018e4d89a74",
      "outcome": "interview_callback",
      "prediction_error_score": 0.082
    }
    ```
*   **Errors:**
    *   `404 Not Found`: Execution ID not recognized.
    *   `422 Unprocessable Entity`: Invalid outcome category (must be one of: `applied`, `interview_callback`, `offer`, `rejection`, `ghosted`).

---

### 2.6 Dashboard Domain

#### `GET /dashboard`
Aggregated widget feed summarizing user stats for home display.
*   **Authentication:** `BearerAuth`
*   **Success Response (`200 OK`):**
    ```json
    {
      "health_score": {
        "current": 78.5,
        "delta_7d": 1.2
      },
      "position_delta_summary": {
        "gaps_count": 3,
        "top_gaps": ["Kubernetes", "LangGraph"]
      },
      "market_insights_summary": {
        "hiring_trends": "AI infrastructure sector growth leads this week at +34.2% velocity."
      },
      "active_applications_count": 4,
      "opportunities_spotlight": [
        {
          "posting_id": "4fa8e230-22d4-4f89-8a12-dcf019324a12",
          "title": "AI Platform Engineer",
          "company_name": "Innovate AI",
          "matching_score": 92.4
        }
      ]
    }
    ```
