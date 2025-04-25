from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Iterable, List

from pydantic import BaseModel


class EventOut(BaseModel):
    title: str
    start: datetime
    end: datetime | None = None


class BaseCalendarProvider(ABC):
    @abstractmethod
    def add_event(self, user_id: str, title: str, start: datetime, end: datetime | None = None) -> None: ...

    @abstractmethod
    def list_events(
        self, user_id: str, from_dt: datetime | None = None, to_dt: datetime | None = None
    ) -> List[EventOut]: ...

    # ── helper: возвращает все события пользователя ───────
    def all_events(self, user_id: str) -> Iterable[EventOut]:
        return self.list_events(user_id, None, None)
