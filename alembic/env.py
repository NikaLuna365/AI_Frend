# /app/alembic/env.py (Версия для MVP Beta Backend Plan)

import asyncio
from logging.config import fileConfig

# Импортируем нужные функции из SQLAlchemy
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import create_async_engine

# Импортируем Alembic context
from alembic import context

# --- Конфигурация ---
# Это объект конфигурации Alembic, читает alembic.ini
config = context.config

# Интерпретируем файл конфигурации для стандартного логирования Python.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# --- Метаданные Моделей ---
# Импортируем базовый класс SQLAlchemy из нашего проекта
from app.db.base import Base

# ВАЖНО: Импортируем ТОЛЬКО модули, содержащие модели,
# НЕОБХОДИМЫЕ ДЛЯ MVP, чтобы Alembic их "увидел"
import app.core.users.models # noqa (Предполагаем, что User и Message здесь)
import app.core.achievements.models # noqa (Предполагаем, что AchievementRule и Achievement здесь)
# import app.core.reminders.models # noqa (ЗАКОММЕНТИРОВАНО - не нужно для MVP)
# Добавьте сюда импорты других MVP моделей, если они есть (например, для RAG/Facts)

# Устанавливаем target_metadata для поддержки 'autogenerate'
# Alembic будет сравнивать состояние БД с моделями, зарегистрированными в этой Base.metadata
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
        compare_type=True, # Сравнивать типы столбцов (важно для PostgreSQL)
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
        raise ValueError("Database URL not configured in alembic.ini (sqlalchemy.url)")

    # Адаптируем URL для asyncpg, если он в синхронном формате
    if db_url.startswith("postgresql://"):
        async_db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif db_url.startswith("postgresql+psycopg2://"):
        async_db_url = db_url.replace("postgresql+psycopg2://", "postgresql+asyncpg://", 1)
    elif db_url.startswith("postgresql+asyncpg://"):
        async_db_url = db_url # Уже правильный
    else:
        # Если вы планируете использовать другую БД в будущем, добавьте обработку здесь
        raise ValueError(f"Unsupported DB URL scheme for async operation: {db_url}")

    # Создаем асинхронный движок
    # Используем poolclass=pool.NullPool, т.к. Alembic выполняет короткие операции
    connectable = create_async_engine(
        async_db_url,
        poolclass=pool.NullPool,
    )

    # Асинхронно подключаемся
    async with connectable.connect() as connection:
        # Выполняем миграции синхронно внутри асинхронной транзакции
        await connection.run_sync(do_run_migrations)

    # Освобождаем ресурсы движка явно
    await connectable.dispose()

# --- Основная логика env.py ---
# Определяем режим (offline или online) и запускаем соответствующую функцию
if context.is_offline_mode():
    run_migrations_offline()
else:
    # Запускаем асинхронную функцию для online режима
    # asyncio.run() создает и управляет event loop для этого вызова
    asyncio.run(run_migrations_online())
