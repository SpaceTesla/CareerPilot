# Feature Specification: Architecture Documentation

## 1. Purpose
The Architecture Documentation feature establishes the documentation standards and delivery formats for CareerPilot. It ensures that system diagrams, domain models, agent graphs, and Architecture Decision Records (ADRs) are maintained using code-first tools (like Mermaid and Markdown) directly in the source control repository.

This guarantees that documentation remains synchronized with codebase changes, simplifying developer onboarding, reducing operations errors, and documenting core design choices.

---

## 2. User Value
Directly supports the **Operations & Maintenance** context of the **Career Intelligence Compounding Loop**.
- **Compounding Loop Connection**: Clear documentation of domain boundaries (e.g., separating Career Profile and Market Intelligence) prevents codebase complexity from slowing down development. Keeping the architecture documentation updated ensures developers can quickly implement and calibrate new agent workflows, maintaining the platform's development speed.
- **User Benefit**: Users experience a stable platform with faster feature updates and minimal downtime, as the engineering team has clear, up-to-date documentation to resolve issues.

---

## 3. Requirements
- **System Architecture Diagrams**: Maintain high-level C4 model diagrams showing platform systems, databases, and network boundaries.
- **Domain Architecture Diagrams**: Maintain diagrams showing the boundaries, interfaces, and database relationships of each context.
- **Workflow Diagrams**: Maintain sequence and state-machine diagrams illustrating Temporal workflow steps.
- **Agent Architecture Diagrams**: Document LangGraph state definitions, node routers, and supervisor loop logic.
- **Deployment Diagrams**: Map production configurations showing Docker containers, Kubernetes namespaces, load balancers, and databases.
- **Architecture Decision Records (ADRs)**: Standardize on the Michael Nygard format for documenting system changes and design choices.
- **Developer Onboarding Guide**: Provide setup instructions, code styles, testing practices, and PR guidelines for new developers.
- **Operations Guide**: Provide guides for database backups, scaling limits, metric thresholds, and alert triage.
- **API Documentation**: Maintain automated, interactive OpenAPI specifications `/docs` powered by FastAPI.
- **Portfolio Showcase Documentation**: Provide structured architecture overviews for developers and users.

---

## 4. Database Changes
No database schema changes are required. All documentation, diagrams, and ADRs are stored as Markdown and Mermaid source code files directly in the `/docs` folder of the Git repository.

---

## 5. API Endpoints

### Get Architecture Decision Records
- **HTTP Method**: `GET`
- **Route**: `/api/v2/docs/adrs`
- **Response Payload (JSON)**:
```json
{
  "adrs": [
    {
      "id": "adr-001",
      "title": "Use Temporal for Long-Running Workflows",
      "status": "ACCEPTED",
      "date": "2026-06-08",
      "summary": "We adopted Temporal to guarantee execution durability and simplify multi-tier application retries."
    },
    {
      "id": "adr-002",
      "title": "Adopt LangGraph for Agent Workflows",
      "status": "ACCEPTED",
      "date": "2026-06-08",
      "summary": "We chose LangGraph to manage complex state transitions and loop behaviors in agent reasoning."
    }
  ]
}
```
- **HTTP Status Codes**:
  - `200 OK`: ADR list retrieved.
  - `401 Unauthorized`: Invalid credentials.

### Fetch OpenAPI Specification
- **HTTP Method**: `GET`
- **Route**: `/api/v2/docs/openapi.json`
- **Response Headers**:
  - `Content-Type: application/json`
- **Response Body**: Standard OpenAPI JSON specification.
- **HTTP Status Codes**:
  - `200 OK`: Specification returned.

---

## 6. Domain Models

```python
from pydantic import BaseModel
from typing import List

class ADRItem(BaseModel):
    id: str
    title: str
    status: str
    date: str
    summary: str

class ADRListResponse(BaseModel):
    adrs: List[ADRItem]
```

---

## 7. Services

### Class: `DocumentationService`
Parses local Markdown files in the `/docs` directory to serve ADR and system data over the API.

- **Method**: `list_adrs`
  - **Inputs**: None.
  - **Return Type**: `ADRListResponse`
  - **Responsibilities**:
    - Scans the `/docs/adrs/` directory for Markdown files.
    - Parses YAML frontmatter headers from each file (containing ID, title, status, date, and summary).
    - Returns compiled ADR metadata.

- **Method**: `get_openapi_spec`
  - **Inputs**: None.
  - **Return Type**: `str` (JSON spec content)
  - **Responsibilities**:
    - Dynamically exports the FastAPI OpenAPI specification.

---

## 8. Events
No event-driven mechanics exist for documentation. Documentation updates are handled via Git version control workflows.

---

## 9. Background Jobs
No scheduled background jobs. Documentation compiles statically during container build stages.

---

## 10. Acceptance Criteria
- **Scenario**: Developer reads ADR list.
  - **Given**: Two Markdown files exist in the `/docs/adrs/` folder.
  - **When**: A request is made to `/api/v2/docs/adrs`.
  - **Then**: The system parses the Markdown files and returns them as structured JSON objects.
- **Scenario**: API spec changes.
  - **Given**: A new router endpoint is registered in FastAPI.
  - **When**: A request is made to `/api/v2/docs/openapi.json`.
  - **Then**: The returned JSON includes the schema, parameters, and responses of the new endpoint.

---

## 11. Edge Cases
- **Diagram-to-Code Drift**: Developers update application code but forget to update the corresponding Mermaid diagrams.
  - **Resolution**: Use Markdown linting scripts in the CI pipeline to verify Mermaid syntax and ensure all diagram files match current project structures.
- **Broken File Links**: Markdown links reference documents that have been moved or deleted.
  - **Resolution**: Use markdown-link-check utilities in the CI pipeline to scan the `/docs` folder and fail builds on broken links.

---

## 12. Test Requirements
- **Unit Tests**: Test the markdown frontmatter parser to verify it handles missing values and malformed YAML headers correctly.
- **Integration Tests**: Hit the documentation endpoints directly to verify correct folder navigation and file read permissions.

---

## 13. Dependencies
- **[F5.3: Outcome Calibration](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/feature-specs/outcome-calibration.md)**: Integrates model calibration specs into documentation.
- **[F6.2: Metrics & Monitoring](file:///C:/Users/shiva/Desktop/Projects/CareerPilot/docs/feature-specs/metrics-monitoring.md)**: Integrates metric definitions and alert rules into the Operations Guide.

---
