# CareerPilot Implementation Doctrine

## Purpose

This document defines the non-negotiable engineering principles for CareerPilot.

All implementation decisions must comply with this doctrine.

When conflicts occur:

Architecture Document > Doctrine > Feature Specification > Task Description

---

## Commit message guidance

Use Conventional Commit style for all commits touching the repository. Each commit should have a compact header and a short, 1-2 line summary (the "Short"), followed by an optional multi-line description that explains why the change was made and any migration or follow-up steps.

Header format (required):

- type(scope): short-summary

Where `type` is one of `feat`, `fix`, `docs`, `refactor`, `perf`, `test`, `chore`, `ci`, `build`, etc. `scope` is a short module or area (optional but recommended).

Body format (recommended):

- Short: One-line summary expanding the header (1-2 lines).
- Description: Longer explanation (3-6 lines) with reasoning, migration notes, and testing guidance.

Checklist for commit bodies:

- Explain the why, not just the what.
- Note any breaking changes or required migrations.
- Mention related tickets/PRs if applicable.
- Include test notes: what to run and what to expect.

Examples

Documentation change:

```text
docs(implementation): clarify doctrine ordering and intent

Short: Clarify precedence: Architecture > Doctrine > Spec.

Description:
Make the precedence explicit so contributors know which document governs conflict resolution. Add examples and a short rationale: architecture documents describe system shape and may supersede doctrine for urgent architecture-level fixes.
```

Feature change:

```text
feat(agent): require structured outputs and observability

Short: Enforce typed outputs and observability for agents.

Description:
Require all agents to produce typed, structured outputs and emit observability events to enable evaluation and tracing. Add unit tests for output schema and update agent bootstrap to register metrics. Migration: update existing agents to implement `to_struct()` by YYYY-MM-DD.
```

Refactor (code/structure) example:

```text
refactor(api): reorganize route modules for readability

Short: Move routes into feature-scoped modules and simplify imports.

Description:
Split the large `api.v1` router into smaller feature modules (identity, resume, analysis). Update import paths and tests. This is a non-functional change; CI should pass without data migrations. Follow-up: update docs and adjust any tooling that depends on old import paths.
```

Bugfix example:

```text
fix(db): ensure transaction rollback on repository errors

Short: Rollback DB session on repository exceptions.

Description:
Previously some repository exceptions left sessions open and caused inconsistent states. Wrap repository operations with session context manager and add an integration test to assert rollback behavior on error.
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

## Completion Criteria

A feature is complete only when:

- Code implemented
- Tests passing
- Documentation updated
- Metrics added
- Health checks added
- CI passing

Anything less is incomplete.
