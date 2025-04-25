"""
Базовые абстракции календарных провайдеров.

⚠️  Не импортируем ничего из app.core.calendar,
чтобы избежать циклической зависимости.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Protocol


# --------------------------------------------------------------------------- #
#                               Pydantic-like схемы                           #
# --------------------------------------------------------------------------- #

class CalendarEvent(Protocol):
    title: str
    start: datetime
    end: datetime | None


# --------------------------------------------------------------------------- #
#                        Абстрактный календарный провайдер                    #
# --------------------------------------------------------------------------- #

class BaseCalendarProvider(ABC):
    """Интерфейс любого календарного бэкэнда (Google, Outlook, No-op …)."""

    @abstractmethod
    def list_events(
        self,
        user_id: str,
        *,
        from_dt: datetime,
        to_dt: datetime | None = None,
    ) -> List[CalendarEvent]:
        ...

    @abstractmethod
    def add_event(
        self,
        user_id: str,
        title: str,
        start: datetime,
        end: datetime | None = None,
    ) -> CalendarEvent:
        ...


# --------------------------------------------------------------------------- #
#                    ↓↓↓  get_calendar_provider «добавится» позднее  ↓↓↓      #
# --------------------------------------------------------------------------- #
# Пакет app.core.calendar, закончив инициализацию, сам присвоит
#   this_module.get_calendar_provider = real_function
