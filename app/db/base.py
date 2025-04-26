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
    """Единый DeclarativeBase для всех ORM-моделей."""
    pass


# --------------------------------------------------------------------------- #
#                               Engine & Session                              #
# --------------------------------------------------------------------------- #

# Включаем echo в режиме dev, иначе скрываем SQL-логи
_engine_kwargs: dict[str, object] = {
    "echo": settings.ENVIRONMENT == "dev",
    "pool_pre_ping": True,
}

engine = create_engine(settings.DATABASE_URL, **_engine_kwargs)

# Фабрика сессий и «thread-/task-local» сессия
SessionLocal: sessionmaker[Session] = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)
ScopedSession: scoped_session[Session] = scoped_session(SessionLocal)


# --------------------------------------------------------------------------- #
#                            Helpers / dependencies                           #
# --------------------------------------------------------------------------- #

def get_db_session() -> Generator[Session, None, None]:
    """
    FastAPI dependency.
    Использует scoped_session, чтобы одной и той же таске/треду вернуть один объект Session.
    """
    db = ScopedSession()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def session_context() -> Generator[Session, None, None]:
    """
    Контекстный менеджер для скриптов/тестов.
    Автоматически коммитит при выходе, рулбекает при ошибке.
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
