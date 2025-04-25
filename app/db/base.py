# app/db/base.py

from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import (
    DeclarativeBase,
    Session,
    scoped_session,
    sessionmaker,
)

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

# Включаем echo=true в dev, чтобы видеть в логах SQL-запросы
_engine_kwargs: dict[str, object] = {
    "echo": settings.ENVIRONMENT == "dev",
    "pool_pre_ping": True,
}

engine = create_engine(settings.DATABASE_URL, **_engine_kwargs)

# фабрика классических сессий
SessionLocal: sessionmaker[Session] = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

# scoped_session для правильной работы в многопоточном/многозадачном окружении
ScopedSession: scoped_session[Session] = scoped_session(SessionLocal)


# --------------------------------------------------------------------------- #
#                            helpers / dependency                             #
# --------------------------------------------------------------------------- #

def get_db_session() -> Generator[Session, None, None]:
    """
    FastAPI dependency.
    Использует scoped_session, чтобы одной и той же таске/треду вернуть один объект Session.
    """
    db = Scoped_session()  # lazy-init для текущего потока / таска
    try:
        yield db
    finally:
        db.close()


@contextmanager
def session_context() -> Generator[Session, None, None]:
    """
    Контекстный менеджер для скриптов/тестов.
    Автоматически коммитит или откатывает транзакцию.
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


__all__ = [
    "engine",
    "SessionLocal",
    "ScopedSession",
    "Base",
    "get_db_session",
    "session_context",
]
