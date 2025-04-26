# app/core/llm/message.py

from typing import TypedDict
from datetime import datetime

class Message(TypedDict):
    """Представляет одно текстовое сообщение для LLM."""
    role: str       # 'user' или 'assistant'
    content: str    # текст сообщения

class Event(TypedDict):
    """
    Событие, извлечённое из текста LLM.
    Поля:
      - title   : заголовок/название события
      - start   : время начала (datetime)
      - end     : время окончания (или None, если не задано)
    """
    title: str
    start: datetime
    end: datetime | None
