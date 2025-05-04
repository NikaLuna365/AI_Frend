# /app/app/db/base.py (Финальная версия с commit в зависимости)

from __future__ import annotations

import contextlib
import logging
from typing import AsyncGenerator

# Импорты SQLAlchemy
from sqlalchemy import create_engine # Для синхронного движка в тестах
from sqlalchemy.ext.asyncio import (
    async_sessionmaker,
    AsyncSession,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.exc import SQLAlchemyError # Для более специфичного except

# Импорт настроек
from app.config import settings

log = logging.getLogger(__name__)

# --- Declarative Base ---
class Base(DeclarativeBase):
    pass

# --- Engine & Session factory ---
engine = None
async_session_factory = None

# --- Инициализация engine и фабрики (как в ответе #18) ---
# (Этот блок должен быть здесь и работать корректно)
if settings.ENVIRONMENT == "test":
    log.info("Using SYNC SQLite database (aiosqlite) for tests.")
    engine = create_engine(
        "sqlite+aiosqlite:///:memory:", connect_args={"check_same_thread": False}, echo=False, future=True
    )
    async_session_factory = async_sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False
    )
else:
    log.info("Using ASYNC PostgreSQL database: %s", settings.DATABASE_URL)
    if not settings.DATABASE_URL.startswith("postgresql+asyncpg://"):
        log.warning("DATABASE_URL does not start with 'postgresql+asyncpg://'.")
        # Лучше выбросить ошибку, чтобы не продолжать с неверной конфигурацией
        raise ValueError("DATABASE_URL must use 'asyncpg' driver for async operations.")

    engine = create_async_engine(
        settings.DATABASE_URL, echo=(settings.ENVIRONMENT == "dev"), pool_pre_ping=True, future=True
    )
    async_session_factory = async_sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False
    )

if async_session_factory is None: # pragma: no cover
    raise RuntimeError("Async session factory could not be initialized!")
# --- Конец инициализации ---


# --- ИСПРАВЛЕННАЯ ЗАВИСИМОСТЬ С COMMIT ---
async def get_async_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency: Creates and yields an async session, handling commit/rollback.
    """
    session: AsyncSession | None = None
    session_id_for_log = "N/A" # Для логирования в случае ошибки создания
    try:
        session = async_session_factory()
        session_id_for_log = id(session) # Получаем ID для логов
        log.debug(">>> get_async_db_session: Session %s created, yielding...", session_id_for_log)
        yield session
        # --- ЯВНЫЙ COMMIT ЗДЕСЬ ---
        log.debug(">>> get_async_db_session: Session %s work done, committing...", session_id_for_log)
        await session.commit()
        log.info(">>> get_async_db_session: Session %s committed.", session_id_for_log)
        # ---------------------------
    except SQLAlchemyError as db_exc: # Ловим специфичные ошибки SQLAlchemy
        log.exception( # Используем exception для полного трейсбэка
            ">>> get_async_db_session: SQLAlchemyError in session %s, rolling back...",
            session_id_for_log
        )
        if session is not None:
            await session.rollback()
        # Можно выбросить HTTPException или само исключение
        # raise HTTPException(status_code=500, detail="Database error") from db_exc
        raise db_exc # Перебрасываем исходное
    except Exception as e: # Ловим другие ошибки
        log.exception(
            ">>> get_async_db_session: Non-DB Exception in session %s scope, rolling back...",
             session_id_for_log
        )
        if session is not None:
            await session.rollback()
        raise e # Перебрасываем исходное
    finally:
        if session is not None:
            log.debug(">>> get_async_db_session: Closing session %s", session_id_for_log)
            await session.close() # Закрываем сессию в finally
# ---------------------------------------------

# --- Контекстный менеджер (без изменений) ---
@contextlib.asynccontextmanager
async def async_session_context() -> AsyncGenerator[AsyncSession, None]:
    # ... (код как в ответе #18, он уже содержит commit/rollback) ...
    session: AsyncSession = async_session_factory()
    log.debug("Entering async session context %s", id(session))
    try:
        yield session
        log.debug("Committing session %s from context", id(session))
        await session.commit()
    except Exception:
        log.exception("Rolling back session %s from context due to exception", id(session))
        await session.rollback()
        raise
    finally:
        log.debug("Closing session %s from context", id(session))
        await session.close()


# --- Экспорты ---
__all__ = [
    "Base", "engine", "async_session_factory", "AsyncSession",
    "get_async_db_session", "async_session_context",
]
