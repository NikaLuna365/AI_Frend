"""
Пакет calendar: фабрика провайдеров + публичные экспорты.
"""

from __future__ import annotations

import importlib
import os
import sys
from datetime import datetime
from typing import Dict, Type

from app.config import settings
from .base import BaseCalendarProvider, CalendarEvent  # noqa: F401

# --------------------------------------------------------------------------- #
#                            Реальные / заглушки-провайдеры                   #
# --------------------------------------------------------------------------- #

def _lazy_import(module_path: str, attr_name: str) -> Type[BaseCalendarProvider]:
    """
    Отложенный импорт, чтобы тяжёлые SDK не тянулись при unit-тестах.

    `module_path` может быть относительным ('.google').
    Мы передаём текущий пакет в `package`, чтобы Python правильно
    резолвил относительный путь.
    """
    module = importlib.import_module(module_path, package=__name__)
    return getattr(module, attr_name)


CALENDAR_PROVIDERS: Dict[str, Type[BaseCalendarProvider]] = {
    "google": _lazy_import(".google", "GoogleCalendarProvider"),
    "noop":   _lazy_import(".noop",   "NoOpCalendarProvider"),
}

# --------------------------------------------------------------------------- #
#                          Фабрика, видимая остальному коду                   #
# --------------------------------------------------------------------------- #

def get_calendar_provider(name: str | None = None) -> BaseCalendarProvider:
    """
    Вернуть инстанс провайдера.

    • если name передан явно — берём его;
    • иначе читаем из конфигурации (settings.CALENDAR_PROVIDER);
    • выбрасываем ValueError, если неизвестно.
    """
    provider_name = (name or settings.CALENDAR_PROVIDER).lower()
    try:
        cls = CALENDAR_PROVIDERS[provider_name]
    except KeyError as exc:
        raise ValueError(f"Unknown calendar provider: {provider_name!r}") from exc
    return cls()


# --------------------------------------------------------------------------- #
#                Экспортируем для «старых» импортов + public API              #
# --------------------------------------------------------------------------- #

__all__: list[str] = [
    "BaseCalendarProvider",
    "CalendarEvent",
    "get_calendar_provider",
]

# ① Делаем атрибут доступным как app.core.calendar.get_calendar_provider
sys.modules[__name__].get_calendar_provider = get_calendar_provider  # type: ignore[attr-defined]

# ② Прокидываем его в модуль base, чтобы старые импорты продолжали работать
_base_mod = sys.modules[__name__ + ".base"]
setattr(_base_mod, "get_calendar_provider", get_calendar_provider)
