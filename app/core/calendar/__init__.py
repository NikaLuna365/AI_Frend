"""
core.calendar
~~~~~~~~~~~~~
Единая точка входа для работы с календарём.

Интерфейс BaseCalendarProvider минимален – нужны только
list_events() и add_event(). Реальные провайдеры (Google)
и noop-заглушка регистрируются в словаре.

Использование:
    from app.core.calendar import get_calendar_provider

    calendar = get_calendar_provider()
    calendar.add_event(…)
"""
from __future__ import annotations

from typing import Dict, Type

from app.config import settings
from .base import BaseCalendarProvider
from .providers.noop import NoopCalendarProvider
from .providers.google import GoogleCalendarProvider

_PROVIDER_REGISTRY: Dict[str, Type[BaseCalendarProvider]] = {
    "noop": NoopCalendarProvider,
    "google": GoogleCalendarProvider,
}


def get_calendar_provider() -> BaseCalendarProvider:
    name = settings.CALENDAR_PROVIDER.lower()
    try:
        return _PROVIDER_REGISTRY[name]()  # type: ignore[call-arg]
    except KeyError as exc:  # pragma: no cover
        raise RuntimeError(f"Unknown calendar provider: {name}") from exc
