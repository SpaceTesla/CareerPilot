from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta
from uuid import UUID, uuid4

import bcrypt
import jwt
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.infrastructure.database.models import RefreshToken
from app.services.redis_service import RedisService

logger = get_logger(__name__)


class AuthService:
    """
    Handles JWT authentication, token generation, verification, and rotation.
    """

    @staticmethod
    def hash_password(password: str) -> str:
        """
        Hashes password using bcrypt.
        """
        pwd_bytes = password.encode("utf-8")
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(pwd_bytes, salt)
        return hashed.decode("utf-8")

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """
        Validates password matches hash.
        """
        try:
            return bcrypt.checkpw(
                plain_password.encode("utf-8"), hashed_password.encode("utf-8")
            )
        except Exception:
            return False

    @staticmethod
    def create_access_token(user_id: UUID) -> str:
        """
        Issues a short-lived access JWT (15-minute lifespan).
        """
        import time
        now = int(time.time())
        expire = now + 15 * 60
        payload = {
            "sub": str(user_id),
            "exp": expire,
            "type": "access",
        }
        secret = settings.jwt_secret or "replace-with-strong-secret"
        return jwt.encode(payload, secret, algorithm=settings.jwt_algorithm)

    @staticmethod
    async def create_refresh_token(db: AsyncSession, user_id: UUID) -> str:
        """
        Issues a long-lived refresh JWT (7-day lifespan) and tracks it in DB.
        """
        import time
        now_ts = int(time.time())
        expire_ts = now_ts + 7 * 24 * 3600
        token_id = str(uuid4())
        payload = {
            "sub": str(user_id),
            "exp": expire_ts,
            "jti": token_id,
            "type": "refresh",
        }
        secret = settings.jwt_secret or "replace-with-strong-secret"
        token_str = jwt.encode(payload, secret, algorithm=settings.jwt_algorithm)

        token_hash = hashlib.sha256(token_str.encode("utf-8")).hexdigest()

        expire_dt = datetime.utcnow() + timedelta(days=7)

        db_token = RefreshToken(
            id=token_id,
            user_id=str(user_id),
            token_hash=token_hash,
            expires_at=expire_dt,
            is_revoked=False,
        )
        db.add(db_token)
        await db.flush()
        return token_str

    @staticmethod
    async def verify_refresh_token(db: AsyncSession, token: str) -> UUID:
        """
        Decodes refresh token and ensures matching db record exists and is active.
        """
        secret = settings.jwt_secret or "replace-with-strong-secret"
        try:
            payload = jwt.decode(token, secret, algorithms=[settings.jwt_algorithm])
            if payload.get("type") != "refresh":
                raise HTTPException(status_code=401, detail="Invalid token type")
            user_id = UUID(payload["sub"])
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=401, detail="Refresh token expired"
            ) from None
        except jwt.InvalidTokenError:
            raise HTTPException(
                status_code=401, detail="Invalid refresh token"
            ) from None


        token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()

        stmt = select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        result = await db.execute(stmt)
        db_token = result.scalar_one_or_none()

        if not db_token:
            raise HTTPException(status_code=401, detail="Refresh token not found")

        if db_token.is_revoked:
            # Check Redis for race condition grace period (10 seconds)
            try:
                redis_client = RedisService.get_client()
                cached_tokens = await redis_client.get(f"rotated_token:{token_hash}")
                await redis_client.close()
                if cached_tokens:
                    return user_id
            except Exception as e:
                logger.error(f"Redis lookup error for grace period: {e}")

            raise HTTPException(
                status_code=401, detail="Refresh token has been revoked"
            )

        if db_token.expires_at < datetime.utcnow():
            raise HTTPException(status_code=401, detail="Refresh token expired")

        return user_id

    @staticmethod
    async def rotate_tokens(db: AsyncSession, refresh_token: str) -> dict:
        """
        Rotates refresh and access tokens, implementing a 10-second grace period
        for parallel client requests.
        """
        token_hash = hashlib.sha256(refresh_token.encode("utf-8")).hexdigest()

        # Check Redis for race condition grace period first
        try:
            redis_client = RedisService.get_client()
            cached_tokens = await redis_client.get(f"rotated_token:{token_hash}")
            await redis_client.close()
            if cached_tokens:
                logger.info("Serving rotated tokens from grace period cache.")
                return json.loads(cached_tokens)
        except Exception as e:
            logger.error(f"Redis lookup error during token rotation: {e}")

        # Verify old token validity
        user_id = await AuthService.verify_refresh_token(db, refresh_token)

        # Revoke old token in database
        stmt = select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        result = await db.execute(stmt)
        db_token = result.scalar_one_or_none()
        if db_token:
            db_token.is_revoked = True
            await db.flush()

        # Create new tokens
        access_token = AuthService.create_access_token(user_id)
        new_refresh_token = await AuthService.create_refresh_token(db, user_id)

        tokens_response = {
            "access_token": access_token,
            "refresh_token": new_refresh_token,
            "token_type": "bearer",
        }

        # Cache response in Redis with 10 seconds TTL
        try:
            redis_client = RedisService.get_client()
            await redis_client.setex(
                f"rotated_token:{token_hash}", 10, json.dumps(tokens_response)
            )
            await redis_client.close()
        except Exception as e:
            logger.error(f"Failed to cache rotated tokens in Redis: {e}")

        return tokens_response

    @staticmethod
    async def revoke_refresh_token(db: AsyncSession, token: str) -> None:
        """
        Deletes or marks refresh token as revoked.
        """
        token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
        stmt = select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        result = await db.execute(stmt)
        db_token = result.scalar_one_or_none()
        if db_token:
            db_token.is_revoked = True
            await db.flush()
