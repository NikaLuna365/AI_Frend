# /app/alembic/env.py - ИСПРАВЛЕННАЯ ВЕРСИЯ

import asyncio
from logging.config import fileConfig

# Импортируем нужные функции из SQLAlchemy
from sqlalchemy import pool
from sqlalchemy import engine_from_config # Для синхронной работы в offline режиме
from sqlalchemy.ext.asyncio import async_engine_from_config # Для online режима

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
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well. By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.
    """
    # Используем синхронный URL из alembic.ini
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        # compare_type=True может быть полезен для автогенерации специфичных типов
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()

def do_run_migrations(connection) -> None:
    """Helper function called by run_migrations_online."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        # compare_type=True может быть полезен для автогенерации специфичных типов
        compare_type=True,
        )

    with context.begin_transaction():
        context.run_migrations()

async def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.
    """
    # Создаем АСИНХРОННЫЙ движок из конфигурации alembic.ini
    # ВНИМАНИЕ: Используем async_engine_from_config
    connectable = async_engine_from_config(
        # --- ИСПРАВЛЕНИЕ ЗДЕСЬ ---
        config.get_section(config.config_ini_section), # Используем правильное имя секции
        # -------------------------
        prefix="sqlalchemy.",
        poolclass=pool.NullPool, # Не используем пул соединений для Alembic
    )

    # Подключаемся асинхронно
    async with connectable.connect() as connection:
        # Запускаем миграции синхронно внутри асинхронной транзакции
        await connection.run_sync(do_run_migrations)

    # Освобождаем ресурсы движка
    await connectable.dispose()

# Определяем режим и запускаем соответствующую функцию
if context.is_offline_mode():
    run_migrations_offline()
else:
    # Запускаем асинхронную функцию run_migrations_online
    asyncio.run(run_migrations_online())
