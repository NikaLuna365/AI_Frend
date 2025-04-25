# app/db/base.py
"""
Engine / SessionLocal + helperы.
Совместим как с новым кодом, так и со старыми импортами (get_db_session).
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, inspect
from sqlalchemy.engine import Engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import settings

# ---------------------------------------------------------------------- #
# Engine / Session
# ---------------------------------------------------------------------- #
engine = create_engine(
    settings.DATABASE_URL,
    echo=settings.ENVIRONMENT == "dev",
    future=True,
)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False, future=True)
Base = declarative_base()

# ---------------------------------------------------------------------- #
# Compatibility: Engine.table_names() (SQLAlchemy ≥2.0)
# ---------------------------------------------------------------------- #
def _table_names(self: Engine) -> list[str]:
    return inspect(self).get_table_names()

if not hasattr(Engine, "table_names"):
    Engine.table_names = _table_names  # type: ignore

# ---------------------------------------------------------------------- #
# Dependency helpers
# ---------------------------------------------------------------------- #
def get_db_session() -> Generator:
    """
    FastAPI dependency — yield Session и корректно закрыть.
    Старые роуты рассчитывают именно на это имя.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def db_session():
    """Контекст-менеджер для скриптов/тасков без FastAPI."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


__all__ = [
    "engine",
    "SessionLocal",
    "Base",
    "get_db_session",  # важно: экспортируем для импортов в роутерах
    "db_session",
]
