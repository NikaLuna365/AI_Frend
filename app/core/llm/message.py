# /app/app/core/llm/message.py (Проверенная версия)

from __future__ import annotations # Используем для < 3.9

from typing import TypedDict # Используем TypedDict
from datetime import datetime

# --- Определения ---
class Message(TypedDict):
    """Представляет одно текстовое сообщение для LLM."""
    role: str       # 'user' или 'assistant' (или 'model' для Gemini)
    content: str    # текст сообщения

class Event(TypedDict):
    """
    Событие, извлечённое из текста LLM.
    """
    title: str
    start: datetime
    end: datetime | None # Используем Union для < 3.10 или | для >= 3.10

# --- Экспорты ---
__all__ = ["Message", "Event"] # Экспортируем явно
