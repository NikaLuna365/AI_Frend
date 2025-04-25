"""
DeclarativeBase + Engine/Session фабрики.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import (
    DeclarativeBase,
    scoped_session,
    sessionmaker,
    Session,
)

from app.config import settings


class Base(DeclarativeBase):
    """Один-единственный Base для всех ORM-моделей."""


# ─────────────────────────── engine / session ────────────────────────────

_engine_kwargs: dict[str, object] = {
    "echo": settings.ENVIRONMENT == "dev",
    "pool_pre_ping": True,
}

engine = create_engine(settings.DATABASE_URL, **_engine_kwargs)

SessionLocal: sessionmaker[Session] = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

ScopedSession: scoped_session[Session] = scoped_session(SessionLocal)


# ───────────────────────── helpers / dependency ──────────────────────────

def get_db_session() -> Generator[Session, None, None]:
    """
    FastAPI dependency / generic helper.
    """
    db = ScopedSession()        # ← исправлена опечатка
    try:
        yield db
    finally:
        db.close()


@contextmanager
def session_context() -> Generator[Session, None, None]:
    db = ScopedSession()
    try:
        yield db
        db.commit()
    except Exception:           # pragma: no cover
        db.rollback()
        raise
    finally:
        db.close()
