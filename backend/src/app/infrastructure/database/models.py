from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database.connection import Base


def now_utc() -> datetime:
    return datetime.utcnow()


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=now_utc, onupdate=now_utc
    )

    profiles: Mapped[list[ResumeProfile]] = relationship(
        "ResumeProfile", back_populates="user"
    )


class ResumeProfile(Base):
    __tablename__ = "resume_profiles"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"))
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)

    socials_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_data: Mapped[dict[str, Any]] = mapped_column(JSON)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=now_utc, onupdate=now_utc
    )

    user: Mapped[User] = relationship("User", back_populates="profiles")


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"))
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=now_utc, onupdate=now_utc
    )


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    conversation_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("conversations.id")
    )
    role: Mapped[str] = mapped_column(String(16))  # user|assistant|system
    content: Mapped[str] = mapped_column(Text)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=now_utc)


class AnalysisHistory(Base):
    __tablename__ = "analysis_history"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"))
    profile_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("resume_profiles.id")
    )
    overall_score: Mapped[float] = mapped_column(Text)  # Store as text for flexibility
    grade: Mapped[str | None] = mapped_column(String(1), nullable=True)
    section_scores_json: Mapped[dict[str, Any]] = mapped_column(JSON)
    analysis_data_json: Mapped[dict[str, Any]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc)