# CareerPilot Implementation Doctrine

## Purpose

This document defines the non-negotiable engineering principles for CareerPilot.

All implementation decisions must comply with this doctrine.

When conflicts occur:

Architecture Document > Doctrine > Feature Specification > Task Description

---

## Commit message guidance

Use Conventional Commit style for all commits touching the repository. Each commit should have a compact header followed by a list of technical change items or bullet points summarizing the work.

Header format (required):

- type(scope): short-summary

Where `type` is one of `feat`, `fix`, `docs`, `refactor`, `perf`, `test`, `chore`, `ci`, `build`, etc. `scope` is a short module or area (optional but recommended).

Body format (required):

- A bulleted list using `-` for each distinct code modification, schema change, added service/method, bug fix, configuration update, or new integration test.
- Keep bullets concise, technical, and direct, explaining what was changed and where.

Checklist for commit bodies:

- List all database model, schema, and migration changes.
- Detail new services, interfaces, logic components, and helper integrations.
- Enumerate updated/added API route controllers and endpoint changes.
- Outline newly introduced tests or changes to test isolation setup.

Examples

Feature change:

```text
feat(market): fix market ingestion serialization, regex parsing, and test isolation
- Use Pydantic's model_dump(mode="json") to convert Decimal and date fields to JSON-serializable primitives for raw ingestion payloads
- Add support for 'a year', 'a yr', 'a month', 'an hour' formats in salary extraction regex
- Clear database tables (job postings, duplicates, compensation, runs) before running integration tests to ensure test isolation
- Configure Ruff to ignore B008 and ARG001 in pyproject.toml to match FastAPI endpoint conventions
- Fix misc style violations: wrap long lines under 88 characters, use .is_(None) for SQL checks, and utilize implicit truth testing
```

Feature / Wave implementation example:

```text
feat(intelligence): implement Wave 5 intelligence synthesis and career dashboard
- Define new database models for health scores, targets, deltas, snapshots, ghost postings, opportunity scores, and dashboard analytics
- Generate Alembic migration 90c09ec38235 to create target specification, score, and signal tables
- Implement CareerHealthService to compute composite health scores across five weighted metrics
- Implement PositionDeltaService to detect missing target skills, identify top-3 gaps, and generate recommendations
- Implement services for GhostPostingDetectorService, OpportunityScoringService, and CompanyIntelligenceService
- Create DashboardAggregationService to gather dashboard widget payloads concurrently with Redis-backed caching and eviction
- Define FastAPI routes for /api/v2/intelligence and /api/v2/dashboard registered under versioned routers
- Add full end-to-end integration tests in test_intelligence_dashboard.py covering the dashboard widget and analytics lifecycle
```

PR title guidance

- Use the commit header as the PR title when possible.
- If multiple commits are in a PR, use the most-significant commit header or craft a concise PR title and reference commits in the description.

When to use which `type` (quick guide):

- `feat`: new features or endpoints
- `fix`: bug fixes
- `docs`: README, comments, or docs changes
- `refactor`: code changes that do not alter behavior
- `perf`: performance improvements
- `test`: tests or test infra changes
- `chore`: tooling, dependency bumps, housekeeping
- `ci`: CI pipeline changes
- `build`: build system changes

Keep commit hygiene: small, focused commits are easier to review and revert.

# Core Philosophy

CareerPilot is an intelligence platform.

The primary objective is not automation.

The primary objective is producing accurate career intelligence that compounds over time.

Every feature must contribute to one or more of:

- Career Health Score
- Position Delta
- Market Intelligence
- Opportunity Intelligence
- Outcome Learning

Features that do not strengthen the intelligence loop should not be introduced.

---

# Development Principles

## Backend First

Implement backend systems before frontend experiences.

Required order:

1. Schema
2. Repository
3. Service
4. API
5. Tests
6. UI

Never build UI before business logic exists.

---

## Vertical Slice Development

Implement complete features.

Avoid:

- Building all database models first
- Building all APIs first
- Building all frontend pages first

Preferred:

Feature → End-to-End Completion

Example:

Authentication

- Schema
- Service
- API
- Tests
- UI

Then move to next feature.

---

## Explicit Domain Ownership

Each domain owns its own models, services, APIs, and workflows.

Domains:

- Identity Context
- Career Profile Context
- Market Intelligence Context
- Intelligence Synthesis Context
- Execution Context
- Strategy Context

Cross-domain coupling must be minimized.

---

## Explainability First

Every intelligence output must include evidence.

Never produce:

- Health scores without reasoning
- Rankings without rationale
- Recommendations without supporting evidence

All intelligence outputs must be explainable.

---

## Outcome Driven Design

Outcome data is the most valuable asset in the system.

Preserve:

- Application outcomes
- Interview outcomes
- Offer outcomes
- Career progression outcomes

Never discard outcome data.

---

## Human Approval Gates

High-impact actions require approval.

Examples:

- Job applications
- Profile modifications
- Strategy updates

Agents may recommend.

Humans approve.

---

## Observability Required

Every service must expose:

- Structured logs
- Metrics
- Health checks

Critical workflows must be traceable.

---

## Testing Requirements

Minimum:

- Unit tests for business logic
- Integration tests for APIs
- Workflow tests for Temporal workflows

No feature is complete without tests.

---

## Security Requirements

- JWT authentication
- Secrets via environment variables
- No hardcoded credentials
- Input validation everywhere
- Principle of least privilege

---

## AI System Requirements

All agents must:

- Operate on typed state
- Produce structured outputs
- Be observable
- Be evaluatable

Prompt-only systems are prohibited.

---

## Retrieval Requirements

Default retrieval pipeline:

BM25
→ Vector Search
→ Reranking

Single-stage retrieval is not allowed.

---

## Architecture Requirements

Preferred Stack:

- FastAPI
- PostgreSQL
- Redis
- Celery
- Temporal
- Qdrant
- LangGraph
- Docker

Technology substitutions require justification.

---

## Formatting & Documentation Requirements

- Whenever referring to a filename in documentation, pull request descriptions, code comments, or commit messages, surround the filename with backticks (e.g., `IMPLEMENTATION_DOCTRINE.md`).

---

## Completion Criteria

A feature is complete only when:

- Code implemented
- Tests passing
- Documentation updated
- Metrics added
- Health checks added
- CI passing

Anything less is incomplete.
