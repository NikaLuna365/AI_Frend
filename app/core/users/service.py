# /app/app/core/users/service.py (Версия для MVP - без Google специфики)

from __future__ import annotations

import logging
from typing import List, Sequence, Optional

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import func

from app.core.llm.message import Message
from app.core.users.models import User, Message as MessageModel # Модели User и Message

log = logging.getLogger(__name__)


class UsersService:
    """
    Асинхронный сервис для работы с пользователями и сообщениями (MVP).
    Работает с внутренними user_id.
    """
    model = User

    def __init__(self, db_session: AsyncSession):
        """
        Инициализирует сервис с асинхронной сессией БД.

        Args:
            db_session (AsyncSession): Активная сессия SQLAlchemy.
        """
        self.db: AsyncSession = db_session

    async def get_or_create_user(self, user_id: str, name: str | None = None) -> User:
        """
        Находит пользователя по внутреннему ID или создает нового.
        Может опционально установить имя.

        Args:
            user_id (str): Внутренний идентификатор пользователя.
            name (str | None, optional): Имя пользователя. Defaults to None.

        Returns:
            User: Найденный или созданный объект пользователя (ORM модель).
        """
        log.debug("Ensuring user by internal id=%s", user_id)
        user = await self.db.get(User, user_id)
        if not user:
            log.info("User with internal id=%s not found, creating.", user_id)
            user = User(id=user_id, name=name) # Создаем с ID и опциональным именем
            self.db.add(user)
            await self.db.flush()
            await self.db.refresh(user)
            log.info("Created new user: %r", user)
        # Если пользователь найден и передано имя, можно обновить имя
        elif name and user.name != name:
             log.debug("Updating name for existing user %s", user.id)
             user.name = name
             self.db.add(user)
             await self.db.flush()
             await self.db.refresh(user)
        else:
            log.debug("Found existing user: %r", user)
        return user

    async def ensure_user(self, user_id: str, name: str | None = None) -> User:
        """Thin wrapper around :meth:`get_or_create_user` for backwards compatibility."""
        return await self.get_or_create_user(user_id, name=name)

    async def save_message(self, user_id: str, message: Message) -> MessageModel:
        """
        Сохраняет новое сообщение в истории диалога пользователя.
        Убеждается, что пользователь существует.

        Args:
            user_id (str): Внутренний идентификатор пользователя.
            message (Message): Сообщение (TypedDict) для сохранения.

        Returns:
            MessageModel: Сохраненный объект сообщения (ORM модель).
        """
        # Убедимся, что пользователь существует перед сохранением
        await self.get_or_create_user(user_id) # Вызываем для проверки/создания

        log.debug("Saving message for user_id=%s, role=%s", user_id, message['role'])
        db_msg = MessageModel(
            user_id=user_id,
            role=message['role'],
            content=message['content']
        )
        self.db.add(db_msg)
        await self.db.flush()
        await self.db.refresh(db_msg)
        log.info("Saved message id=%d for user %s", db_msg.id, user_id)
        # TODO: Вызов AchievementsService
        return db_msg

    async def get_recent_messages(self, user_id: str, limit: int = 20) -> List[Message]:
        """
        Получает последние сообщения пользователя из истории.

        Args:
            user_id (str): Внутренний идентификатор пользователя.
            limit (int, optional): Максимальное количество сообщений. Defaults to 20.

        Returns:
            List[Message]: Список сообщений в хронологическом порядке.
        """
        # Код остается тем же, что и в предыдущей версии
        log.debug("Getting recent messages for user_id=%s, limit=%d", user_id, limit)
        stmt = (
            select(MessageModel)
            .where(MessageModel.user_id == user_id)
            .order_by(desc(MessageModel.created_at))
            .limit(limit)
        )
        result = await self.db.scalars(stmt)
        raw_messages = result.all()
        messages: List[Message] = [
            Message(role=m.role, content=m.content) for m in reversed(raw_messages)
        ]
        log.debug("Found %d recent messages for user %s", len(messages), user_id)
        return messages
