"""
Calendar subsystem package.

• ``CalendarEvent``  – общая Pydantic-модель события (см. base.py).
• ``BaseCalendarProvider`` – абстрактный интерфейс провайдера.
• ``get_calendar_provider()`` – фабрика, возвращающая инстанс
  нужного провайдера по имени или из ``settings.CALENDAR_PROVIDER``.

Ленивая загрузка (``importlib.import_module``) исключает тяжёлые
зависимости (Google SDK и т. п.) в dev/CI, пока они реально не нужны.
"""
from __future__ import annotations

import importlib
import sys
from typing import Dict, Type

from app.config import settings
from .base import BaseCalendarProvider, CalendarEvent  # noqa: F401 (экспорт в __all__)

# --------------------------------------------------------------------------- #
#                       helpers: lazy-import specific provider                #
# --------------------------------------------------------------------------- #
def _lazy_import(module_suffix: str, class_name: str) -> Type[BaseCalendarProvider]:
    """
    _lazy_import(".noop", "NoOpCalendarProvider")  →  <class NoOpCalendarProvider>
    Относительный путь (``.noop``) ищется внутри текущего пакета.
    """
    module = importlib.import_module(f"{__name__}{module_suffix}", package=__name__)
    return getattr(module, class_name)


# --------------------------------------------------------------------------- #
#                       registry: name → provider-class                       #
# --------------------------------------------------------------------------- #
_PROVIDER_CLASSES: Dict[str, Type[BaseCalendarProvider]] = {
    "noop": _lazy_import(".noop", "NoOpCalendarProvider"),
    # "google": _lazy_import(".google", "GoogleCalendarProvider"),  # позже
}

# --------------------------------------------------------------------------- #
#                                 public API                                  #
# --------------------------------------------------------------------------- #
def get_calendar_provider(name: str | None = None) -> BaseCalendarProvider:
    """
    Вернуть экземпляр календарного провайдера.

    • ``name`` – явное имя (case-insensitive).  
    • Если не передано — берём из ``settings.CALENDAR_PROVIDER``;
      в ``.env.test`` / ``.env.dev`` по-умолчанию это «noop».
    """
    provider_key = (name or settings.CALENDAR_PROVIDER).lower()
    try:
        provider_cls = _PROVIDER_CLASSES[provider_key]
    except KeyError as exc:  # pragma: no cover
        raise ValueError(f"Unknown calendar provider: {provider_key}") from exc
    return provider_cls()


# --------------------------------------------------------------------------- #
#           make get_calendar_provider видимым из app.core.calendar.base      #
# --------------------------------------------------------------------------- #
_base_mod = sys.modules[f"{__name__}.base"]
setattr(_base_mod, "get_calendar_provider", get_calendar_provider)

# а также напрямую из ``app.core.calendar`` — это ожидают юнит-тесты
globals()["get_calendar_provider"] = get_calendar_provider

__all__: list[str] = [
    "CalendarEvent",
    "BaseCalendarProvider",
    "get_calendar_provider",
]
