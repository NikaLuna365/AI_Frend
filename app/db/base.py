"""
База ORM-моделей и session-фабрика.

▪  Единственный DeclarativeBase ― чтобы MetaData был общий.
▪  SessionLocal используется fastapi-depends или в сервисах напрямую.
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, scoped_session, sessionmaker

from app.config import settings

# --------------------------------------------------------------------------- #
#                               Declarative base                              #
# --------------------------------------------------------------------------- #


class Base(DeclarativeBase):
    """Один-единственный Base для всех моделей проекта."""
    pass


# --------------------------------------------------------------------------- #
#                               Engine & Session                              #
# --------------------------------------------------------------------------- #

# Используем echo в dev для удобства, в prod отключаем
_engine_kwargs: dict[str, object] = {
    "echo": settings.ENVIRONMENT == "dev",
    "pool_pre_ping": True,
}

engine = create_engine(settings.DATABASE_URL, **_engine_kwargs)

# sessionmaker() создаёт фабрику, scoped_session ― даёт «thread-local» сессию
SessionLocal: sessionmaker[Session] = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

ScopedSession: scoped_session[Session] = scoped_session(SessionLocal)


# --------------------------------------------------------------------------- #
#                            helpers / dependency                             #
# --------------------------------------------------------------------------- #

def get_db_session() -> Generator[Session, None, None]:  # FastAPI dependency
    db = ScopedSession()  # lazy-init для текущего thread / async-task
    try:
        yield db
    finally:
        db.close()


@contextmanager
def session_context() -> Generator[Session, None, None]:
    """Контекстный менеджер для скриптов/тестов."""
    db = ScopedSession()
    try:
        yield db
        db.commit()
    except Exception:  # pragma: no cover
        db.rollback()
        raise
    finally:
        db.close()
