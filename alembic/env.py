# /app/alembic/env.py (Финальная версия для Фазы 0)

import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.ext.asyncio import create_async_engine # Только асинхронный движок

from alembic import context

# --- Конфигурация ---
# Это объект конфигурации Alembic, читает alembic.ini
config = context.config

# Интерпретируем .ini файл для стандартного логирования Python.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# --- Метаданные Моделей ---
# Импортируем базовый класс SQLAlchemy из нашего проекта
from app.db.base import Base
# ВАЖНО: Импортируем ВСЕ модули, содержащие модели SQLAlchemy,
# чтобы они были зарегистрированы в Base.metadata
import app.core.users.models # noqa
import app.core.reminders.models # noqa
import app.core.achievements.models # noqa
# Добавьте сюда будущие модели...

# Устанавливаем target_metadata для поддержки 'autogenerate'
target_metadata = Base.metadata

# --- Функции Выполнения Миграций ---

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.
    Генерирует SQL скрипты без подключения к БД.
    """
    # Получаем URL из секции [alembic] файла alembic.ini
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True, # Генерировать SQL без плейсхолдеров
        dialect_opts={"paramstyle": "named"},
        compare_type=True, # Сравнивать типы столбцов (важно для некоторых СУБД)
    )

    with context.begin_transaction():
        context.run_migrations()

def do_run_migrations(connection) -> None:
    """Вспомогательная функция для запуска миграций с готовым соединением."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True, # Сравнивать типы столбцов
        )
    with context.begin_transaction():
        context.run_migrations()

async def run_migrations_online() -> None:
    """Run migrations in 'online' mode.
    Подключается к БД и применяет миграции.
    """
    # Получаем URL из секции [alembic] файла alembic.ini
    db_url = config.get_main_option("sqlalchemy.url")
    if not db_url:
        # Эта ошибка не должна возникать, если alembic.ini настроен правильно
        raise ValueError("Database URL not configured in alembic.ini (sqlalchemy.url)")

    # Адаптируем URL для asyncpg, если он в синхронном формате
    if db_url.startswith("postgresql://"):
        async_db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif db_url.startswith("postgresql+psycopg2://"):
        async_db_url = db_url.replace("postgresql+psycopg2://", "postgresql+asyncpg://", 1)
    elif db_url.startswith("postgresql+asyncpg://"):
        async_db_url = db_url # Уже правильный
    else:
        raise ValueError(f"Unsupported DB URL scheme for async: {db_url}")

    # Создаем асинхронный движок
    connectable = create_async_engine(
        async_db_url,
        poolclass=pool.NullPool, # Не используем пул для Alembic
    )

    # Асинхронно подключаемся
    async with connectable.connect() as connection:
        # Выполняем миграции синхронно внутри асинхронной транзакции
        await connection.run_sync(do_run_migrations)

    # Освобождаем ресурсы движка
    await connectable.dispose()

# --- Основная логика env.py ---
if context.is_offline_mode():
    run_migrations_offline()
else:
    # Запускаем асинхронную функцию для online режима
    asyncio.run(run_migrations_online())
