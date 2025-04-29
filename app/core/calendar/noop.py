# app/core/calendar/noop.py

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import List, Optional # Используем typing.List

from .base import BaseCalendarProvider, CalendarEvent

log = logging.getLogger(__name__)


class NoOpCalendarProvider(BaseCalendarProvider):
    """
    Асинхронная заглушка-календарь; хранит события в оперативной памяти.
    Имитирует асинхронное поведение.
    """

    name: str = "noop"

    def __init__(self) -> None:
        # Внутреннее «хранилище» событий
        self._events: list[CalendarEvent] = []
        log.info("Initialized NoOpCalendarProvider (in-memory)")

    async def list_events(
        self,
        user_id: str,
        start_dt: Optional[datetime] = None,
        end_dt: Optional[datetime] = None,
    ) -> List[CalendarEvent]:
        """
        Возвращает события пользователя из памяти, имитируя async.

        Args:
            user_id (str): ID пользователя.
            start_dt (Optional[datetime], optional): Начало интервала.
            end_dt (Optional[datetime], optional): Конец интервала.

        Returns:
            List[CalendarEvent]: Список событий.
        """
        log.debug(
            "NoOp: Listing events for user %s between %s and %s",
            user_id, start_dt, end_dt
        )
        # Фильтрация выполняется синхронно, но сам метод async
        events_for_user = [ev for ev in self._events if ev["user_id"] == user_id]
        filtered_events = events_for_user

        if start_dt:
            filtered_events = [ev for ev in filtered_events if ev["start"] >= start_dt]
        if end_dt:
            # Событие попадает в интервал, если его начало или конец внутри
            # (или если оно без конца и начало внутри)
            filtered_events = [
                ev for ev in filtered_events
                if (ev["end"] or ev["start"]) >= start_dt and ev["start"] <= end_dt
            ] # Уточнена логика фильтрации по датам

        log.debug("NoOp: Found %d events for user %s", len(filtered_events), user_id)
        return filtered_events

    async def add_event(
        self,
        user_id: str,
        title: str,
        start: datetime,
        end: Optional[datetime] = None,
        description: Optional[str] = None,
    ) -> CalendarEvent:
        """
        Добавляет событие в память, имитируя async.

        Args:
            user_id (str): ID пользователя.
            title (str): Название.
            start (datetime): Начало.
            end (Optional[datetime], optional): Конец.
            description (Optional[str], optional): Описание.

        Returns:
            CalendarEvent: Созданное событие.
        """
        log.info("NoOp: Adding event for user %s: '%s'", user_id, title)
        new_event_id = str(uuid.uuid4())
        new_event: CalendarEvent = {
            "id": new_event_id,
            "user_id": user_id,
            "title": title,
            "start": start,
            "end": end,
            "description": description,
            "provider": self.name,
        }
        self._events.append(new_event)
        log.info("NoOp: Event added with id %s", new_event_id)
        return new_event

    async def delete_event(self, user_id: str, event_id: str) -> None:
        """
        Удаляет событие из памяти, имитируя async.

        Args:
            user_id (str): ID пользователя (в noop не используется для проверки).
            event_id (str): ID события для удаления.
        """
        log.info("NoOp: Deleting event id %s for user %s", event_id, user_id)
        initial_len = len(self._events)
        self._events = [ev for ev in self._events if ev["id"] != event_id]
        if len(self._events) < initial_len:
            log.info("NoOp: Event id %s deleted", event_id)
        else:
            log.warning("NoOp: Event id %s not found for deletion", event_id)


__all__ = ["NoOpCalendarProvider"]
