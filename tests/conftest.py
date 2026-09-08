from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from services.common.db import SessionLocal, db_reachable


@pytest.fixture
def db_session() -> Session:
    """A session inside a transaction that is rolled back after the test."""
    if not db_reachable():
        pytest.skip("DATABASE_URL not reachable")
    session = SessionLocal()
    session.begin()
    try:
        yield session
    finally:
        session.rollback()
        session.close()
