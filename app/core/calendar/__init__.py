"""
Публичный пакет calendar.

`get_calendar_provider()` – ленивый импорт конкретного провайдера
в зависимости от конфига.
"""

from __future__ import annotations

from importlib import import_module
from typing import Protocol, Type

from app.config import settings


class BaseCalendarProvider(Protocol):  # минимальный контракт
    name: str

    def list_events(self, user_id: str, from_dt, to_dt): ...
    def add_event(self, user_id: str, title: str, start, end=None): ...


def _lazy(module_path: str, cls_name: str) -> Type[BaseCalendarProvider]:
    mod = import_module(module_path, package=__name__)
    return getattr(mod, cls_name)


# регистр доступных реализаций
_provider_map: dict[str, Type[BaseCalendarProvider]] = {
    "noop":  _lazy(".noop",   "NoOpCalendarProvider"),
    "google": _lazy(".google", "GoogleCalendarProvider"),
}


def get_calendar_provider(name: str | None = None) -> BaseCalendarProvider:
    """
    Фабрика-single-ton. Возвращает *экземпляр* провайдера.
    """
    provider_name = (name or settings.CALENDAR_PROVIDER or "noop").lower()
    if provider_name not in _provider_map:
        raise ValueError(f"Unknown calendar provider: {provider_name}")

    cls = _provider_map[provider_name]
    # singleton per process: кешируем как атрибут модуля
    attr = f"_cached_{provider_name}"
    if not globals().get(attr):
        globals()[attr] = cls()
    return globals()[attr]
