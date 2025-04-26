# app/db/base.py
"""
Unified SQLAlchemy base & session factory.

• Uses **single Declarative `Base`** so that all models share one MetaData
  – this prevents duplicate table definitions when models are imported multiple times in tests.

• Automatically switches engine:
    ENVIRONMENT=test  →  SQLite in-memory (fast, no external deps)
    otherwise        →  DATABASE_URL from .env (PostgreSQL in dev/prod)

The helper `get_db_session()` is used both as FastAPI dependency and
in synchronous service code / Celery tasks.
"""

from __future__ import annotations

import contextlib
import os
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, scoped_session, sessionmaker

from app.config import settings


# --------------------------------------------------------------------------- #
#                               Declarative Base                              #
# --------------------------------------------------------------------------- #
class Base(DeclarativeBase):
    """Один-единственный Base на проект."""
    pass


# --------------------------------------------------------------------------- #
#                            Engine & Session factory                         #
# --------------------------------------------------------------------------- #
def _make_engine():
    """Return SQLAlchemy Engine depending on ENVIRONMENT."""
    if settings.ENVIRONMENT == "test":
        # In-memory SQLite for unit / CI tests – spins up instantly,
        # PgSQL-specific types are compatible enough for our models.
        return create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            echo=False,
            future=True,
        )

    # dev / prod – whatever is in DATABASE_URL
    return create_engine(
        settings.DATABASE_URL,
        echo=settings.ENVIRONMENT == "dev",
        pool_pre_ping=True,
        future=True,
    )


_engine = _make_engine()

# Session factory. `scoped_session` provides task/thread-local instances.
SessionLocal: sessionmaker[Session] = sessionmaker(
    bind=_engine,
    autocommit=False,
    autoflush=False,
    future=True,
)
ScopedSession = scoped_session(SessionLocal)


# --------------------------------------------------------------------------- #
#                         Public helpers / dependencies                       #
# --------------------------------------------------------------------------- #
def get_db_session() -> Generator[Session, None, None]:
    """
    FastAPI dependency (sync). Ensures single Session per request / Celery task.
    """
    db = ScopedSession()  # lazy-init for current task/thread
    try:
        yield db
    finally:
        db.close()


@contextlib.contextmanager
def session_context() -> Generator[Session, None, None]:
    """
    Context-manager for scripts/tests. Commits on success, rollbacks otherwise.
    """
    db = ScopedSession()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


# --------------------------------------------------------------------------- #
#                         Convenience re-exports for tests                    #
# --------------------------------------------------------------------------- #
engine = _engine  # tests import this directly

__all__: list[str] = [
    "Base",
    "engine",
    "SessionLocal",
    "ScopedSession",
    "get_db_session",
    "session_context",
]
