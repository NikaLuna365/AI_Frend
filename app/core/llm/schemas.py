# app/core/llm/schemas.py
from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, Field


class Message(BaseModel):
    """
    Одна запись диалога для передачи в LLM.
    """
    role: str = Field(..., description="роль отправителя: 'user', 'assistant', 'system'")
    content: str = Field(..., description="текст сообщения")


class Event(BaseModel):
    """
    Событие, извлечённое из текста (дата/время + описание).
    """
    title: str = Field(..., description="название или краткое описание события")
    start: datetime = Field(..., description="начало события")
    end: datetime | None = Field(None, description="(опционально) окончание события")
