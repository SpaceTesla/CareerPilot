# Feature Specification: Career Profile Domain

## 1. Purpose
This feature handles the structured representation, storage, validation, and historical versioning of a user's professional background. It defines database schemas and API endpoints for managing the core profile entities: professional summaries, skills (with proficiency and experience metrics), work experiences, education histories, and projects. It implements a versioning pipeline to ensure any modifications are tracked, rollbackable, and auditable.

For details on the feature relationships, see [DEPENDENCY_GRAPH.md](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/DEPENDENCY_GRAPH.md) and the backlog in [backlog.md](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/backlog.md).

## 2. User Value
A user's profile is the primary asset that determines their marketability. By providing a structured and versioned profile database, users can maintain a single "source of truth" for their skills and experiences. The versioning system ensures that updates (such as tailoring a resume or adding a project) can be compared and reverted safely. This profile structure is the core inputs used by the Position Delta and Career Health engines to track goals alignment.

## 3. Requirements
- **Structured Representation**: Design normalized database entities for core profile components: Skills, Work Experience, Education, and Projects.
- **Profile Versioning**: On every profile update, the service must serialize the current state of the profile and child records into a JSON payload and store it in a version history table. This allows users to track changes over time and restore historical snapshots.
- **CRUD Operations**: Build full RESTful API endpoints for retrieving, updating, and deleting individual profile entities.
- **Validation Rules**: Implement model-level constraints, including start date validation (must be prior to end date), location normalization, and non-empty experience descriptions.
- **Cascade Operations**: Ensure deleting a profile or user deletes all associated child collections cleanly.

## 4. Database Changes

### `career_profiles`
The root profile header for a user.
- `id`: `UUID` (Primary Key, Default: `uuid_generate_v4()`)
- `user_id`: `UUID` (Foreign Key referencing `users.id` ON DELETE CASCADE, Unique, Indexed, Not Null)
- `headline`: `VARCHAR(255)` (Nullable)
- `summary`: `TEXT` (Nullable)
- `location`: `VARCHAR(100)` (Nullable)
- `current_salary`: `NUMERIC(12, 2)` (Nullable)
- `created_at`: `TIMESTAMP WITH TIME ZONE` (Default: `NOW()`, Not Null)
- `updated_at`: `TIMESTAMP WITH TIME ZONE` (Default: `NOW()`, Not Null)

### `profile_versions`
Stores snapshots of the profile state for auditing and rollback.
- `id`: `UUID` (Primary Key, Default: `uuid_generate_v4()`)
- `profile_id`: `UUID` (Foreign Key referencing `career_profiles.id` ON DELETE CASCADE, Indexed, Not Null)
- `version_number`: `INTEGER` (Not Null)
- `snapshot_payload`: `JSONB` (Not Null) - Complete serialized JSON representation of the profile, experiences, education, projects, and skills.
- `created_at`: `TIMESTAMP WITH TIME ZONE` (Default: `NOW()`, Not Null)

### `skills`
User's self-declared or extracted technical and soft skills.
- `id`: `UUID` (Primary Key, Default: `uuid_generate_v4()`)
- `profile_id`: `UUID` (Foreign Key referencing `career_profiles.id` ON DELETE CASCADE, Indexed, Not Null)
- `skill_name`: `VARCHAR(100)` (Indexed, Not Null)
- `years_experience`: `NUMERIC(4, 1)` (Not Null)
- `proficiency`: `VARCHAR(50)` (Not Null) - E.g. "NOVICE", "INTERMEDIATE", "ADVANCED", "EXPERT"
- `created_at`: `TIMESTAMP WITH TIME ZONE` (Default: `NOW()`, Not Null)
- `updated_at`: `TIMESTAMP WITH TIME ZONE` (Default: `NOW()`, Not Null)

### `experiences`
Work history timeline.
- `id`: `UUID` (Primary Key, Default: `uuid_generate_v4()`)
- `profile_id`: `UUID` (Foreign Key referencing `career_profiles.id` ON DELETE CASCADE, Indexed, Not Null)
- `company_name`: `VARCHAR(255)` (Indexed, Not Null)
- `job_title`: `VARCHAR(255)` (Not Null)
- `start_date`: `DATE` (Not Null)
- `end_date`: `DATE` (Nullable)
- `description`: `TEXT` (Not Null)
- `is_current`: `BOOLEAN` (Default: `False`, Not Null)
- `created_at`: `TIMESTAMP WITH TIME ZONE` (Default: `NOW()`, Not Null)
- `updated_at`: `TIMESTAMP WITH TIME ZONE` (Default: `NOW()`, Not Null)

### `education`
Academic history.
- `id`: `UUID` (Primary Key, Default: `uuid_generate_v4()`)
- `profile_id`: `UUID` (Foreign Key referencing `career_profiles.id` ON DELETE CASCADE, Indexed, Not Null)
- `institution`: `VARCHAR(255)` (Not Null)
- `degree`: `VARCHAR(255)` (Nullable)
- `field_of_study`: `VARCHAR(255)` (Nullable)
- `start_date`: `DATE` (Not Null)
- `end_date`: `DATE` (Nullable)
- `created_at`: `TIMESTAMP WITH TIME ZONE` (Default: `NOW()`, Not Null)
- `updated_at`: `TIMESTAMP WITH TIME ZONE` (Default: `NOW()`, Not Null)

### `projects`
Side projects or specific work highlights.
- `id`: `UUID` (Primary Key, Default: `uuid_generate_v4()`)
- `profile_id`: `UUID` (Foreign Key referencing `career_profiles.id` ON DELETE CASCADE, Indexed, Not Null)
- `project_name`: `VARCHAR(255)` (Not Null)
- `description`: `TEXT` (Not Null)
- `role_description`: `TEXT` (Nullable)
- `url`: `VARCHAR(512)` (Nullable)
- `created_at`: `TIMESTAMP WITH TIME ZONE` (Default: `NOW()`, Not Null)
- `updated_at`: `TIMESTAMP WITH TIME ZONE` (Default: `NOW()`, Not Null)

## 5. API Endpoints

### `GET /api/v2/profile`
Retrieves the complete profile for the authenticated user, including skills, experiences, education, and projects.
- **Request Headers**: JWT Bearer Token in `Authorization`
- **Response Body (200 OK)**:
  ```json
  {
    "id": "a61fa1c8-2b81-424a-a232-06900ee9c104",
    "user_id": "e229c9bb-36db-4876-b9a6-d6b797cc963a",
    "headline": "Senior Backend Engineer",
    "summary": "5+ years developing robust backend services.",
    "location": "San Francisco, CA",
    "current_salary": 165000.00,
    "skills": [
      {
        "id": "c7128cf7-21a4-4f81-9b1b-7a32bd32a688",
        "skill_name": "Python",
        "years_experience": 5.0,
        "proficiency": "EXPERT"
      }
    ],
    "experiences": [
      {
        "id": "3be8a75e-85c1-4034-927e-855cdbc5ccb6",
        "company_name": "Tech Corp",
        "job_title": "Backend Engineer",
        "start_date": "2021-03-01",
        "end_date": null,
        "description": "Led optimization of postgres DB queries.",
        "is_current": true
      }
    ],
    "education": [],
    "projects": []
  }
  ```

### `PUT /api/v2/profile`
Updates the primary profile attributes. Re-saves child records if modified, auto-creating a new version snapshot.
- **Request Headers**: JWT Bearer Token
- **Request Body**:
  ```json
  {
    "headline": "Staff Platform Engineer",
    "summary": "6+ years building scalable systems.",
    "location": "San Francisco, CA",
    "current_salary": 185000.00,
    "skills": [
      {
        "skill_name": "Python",
        "years_experience": 6.0,
        "proficiency": "EXPERT"
      },
      {
        "skill_name": "Kubernetes",
        "years_experience": 2.0,
        "proficiency": "INTERMEDIATE"
      }
    ],
    "experiences": [
      {
        "company_name": "Tech Corp",
        "job_title": "Senior Platform Engineer",
        "start_date": "2021-03-01",
        "end_date": "2026-06-01",
        "description": "Maintained platform services.",
        "is_current": false
      }
    ],
    "education": [],
    "projects": []
  }
  ```
- **Response Body (200 OK)**: Returns the updated profile representation and the auto-assigned version metadata under headers or status payloads.

### `GET /api/v2/profile/versions`
Fetches a list of metadata for all saved historical profile versions.
- **Response Body (200 OK)**:
  ```json
  [
    {
      "version_number": 2,
      "created_at": "2026-06-09T02:04:18Z",
      "summary_snippet": "6+ years building scalable systems."
    },
    {
      "version_number": 1,
      "created_at": "2026-06-08T14:30:00Z",
      "summary_snippet": "5+ years developing robust backend services."
    }
  ]
  ```

### `POST /api/v2/profile/versions/{version_number}/restore`
Replaces the active profile data with the specified version snapshot payload.
- **Response Body (200 OK)**: Returns the fully restored profile.

## 6. Domain Models

### Pydantic Schemas

```python
from pydantic import BaseModel, condecimal, Field
from uuid import UUID
from datetime import date
from typing import List, Optional
from decimal import Decimal
from enum import Enum

class ProficiencyLevel(str, Enum):
    NOVICE = "NOVICE"
    INTERMEDIATE = "INTERMEDIATE"
    ADVANCED = "ADVANCED"
    EXPERT = "EXPERT"

class SkillSchema(BaseModel):
    id: Optional[UUID] = None
    skill_name: str
    years_experience: Decimal = Field(..., max_digits=3, decimal_places=1)
    proficiency: ProficiencyLevel

class ExperienceSchema(BaseModel):
    id: Optional[UUID] = None
    company_name: str
    job_title: str
    start_date: date
    end_date: Optional[date] = None
    description: str
    is_current: bool

class EducationSchema(BaseModel):
    id: Optional[UUID] = None
    institution: str
    degree: Optional[str] = None
    field_of_study: Optional[str] = None
    start_date: date
    end_date: Optional[date] = None

class ProjectSchema(BaseModel):
    id: Optional[UUID] = None
    project_name: str
    description: str
    role_description: Optional[str] = None
    url: Optional[str] = None

class ProfileUpdate(BaseModel):
    headline: Optional[str] = None
    summary: Optional[str] = None
    location: Optional[str] = None
    current_salary: Optional[Decimal] = None
    skills: List[SkillSchema] = []
    experiences: List[ExperienceSchema] = []
    education: List[EducationSchema] = []
    projects: List[ProjectSchema] = []
```

## 7. Services

### `ProfileService`
- **Responsibilities**: Performs business logic validation and persists changes via the Repository layer. Computes profile completeness scoring (0-100) and triggers version creation.
- **Methods**:
  - `get_by_user_id(user_id: UUID) -> CareerProfile`: Fetches current active profile.
  - `update_profile(user_id: UUID, data: ProfileUpdate) -> CareerProfile`: Writes updates, calculates delta, creates a row in `profile_versions`, and updates active tables in a single transaction. Emits `profile.updated` event.
  - `restore_version(user_id: UUID, version_number: int) -> CareerProfile`: Re-populates experiences, education, projects, and skills tables from snapshot payload.
  - `calculate_completeness(profile: CareerProfile) -> int`: Simple percentage score of present fields.

## 8. Events

- **`profile.updated`**:
  - **Producer**: `ProfileService.update_profile`
  - **Consumers**: `CareerHealthScoreEngine` (updates scoring), `PositionDeltaEngine` (re-runs gap evaluations).
  - **Payload**:
    ```json
    {
      "event_id": "0d3a77bd-7d1c-43f1-b99b-9ea2dbb8cc9a",
      "event_type": "profile.updated",
      "timestamp": "2026-06-09T02:04:18Z",
      "data": {
        "user_id": "e229c9bb-36db-4876-b9a6-d6b797cc963a",
        "profile_id": "a61fa1c8-2b81-424a-a232-06900ee9c104",
        "version_number": 3,
        "skills": ["Python", "Kubernetes"]
      }
    }
    ```

## 9. Background Jobs
No periodic background tasks are registered by this module. All computations are done synchronously during transaction commits, emitting events for downstream systems.

## 10. Acceptance Criteria

- **Scenario: Experience Date Validation**
  - **Given** a user is updating their experiences list,
  - **When** the experience `start_date` is later than `end_date` (and `is_current` is false),
  - **Then** raise HTTP 422 Unprocessable Entity and reject save.
- **Scenario: Version Creation on Update**
  - **Given** a user has an existing version 1 profile,
  - **When** calling `PUT /api/v2/profile` with valid new details,
  - **Then** the updates are committed, and a new record in `profile_versions` is created with version number 2 containing the snapshot.
- **Scenario: Restore Historical Version**
  - **Given** a user has profile versions 1 and 2,
  - **When** calling `POST /api/v2/profile/versions/1/restore`,
  - **Then** overwrite all current records in tables with version 1 data, increments version to 3, and returns the restored profile.

## 11. Edge Cases
- **Overlapping Experience Dates with Current Tag**: The validation layer does not restrict parallel jobs (as engineers sometimes consult or double-hat), but it enforces that at most two experiences can have `is_current: True` concurrently.
- **Concurrency during Restoration**: If a profile is updated while a restoration workflow runs, the database locking mechanism (`SELECT FOR UPDATE`) locks the `career_profiles` row to prevent double-writes and transaction failures.
- **Empty Skills Array**: If the user sends an empty array of skills, it is accepted, but the profile completeness score drops significantly.

## 12. Test Requirements
- **Unit Tests**:
  - Test validation rules for experiences (start/end dates) and education.
  - Assert profile completeness algorithm returns expected weights (e.g. skills: 30%, experiences: 40%, education: 15%, projects: 15%).
- **Integration Tests**:
  - Assert that calling update APIs twice generates exactly two distinct entries in `profile_versions`.
  - Assert version restoration completely overwrites the database tables and deletes orphan records.

## 13. Dependencies
This feature depends on [authentication-identity-context.md](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/feature-specs/authentication-identity-context.md).
Downward features that depend on this are:
- [resume-import-profile-sync.md](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/feature-specs/resume-import-profile-sync.md)
- [career-health-score-engine-v1.md](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/feature-specs/career-health-score-engine-v1.md)
- [position-delta-engine.md](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/feature-specs/position-delta-engine.md)
- [career-dashboard.md](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/feature-specs/career-dashboard.md)
