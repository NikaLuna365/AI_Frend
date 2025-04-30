# /app/alembic/env.py

import asyncio
from logging.config import fileConfig

# --- ИСПРАВЛЕНИЕ: Импортируем engine_from_config из sqlalchemy ---
from sqlalchemy import pool, engine_from_config # <--- Добавили engine_from_config

# Используем асинхронный движок для поддержки моделей,
# но сами операции Alembic будут синхронными.
from sqlalchemy.ext.asyncio import async_engine_from_config # <--- Оставляем это для run_migrations_online

from alembic import context

# Импортируем Base из нашего проекта, чтобы Alembic знал о моделях
from app.db.base import Base
# Импортируем все модули с моделями
import app.core.users.models # noqa
import app.core.reminders.models # noqa
import app.core.achievements.models # noqa

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True, # Оставляем для PostgreSQL
    )

    with context.begin_transaction():
        context.run_migrations()

def do_run_migrations(connection) -> None:
    """Helper function to run migrations using a given connection."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True, # Оставляем для PostgreSQL
    )

    with context.begin_transaction():
        context.run_migrations()

async def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""

    # --- ИСПРАВЛЕНИЕ: Используем config_ini_section ---
    # Создаем connectable (асинхронный движок) из секции alembic.ini
    connectable = async_engine_from_config(
        # config.get_section(config.config_main_section), # <-- БЫЛО НЕПРАВИЛЬНО
        config.get_section(config.config_ini_section), # <-- ИСПРАВЛЕНО
        prefix="sqlalchemy.",
        poolclass=pool.NullPool, # Используем NullPool для Alembic
    )
    # -------------------------------------------------

    async with connectable.connect() as connection:
        # Запускаем миграции через run_sync
        await connection.run_sync(do_run_migrations)

    # Очищаем движок
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
