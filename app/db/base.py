# app/db/base.py

"""
Unified Asynchronous SQLAlchemy base & session factory.

Provides:
- Single Declarative Base (`Base`) for all models.
- Asynchronous Engine (`engine`) configured based on ENVIRONMENT:
    - ENVIRONMENT=test -> SQLite in-memory (sync for simplicity in tests for now)
    - Otherwise        -> PostgreSQL via asyncpg using settings.DATABASE_URL
- Asynchronous Session Factory (`async_session_factory`) for creating sessions.
- FastAPI Dependency (`get_async_db_session`) for injecting sessions into routes.
- Async Context Manager (`async_session_context`) for scripts/tests/workers.
"""
from __future__ import annotations

import contextlib
import logging
from typing import AsyncGenerator

# Используем create_engine для синхронного SQLite в тестах
from sqlalchemy import create_engine
# Используем async_engine_from_config и create_async_engine для async
from sqlalchemy.ext.asyncio import (
    async_sessionmaker,
    AsyncSession,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

log = logging.getLogger(__name__)

# --------------------------------------------------------------------------- #
#                               Declarative Base                              #
# --------------------------------------------------------------------------- #
class Base(DeclarativeBase):
    """Single declarative base for the project."""
    pass

# --------------------------------------------------------------------------- #
#                            Engine & Session factory                         #
# --------------------------------------------------------------------------- #
# Инициализация engine как None по умолчанию
engine = None
async_session_factory = None

if settings.ENVIRONMENT == "test":
    log.info("Using SYNC SQLite database for tests.")
    # Для тестов пока оставим синхронный SQLite для простоты
    # Это потребует адаптации тестов, использующих фикстуры с сессиями,
    # или перехода на async-совместимую тестовую БД позже (например, aiosqlite)
    # Важно: Тесты НЕ СМОГУТ проверить реальную асинхронную работу с БД.
    # Это компромисс ради скорости и простоты начального этапа рефакторинга тестов.
    engine = create_engine(
        "sqlite+aiosqlite:///:memory:", # Используем aiosqlite для совместимости с async API
        connect_args={"check_same_thread": False},
        echo=False,
        future=True, # SQLAlchemy 2.0 style
    )
    # Создаем async_sessionmaker даже для SQLite для единообразия интерфейса
    async_session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False, # Важно для async
        autocommit=False,
        autoflush=False,
    )

    # Определяем Base.metadata.create_all/drop_all для синхронного движка
    # для использования в тестовых фикстурах
    async def create_db_and_tables():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def drop_db_and_tables():
         async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)

else:
    log.info("Using ASYNC PostgreSQL database: %s", settings.DATABASE_URL)
    # Для dev/prod используем асинхронный PostgreSQL
    # Убедитесь, что DATABASE_URL имеет префикс 'postgresql+asyncpg://'
    if not settings.DATABASE_URL.startswith("postgresql+asyncpg://"):
        log.warning(
            "DATABASE_URL does not start with 'postgresql+asyncpg://'. "
            "Ensure asyncpg driver is specified."
        )
        # Можно либо выбросить ошибку, либо попытаться исправить (менее надежно)
        # raise ValueError("DATABASE_URL must use 'asyncpg' driver for async operations.")

    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=settings.ENVIRONMENT == "dev", # Логгирование SQL в dev
        pool_pre_ping=True, # Проверка соединения перед использованием
        future=True, # Обязательно для SQLAlchemy 2.0
        # Настройки пула соединений (можно тюнить при необходимости)
        # pool_size=10,
        # max_overflow=20,
    )

    async_session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False, # Важно для async, чтобы объекты были доступны после commit
        autocommit=False,
        autoflush=False,
    )

    async def create_db_and_tables():
         log.warning("Database creation is typically handled by Alembic in dev/prod.")
         # В dev/prod создание таблиц обычно делается через Alembic
         # Эта функция здесь больше для полноты картины
         # async with engine.begin() as conn:
         #     await conn.run_sync(Base.metadata.create_all) # НЕ РЕКОМЕНДУЕТСЯ в проде

    async def drop_db_and_tables():
        log.warning("Database dropping is typically handled by Alembic in dev/prod.")
        # В dev/prod удаление таблиц обычно делается через Alembic
        # async with engine.begin() as conn:
        #     await conn.run_sync(Base.metadata.drop_all) # НЕ РЕКОМЕНДУЕТСЯ в проде


# Проверяем, что фабрика сессий создана
if async_session_factory is None: # pragma: no cover
    raise RuntimeError("Async session factory not initialized!")

# --------------------------------------------------------------------------- #
#                         Public helpers / dependencies                       #
# --------------------------------------------------------------------------- #

async def get_async_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency to get an async database session.

    Yields:
        AsyncSession: The database session.
    """
    async with async_session_factory() as session:
        log.debug("Yielding new async session %s", id(session))
        try:
            yield session
        except Exception:
            log.exception("Rolling back session %s due to exception", id(session))
            await session.rollback()
            raise
        finally:
            log.debug("Closing async session %s", id(session))
            # Закрытие сессии не требуется с async context manager 'async with'
            # await session.close() # Не нужно

@contextlib.asynccontextmanager
async def async_session_context() -> AsyncGenerator[AsyncSession, None]:
    """
    Async context manager for database sessions in scripts/tests/workers.
    Handles commit on success and rollback on error.

    Yields:
        AsyncSession: The database session.
    """
    async with async_session_factory() as session:
        log.debug("Entering async session context %s", id(session))
        try:
            yield session
            log.debug("Committing session %s", id(session))
            await session.commit()
        except Exception:
            log.exception("Rolling back session %s from context due to exception", id(session))
            await session.rollback()
            raise
        finally:
            log.debug("Exiting async session context %s", id(session))
            # Закрытие сессии не требуется с async context manager 'async with'

# --------------------------------------------------------------------------- #
#                          Convenience re-exports                             #
# --------------------------------------------------------------------------- #
__all__: list[str] = [
    "Base",
    "engine", # Экспортируем engine (может быть sync или async)
    "async_session_factory",
    "AsyncSession", # Экспортируем сам тип сессии
    "get_async_db_session",
    "async_session_context",
    "create_db_and_tables", # Для использования в тестах
    "drop_db_and_tables",   # Для использования в тестах
]
