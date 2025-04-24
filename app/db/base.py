# app/db/base.py
"""
Базовая настройка SQLAlchemy + зависимость FastAPI.

Экспортируем:
    - engine           : общий движок SQLAlchemy
    - SessionLocal     : sessionmaker, привязанный к engine
    - Base             : DeclarativeBase для моделей
    - get_db_session() : зависимость для FastAPI (yield Session)
"""

from __future__ import annotations

from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session

from app.config import settings

# --------------------------------------------------------------------------- #
# Engine
# --------------------------------------------------------------------------- #

# echo=True выводит полный SQL в консоль — полезно на dev-стенде.
# На проде можно переключить на False или настроить логирование отдельно.
engine = create_engine(
    settings.DATABASE_URL,
    echo=settings.ENVIRONMENT == "development",
    pool_pre_ping=True,  # проверка соединений в пуле
    future=True,  # SQLAlchemy 2.0 style
)

# --------------------------------------------------------------------------- #
# Session factory
# --------------------------------------------------------------------------- #

SessionLocal: sessionmaker[Session] = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    future=True,
    expire_on_commit=False,
)

# --------------------------------------------------------------------------- #
# Declarative Base
# --------------------------------------------------------------------------- #

Base = declarative_base()

# --------------------------------------------------------------------------- #
# Dependency for FastAPI
# --------------------------------------------------------------------------- #

def get_db_session() -> Generator[Session, None, None]:
    """
    Генератор-зависимость FastAPI.

    Usage::
        from fastapi import Depends
        from sqlalchemy.orm import Session
        from app.db.base import get_db_session

        @router.get("/items/")
        def list_items(db: Session = Depends(get_db_session)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


__all__: list[str] = [
    "engine",
    "SessionLocal",
    "Base",
    "get_db_session",
]
