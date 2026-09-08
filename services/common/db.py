"""SQLAlchemy engine and session factory shared by every service."""
from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from services.common.config import settings

import os

# Hosted poolers (Supabase Supavisor, PgBouncer) cap client connections, so the pool is small by
# default and tunable per host. pool_recycle keeps idle connections from being closed under us.
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_size=int(os.environ.get("SIYANA_DB_POOL_SIZE", "5")),
    max_overflow=int(os.environ.get("SIYANA_DB_MAX_OVERFLOW", "5")),
    pool_recycle=int(os.environ.get("SIYANA_DB_POOL_RECYCLE", "300")),
    pool_timeout=30,
    future=True,
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, class_=Session)


def get_session() -> Iterator[Session]:
    """FastAPI dependency: one session per request, committed on success."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def db_reachable() -> bool:
    try:
        with engine.connect() as conn:
            conn.execute(text("select 1"))
        return True
    except Exception:
        return False
