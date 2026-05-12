"""Job application tracking API routes."""

from __future__ import annotations

import asyncio
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, HttpUrl

from app.api.dependencies.auth import enforce_user_access, get_authenticated_user_id
from app.infrastructure.database.connection import get_session
from app.infrastructure.database.models import JobApplication
from app.infrastructure.database.repositories.job_application_repository import (
    JobApplicationRepository,
)

router = APIRouter(prefix="/applications", tags=["applications"])

APPLICATION_STATUSES = {"applied", "interviewing", "offer", "rejected", "withdrawn"}


def _validate_uuid(value: str, field_name: str) -> None:
    try:
        uuid.UUID(value)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid {field_name}") from exc


def _serialize(app: JobApplication) -> dict[str, Any]:
    return {
        "id": app.id,
        "user_id": app.user_id,
        "job_title": app.job_title,
        "company": app.company,
        "job_url": app.job_url,
        "source": app.source,
        "location": app.location,
        "status": app.status,
        "notes": app.notes,
        "job_data": app.job_data_json,
        "applied_at": app.applied_at.isoformat() if app.applied_at else None,
        "updated_at": app.updated_at.isoformat() if app.updated_at else None,
    }


# ── Request bodies ──────────────────────────────────────────────────────────────


class CreateApplicationRequest(BaseModel):
    user_id: str
    job_title: str
    company: str | None = None
    job_url: str | None = None
    source: str | None = None
    location: str | None = None
    status: str = "applied"
    notes: str | None = None
    job_data: dict[str, Any] | None = None


class UpdateApplicationRequest(BaseModel):
    status: str | None = None
    notes: str | None = None


# ── Endpoints ───────────────────────────────────────────────────────────────────


@router.post("")
async def create_application(
    body: CreateApplicationRequest,
    auth_user_id: str | None = Depends(get_authenticated_user_id),
) -> dict[str, Any]:
    """Track a new job application."""
    _validate_uuid(body.user_id, "user_id")
    enforce_user_access(body.user_id, auth_user_id)

    if body.status not in APPLICATION_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"status must be one of: {', '.join(sorted(APPLICATION_STATUSES))}",
        )

    app_id = str(uuid.uuid4())
    with get_session() as session:
        repo = JobApplicationRepository(session)

        # Prevent duplicate tracking for the same URL
        if body.job_url:
            existing = repo.get_by_url(body.user_id, body.job_url)
            if existing:
                return _serialize(existing)

        application = JobApplication(
            id=app_id,
            user_id=body.user_id,
            job_title=body.job_title,
            company=body.company,
            job_url=body.job_url,
            source=body.source,
            location=body.location,
            status=body.status,
            notes=body.notes,
            job_data_json=body.job_data,
        )
        repo.create(application)
        return _serialize(application)


@router.get("")
async def list_applications(
    user_id: str = Query(..., description="User ID"),
    status: str | None = Query(None, description="Filter by status"),
    auth_user_id: str | None = Depends(get_authenticated_user_id),
) -> dict[str, Any]:
    """List all tracked job applications for a user."""
    _validate_uuid(user_id, "user_id")
    enforce_user_access(user_id, auth_user_id)

    if status and status not in APPLICATION_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"status must be one of: {', '.join(sorted(APPLICATION_STATUSES))}",
        )

    with get_session() as session:
        repo = JobApplicationRepository(session)
        applications = repo.get_by_user(user_id, status)
        return {
            "applications": [_serialize(a) for a in applications],
            "total": len(applications),
            "by_status": {
                s: sum(1 for a in applications if a.status == s)
                for s in APPLICATION_STATUSES
            },
        }


@router.patch("/{application_id}")
async def update_application(
    application_id: str,
    body: UpdateApplicationRequest,
    user_id: str = Query(..., description="User ID"),
    auth_user_id: str | None = Depends(get_authenticated_user_id),
) -> dict[str, Any]:
    """Update application status or notes."""
    _validate_uuid(user_id, "user_id")
    _validate_uuid(application_id, "application_id")
    enforce_user_access(user_id, auth_user_id)

    if body.status and body.status not in APPLICATION_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"status must be one of: {', '.join(sorted(APPLICATION_STATUSES))}",
        )

    updates: dict[str, Any] = {}
    if body.status is not None:
        updates["status"] = body.status
    if body.notes is not None:
        updates["notes"] = body.notes

    with get_session() as session:
        repo = JobApplicationRepository(session)
        app = repo.get_by_id(application_id)
        if not app:
            raise HTTPException(status_code=404, detail="Application not found")
        if app.user_id != user_id:
            raise HTTPException(status_code=403, detail="Access denied")
        updated = repo.update(application_id, updates)
        if not updated:
            raise HTTPException(status_code=404, detail="Application not found")
        return _serialize(updated)


@router.delete("/{application_id}")
async def delete_application(
    application_id: str,
    user_id: str = Query(..., description="User ID"),
    auth_user_id: str | None = Depends(get_authenticated_user_id),
) -> dict[str, Any]:
    """Delete a tracked application."""
    _validate_uuid(user_id, "user_id")
    _validate_uuid(application_id, "application_id")
    enforce_user_access(user_id, auth_user_id)

    with get_session() as session:
        repo = JobApplicationRepository(session)
        app = repo.get_by_id(application_id)
        if not app:
            raise HTTPException(status_code=404, detail="Application not found")
        if app.user_id != user_id:
            raise HTTPException(status_code=403, detail="Access denied")
        repo.delete(application_id)
        return {"deleted": True, "id": application_id}


@router.post("/auto-fill")
async def auto_fill_application(
    body: dict[str, Any],
    auth_user_id: str | None = Depends(get_authenticated_user_id),
) -> dict[str, Any]:
    """
    Start a background Playwright autofill job.
    Returns a task_id immediately (non-blocking).
    Poll GET /auto-fill/{task_id} for progress + screenshots.
    Automatically uses a saved portal session if one exists for this user.
    """
    user_id: str = body.get("user_id", "")
    job_url: str = body.get("job_url", "")
    job_title: str = body.get("job_title", "")
    job_company: str = body.get("job_company", "")

    if not user_id or not job_url:
        raise HTTPException(status_code=400, detail="user_id and job_url are required")

    _validate_uuid(user_id, "user_id")
    enforce_user_access(user_id, auth_user_id)

    from app.services.automation_service import automation_service

    task_id = automation_service.create_fill_task(user_id, job_url, job_title, job_company)
    asyncio.create_task(automation_service._run_fill_task(task_id, user_id, job_url))
    return {
        "task_id": task_id,
        "status": "started",
        "portal": automation_service.get_fill_task(task_id)["portal"],
        "poll_url": f"/applications/auto-fill/{task_id}",
    }


@router.post("/auto-fill/{task_id}/confirm")
async def confirm_autofill_task(
    task_id: str,
    body: dict[str, Any],
    auth_user_id: str | None = Depends(get_authenticated_user_id),
) -> dict[str, Any]:
    """
    Confirm or cancel a pending autofill submission.
    Body: { "user_id": "...", "confirmed": true | false }
    """
    user_id: str = body.get("user_id", "")
    confirmed: bool = bool(body.get("confirmed", False))

    if not user_id:
        raise HTTPException(status_code=400, detail="user_id is required")
    _validate_uuid(user_id, "user_id")
    enforce_user_access(user_id, auth_user_id)

    from app.services.automation_service import automation_service

    task = automation_service.get_fill_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found.")
    if task["user_id"] != user_id:
        raise HTTPException(status_code=403, detail="Access denied.")
    if task["status"] != "awaiting_confirmation":
        raise HTTPException(status_code=409, detail="Task is not awaiting confirmation.")

    ok = automation_service.confirm_fill_task(task_id, confirmed)
    if not ok:
        raise HTTPException(status_code=409, detail="Confirmation event not found — task may have timed out.")
    return {"task_id": task_id, "confirmed": confirmed}


@router.get("/auto-fill/{task_id}")
async def get_autofill_task(
    task_id: str,
    user_id: str = Query(...),
    auth_user_id: str | None = Depends(get_authenticated_user_id),
) -> dict[str, Any]:
    """
    Poll the status of a running autofill task.

    Response fields:
        task_id       : UUID of the task
        status        : pending | running | done | error
        portal        : detected portal name
        result_status : filled | no_fields_found | unsupported | error | null
        steps         : list of {step, message, screenshot (base64), timestamp}
        fields_filled : list of field names filled
        error         : error message if status=error
        finished_at   : ISO timestamp when done, else null
    """
    _validate_uuid(user_id, "user_id")
    enforce_user_access(user_id, auth_user_id)

    from app.services.automation_service import automation_service

    task = automation_service.get_fill_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found.")
    if task["user_id"] != user_id:
        raise HTTPException(status_code=403, detail="Access denied.")
    return task


@router.post("/session/login")
async def save_portal_session(
    body: dict[str, Any],
    auth_user_id: str | None = Depends(get_authenticated_user_id),
) -> dict[str, Any]:
    """
    Log in to a job portal once with email + password.
    The session (cookies) is saved to the database and reused automatically
    by the auto-fill endpoint — no login required on subsequent calls.

    Supported portals: indeed, linkedin, naukri, glassdoor
    """
    user_id: str = body.get("user_id", "")
    portal: str = body.get("portal", "").lower()
    email: str = body.get("email", "")
    password: str = body.get("password", "")

    if not all([user_id, portal, email, password]):
        raise HTTPException(
            status_code=400,
            detail="user_id, portal, email and password are required",
        )

    _validate_uuid(user_id, "user_id")
    enforce_user_access(user_id, auth_user_id)

    from app.services.automation_service import automation_service

    result = await automation_service.login_and_save_session(user_id, portal, email, password)
    if result.get("status") == "failed":
        raise HTTPException(status_code=401, detail=result["message"])
    if result.get("status") == "error":
        raise HTTPException(status_code=500, detail=result["message"])
    return result


@router.get("/session/status")
async def get_session_status(
    user_id: str = Query(..., description="User ID"),
    auth_user_id: str | None = Depends(get_authenticated_user_id),
) -> dict[str, Any]:
    """List which portals have a saved login session for this user."""
    _validate_uuid(user_id, "user_id")
    enforce_user_access(user_id, auth_user_id)

    from app.services.automation_service import automation_service

    sessions = automation_service.get_session_status(user_id)
    return {"sessions": sessions, "total": len(sessions)}


@router.delete("/session/{portal}")
async def delete_portal_session(
    portal: str,
    user_id: str = Query(..., description="User ID"),
    auth_user_id: str | None = Depends(get_authenticated_user_id),
) -> dict[str, Any]:
    """Delete a saved portal session."""
    _validate_uuid(user_id, "user_id")
    enforce_user_access(user_id, auth_user_id)

    from app.services.automation_service import automation_service

    deleted = automation_service.delete_session(user_id, portal)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"No saved session for portal '{portal}'")
    return {"deleted": True, "portal": portal}


@router.post("/session/import")
async def import_browser_session(
    body: dict[str, Any],
    auth_user_id: str | None = Depends(get_authenticated_user_id),
) -> dict[str, Any]:
    """
    Import cookies exported from your real browser (Brave, Chrome, Firefox)
    so that Playwright can reuse your existing login session — including
    Google OAuth sessions — without needing to log in again.

    **How to use (5 steps):**

    1. Install the **EditThisCookie** or **Cookie-Editor** extension in Brave.
    2. Navigate to `indeed.com` (or whichever portal) while already signed in.
    3. Click the extension icon → **Export** (copies a JSON array to your clipboard).
    4. POST that JSON array to this endpoint as `cookies`.
    5. Call `/applications/auto-fill` as normal — it will use the imported session.

    **Supported portals:** indeed, linkedin, naukri, glassdoor

    **Body:**
    ```json
    {
      "user_id": "...",
      "portal": "indeed",
      "cookies": [ ...paste JSON array from extension... ]
    }
    ```
    """
    user_id: str = body.get("user_id", "")
    portal: str = (body.get("portal") or "").lower()
    cookies: list[dict[str, Any]] = body.get("cookies", [])

    if not user_id or not portal:
        raise HTTPException(status_code=400, detail="user_id and portal are required")
    if not isinstance(cookies, list) or len(cookies) == 0:
        raise HTTPException(
            status_code=400,
            detail=(
                "cookies must be a non-empty JSON array. "
                "Export them from EditThisCookie or Cookie-Editor extension."
            ),
        )

    _validate_uuid(user_id, "user_id")
    enforce_user_access(user_id, auth_user_id)

    from app.services.automation_service import automation_service

    result = automation_service.import_session(user_id, portal, cookies)
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result["message"])
    return result
