# app/db/base.py
"""
Инициализация Engine / SessionLocal + «compat layer» для SQLAlchemy 2.*
чтобы в тестах работал устаревший engine.table_names().
"""

from __future__ import annotations

import os
from contextlib import contextmanager

from sqlalchemy import create_engine, inspect
from sqlalchemy.engine import Engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import settings

# ---------------------------------------------------------------------------------
# Engine / Session
# ---------------------------------------------------------------------------------
engine = create_engine(
    settings.DATABASE_URL,
    echo=settings.ENVIRONMENT == "dev",
    future=True,
)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False, future=True)
Base = declarative_base()

# ---------------------------------------------------------------------------------
# Compatibility: add .table_names() to Engine (SQLAlchemy ≥2.0)
# ---------------------------------------------------------------------------------
def _table_names(self: Engine) -> list[str]:
    return inspect(self).get_table_names()

if not hasattr(Engine, "table_names"):
    Engine.table_names = _table_names  # type: ignore

# ---------------------------------------------------------------------------------
# Dependency helper
# ---------------------------------------------------------------------------------
@contextmanager
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
