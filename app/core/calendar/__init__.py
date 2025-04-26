# app/core/calendar/__init__.py
"""
Calendar subsystem package.

• `CalendarEvent`  – общая Pydantic-модель события (см. base.py).
• `BaseCalendarProvider` – абстрактный интерфейс провайдера.
• `get_calendar_provider()` – фабрика, возвращающая инстанс
  нужного провайдера по имени или из `settings.CALENDAR_PROVIDER`.

Ленивая загрузка (`importlib.import_module`) исключает тяжёлые
зависимости (Google SDK и т. п.) в dev/CI, пока они реально не нужны.
"""

from __future__ import annotations

import importlib
import sys
from typing import Dict, Type

from app.config import settings
from .base import BaseCalendarProvider, CalendarEvent  # noqa: F401  (важно для __all__)

# --------------------------------------------------------------------------- #
#                       helpers: lazy-import specific provider                #
# --------------------------------------------------------------------------- #


def _lazy_import(module_suffix: str, class_name: str) -> Type[BaseCalendarProvider]:
    """
    >>> _lazy_import(".noop", "NoOpCalendarProvider")  ->  <class NoOpCalendarProvider>
    Относительный путь (`.noop`) ищется внутри текущего пакета.
    """
    module = importlib.import_module(f"{__name__}{module_suffix}", package=__name__)
    return getattr(module, class_name)


# --------------------------------------------------------------------------- #
#                         registry: name → provider-class                     #
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
    Возвращает экземпляр провайдера.

    • `name` – явное имя (case-insensitive).  
    • Если не передано – берём из `settings.CALENDAR_PROVIDER`.
      По-умолчанию в .env.test/.env.dev это «noop».
    """
    provider_key = (name or settings.CALENDAR_PROVIDER).lower()

    try:
        provider_cls = _PROVIDER_CLASSES[provider_key]
    except KeyError as exc:  # pragma: no cover
        raise ValueError(f"Unknown calendar provider: {provider_key}") from exc

    return provider_cls()


# --------------------------------------------------------------------------- #
#            make get_calendar_provider visible from app.core.calendar.base   #
# --------------------------------------------------------------------------- #
#  Тесты делают:  from app.core.calendar.base import get_calendar_provider
#  Чтобы не плодить циклы, прямо дописываем атрибут в already-imported module.

_base_mod = sys.modules[f"{__name__}.base"]
setattr(_base_mod, "get_calendar_provider", get_calendar_provider)


__all__: list[str] = [
    "CalendarEvent",
    "BaseCalendarProvider",
    "get_calendar_provider",
]
