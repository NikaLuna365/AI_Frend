from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TypedDict, Optional, List
from datetime import datetime

# --------------------------------------------------------------------------- #
#                             Событие в календаре                             #
# --------------------------------------------------------------------------- #

class CalendarEvent(TypedDict):
    id: str
    user_id: str
    title: str
    start: datetime
    end: Optional[datetime]
    description: Optional[str]
    provider: str


# --------------------------------------------------------------------------- #
#                         Интерфейс провайдера календаря                      #
# --------------------------------------------------------------------------- #

class BaseCalendarProvider(ABC):
    """Базовый интерфейс для всех календарных провайдеров."""
    name: str

    @abstractmethod
    def list_events(
        self,
        user_id: str,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> List[CalendarEvent]:
        """Получить список событий пользователя в интервале."""
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
        """Создать новое событие."""
        ...

    @abstractmethod
    def delete_event(self, event_id: str) -> None:
        """Удалить событие по идентификатору."""
        ...

# Для удобства тестов: переэкспортируем функцию
from app.core.calendar import get_calendar_provider  # noqa: F401
