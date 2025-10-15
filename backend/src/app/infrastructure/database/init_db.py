from __future__ import annotations

from sqlalchemy import text

from app.core.config import settings
from app.infrastructure.database import models  # noqa: F401 - ensure models load
from app.infrastructure.database.connection import Base, engine


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


if __name__ == "__main__":
    init_db()
