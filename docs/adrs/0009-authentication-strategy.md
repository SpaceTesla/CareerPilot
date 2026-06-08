# ADR 0009: Authentication Strategy

## Status
Accepted

## Context
CareerPilot is a career operating system and intelligence platform that processes highly sensitive user data, including professional history, resume documents, compensation details, career goals, and private application outcomes. Unauthorized access to this data represents a major security and privacy risk.

In the design of CareerPilot V2, the system is structured around decoupled domain contexts. The authentication strategy must support this architecture by providing secure, stateless, and verifiable session management across domains (e.g., Identity, Career Profile, Execution, Intelligence Synthesis) without introducing high-latency database queries on every API request.

Key constraints and objectives include:
1. **Stateless Authorization**: Requests to the backend API services (built on FastAPI) must be authenticated statelessly to keep response latency low and prevent session-store bottlenecks.
2. **Secure Persistence**: Password storage must resist brute-force and offline dictionary attacks.
3. **Session Durability & Security**: Users should remain logged in during active usage (passive/weekly career tracking), but the credentials used to access sensitive APIs must be short-lived to limit the window of opportunity for intercepted tokens.
4. **Environment Isolation**: Secrets, credentials, and signing keys must be managed dynamically and never committed to source control.
5. **Alignment with Core Principles**: Compliance with the security guidelines in [IMPLEMENTATION_DOCTRINE.md](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/IMPLEMENTATION_DOCTRINE.md).

## Decision
We will implement a hybrid token-based authentication system using symmetric JSON Web Tokens (JWT) for session management and authorization, coupled with `bcrypt` for password hashing, and Pydantic `BaseSettings` for environment variable configuration.

The implementation details are as follows:

### 1. Cryptographic Password Hashing
- **Algorithm**: `bcrypt` (specifically `bcrypt` via the `passlib` or `cryptography` libraries in Python).
- **Work Factor (Cost)**: Configured to `12` by default. This provides a balance between verification latency (approx. 250-300ms on modern CPUs) and resilience against offline brute-force attacks.
- **Salt Generation**: Unique, random salts generated automatically by `bcrypt` per password hash.

### 2. Token-Based Authentication Strategy
The system will issue two classes of tokens upon successful authentication:

#### A. Access Tokens
- **Type**: JSON Web Token (JWT).
- **Signing Algorithm**: HMAC using SHA-256 (`HS256`).
- **Signing Key**: Symmetric key (`JWT_SECRET_KEY`) loaded from the environment.
- **Lifespan**: `15 minutes`.
- **Payload**: Contains standard claims:
  - `sub` (Subject): The unique user UUID.
  - `exp` (Expiration Time): Unix epoch timestamp.
  - `type`: Explicitly set to `access`.
- **Transmission**: Sent via HTTP `Authorization: Bearer <token>` headers. Access tokens are stateless and are verified in-memory by FastAPI middleware without querying the database.

#### B. Refresh Tokens
- **Type**: Random cryptographically secure UUID or high-entropy string wrapped in a signed JWT.
- **Lifespan**: `7 days`.
- **Payload**: Contains standard claims with `type` set to `refresh`.
- **Transmission**: Passed via secure, HTTP-only, SameSite=Lax cookies (or JSON response payloads for cross-origin client flexibilities, rotating on every usage).
- **State Tracking**: Unlike access tokens, active refresh tokens are tracked in the database to allow immediate revocation (e.g., on logout or security breach). The database stores a hashed representation of the active refresh token to protect against database leak compromises.
- **Token Rotation (RTR)**: Every time a refresh token is used to obtain a new access token, the old refresh token is invalidated, and a new refresh token is issued.
- **Race Condition Mitigation**: To prevent concurrent API refresh requests from locking out users, the system allows a `10-second grace period`. During this window, an recently rotated refresh token is still accepted once to issue new tokens.

### 3. Session Middleware & Injection
FastAPI dependency injection is used to enforce authentication on routes:
- **Verification**: Middleware decodes and verifies the signature and expiration of the JWT.
- **Current User Injection**: The verified user UUID from the `sub` claim is used to retrieve the user's context, caching the user model locally within the request state to avoid redundant DB queries.

### 4. Configuration Security
- All keys, secrets, and configurations are loaded via Pydantic `BaseSettings` from OS environment variables.
- Default development values are defined, but production environments enforce strict validations requiring external secrets.

## Alternatives Considered

### 1. Asymmetric JWTs (RS256/ES256)
- **Description**: Using a private key on the authentication service to sign tokens, and public keys on other domain services to verify them.
- **Why Rejected**: CareerPilot V2 is developed as a modular service deployed together in a single system framework (FastAPI). Asymmetric cryptography adds key management complexity (distribution of public keys, key rotation routines) without immediate benefit, as all domains currently share a secure backend trust boundary. If the architecture transitions to fully decoupled microservices in the future, we can migrate from HS256 to RS256/ES256.

### 2. Stateful Session Cookies (Redis-backed Sessions)
- **Description**: Storing active sessions in Redis and passing session IDs via cookies.
- **Why Rejected**: While this allows instant revocation of all active sessions and avoids token expiration logic on the client, it increases connection overhead to Redis on every single API request. In an intelligence platform that runs heavy analysis and async evaluations, stateless JWT verification helps maintain high throughput and low latency at the gateway level.

### 3. PBKDF2 or Argon2 for Hashing
- **Description**: Argon2 is the winner of the Password Hashing Competition (PHC) and offers memory-hard hashing.
- **Why Rejected**: Argon2 is technically superior to bcrypt, but bcrypt is highly standard, widely supported across all platform environments, and has optimized, natively compiled bindings in Python that require zero extra C-library compilation steps in Docker containers. Bcrypt provides more than sufficient defense margins for candidate profiles.

## Consequences

### Positive
- **High Performance**: Verifying access tokens statelessly requires zero database roundtrips, resulting in sub-millisecond authentication overhead for protected API routes.
- **Reduced Attack Window**: If an access token is compromised, its 15-minute lifespan limits the duration of the exploit.
- **Secure Revocation**: Refresh token rotation combined with database tracking enables the backend to invalidate sessions on demand (e.g., during explicit logouts).
- **Developer Simplicity**: Symmetric signing (HS256) simplifies local and containerized deployment, aligning with [project-setup-architecture.md](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/feature-specs/project-setup-architecture.md).

### Negative
- **Database Writes on Token Refresh**: Although access token verification is database-free, rotating the refresh token requires writing the new token hash to the PostgreSQL `users` or a dedicated tracking table, introducing write overhead once every 15 minutes per active client.
- **Client Complexity**: Frontend applications must monitor access token lifetimes, store tokens securely in-memory, handle silent refreshes, and gracefully recover from expired sessions.

## Tradeoffs

### Immediate Simplicity vs. Long-Term Distribution
We chose symmetric signing (`HS256`) over asymmetric signing (`RS256`). This trades minor future-proofing (where separate microservices might verify tokens using only public keys) for immediate implementation speed, ease of container configuration, and reduced code complexity.

### Security Tightness vs. Concurrent Request Resilience
By choosing Refresh Token Rotation (RTR) with a 10-second grace window, we trade absolute token uniqueness for operational reliability. Without the grace period, concurrent browser requests (such as a page refresh triggering parallel API queries) would result in token reuse detection false-positives, force-logging out active users. The 10-second window represents an acceptable security tradeoff.
