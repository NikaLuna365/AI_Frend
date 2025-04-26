from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional

from .base import BaseCalendarProvider, CalendarEvent


class NoOpCalendarProvider(BaseCalendarProvider):
    """Заглушка-календарь; хранит события в оперативной памяти."""

    name: str = "noop"

    def __init__(self) -> None:
        # Внутреннее «хранилище»
        self._events: list[CalendarEvent] = []

    def list_events(
        self,
        user_id: str,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> List[CalendarEvent]:
        events = [ev for ev in self._events if ev["user_id"] == user_id]
        if start:
            events = [ev for ev in events if ev["start"] >= start]
        if end:
            events = [ev for ev in events if (ev["end"] or ev["start"]) <= end]
        return events

    def add_event(
        self,
        user_id: str,
        title: str,
        start: datetime,
        end: Optional[datetime] = None,
        description: Optional[str] = None,
    ) -> CalendarEvent:
        new_event: CalendarEvent = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "title": title,
            "start": start,
            "end": end,
            "description": description,
            "provider": self.name,
        }
        self._events.append(new_event)
        return new_event

    def delete_event(self, event_id: str) -> None:
        self._events = [ev for ev in self._events if ev["id"] != event_id]


__all__ = ["NoOpCalendarProvider"]
