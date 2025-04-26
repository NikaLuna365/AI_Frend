# app/db/base.py
"""
Single declarative Base + session helpers.

• Uses test-friendly SQLite in-memory when ENVIRONMENT == 'test'.
• Provides `get_db_session` dependency and `session_context` helper.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, scoped_session, sessionmaker

from app.config import settings

# --------------------------------------------------------------------------- #
#                               Declarative base                              #
# --------------------------------------------------------------------------- #


class Base(DeclarativeBase):
    """Common declarative base for all ORM models."""


# --------------------------------------------------------------------------- #
#                               Engine & Session                              #
# --------------------------------------------------------------------------- #

if settings.ENVIRONMENT == "test":
    DATABASE_URL = "sqlite+pysqlite:///:memory:"
    _engine_kwargs: dict[str, object] = {"echo": False, "future": True}
else:
    DATABASE_URL = settings.DATABASE_URL
    _engine_kwargs = {
        "echo": settings.ENVIRONMENT == "dev",
        "pool_pre_ping": True,
        "future": True,
    }

engine = create_engine(DATABASE_URL, **_engine_kwargs)

# Session factory
SessionLocal: sessionmaker[Session] = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False,
)

# Thread / task–local scoped session
ScopedSession: scoped_session[Session] = scoped_session(SessionLocal)

# --------------------------------------------------------------------------- #
#                            helpers / dependency                             #
# --------------------------------------------------------------------------- #


def get_db_session() -> Generator[Session, None, None]:
    """
    FastAPI / service dependency.
    Returns a thread-local Session that is automatically closed.
    """
    db = ScopedSession()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def session_context() -> Generator[Session, None, None]:
    """
    Context-manager for CLI scripts / unit-tests that need manual control over commit.
    """
    db = ScopedSession()
    try:
        yield db
        db.commit()
    except Exception:  # pragma: no cover
        db.rollback()
        raise
    finally:
        db.close()


__all__: list[str] = ["Base", "engine", "SessionLocal", "ScopedSession", "get_db_session", "session_context"]
