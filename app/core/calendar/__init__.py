from __future__ import annotations

import os
from typing import Dict, Type

from app.config import settings
from .base import BaseCalendarProvider, CalendarEvent
from .noop import NoOpCalendarProvider
from .google import GoogleCalendarProvider  # предполагается, что файл google.py есть

# --------------------------------------------------------------------------- #
#                          Провайдер-реестр / фабрика                          #
# --------------------------------------------------------------------------- #

_providers: Dict[str, Type[BaseCalendarProvider]] = {
    "noop": NoOpCalendarProvider,
    "google": GoogleCalendarProvider,
}

def get_calendar_provider(name: str | None = None) -> BaseCalendarProvider:
    """
    Возвращает экземпляр провайдера по имени.
    Если имя не передано — смотрим settings.CALENDAR_PROVIDER.
    """
    key = (name or settings.CALENDAR_PROVIDER).lower()
    cls = _providers.get(key)
    if not cls:
        raise ValueError(f"Unknown calendar provider: {key!r}")
    return cls()
