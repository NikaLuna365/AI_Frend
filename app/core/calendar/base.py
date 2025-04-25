# app/core/calendar/base.py

"""
Интерфейс CalendarProvider и фабрика get_calendar_provider.
"""

from __future__ import annotations
import sys
from typing import Protocol, Any, List

from app.config import settings
from .google import GoogleCalendarProvider

class CalendarProvider(Protocol):
    """Протокол (интерфейс) для календарных провайдеров."""

    def add_event(
        self,
        user_id: str,
        title: str,
        start_dt: Any,
        end_dt: Any | None = None,
        metadata: dict[str, Any] | None = None
    ) -> Any:
        ...

    def list_events(
        self,
        user_id: str,
        from_dt: Any,
        to_dt: Any
    ) -> List[Any]:
        ...


def _make_provider() -> CalendarProvider:
    if settings.CALENDAR_PROVIDER == "google":
        try:
            return GoogleCalendarProvider()
        except Exception:
            # при ошибках инициализации (например, на тестах без JSON)
            return _NoOpCalendarProvider()
    # для будущих реализаций (outlook, ical и т.д.)
    return _NoOpCalendarProvider()


def get_calendar_provider() -> CalendarProvider:
    """Фабрика: возвращает нужный провайдер."""
    return _make_provider()

# Такое нужно, чтобы monkeypatch.setattr(get_calendar_provider.__module__, ...)
# работал корректно, а не ссылался на строку.
get_calendar_provider.__module__ = sys.modules[__name__].__name__  # "app.core.calendar.base"


class _NoOpCalendarProvider:
    """Заглушка, ничего не делающая."""

    def add_event(self, *args, **kwargs) -> None:
        return None

    def list_events(self, *args, **kwargs) -> list[Any]:
        return []
