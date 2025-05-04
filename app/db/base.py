# /app/app/db/base.py (Исправленная версия с commit в зависимости)

from __future__ import annotations

import contextlib
import logging
from typing import AsyncGenerator # Убедимся, что импортирован

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import (
    async_sessionmaker,
    AsyncSession,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

log = logging.getLogger(__name__)

# --- Declarative Base (без изменений) ---
class Base(DeclarativeBase):
    pass

# --- Engine & Session factory (без изменений) ---
# ... (код _make_engine, engine, async_session_factory, create_db_and_tables, drop_db_and_tables) ...
# --- Предполагаем, что async_session_factory определен корректно ---
if 'async_session_factory' not in globals() or async_session_factory is None: # pragma: no cover
     # Пересоздаем на всякий случай, если логика выше была в if/else
     if settings.ENVIRONMENT == "test":
         _engine = create_engine("sqlite+aiosqlite:///:memory:", connect_args={"check_same_thread": False}, echo=False, future=True)
         async_session_factory = async_sessionmaker(bind=_engine, class_=AsyncSession, expire_on_commit=False)
     else:
         _engine = create_async_engine(settings.DATABASE_URL, echo=settings.ENVIRONMENT == "dev", pool_pre_ping=True, future=True)
         async_session_factory = async_sessionmaker(bind=_engine, class_=AsyncSession, expire_on_commit=False)
     engine = _engine # Обновляем engine на всякий случай

if async_session_factory is None: # pragma: no cover
     raise RuntimeError("Async session factory could not be initialized!")
# ---------------------------------------------------------------------------

# --- Public helpers / dependencies ---

async def get_async_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency to get an async database session.
    Handles commit on success and rollback on error within the request scope.
    """
    session: AsyncSession | None = None # Инициализируем None
    try:
        # Получаем сессию из фабрики
        session = async_session_factory()
        log.debug("Yielding new async session %s", id(session))
        # Передаем сессию в эндпоинт
        yield session
        # --- ВАЖНО: Коммитим транзакцию при УСПЕШНОМ завершении эндпоинта ---
        log.debug("Committing session %s after successful request", id(session))
        await session.commit()
        # ------------------------------------------------------------------
    except Exception as e:
        # Если в эндпоинте возникло исключение
        log.exception("Rolling back session %s due to exception in request", id(session) if session else "N/A")
        if session is not None: # Проверяем, что сессия была создана перед rollback
            await session.rollback()
        # Перебрасываем исключение дальше, чтобы FastAPI вернул ошибку
        raise e
    finally:
        # Закрываем сессию в любом случае (хотя async with в фабрике может делать это сам)
        if session is not None:
            log.debug("Closing async session %s", id(session))
            await session.close() # Явное закрытие для надежности

# --- async_session_context (без изменений, т.к. commit/rollback там уже есть) ---
@contextlib.asynccontextmanager
async def async_session_context() -> AsyncGenerator[AsyncSession, None]:
    """Async context manager for DB sessions (scripts/tests/workers)."""
    session: AsyncSession = async_session_factory()
    log.debug("Entering async session context %s", id(session))
    try:
        yield session
        log.debug("Committing session %s from context", id(session))
        await session.commit() # Commit уже был здесь
    except Exception:
        log.exception("Rolling back session %s from context due to exception", id(session))
        await session.rollback()
        raise
    finally:
        log.debug("Closing session %s from context", id(session))
        await session.close()

# --- Convenience re-exports (без изменений) ---
# ... (engine, AsyncSession и т.д.) ...
__all__ = [
    "Base", "engine", "async_session_factory", "AsyncSession",
    "get_async_db_session", "async_session_context",
    # "create_db_and_tables", "drop_db_and_tables" # Уберем их пока из экспорта
]
