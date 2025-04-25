# app/core/calendar/noop.py
from typing import Any


class NoOpCalendarProvider:
    """Ничего не делает — используется в тестах."""

    def add_event(self, *args, **kwargs) -> None: ...

    def list_events(self, *args, **kwargs) -> list[Any]:
        return []
