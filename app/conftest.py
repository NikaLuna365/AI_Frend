# conftest.py
import os
import sys

# Добавляем корень репозитория в PYTHONPATH, чтобы 'import app...' работал
sys.path.insert(0, str(os.path.dirname(__file__)))

# Тестовое окружение: in-memory SQLite и eager Celery
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

# Обязательно после установки ENVIRONMENT подключаем Celery-конфиг eager
from app.workers.tasks import celery_app

celery_app.conf.task_always_eager = True
celery_app.conf.task_eager_propagates = True
