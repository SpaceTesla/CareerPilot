from __future__ import annotations

from fastapi import Depends, Header, HTTPException
from jwt import InvalidTokenError, decode
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.infrastructure.database.models import User
from app.services.database_service import DatabaseService


def get_authenticated_user_id(
    authorization: str | None = Header(default=None, alias="Authorization"),
) -> str | None:
    """Return authenticated user_id from JWT bearer token.

    If auth is disabled and no token is provided, returns None to preserve
    local/dev flow.
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

    # In case settings.jwt_secret is not set but auth is not required, handle gracefully
    secret = settings.jwt_secret or "replace-with-strong-secret"

    try:
        payload = decode(token, secret, algorithms=[settings.jwt_algorithm])
    except InvalidTokenError as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired token") from exc

    user_id = payload.get("sub") or payload.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Token missing user identity")

    return str(user_id)


async def get_current_user(
    db: AsyncSession = Depends(DatabaseService.get_session),  # noqa: B008
    user_id: str | None = Depends(get_authenticated_user_id),  # noqa: B008
) -> User | None:
    """Return the current database User object if authenticated."""
    if not user_id:
        if settings.auth_required:
            raise HTTPException(status_code=401, detail="Authentication required")
        return None

    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return user


def enforce_user_access(
    request_user_id: str, authenticated_user_id: str | None
) -> None:
    """Ensure users can only operate on their own user-scoped resources."""
    if authenticated_user_id is None:
        if settings.auth_required:
            raise HTTPException(status_code=401, detail="Authentication required")
        return

    if request_user_id != authenticated_user_id:
        raise HTTPException(status_code=403, detail="Access denied for requested user")

