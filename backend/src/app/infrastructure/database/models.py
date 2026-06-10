from __future__ import annotations

from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Text,
    Date,
    Integer,
    Index,
)
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
    profile: Mapped[CareerProfile | None] = relationship(
        "CareerProfile", back_populates="user", uselist=False, cascade="all, delete-orphan"
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


class CareerProfile(Base):
    __tablename__ = "career_profiles"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True, nullable=False
    )
    headline: Mapped[str | None] = mapped_column(String(255), nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    location: Mapped[str | None] = mapped_column(String(100), nullable=True)
    current_salary: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=now_utc, onupdate=now_utc, nullable=False
    )

    user: Mapped[User] = relationship("User", back_populates="profile")
    skills: Mapped[list[Skill]] = relationship(
        "Skill", back_populates="profile", cascade="all, delete-orphan"
    )
    experiences: Mapped[list[Experience]] = relationship(
        "Experience", back_populates="profile", cascade="all, delete-orphan"
    )
    education: Mapped[list[Education]] = relationship(
        "Education", back_populates="profile", cascade="all, delete-orphan"
    )
    projects: Mapped[list[Project]] = relationship(
        "Project", back_populates="profile", cascade="all, delete-orphan"
    )
    versions: Mapped[list[ProfileVersion]] = relationship(
        "ProfileVersion", back_populates="profile", cascade="all, delete-orphan"
    )
    resumes: Mapped[list[UploadedResume]] = relationship(
        "UploadedResume", back_populates="profile", cascade="all, delete-orphan"
    )


class ProfileVersion(Base):
    __tablename__ = "profile_versions"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    profile_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("career_profiles.id", ondelete="CASCADE"), index=True, nullable=False
    )
    version_number: Mapped[int] = mapped_column(nullable=False)
    snapshot_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc, nullable=False)

    profile: Mapped[CareerProfile] = relationship("CareerProfile", back_populates="versions")


class Skill(Base):
    __tablename__ = "skills"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    profile_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("career_profiles.id", ondelete="CASCADE"), index=True, nullable=False
    )
    skill_name: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    years_experience: Mapped[float] = mapped_column(Numeric(4, 1), nullable=False)
    proficiency: Mapped[str] = mapped_column(String(50), nullable=False)  # NOVICE, INTERMEDIATE, ADVANCED, EXPERT
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=now_utc, onupdate=now_utc, nullable=False
    )

    profile: Mapped[CareerProfile] = relationship("CareerProfile", back_populates="skills")


class Experience(Base):
    __tablename__ = "experiences"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    profile_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("career_profiles.id", ondelete="CASCADE"), index=True, nullable=False
    )
    company_name: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    job_title: Mapped[str] = mapped_column(String(255), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)  # DATE type
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    is_current: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=now_utc, onupdate=now_utc, nullable=False
    )

    profile: Mapped[CareerProfile] = relationship("CareerProfile", back_populates="experiences")


class Education(Base):
    __tablename__ = "education"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    profile_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("career_profiles.id", ondelete="CASCADE"), index=True, nullable=False
    )
    institution: Mapped[str] = mapped_column(String(255), nullable=False)
    degree: Mapped[str | None] = mapped_column(String(255), nullable=True)
    field_of_study: Mapped[str | None] = mapped_column(String(255), nullable=True)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=now_utc, onupdate=now_utc, nullable=False
    )

    profile: Mapped[CareerProfile] = relationship("CareerProfile", back_populates="education")


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    profile_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("career_profiles.id", ondelete="CASCADE"), index=True, nullable=False
    )
    project_name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    role_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=now_utc, onupdate=now_utc, nullable=False
    )

    profile: Mapped[CareerProfile] = relationship("CareerProfile", back_populates="projects")


class UploadedResume(Base):
    __tablename__ = "uploaded_resumes"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    profile_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("career_profiles.id", ondelete="CASCADE"), index=True, nullable=False
    )
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_size: Mapped[int] = mapped_column(nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    parsed_payload: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    confidence_score: Mapped[float | None] = mapped_column(Numeric(3, 2), nullable=True)
    is_synced: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc, nullable=False)

    profile: Mapped[CareerProfile] = relationship("CareerProfile", back_populates="resumes")


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    website: Mapped[str | None] = mapped_column(String(255), nullable=True)
    logo_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    sector: Mapped[str | None] = mapped_column(String(100), nullable=True)
    size_range: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=now_utc, onupdate=now_utc, nullable=False
    )
    hiring_velocity_30d: Mapped[float] = mapped_column(
        Numeric(6, 2), default=0.0, nullable=False
    )
    hiring_velocity_90d: Mapped[float] = mapped_column(
        Numeric(6, 2), default=0.0, nullable=False
    )
    trend_direction: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )
    attractiveness_score: Mapped[float] = mapped_column(
        Numeric(5, 2), default=0.0, nullable=False
    )
    last_aggregated_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )

    postings: Mapped[list[JobPosting]] = relationship("JobPosting", back_populates="company")


class JobPosting(Base):
    __tablename__ = "job_postings"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    company_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("companies.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    raw_title: Mapped[str] = mapped_column(String(255), nullable=False)
    location: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    url: Mapped[str] = mapped_column(String(1024), index=True, nullable=False)
    compensation_min: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    compensation_max: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(10), default="USD", nullable=False)
    source: Mapped[str] = mapped_column(String(100), nullable=False)
    source_id: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    post_date: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    expiry_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True, nullable=False)
    deduplicated_to_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("job_postings.id", ondelete="SET NULL"), index=True, nullable=True
    )
    merged_into_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("job_postings.id", ondelete="SET NULL"), index=True, nullable=True
    )
    dedupe_fingerprint: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_ghost_posting: Mapped[bool] = mapped_column(
        Boolean, default=False, index=True, nullable=False
    )
    ghost_score: Mapped[float] = mapped_column(
        Numeric(5, 2), default=0.0, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=now_utc, onupdate=now_utc, nullable=False
    )

    company: Mapped[Company] = relationship("Company", back_populates="postings")
    skills: Mapped[list[JobPostingSkill]] = relationship("JobPostingSkill", back_populates="job_posting")


class NormalizedSkill(Base):
    __tablename__ = "normalized_skills"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    aliases: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc, nullable=False)


class JobPostingSkill(Base):
    __tablename__ = "job_postings_skills"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    job_posting_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("job_postings.id", ondelete="CASCADE"), index=True, nullable=False
    )
    skill_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("normalized_skills.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    raw_mention: Mapped[str | None] = mapped_column(String(100), nullable=True)
    extraction_method: Mapped[str | None] = mapped_column(String(50), nullable=True)
    confidence_score: Mapped[float | None] = mapped_column(Numeric(4, 3), nullable=True)
    context_sentence: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc, nullable=False)

    job_posting: Mapped[JobPosting] = relationship("JobPosting", back_populates="skills")


class IngestionAuditLog(Base):
    __tablename__ = "ingestion_audit_logs"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    source: Mapped[str] = mapped_column(String(100), nullable=False)
    job_count_attempted: Mapped[int] = mapped_column(nullable=False)
    job_count_inserted: Mapped[int] = mapped_column(nullable=False)
    job_count_duplicated: Mapped[int] = mapped_column(nullable=False)
    job_count_failed: Mapped[int] = mapped_column(nullable=False)
    log_details: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc, nullable=False)


class JobSource(Base):
    __tablename__ = "job_sources"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    source_key: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    rate_limit_limit: Mapped[int | None] = mapped_column(nullable=True)
    rate_limit_remaining: Mapped[int | None] = mapped_column(nullable=True)
    rate_limit_reset_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    error_count_24h: Mapped[int] = mapped_column(default=0, nullable=False)
    last_run_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=now_utc, onupdate=now_utc, nullable=False
    )


class JobIngestionRun(Base):
    __tablename__ = "job_ingestion_runs"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    source_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("job_sources.id", ondelete="CASCADE"), index=True, nullable=False
    )
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    items_scraped: Mapped[int] = mapped_column(default=0, nullable=False)
    items_inserted: Mapped[int] = mapped_column(default=0, nullable=False)
    items_failed: Mapped[int] = mapped_column(default=0, nullable=False)
    error_log: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class RawJobPosting(Base):
    __tablename__ = "raw_job_postings"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    ingestion_run_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("job_ingestion_runs.id", ondelete="CASCADE"), index=True, nullable=False
    )
    source_key: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    external_id: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    company_name: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    location_raw: Mapped[str] = mapped_column(String(255), nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    salary_raw: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    raw_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc, nullable=False)


class JobDuplicate(Base):
    __tablename__ = "job_duplicates"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    primary_job_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("job_postings.id", ondelete="CASCADE"), index=True, nullable=False
    )
    duplicate_job_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("job_postings.id", ondelete="CASCADE"), index=True, nullable=False
    )
    confidence_score: Mapped[float] = mapped_column(Numeric(4, 3), nullable=False)
    title_similarity: Mapped[float] = mapped_column(Numeric(4, 3), nullable=False)
    company_similarity: Mapped[float] = mapped_column(Numeric(4, 3), nullable=False)
    description_similarity: Mapped[float] = mapped_column(Numeric(4, 3), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="PENDING_REVIEW", index=True, nullable=False)
    reviewed_by: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc, nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class DedupeAuditLog(Base):
    __tablename__ = "dedupe_audit_logs"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    primary_job_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("job_postings.id", ondelete="CASCADE"), index=True, nullable=False
    )
    merged_job_id: Mapped[str] = mapped_column(String(36), nullable=False)
    merge_details: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc, nullable=False)


class SkillTrendDaily(Base):
    __tablename__ = "skill_trends_daily"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    skill_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("normalized_skills.id", ondelete="CASCADE"), index=True, nullable=False
    )
    snapshot_date: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    posting_count: Mapped[int] = mapped_column(nullable=False)
    total_postings_count: Mapped[int] = mapped_column(nullable=False)
    frequency: Mapped[float] = mapped_column(Numeric(6, 5), nullable=False)


class SkillRelationship(Base):
    __tablename__ = "skill_relationships"

    parent_skill_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("normalized_skills.id", ondelete="CASCADE"), primary_key=True
    )
    child_skill_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("normalized_skills.id", ondelete="CASCADE"), primary_key=True
    )
    relationship_type: Mapped[str] = mapped_column(String(50), nullable=False)
    confidence_score: Mapped[float] = mapped_column(Numeric(4, 3), nullable=False)


class CompensationRecord(Base):
    __tablename__ = "compensation_records"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    job_posting_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("job_postings.id", ondelete="CASCADE"), nullable=True
    )
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)
    min_salary: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    max_salary: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    payment_interval: Mapped[str] = mapped_column(String(50), nullable=False)
    computed_annual_min: Mapped[float] = mapped_column(Numeric(12, 2), index=True, nullable=False)
    computed_annual_max: Mapped[float] = mapped_column(Numeric(12, 2), index=True, nullable=False)
    equity_min: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    equity_max: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    location_normalized: Mapped[str] = mapped_column(String(150), index=True, nullable=False)
    col_tier: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc, nullable=False)


class CompensationBenchmark(Base):
    __tablename__ = "compensation_benchmarks"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    role_type: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    location_normalized: Mapped[str] = mapped_column(String(150), index=True, nullable=False)
    skill_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("normalized_skills.id", ondelete="CASCADE"), index=True, nullable=True
    )
    p25_salary: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    p50_salary: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    p75_salary: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    sample_size: Mapped[int] = mapped_column(nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc, nullable=False)


class CareerHealthScore(Base):
    __tablename__ = "career_health_scores"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    score: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    skill_alignment_score: Mapped[float] = mapped_column(
        Numeric(5, 2), nullable=False
    )
    market_positioning_score: Mapped[float] = mapped_column(
        Numeric(5, 2), nullable=False
    )
    activity_health_score: Mapped[float] = mapped_column(
        Numeric(5, 2), nullable=False
    )
    compensation_alignment_score: Mapped[float] = mapped_column(
        Numeric(5, 2), nullable=False
    )
    profile_completeness_score: Mapped[float] = mapped_column(
        Numeric(5, 2), nullable=False
    )
    primary_insight: Mapped[str] = mapped_column(Text, nullable=False)
    top_driver: Mapped[str] = mapped_column(String(255), nullable=False)
    top_detractor: Mapped[str] = mapped_column(String(255), nullable=False)
    computed_at: Mapped[datetime] = mapped_column(
        DateTime, default=now_utc, index=True, nullable=False
    )

    __table_args__ = (
        Index("idx_health_scores_user_computed", "user_id", "computed_at"),
    )


class TargetRoleSpecification(Base):
    __tablename__ = "target_role_specifications"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    role_title: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    typical_experience_years: Mapped[float] = mapped_column(
        Numeric(4, 1), nullable=False
    )
    typical_salary_p50: Mapped[float | None] = mapped_column(
        Numeric(12, 2), nullable=True
    )
    typical_salary_p75: Mapped[float | None] = mapped_column(
        Numeric(12, 2), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=now_utc, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=now_utc, onupdate=now_utc, nullable=False
    )


class PositionDelta(Base):
    __tablename__ = "position_deltas"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False,
    )
    target_role: Mapped[str] = mapped_column(String(255), nullable=False)
    missing_skills: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON, default=list, nullable=False
    )
    top_3_prioritized_gaps: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON, default=list, nullable=False
    )
    recommendation_summary: Mapped[str] = mapped_column(Text, nullable=False)
    computed_at: Mapped[datetime] = mapped_column(
        DateTime, default=now_utc, index=True, nullable=False
    )


class CompanyWatchlist(Base):
    __tablename__ = "company_watchlists"

    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    company_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("companies.id", ondelete="CASCADE"),
        primary_key=True,
    )
    notifications_enabled: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=now_utc, nullable=False
    )


class CompanySnapshot(Base):
    __tablename__ = "company_snapshots"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    company_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("companies.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    active_postings_count: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )
    hiring_velocity: Mapped[float] = mapped_column(
        Numeric(6, 2), nullable=False
    )
    attractiveness_score: Mapped[float] = mapped_column(
        Numeric(5, 2), nullable=False
    )
    snapshot_date: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=now_utc, nullable=False
    )


class GhostPostingSignal(Base):
    __tablename__ = "ghost_posting_signals"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    job_posting_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("job_postings.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False,
    )
    ghost_score: Mapped[float] = mapped_column(
        Numeric(5, 2), index=True, nullable=False
    )
    is_flagged_ghost: Mapped[bool] = mapped_column(
        Boolean, default=False, index=True, nullable=False
    )
    age_days: Mapped[int] = mapped_column(Integer, nullable=False)
    repost_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    company_velocity_ratio: Mapped[float] = mapped_column(
        Numeric(4, 2), nullable=False
    )
    cohort_applications: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )
    cohort_interviews: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    computed_at: Mapped[datetime] = mapped_column(
        DateTime, default=now_utc, nullable=False
    )


class OpportunityScore(Base):
    __tablename__ = "opportunity_scores"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    job_posting_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("job_postings.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    fit_score: Mapped[float] = mapped_column(
        Numeric(5, 2), index=True, nullable=False
    )
    skill_fit_score: Mapped[float] = mapped_column(
        Numeric(5, 2), nullable=False
    )
    experience_fit_score: Mapped[float] = mapped_column(
        Numeric(5, 2), nullable=False
    )
    compensation_fit_score: Mapped[float] = mapped_column(
        Numeric(5, 2), nullable=False
    )
    company_attractiveness_score: Mapped[float] = mapped_column(
        Numeric(5, 2), nullable=False
    )
    explanation_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    computed_at: Mapped[datetime] = mapped_column(
        DateTime, default=now_utc, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=now_utc, onupdate=now_utc, nullable=False
    )

    __table_args__ = (
        Index("idx_user_job_opp_scores", "user_id", "job_posting_id", unique=True),
    )


class DashboardAnalyticsEvent(Base):
    __tablename__ = "dashboard_analytics_events"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    widget_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        JSON, default=dict, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=now_utc, index=True, nullable=False
    )

