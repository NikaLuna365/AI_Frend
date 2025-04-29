# app/core/reminders/service.py

"""Service-layer for Reminders."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import List, Sequence # Добавляем Sequence для лучшей типизации

from sqlalchemy import select # Используем select для запросов
from sqlalchemy.ext.asyncio import AsyncSession

# Импортируем исправленную модель Reminder
from .models import Reminder

log = logging.getLogger(__name__)

class RemindersService:
    """
    Асинхронный сервис для работы с Напоминаниями.
    Использует внедрение зависимостей (DI) для получения AsyncSession.
    """

    def __init__(self, db_session: AsyncSession) -> None:
        """
        Инициализирует сервис с асинхронной сессией БД.

        Args:
            db_session (AsyncSession): Активная асинхронная сессия SQLAlchemy.
        """
        self.db: AsyncSession = db_session

    # ------------------------------------------------------------------ #
    #                       Public business-methods                      #
    # ------------------------------------------------------------------ #

    async def create_reminder(
        self,
        user_id: str,
        title: str,
        due_at: datetime,
        source_event_id: str | None = None
    ) -> Reminder:
        """
        Создает новое напоминание для пользователя.

        Args:
            user_id (str): Идентификатор пользователя.
            title (str): Текст напоминания.
            due_at (datetime): Время срабатывания (UTC).
            source_event_id (str | None, optional): ID исходного события календаря.

        Returns:
            Reminder: Созданный объект напоминания (ORM модель).
        """
        log.info(
            "Creating reminder for user %s: title='%s', due_at=%s",
            user_id, title, due_at.isoformat()
        )
        new_reminder = Reminder(
            user_id=user_id,
            title=title,
            due_at=due_at,
            source_event_id=source_event_id,
            sent=False # Убедимся, что по умолчанию false
        )
        self.db.add(new_reminder)
        await self.db.flush()
        await self.db.refresh(new_reminder)
        log.info("Created reminder id=%d", new_reminder.id)

        # --- Точка для интеграции Achievements ---
        # TODO: Вызвать AchievementsService.check_and_award() здесь
        # achievement_service = AchievementsService(self.db)
        # await achievement_service.check_and_award(user_id, "reminder_created", ...)
        # -----------------------------------------

        return new_reminder

    async def list_due_and_unsent(self) -> Sequence[Reminder]:
        """
        Возвращает список напоминаний, время которых наступило (<= UTC now)
        и которые еще не были отправлены.

        Returns:
            Sequence[Reminder]: Последовательность объектов Reminder.
        """
        now_utc = datetime.utcnow()
        log.debug("Listing due and unsent reminders (due <= %s)", now_utc.isoformat())
        stmt = (
            select(Reminder)
            .where(Reminder.due_at <= now_utc)
            .where(Reminder.sent == False) # Используем '==' для сравнения в SQLAlchemy
            .order_by(Reminder.due_at) # Опционально, для порядка обработки
        )
        result = await self.db.scalars(stmt)
        reminders = result.all()
        log.info("Found %d due and unsent reminders", len(reminders))
        return reminders

    async def mark_sent(self, reminder_id: int) -> Reminder | None:
        """
        Помечает напоминание как отправленное.

        Args:
            reminder_id (int): ID напоминания.

        Returns:
            Reminder | None: Обновленный объект Reminder или None, если не найден.
        """
        log.debug("Marking reminder id=%d as sent", reminder_id)
        reminder = await self.db.get(Reminder, reminder_id)
        if reminder:
            if not reminder.sent:
                reminder.sent = True
                self.db.add(reminder) # Добавляем измененный объект в сессию
                await self.db.flush()
                await self.db.refresh(reminder)
                log.info("Marked reminder id=%d as sent", reminder_id)
            else:
                log.warning("Reminder id=%d was already marked as sent.", reminder_id)
            return reminder
        else:
            log.warning("Reminder id=%d not found to mark as sent.", reminder_id)
            return None

    async def get_reminder_by_id(self, reminder_id: int) -> Reminder | None:
        """
        Получает напоминание по его ID.

        Args:
            reminder_id (int): ID напоминания.

        Returns:
            Reminder | None: Найденный объект Reminder или None.
        """
        log.debug("Getting reminder by id=%d", reminder_id)
        return await self.db.get(Reminder, reminder_id)

    async def delete_reminder(self, reminder_id: int) -> bool:
        """
        Удаляет напоминание по ID.

        Args:
            reminder_id (int): ID напоминания.

        Returns:
            bool: True, если напоминание было найдено и удалено, иначе False.
        """
        log.debug("Deleting reminder id=%d", reminder_id)
        reminder = await self.db.get(Reminder, reminder_id)
        if reminder:
            await self.db.delete(reminder)
            await self.db.flush()
            log.info("Deleted reminder id=%d", reminder_id)
            return True
        else:
            log.warning("Reminder id=%d not found for deletion.", reminder_id)
            return False

    # ... можно добавить другие методы по необходимости (list_all_for_user, update, etc.)
