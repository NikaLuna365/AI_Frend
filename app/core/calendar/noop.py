"""
No-op / In-memory CalendarProvider.

Используется в dev-/test-режиме, когда нам не нужен реальный внешний
календарь (Google Calendar и т. д.).  Держит события в обычном списке
в пределах одного процесса, поэтому:

* Подходит для unit-тестов и локальной разработки;
* Не должен использоваться в production — данные не пPersistent.

API полностью повторяет BaseCalendarProvider, чтобы избежать «битых»
импортов и AttributeError'ов.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional

from .base import BaseCalendarProvider, CalendarEvent


class NoOpCalendarProvider(BaseCalendarProvider):
    """Заглушка-календарь; реализует методы базового интерфейса «в памяти»."""

    name: str = "noop"

    # --------------------------------------------------------------------- #
    #                               Конструктор                             #
    # --------------------------------------------------------------------- #
    def __init__(self) -> None:
        # Вся «БД» — это список событий в RAM процесса.
        self._events: list[CalendarEvent] = []

    # --------------------------------------------------------------------- #
    #                          CRUD-операции с событиями                    #
    # --------------------------------------------------------------------- #
    def list_events(
        self,
        user_id: str,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> List[CalendarEvent]:
        """
        Вернуть события пользователя в заданном интервале.
        Если start/end не заданы — вернуть всё.
        """
        events = [ev for ev in self._events if ev.user_id == user_id]
        if start:
            events = [ev for ev in events if ev.start >= start]
        if end:
            events = [ev for ev in events if (ev.end or ev.start) <= end]
        return events

    def add_event(
        self,
        user_id: str,
        title: str,
        start: datetime,
        end: Optional[datetime] = None,
        description: Optional[str] = None,
    ) -> CalendarEvent:
        """Создать событие и сохранить его во внутренний список."""
        new_event = CalendarEvent(
            id=str(uuid.uuid4()),
            user_id=user_id,
            title=title,
            start=start,
            end=end,
            description=description,
            provider=self.name,
        )
        self._events.append(new_event)
        return new_event

    def delete_event(self, event_id: str) -> None:
        """Удалить событие по ID (если нет — игнорируем silently)."""
        self._events = [ev for ev in self._events if ev.id != event_id]


# ------------------------------------------------------------------------- #
#                    Сделаем явный экспорт — удобнее для import *           #
# ------------------------------------------------------------------------- #
__all__: list[str] = ["NoOpCalendarProvider"]
