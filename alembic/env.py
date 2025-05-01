# alembic/env.py - ИСПРАВЛЕННАЯ ВЕРСИЯ v2

import asyncio
from logging.config import fileConfig

# Импортируем нужные функции из SQLAlchemy
from sqlalchemy import pool
# Убираем engine_from_config, он не нужен для online-режима с явным URL
# from sqlalchemy import engine_from_config
from sqlalchemy.ext.asyncio import create_async_engine # Используем create_async_engine

# Импортируем Alembic context
from alembic import context

# Импортируем Base из нашего проекта для MetaData
from app.db.base import Base
# Импортируем все модули с моделями, чтобы Alembic их "увидел"
import app.core.users.models # noqa
import app.core.reminders.models # noqa
import app.core.achievements.models # noqa
# Добавьте сюда импорты других модулей с моделями, если они появятся

# Это объект конфигурации Alembic, который предоставляет
# доступ к значениям из .ini файла.
config = context.config

# Интерпретируем файл конфигурации для Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Добавляем объект MetaData моделей для поддержки 'autogenerate'
target_metadata = Base.metadata

# Другие опции из env, можно установить через командную строку:
# my_important_option = config.get_main_option("my_important_option")

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    # Читаем URL из alembic.ini
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()

def do_run_migrations(connection) -> None:
    """Helper function called by run_migrations_online."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        )

    with context.begin_transaction():
        context.run_migrations()

async def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""

    # --- ИСПРАВЛЕНИЕ ЗДЕСЬ ---
    # Явно читаем URL из конфигурации alembic.ini по ключу 'sqlalchemy.url'
    db_url = config.get_main_option("sqlalchemy.url")
    if not db_url:
        raise ValueError("Database URL is not configured in alembic.ini (sqlalchemy.url)")

    # ВНИМАНИЕ: Alembic сам по себе работает синхронно, но для создания
    # асинхронного connectable мы используем асинхронный URL,
    # заменив синхронный драйвер на asyncpg.
    # Если в alembic.ini указан синхронный URL (напр. postgresql://),
    # нам нужно его адаптировать.
    if db_url.startswith("postgresql://"):
        async_db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif db_url.startswith("postgresql+psycopg2://"): # Обработаем и этот случай
         async_db_url = db_url.replace("postgresql+psycopg2://", "postgresql+asyncpg://", 1)
    elif db_url.startswith("postgresql+asyncpg://"):
        async_db_url = db_url # Уже правильный формат
    else:
        # Поддерживаем только PostgreSQL сейчас
        raise ValueError(f"Unsupported database URL scheme for async: {db_url}")

    # Создаем АСИНХРОННЫЙ движок явно, используя URL
    connectable = create_async_engine(
        async_db_url,
        poolclass=pool.NullPool, # Не используем пул соединений для Alembic
    )
    # -------------------------------------------------

    async with connectable.connect() as connection:
        # Запускаем миграции синхронно внутри асинхронной транзакции
        await connection.run_sync(do_run_migrations)

    # Освобождаем ресурсы движка
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
