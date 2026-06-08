# Feature Specification: Authentication & Identity Context

## 1. Purpose
This feature handles user authentication, session security, and profile identification. It implements JWT access and refresh token authentication, secure password storage using bcrypt hashing, registration workflows, current user extraction middleware, user preferences management, and career goals schema. It establishes the baseline security protocol for protecting candidate data and defines user-specific targets that drive the Career Intelligence compounding loop.

For more details, see [careerpilot_v2.md](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/careerpilot_v2.md) and [DEPENDENCY_GRAPH.md](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/DEPENDENCY_GRAPH.md).

## 2. User Value
Security is non-negotiable when dealing with highly sensitive personal documents (resumes, work histories) and career aspirations. By enforcing JWT-based access controls, users own and control their private data. Additionally, setting up User Preferences and Career Goals establishes the target state (e.g., target role, desired salary range, timeline), which acts as the reference point for calculating the candidate's Career Health Score and Position Delta.

## 3. Requirements
- **Secure Password Hashing**: Use bcrypt to hash passwords prior to database persistence.
- **Access & Refresh Tokens**: Implement JWT tokens. Access tokens have a 15-minute lifespan. Refresh tokens have a 7-day lifespan, are stored as hashed versions in the database, and utilize token rotation.
- **Current User Injection**: Build middleware to validate incoming JWT tokens and inject the current user entity into FastAPI route handlers.
- **Registration & Login**: Deliver secure registration and authentication endpoints.
- **Preferences Management**: Manage system-wide options like job search intensity state (Active, Passive, Closed) and notification preferences.
- **Career Goals Definitions**: Store the target career endpoint, including desired role title, minimum and maximum target compensations, list of target companies, and target transition timeline.

## 4. Database Changes
We define three core tables in this domain context.

### `users`
Represents the root user accounts.
- `id`: `UUID` (Primary Key, Default: `uuid_generate_v4()`)
- `email`: `VARCHAR(255)` (Unique, Indexed, Not Null)
- `password_hash`: `VARCHAR(255)` (Not Null)
- `is_active`: `BOOLEAN` (Default: `True`, Not Null)
- `created_at`: `TIMESTAMP WITH TIME ZONE` (Default: `NOW()`, Not Null)
- `updated_at`: `TIMESTAMP WITH TIME ZONE` (Default: `NOW()`, Not Null)

### `user_preferences`
Represents user configuration options.
- `id`: `UUID` (Primary Key, Default: `uuid_generate_v4()`)
- `user_id`: `UUID` (Foreign Key referencing `users.id` ON DELETE CASCADE, Unique, Indexed, Not Null)
- `job_search_status`: `VARCHAR(50)` (Not Null, E.g. "ACTIVE", "PASSIVE", "CLOSED")
- `weekly_digest_enabled`: `BOOLEAN` (Default: `True`, Not Null)
- `email_notifications`: `BOOLEAN` (Default: `True`, Not Null)
- `created_at`: `TIMESTAMP WITH TIME ZONE` (Default: `NOW()`, Not Null)
- `updated_at`: `TIMESTAMP WITH TIME ZONE` (Default: `NOW()`, Not Null)

### `career_goals`
Defines target job objectives.
- `id`: `UUID` (Primary Key, Default: `uuid_generate_v4()`)
- `user_id`: `UUID` (Foreign Key referencing `users.id` ON DELETE CASCADE, Unique, Indexed, Not Null)
- `target_role`: `VARCHAR(255)` (Not Null)
- `target_compensation_min`: `NUMERIC(12, 2)` (Not Null)
- `target_compensation_max`: `NUMERIC(12, 2)` (Not Null)
- `target_companies`: `JSONB` (Default: `'[]'`, Not Null) - Array of strings representing company names
- `timeline_months`: `INTEGER` (Not Null)
- `created_at`: `TIMESTAMP WITH TIME ZONE` (Default: `NOW()`, Not Null)
- `updated_at`: `TIMESTAMP WITH TIME ZONE` (Default: `NOW()`, Not Null)

### Indexes and Migrations
- Unique index on `users.email`.
- Index on `user_preferences.user_id`.
- Index on `career_goals.user_id`.
- Alembic migration file `V2026_06_09_0001_create_auth_tables.py` will handle creation.

## 5. API Endpoints
All routes reside under the prefix `/api/v2`.

### `POST /api/v2/auth/register`
Creates a new user account, initialization profiles, empty preferences, and empty career goals.
- **Request Body**:
  ```json
  {
    "email": "user@domain.com",
    "password": "SecurePassword123!"
  }
  ```
- **Response Body (201 Created)**:
  ```json
  {
    "id": "e229c9bb-36db-4876-b9a6-d6b797cc963a",
    "email": "user@domain.com",
    "is_active": true,
    "created_at": "2026-06-09T02:04:18Z"
  }
  ```

### `POST /api/v2/auth/login`
Authenticates a user and returns access and refresh tokens.
- **Request Body**:
  ```json
  {
    "email": "user@domain.com",
    "password": "SecurePassword123!"
  }
  ```
- **Response Body (200 OK)**:
  ```json
  {
    "access_token": "eyJhbGciOi...",
    "refresh_token": "eyJhbGciOi...",
    "token_type": "bearer"
  }
  ```

### `POST /api/v2/auth/refresh`
Rotates the user's tokens using a valid refresh token.
- **Request Body**:
  ```json
  {
    "refresh_token": "eyJhbGciOi..."
  }
  ```
- **Response Body (200 OK)**:
  ```json
  {
    "access_token": "eyJhbGciOi...",
    "refresh_token": "eyJhbGciOi...",
    "token_type": "bearer"
  }
  ```

### `GET /api/v2/identity/preferences`
Fetches current user preference settings. Requires JWT Bearer token in the `Authorization` header.
- **Response Body (200 OK)**:
  ```json
  {
    "user_id": "e229c9bb-36db-4876-b9a6-d6b797cc963a",
    "job_search_status": "PASSIVE",
    "weekly_digest_enabled": true,
    "email_notifications": true
  }
  ```

### `PUT /api/v2/identity/preferences`
Updates user preference settings. Requires JWT Bearer token in the `Authorization` header.
- **Request Body**:
  ```json
  {
    "job_search_status": "ACTIVE",
    "weekly_digest_enabled": false,
    "email_notifications": true
  }
  ```
- **Response Body (200 OK)**:
  ```json
  {
    "user_id": "e229c9bb-36db-4876-b9a6-d6b797cc963a",
    "job_search_status": "ACTIVE",
    "weekly_digest_enabled": false,
    "email_notifications": true
  }
  ```

### `GET /api/v2/identity/goals`
Gets current user's target career goals. Requires JWT Bearer token.
- **Response Body (200 OK)**:
  ```json
  {
    "user_id": "e229c9bb-36db-4876-b9a6-d6b797cc963a",
    "target_role": "AI Platform Engineer",
    "target_compensation_min": 180000.00,
    "target_compensation_max": 230000.00,
    "target_companies": ["Anthropic", "OpenAI", "Cursor"],
    "timeline_months": 12
  }
  ```

### `PUT /api/v2/identity/goals`
Updates user's target career goals. Requires JWT Bearer token.
- **Request Body**:
  ```json
  {
    "target_role": "AI Platform Engineer",
    "target_compensation_min": 190000.00,
    "target_compensation_max": 240000.00,
    "target_companies": ["Anthropic", "OpenAI", "Google"],
    "timeline_months": 6
  }
  ```
- **Response Body (200 OK)**:
  ```json
  {
    "user_id": "e229c9bb-36db-4876-b9a6-d6b797cc963a",
    "target_role": "AI Platform Engineer",
    "target_compensation_min": 190000.00,
    "target_compensation_max": 240000.00,
    "target_companies": ["Anthropic", "OpenAI", "Google"],
    "timeline_months": 6
  }
  ```

## 6. Domain Models

### `User`
```python
from pydantic import BaseModel, EmailStr
from uuid import UUID
from datetime import datetime

class UserBase(BaseModel):
    email: EmailStr

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    id: UUID
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True
```

### `Token`
```python
from pydantic import BaseModel

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class TokenPayload(BaseModel):
    sub: str  # User ID as UUID string
    exp: int  # Expiration epoch
```

### `UserPreferences`
```python
from pydantic import BaseModel
from uuid import UUID
from enum import Enum

class JobSearchStatus(str, Enum):
    ACTIVE = "ACTIVE"
    PASSIVE = "PASSIVE"
    CLOSED = "CLOSED"

class UserPreferencesUpdate(BaseModel):
    job_search_status: JobSearchStatus
    weekly_digest_enabled: bool
    email_notifications: bool

class UserPreferencesResponse(UserPreferencesUpdate):
    user_id: UUID

    class Config:
        from_attributes = True
```

### `CareerGoals`
```python
from pydantic import BaseModel, conlist
from uuid import UUID
from typing import List

class CareerGoalsUpdate(BaseModel):
    target_role: str
    target_compensation_min: float
    target_compensation_max: float
    target_companies: List[str]
    timeline_months: int

class CareerGoalsResponse(CareerGoalsUpdate):
    user_id: UUID

    class Config:
        from_attributes = True
```

## 7. Services

### `AuthService`
- **Responsibilities**: Generates JWT payloads, computes password hashes, validates user logins.
- **Methods**:
  - `hash_password(password: str) -> str`: Hashes password using bcrypt.
  - `verify_password(plain_password: str, hashed_password: str) -> bool`: Validates password matches hash.
  - `create_access_token(user_id: UUID) -> str`: Issues a short-lived access JWT.
  - `create_refresh_token(user_id: UUID) -> str`: Issues a long-lived refresh JWT and tracks it in DB.
  - `verify_refresh_token(token: str) -> UUID`: Decodes refresh token and ensures matching db record exists and is active.
  - `revoke_refresh_token(token: str) -> None`: Deletes refresh token tracking.

### `IdentityService`
- **Responsibilities**: Standard user, preferences, and goals management.
- **Methods**:
  - `create_user(user_in: UserCreate) -> User`: Persists new user and constructs default preference and goals profiles.
  - `get_preferences(user_id: UUID) -> UserPreferences`: Fetches settings record.
  - `update_preferences(user_id: UUID, pref_in: UserPreferencesUpdate) -> UserPreferences`: Updates preferences record.
  - `get_goals(user_id: UUID) -> CareerGoals`: Fetches goals record.
  - `update_goals(user_id: UUID, goals_in: CareerGoalsUpdate) -> CareerGoals`: Updates goals record. Emits `identity.goals_updated` event.

## 8. Events
- **`identity.user_registered`**:
  - **Producer**: `IdentityService.create_user`
  - **Consumers**: `NotificationService` (send welcome email), `ProfileService` (initialize empty resume space).
  - **Payload Structure**:
    ```json
    {
      "event_id": "f58f000b-c8c7-4d7a-8f55-728b76eb41a1",
      "event_type": "identity.user_registered",
      "timestamp": "2026-06-09T02:04:18Z",
      "data": {
        "user_id": "e229c9bb-36db-4876-b9a6-d6b797cc963a",
        "email": "user@domain.com"
      }
    }
    ```
- **`identity.goals_updated`**:
  - **Producer**: `IdentityService.update_goals`
  - **Consumers**: `CareerHealthScoreEngine` (trigger score recalculation), `PositionDeltaEngine` (trigger path calculations).
  - **Payload Structure**:
    ```json
    {
      "event_id": "db8cf888-29cf-4a11-bcf7-0d04b8dfad0c",
      "event_type": "identity.goals_updated",
      "timestamp": "2026-06-09T02:04:18Z",
      "data": {
        "user_id": "e229c9bb-36db-4876-b9a6-d6b797cc963a",
        "target_role": "AI Platform Engineer",
        "target_compensation_min": 190000.00,
        "target_compensation_max": 240000.00
      }
    }
    ```

## 9. Background Jobs
No periodic background tasks are registered by this module. All operations are synchronous API requests or asynchronous event-triggered workflows handled in downstream modules.

## 10. Acceptance Criteria

- **Scenario: User Registration**
  - **Given** a new email address and password,
  - **When** calling `POST /api/v2/auth/register`,
  - **Then** create user, return HTTP 201 with user metadata, and verify corresponding records in `user_preferences` and `career_goals` are initialized.
- **Scenario: JWT Authentication Middleware**
  - **Given** an API endpoint requires authentication,
  - **When** the client calls it without an Authorization header,
  - **Then** return HTTP 401 Unauthorized.
  - **When** calling it with an expired JWT token,
  - **Then** return HTTP 401 Unauthorized with token expired headers.
- **Scenario: Goal Compensation Validation**
  - **Given** a user attempts to update their goals,
  - **When** `target_compensation_min` is greater than `target_compensation_max`,
  - **Then** return HTTP 422 Unprocessable Entity and block persistence.

## 11. Edge Cases
- **Token Rotation Race Conditions**: If a user double-clicks or triggers multiple refresh calls in parallel, one might fail due to database rotation. To prevent logout, the system allows a 10-second grace period where the old refresh token remains valid for rotation once.
- **Duplicate Registration**: If a user registers with an existing email address, the service must throw a generic "User already exists" exception (HTTP 409 Conflict) and prevent email enumeration attacks by ensuring registration routes execute at a uniform time using constant-time comparisons.
- **Malformed JWT Signature**: If a token with an invalid signature is presented, the system must return HTTP 401 Unauthorized instantly without reaching downstream middleware.

## 12. Test Requirements
- **Unit Tests**:
  - Assert bcrypt correctly hashes and validates password strings.
  - Assert JWT access tokens expire in exactly 15 minutes, and refresh tokens expire in 7 days.
- **Integration Tests**:
  - Test the full Auth cycle: Register -> Login (receive tokens) -> Use access token on protected resource -> Refresh access token -> Revoke refresh token.
  - Validate validation rules for career goal inputs (negative compensation, empty target role).

## 13. Dependencies
This feature depends directly on the platform configuration defined in [project-setup-architecture.md](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/feature-specs/project-setup-architecture.md).
Downward features that depend on this are:
- [career-profile-domain.md](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/feature-specs/career-profile-domain.md)
- [career-health-score-engine-v1.md](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/feature-specs/career-health-score-engine-v1.md)
- [career-dashboard.md](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/feature-specs/career-dashboard.md)
