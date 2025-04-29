# alembic/env.py

import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
# Используем асинхронный движок для поддержки моделей,
# но сами операции Alembic будут синхронными.
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# Импортируем Base из нашего проекта, чтобы Alembic знал о моделях
# Убедитесь, что все ваши модели импортированы где-то,
# чтобы они были зарегистрированы в Base.metadata
# Например, импортировав основной модуль моделей или все по отдельности
from app.db.base import Base
# Импортируйте здесь все ваши модули с моделями, чтобы они были видны Base.metadata
import app.core.users.models # noqa
import app.core.reminders.models # noqa
import app.core.achievements.models # noqa
# Добавьте другие модели по мере их появления

# Это объект конфигурации Alembic, который предоставляет
# доступ к значениям из .ini файла.
config = context.config

# Интерпретируем файл конфигурации для Python logging.
# Эта строка предполагает, что ваш alembic.ini находится в текущем каталоге.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Добавляем объект MetaData моделей для поддержки 'autogenerate'
# <<< ВАЖНО >>>
target_metadata = Base.metadata

# Другие опции из env, можно установить через командную строку:
# my_important_option = config.get_main_option("my_important_option")
# ... и т.д.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        # Важно для корректной автогенерации типов PostgreSQL
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:
    """
    Helper function to run migrations using a given connection.
    """
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        # Важно для корректной автогенерации типов PostgreSQL
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    # Используем асинхронный движок, сконфигурированный из alembic.ini
    connectable = async_engine_from_config(
        config.get_section(config.config_main_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool, # Используем NullPool для Alembic
    )

    async with connectable.connect() as connection:
        # Запускаем миграции внутри асинхронного соединения,
        # но сами операции Alembic выполняем синхронно через await connection.run_sync
        await connection.run_sync(do_run_migrations)

    # Очищаем движок
    await connectable.dispose()


# Определяем, какой режим запущен - offline или online
if context.is_offline_mode():
    run_migrations_offline()
else:
    # Запускаем асинхронную функцию run_migrations_online
    asyncio.run(run_migrations_online())
