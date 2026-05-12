from __future__ import annotations

from fastapi import Header, HTTPException
from jwt import InvalidTokenError, decode

from app.core.config import settings


def get_authenticated_user_id(
    authorization: str | None = Header(default=None, alias="Authorization"),
) -> str | None:
    """Return authenticated user_id from JWT bearer token.

    If auth is disabled and no token is provided, returns None to preserve local/dev flow.
    """
    if not authorization:
        if settings.auth_required:
            raise HTTPException(status_code=401, detail="Missing authorization token")
        return None

    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")

    token = authorization.split(" ", 1)[1].strip()
    if not token:
        raise HTTPException(status_code=401, detail="Missing bearer token")

    if not settings.jwt_secret:
        raise HTTPException(
            status_code=500,
            detail="Server JWT configuration is missing",
        )

    try:
        payload = decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except InvalidTokenError as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired token") from exc

    user_id = payload.get("sub") or payload.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Token missing user identity")

    return str(user_id)


def enforce_user_access(request_user_id: str, authenticated_user_id: str | None) -> None:
    """Ensure users can only operate on their own user-scoped resources."""
    if authenticated_user_id is None:
        if settings.auth_required:
            raise HTTPException(status_code=401, detail="Authentication required")
        return

    if request_user_id != authenticated_user_id:
        raise HTTPException(status_code=403, detail="Access denied for requested user")
