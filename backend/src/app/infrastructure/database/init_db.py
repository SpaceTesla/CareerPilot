from __future__ import annotations

from sqlalchemy import text

from app.core.config import settings
from app.infrastructure.database import models  # noqa: F401 - ensure models load
from app.infrastructure.database.connection import Base, engine


def _ensure_indexes() -> None:
    index_statements = [
        "CREATE INDEX IF NOT EXISTS ix_resume_profiles_user_id ON resume_profiles (user_id)",
        "CREATE INDEX IF NOT EXISTS ix_conversations_user_id ON conversations (user_id)",
        "CREATE INDEX IF NOT EXISTS ix_messages_conversation_id ON messages (conversation_id)",
        "CREATE INDEX IF NOT EXISTS ix_analysis_history_user_id ON analysis_history (user_id)",
        "CREATE INDEX IF NOT EXISTS ix_analysis_history_profile_id ON analysis_history (profile_id)",
        "CREATE INDEX IF NOT EXISTS ix_user_sessions_user_id ON user_sessions (user_id)",
        "CREATE INDEX IF NOT EXISTS ix_user_sessions_profile_id ON user_sessions (profile_id)",
        "CREATE INDEX IF NOT EXISTS ix_resume_processing_jobs_status ON resume_processing_jobs (status)",
        "CREATE INDEX IF NOT EXISTS ix_resume_processing_jobs_requested_by_user_id ON resume_processing_jobs (requested_by_user_id)",
        "CREATE INDEX IF NOT EXISTS ix_resume_processing_jobs_resolved_user_id ON resume_processing_jobs (resolved_user_id)",
        "CREATE INDEX IF NOT EXISTS ix_job_applications_user_id ON job_applications (user_id)",
        "CREATE INDEX IF NOT EXISTS ix_job_applications_status ON job_applications (status)",
        "CREATE INDEX IF NOT EXISTS ix_recommendation_feedback_user_id ON recommendation_feedback (user_id)",
        "CREATE INDEX IF NOT EXISTS ix_recommendation_feedback_item_type ON recommendation_feedback (item_type)",
        "CREATE INDEX IF NOT EXISTS ix_portal_sessions_user_id ON portal_sessions (user_id)",
        "CREATE INDEX IF NOT EXISTS ix_portal_sessions_portal ON portal_sessions (portal)",
    ]

    with engine.connect() as conn:
        for statement in index_statements:
            try:
                conn.execute(text(statement))
            except Exception:
                conn.rollback()
        conn.commit()


def init_db() -> None:
    if settings.pgvector_enabled:
        with engine.connect() as conn:
            try:
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
                conn.commit()
            except Exception:
                # On non-Postgres or no permissions, ignore quietly for now
                conn.rollback()

    Base.metadata.create_all(bind=engine)
    _ensure_indexes()


if __name__ == "__main__":
    init_db()
