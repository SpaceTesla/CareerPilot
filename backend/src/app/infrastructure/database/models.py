from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database.connection import Base

try:
    from pgvector.sqlalchemy import Vector as PgVector  # type: ignore[import]
    _PGVECTOR_AVAILABLE = True
except ImportError:
    _PGVECTOR_AVAILABLE = False
    PgVector = None  # type: ignore[assignment,misc]


def now_utc() -> datetime:
    return datetime.utcnow()


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=now_utc, onupdate=now_utc
    )

    profiles: Mapped[list[ResumeProfile]] = relationship(
        "ResumeProfile", back_populates="user"
    )
    preferences: Mapped[UserPreferences | None] = relationship(
        "UserPreferences", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    goals: Mapped[CareerGoals | None] = relationship(
        "CareerGoals", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    refresh_tokens: Mapped[list[RefreshToken]] = relationship(
        "RefreshToken", back_populates="user", cascade="all, delete-orphan"
    )


class ResumeProfile(Base):
    __tablename__ = "resume_profiles"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id"), index=True
    )
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)

    socials_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_data: Mapped[dict[str, Any]] = mapped_column(JSON)

    # pgVector skills embedding (768-dim, null until resume is processed with embeddings enabled)
    if _PGVECTOR_AVAILABLE and PgVector is not None:
        skills_embedding: Mapped[list[float] | None] = mapped_column(
            PgVector(768), nullable=True
        )
    else:
        skills_embedding: Mapped[str | None] = mapped_column(Text, nullable=True)  # type: ignore[assignment]

    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=now_utc, onupdate=now_utc
    )

    user: Mapped[User] = relationship("User", back_populates="profiles")


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id"), index=True
    )
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=now_utc, onupdate=now_utc
    )


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    conversation_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("conversations.id"), index=True
    )
    role: Mapped[str] = mapped_column(String(16))  # user|assistant|system
    content: Mapped[str] = mapped_column(Text)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=now_utc)


class AnalysisHistory(Base):
    __tablename__ = "analysis_history"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id"), index=True
    )
    profile_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("resume_profiles.id"), index=True
    )
    overall_score: Mapped[float] = mapped_column(Text)  # Store as text for flexibility
    grade: Mapped[str | None] = mapped_column(String(1), nullable=True)
    section_scores_json: Mapped[dict[str, Any]] = mapped_column(JSON)
    analysis_data_json: Mapped[dict[str, Any]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc)


class UserSession(Base):
    """Tracks user sessions with their active resume profile."""
    __tablename__ = "user_sessions"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id"), index=True
    )
    profile_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("resume_profiles.id"), index=True
    )
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)  # Session name (e.g., resume filename)
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc)
    last_accessed_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc)


class ResumeProcessingJob(Base):
    """Tracks asynchronous resume processing jobs."""

    __tablename__ = "resume_processing_jobs"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    requested_by_user_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id"), nullable=True, index=True
    )
    resolved_user_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id"), nullable=True, index=True
    )
    profile_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("resume_profiles.id"), nullable=True, index=True
    )
    session_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("conversations.id"), nullable=True, index=True
    )
    resume_session_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("user_sessions.id"), nullable=True, index=True
    )

    status: Mapped[str] = mapped_column(String(32), default="queued", index=True)
    filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    enrich: Mapped[bool] = mapped_column(default=True)
    progress: Mapped[int] = mapped_column(default=0)
    message: Mapped[str | None] = mapped_column(String(500), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class JobApplication(Base):
    """Tracks job applications made by the user."""

    __tablename__ = "job_applications"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id"), index=True
    )
    job_title: Mapped[str] = mapped_column(String(255))
    company: Mapped[str | None] = mapped_column(String(255), nullable=True)
    job_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[str | None] = mapped_column(String(64), nullable=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # status: applied | interviewing | offer | rejected | withdrawn
    status: Mapped[str] = mapped_column(String(32), default="applied", index=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    job_data_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    applied_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=now_utc, onupdate=now_utc
    )


class PortalSession(Base):
    """Stores a saved Playwright browser session (cookies + localStorage) per user per portal."""

    __tablename__ = "portal_sessions"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id"), index=True
    )
    # portal: indeed | linkedin | naukri | glassdoor
    portal: Mapped[str] = mapped_column(String(32), index=True)
    # Full Playwright storage_state JSON: {cookies: [...], origins: [...]}
    storage_state: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=now_utc, onupdate=now_utc
    )


class RecommendationFeedback(Base):
    """Stores thumbs-up / thumbs-down feedback on job and course recommendations."""

    __tablename__ = "recommendation_feedback"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id"), index=True
    )
    # item_type: job | course
    item_type: Mapped[str] = mapped_column(String(16), index=True)
    # identifier: job URL for jobs, course title/URL for courses
    item_identifier: Mapped[str] = mapped_column(Text)
    # feedback: helpful | not_helpful
    feedback: Mapped[str] = mapped_column(String(16))
    is_helpful: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=now_utc, onupdate=now_utc
    )


class RefreshToken(Base):
    """Tracks refresh tokens for JWT session rotation."""

    __tablename__ = "refresh_tokens"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    token_hash: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    is_revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc, nullable=False)

    user: Mapped[User] = relationship("User", back_populates="refresh_tokens")


class UserPreferences(Base):
    """User preferences for notifications and application settings."""

    __tablename__ = "user_preferences"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True, nullable=False
    )
    job_search_status: Mapped[str] = mapped_column(String(50), nullable=False)  # ACTIVE, PASSIVE, CLOSED
    weekly_digest_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    email_notifications: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=now_utc, onupdate=now_utc, nullable=False
    )

    user: Mapped[User] = relationship("User", back_populates="preferences")


class CareerGoals(Base):
    """User target career goals configuration."""

    __tablename__ = "career_goals"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True, nullable=False
    )
    target_role: Mapped[str] = mapped_column(String(255), nullable=False)
    target_compensation_min: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    target_compensation_max: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    target_companies: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    timeline_months: Mapped[int] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=now_utc, onupdate=now_utc, nullable=False
    )

    user: Mapped[User] = relationship("User", back_populates="goals")
