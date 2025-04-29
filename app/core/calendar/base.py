# app/core/calendar/base.py
"""
Abstract base and common types for calendar providers.
Now uses asynchronous methods.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
# Используем typing.List вместо list для совместимости < 3.9 если нужно,
# но если проект строго >= 3.9, можно использовать list | None
from typing import TypedDict, List, Optional # Оставляем typing.List

# Импортируем фабрику сюда для удобства использования
# (фабрика сама себя сюда пропишет при импорте __init__.py)
get_calendar_provider: function = lambda name=None: ... # Placeholder

class CalendarEvent(TypedDict):
    """
    Общая структура для представления события календаря.
    Используется как для получения, так и для создания событий.
    """
    id: str # Идентификатор события У ПРОВАЙДЕРА
    user_id: str # Наш внутренний ID пользователя
    title: str
    start: datetime
    end: Optional[datetime]
    description: Optional[str]
    provider: str # Имя провайдера ('noop', 'google', etc.)

class BaseCalendarProvider(ABC):
    """
    Абстрактный интерфейс провайдера календаря (АСИНХРОННЫЙ).
    """

    # Имя провайдера (например, 'noop', 'google')
    name: str

    @abstractmethod
    async def list_events(
        self,
        user_id: str,
        start_dt: Optional[datetime] = None,
        end_dt: Optional[datetime] = None,
    ) -> List[CalendarEvent]:
        """
        Асинхронно возвращает список событий пользователя в заданном интервале.

        Args:
            user_id (str): Наш внутренний ID пользователя.
            start_dt (Optional[datetime], optional): Начало интервала (UTC). Defaults to None.
            end_dt (Optional[datetime], optional): Конец интервала (UTC). Defaults to None.

        Returns:
            List[CalendarEvent]: Список событий.
        """
        ...

    @abstractmethod
    async def add_event(
        self,
        user_id: str,
        title: str,
        start: datetime,
        end: Optional[datetime] = None,
        description: Optional[str] = None,
    ) -> CalendarEvent:
        """
        Асинхронно создает событие в календаре провайдера и возвращает его.

        Args:
            user_id (str): Наш внутренний ID пользователя.
            title (str): Название события.
            start (datetime): Время начала (UTC).
            end (Optional[datetime], optional): Время окончания (UTC). Defaults to None.
            description (Optional[str], optional): Описание события. Defaults to None.

        Returns:
            CalendarEvent: Созданное событие с ID от провайдера.

        Raises:
            Exception: Может выбрасывать исключения при ошибках API провайдера.
        """
        ...

    @abstractmethod
    async def delete_event(self, user_id: str, event_id: str) -> None:
        """
        Асинхронно удаляет событие по его ID у провайдера.

        Args:
            user_id (str): Наш внутренний ID пользователя (может быть нужен для проверки прав).
            event_id (str): ID события У ПРОВАЙДЕРА.

        Raises:
            Exception: Может выбрасывать исключения при ошибках API провайдера
                       (например, событие не найдено или нет прав).
        """
        ...

# Экспортируем типы и интерфейс
__all__ = [
    "CalendarEvent",
    "BaseCalendarProvider",
    "get_calendar_provider",
]
