# app/core/calendar/schemas.py
"""
Pydantic-схемы календарных событий.

Используются в:
    * app/api/v1/chat.py                ― возврат detected_events
    * app/api/v1/calendar.py            ― публичный REST-эндпоинт
    * core.calendar.<provider>.py       ― маппинг данных провайдера → EventOut
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class EventBase(BaseModel):
    """Общие поля события."""

    title: str = Field(..., description="Заголовок события")
    start_dt: datetime = Field(..., description="Дата/время начала события (UTC)")
    end_dt: datetime | None = Field(None, description="Дата/время окончания события (UTC)")
    metadata: dict[str, Any] | None = Field(
        None,
        description="Доп. данные (location, meet-link, color и т. д.)",
    )

    model_config = {"from_attributes": True}


class EventIn(EventBase):
    """Событие, приходящее от пользователя/LLM (ещё без ID)."""


class EventOut(EventBase):
    """Событие, сохранённое в провайдере / БД."""

    id: str = Field(..., description="Идентификатор события в провайдере/БД")


__all__: list[str] = ["EventIn", "EventOut"]
