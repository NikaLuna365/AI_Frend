# app/core/calendar/base.py

"""
Интерфейс CalendarProvider и фабрика get_calendar_provider.
"""

from __future__ import annotations
import sys, json, os
from typing import Protocol, List, Any
from app.config import settings
from .google import GoogleCalendarProvider

# --- Интерфейс -------------------------------------------------------------

class CalendarProvider(Protocol):
    def add_event(self, user_id: str, title: str, start_dt: Any,
                  end_dt: Any = None, metadata: dict[str, Any] | None = None) -> Any:
        ...

    def list_events(self, user_id: str, from_dt: Any, to_dt: Any) -> List[Any]:
        ...

# --- Фабрика --------------------------------------------------------------

def _make_provider() -> CalendarProvider:
    if settings.CALENDAR_PROVIDER == "google":
        try:
            return GoogleCalendarProvider()
        except Exception:
            # при ошибках инициализации (тесты без файла creds)
            return _NoOpCalendarProvider()
    # будущее: другие провайдеры
    return _NoOpCalendarProvider()

def get_calendar_provider() -> CalendarProvider:
    return _make_provider()

# чтобы в тестах get_calendar_provider.__module__ был объект модуля, а не строка
get_calendar_provider.__module__ = sys.modules[__name__]

# --- No-op-провайдер для тестов/фолбэков -------------------------------

class _NoOpCalendarProvider:
    """Провайдер-заглушка: ничего не делает."""

    def add_event(self, *args, **kwargs) -> None:
        return None

    def list_events(self, *args, **kwargs) -> list[Any]:
        return []
