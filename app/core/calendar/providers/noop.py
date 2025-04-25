from __future__ import annotations

from datetime import datetime
from typing import DefaultDict, List
from collections import defaultdict

from ..base import BaseCalendarProvider, EventOut


class NoopCalendarProvider(BaseCalendarProvider):
    """Память - просто в оперативке (только для тестов)."""

    _storage: DefaultDict[str, List[EventOut]] = defaultdict(list)

    def add_event(self, user_id: str, title: str, start: datetime, end: datetime | None = None) -> None:
        self._storage[user_id].append(EventOut(title=title, start=start, end=end))

    def list_events(
        self, user_id: str, from_dt: datetime | None = None, to_dt: datetime | None = None
    ) -> List[EventOut]:
        events = self._storage.get(user_id, [])
        if from_dt or to_dt:
            return [
                ev
                for ev in events
                if (from_dt is None or ev.start >= from_dt) and (to_dt is None or ev.start <= to_dt)
            ]
        return events.copy()
