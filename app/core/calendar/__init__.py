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

# lazy-import, чтобы тяжёлые SDK не тянулись в unit-тестах
def _lazy_import(path: str, name: str) -> Type[BaseCalendarProvider]:
    module = importlib.import_module(path)
    return getattr(module, name)


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
    • выбрасываем KeyError / ValueError, если неизвестно.
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
    # публичное
    "BaseCalendarProvider",
    "CalendarEvent",
    "get_calendar_provider",
]

# ① Сохраняем ссылку в самом пакете
sys.modules[__name__].get_calendar_provider = get_calendar_provider  # type: ignore[attr-defined]

# ② И — главное! — прокидываем её в модуль base,
#     чтобы `from app.core.calendar.base import get_calendar_provider` продолжал работать
_base_mod = sys.modules[__name__ + ".base"]
setattr(_base_mod, "get_calendar_provider", get_calendar_provider)
