# app/core/calendar/base.py
"""
Registry-паттерн для календарных провайдеров.
"""

from __future__ import annotations

import sys
from typing import Any, List, Protocol

from app.config import settings
from .google import GoogleCalendarProvider
from .noop import NoOpProvider


# --------------------------------------------------------------------------- #
# Интерфейс
# --------------------------------------------------------------------------- #
class CalendarProvider(Protocol):
    def add_event(
        self,
        user_id: str,
        title: str,
        start_dt: Any,
        end_dt: Any | None = None,
        metadata: dict[str, Any] | None = None,
    ): ...

    def list_events(
        self,
        user_id: str,
        from_dt: Any,
        to_dt: Any,
    ) -> List[Any]: ...


# --------------------------------------------------------------------------- #
# Registry
# --------------------------------------------------------------------------- #
_CALENDAR_PROVIDERS: dict[str, type[CalendarProvider]] = {
    "google": GoogleCalendarProvider,
    "noop": NoOpProvider,
}


def get_calendar_provider() -> CalendarProvider:
    cls = _CALENDAR_PROVIDERS.get(settings.CALENDAR_PROVIDER, NoOpProvider)
    return cls()


# важно для monkeypatch в тестах
get_calendar_provider.__module__ = sys.modules[__name__]
__all__ = ["get_calendar_provider", "CalendarProvider"]
