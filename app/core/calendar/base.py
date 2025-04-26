# app/core/calendar/base.py
"""
Abstract base and common types for calendar providers.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import TypedDict, List, Optional

class CalendarEvent(TypedDict):
    """
    Общая Pydantic-подобная модель события календаря.
    """
    id: str
    user_id: str
    title: str
    start: datetime
    end: Optional[datetime]
    description: Optional[str]
    provider: str

class BaseCalendarProvider(ABC):
    """
    Абстрактный интерфейс провайдера календаря.
    """

    name: str

    @abstractmethod
    def list_events(
        self,
        user_id: str,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> List[CalendarEvent]:
        """
        Вернуть события пользователя в заданном интервале.
        Если start/end не заданы — вернуть всё.
        """
        ...

    @abstractmethod
    def add_event(
        self,
        user_id: str,
        title: str,
        start: datetime,
        end: Optional[datetime] = None,
        description: Optional[str] = None,
    ) -> CalendarEvent:
        """
        Создать событие и вернуть его.
        """
        ...

    @abstractmethod
    def delete_event(self, event_id: str) -> None:
        """
        Удалить событие по ID.
        """
        ...
