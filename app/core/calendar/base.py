# app/core/calendar/base.py
"""
Registry-паттерн для календарных провайдеров.

GoogleCalendarProvider – реальный
NoOpCalendarProvider   – заглушка (тесты)
"""

from __future__ import annotations

from typing import Protocol, Any

from app.config import settings
from .google import GoogleCalendarProvider
from .noop import NoOpCalendarProvider


class CalendarProvider(Protocol):
    def add_event(
        self,
        user_id: str,
        title: str,
        start_dt: Any,
        end_dt: Any | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Any: ...

    def list_events(self, user_id: str, from_dt: Any, to_dt: Any) -> list[Any]: ...


_PROVIDERS: dict[str, type[CalendarProvider]] = {
    "google": GoogleCalendarProvider,
    "noop": NoOpCalendarProvider,
}


def get_calendar_provider() -> CalendarProvider:
    """Возвращает провайдер, указанный в Settings."""
    name = settings.CALENDAR_PROVIDER.lower()
    cls = _PROVIDERS.get(name, NoOpCalendarProvider)
    return cls()
