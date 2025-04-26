"""
Unified SQLAlchemy base & session factory.

• Single Declarative ``Base`` so that all models share one ``MetaData`` –
  предотвращает дубли таблиц при повторных импортах.

• Engine selection:
        ENVIRONMENT=test  →  SQLite in-memory (молниеносные unit-тесты)
        иначе            →  ``settings.DATABASE_URL`` (PostgreSQL)

The helper ``get_db_session()`` работает и как FastAPI-dependency,
и в сервисах/Celery-тасках.
"""
from __future__ import annotations

import contextlib
from typing import Generator

from sqlalchemy import create_engine, inspect
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
        # In-memory SQLite – быстро и без внешних зависимостей.
        return create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            echo=False,
            future=True,
        )

    # dev / prod – что прописано в .env
    return create_engine(
        settings.DATABASE_URL,
        echo=settings.ENVIRONMENT == "dev",
        pool_pre_ping=True,
        future=True,
    )


_engine = _make_engine()

# --- back-compat: engine.table_names() удалили в SA 2.x, вернём для тестов ----
setattr(
    type(_engine),
    "table_names",
    lambda self: inspect(self).get_table_names()
)
# --------------------------------------------------------------------------- #

SessionLocal: sessionmaker[Session] = sessionmaker(
    bind=_engine, autocommit=False, autoflush=False, future=True
)
ScopedSession = scoped_session(SessionLocal)

# --------------------------------------------------------------------------- #
#                         public helpers / dependencies                       #
# --------------------------------------------------------------------------- #
def get_db_session() -> Generator[Session, None, None]:
    """FastAPI dependency (sync). One Session per request / task."""
    db = ScopedSession()
    try:
        yield db
    finally:
        db.close()


@contextlib.contextmanager
def session_context() -> Generator[Session, None, None]:
    """Context-manager for scripts/tests.  Commit on success, rollback on error."""
    db = ScopedSession()
    try:
        yield db
        db.commit()
    except Exception:  # pragma: no cover
        db.rollback()
        raise
    finally:
        db.close()


# --------------------------------------------------------------------------- #
#                         convenience re-exports for tests                    #
# --------------------------------------------------------------------------- #
engine = _engine

__all__: list[str] = [
    "Base",
    "engine",
    "SessionLocal",
    "ScopedSession",
    "get_db_session",
    "session_context",
]
