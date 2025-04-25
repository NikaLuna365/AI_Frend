# app/db/base.py
"""
База, движок и вспом-helpers.
При ENVIRONMENT=test автоматически создаём/чистим схему — unit-тестам
не нужны миграции или Alembic.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, inspect
from sqlalchemy.engine import Engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import settings

# --------------------------------------------------------------------------- #
# Engine / Session
# --------------------------------------------------------------------------- #
engine = create_engine(
    settings.DATABASE_URL,
    echo=settings.ENVIRONMENT == "dev",
    future=True,
)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False, future=True)
Base = declarative_base()

# --------------------------------------------------------------------------- #
# Engine.table_names() совместимо с SA 2.*
# --------------------------------------------------------------------------- #
def _table_names(self: Engine):  # pragma: no cover
    return inspect(self).get_table_names()


if not hasattr(Engine, "table_names"):
    Engine.table_names = _table_names  # type: ignore[attr-defined]

# --------------------------------------------------------------------------- #
# При тестах — clean schema on import
# --------------------------------------------------------------------------- #
if settings.ENVIRONMENT == "test":  # pragma: no cover
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

# --------------------------------------------------------------------------- #
# FastAPI dependency + context-manager
# --------------------------------------------------------------------------- #
def get_db_session() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


__all__ = [
    "engine",
    "Base",
    "SessionLocal",
    "get_db_session",
    "db_session",
]
