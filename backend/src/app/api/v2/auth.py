from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.models import User
from app.schemas.auth import RefreshTokenRequest, Token, UserCreate, UserResponse
from app.services.auth_service import AuthService
from app.services.database_service import DatabaseService
from app.services.identity_service import IdentityService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED
)
async def register(
    user_in: UserCreate,
    db: AsyncSession = Depends(DatabaseService.get_session),  # noqa: B008
):
    """
    Registers a new user account, creates default preferences and goals,
    and publishes registration event.
    """
    user = await IdentityService.create_user(db, user_in)
    return user


@router.post("/login", response_model=Token)
async def login(
    user_in: UserCreate,
    db: AsyncSession = Depends(DatabaseService.get_session),  # noqa: B008
):
    """
    Authenticates email and password, returning access and refresh tokens.
    """
    stmt = select(User).where(User.email == user_in.email)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user or not AuthService.verify_password(
        user_in.password, user.password_hash
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User is inactive",
        )

    access_token = AuthService.create_access_token(user.id)
    refresh_token = await AuthService.create_refresh_token(db, user.id)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


@router.post("/refresh", response_model=Token)
async def refresh(
    req: RefreshTokenRequest,
    db: AsyncSession = Depends(DatabaseService.get_session),  # noqa: B008
):
    """
    Rotates a refresh token to issue new access and refresh tokens.
    """
    tokens = await AuthService.rotate_tokens(db, req.refresh_token)
    return tokens
