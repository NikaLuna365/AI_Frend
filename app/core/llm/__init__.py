# /app/app/core/llm/__init__.py (ИСПРАВЛЕННАЯ ВЕРСИЯ)

from __future__ import annotations

# --- Реэкспортируем КЛИЕНТ ---
from .client import LLMClient

# --- Реэкспортируем ТИПЫ СООБЩЕНИЙ/СОБЫТИЙ из правильного места ---
from .message import Message, Event

# --- Опционально: Реэкспортируем базовый класс провайдера или фабрику ---
#     (но обычно клиент - основная точка входа)
# from .providers import BaseLLMProvider, get_llm_provider

# --- Определяем, что будет доступно при 'from app.core.llm import *' ---
__all__ = [
    "LLMClient",
    "Message",
    "Event",
    # "BaseLLMProvider", # Раскомментируйте, если нужно
    # "get_llm_provider", # Раскомментируйте, если нужно
]
