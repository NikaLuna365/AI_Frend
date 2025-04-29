# app/core/users/service.py

from __future__ import annotations

import logging
from typing import List, Sequence

# Используем select для построения запросов в SQLAlchemy 2.0
from sqlalchemy import select, desc
# Асинхронная сессия
from sqlalchemy.ext.asyncio import AsyncSession

# Импортируем наши модели и схемы
from app.core.llm.message import Message # Используем TypedDict для возвращаемого типа
from app.core.users.models import User, Message as MessageModel # ORM Модели

log = logging.getLogger(__name__)


class UsersService:
    """
    Асинхронный сервис для работы с данными пользователей и сообщениями.
    Использует внедрение зависимостей (DI) для получения AsyncSession.
    """
    model = User # Оставляем для возможной совместимости или будущих generic view

    def __init__(self, db_session: AsyncSession):
        """
        Инициализирует сервис с асинхронной сессией БД.

        Args:
            db_session (AsyncSession): Активная асинхронная сессия SQLAlchemy.
        """
        self.db: AsyncSession = db_session

    async def ensure_user(self, user_id: str) -> User:
        """
        Находит пользователя по ID или создает нового, если он не существует.

        Args:
            user_id (str): Идентификатор пользователя.

        Returns:
            User: Найденный или созданный объект пользователя (ORM модель).
        """
        log.debug("Ensuring user with id=%s", user_id)
        # Используем session.get для поиска по первичному ключу
        user = await self.db.get(User, user_id)
        if not user:
            log.info("User with id=%s not found, creating new one.", user_id)
            user = User(id=user_id)
            self.db.add(user)
            # Не делаем commit здесь, позволяем вызывающей функции управлять транзакцией
            # await self.db.commit() # Убрано
            await self.db.flush() # Чтобы получить ID или другие default значения если нужно
            await self.db.refresh(user) # Обновляем объект из БД
            log.info("Created new user: %r", user)
        else:
            log.debug("Found existing user: %r", user)
        return user

    async def save_message(self, user_id: str, message: Message) -> MessageModel:
        """
        Сохраняет новое сообщение в истории диалога пользователя.
        Предварительно убеждается, что пользователь существует.

        Args:
            user_id (str): Идентификатор пользователя.
            message (Message): Сообщение (TypedDict) для сохранения.

        Returns:
            MessageModel: Сохраненный объект сообщения (ORM модель).

        Raises:
            SQLAlchemyError: В случае проблем с БД.
        """
        # Гарантируем существование пользователя перед сохранением сообщения
        # Этот вызов сам по себе добавит пользователя в сессию, если он новый
        await self.ensure_user(user_id)

        log.debug("Saving message for user_id=%s, role=%s", user_id, message['role'])
        db_msg = MessageModel(
            user_id=user_id,
            role=message['role'],
            content=message['content']
        )
        self.db.add(db_msg)
        # Не делаем commit здесь, позволяем вызывающей функции управлять транзакцией
        # await self.db.commit() # Убрано
        await self.db.flush() # Отправляем изменения в БД в рамках транзакции
        await self.db.refresh(db_msg) # Получаем ID и default значения
        log.info("Saved message id=%d for user %s", db_msg.id, user_id)

        # --- Точка для интеграции Achievements ---
        # TODO: Вызвать AchievementsService.check_and_award() здесь
        # achievement_service = AchievementsService(self.db)
        # await achievement_service.check_and_award(user_id, "message_saved", message_data=db_msg)
        # -----------------------------------------

        return db_msg

    async def get_recent_messages(self, user_id: str, limit: int = 20) -> List[Message]:
        """
        Получает последние сообщения пользователя из истории.

        Args:
            user_id (str): Идентификатор пользователя.
            limit (int, optional): Максимальное количество сообщений. Defaults to 20.

        Returns:
            List[Message]: Список сообщений в хронологическом порядке (старые -> новые),
                           каждое как TypedDict.
        """
        log.debug("Getting recent messages for user_id=%s, limit=%d", user_id, limit)
        stmt = (
            select(MessageModel)
            .where(MessageModel.user_id == user_id)
            .order_by(desc(MessageModel.created_at))
            .limit(limit)
        )
        # scalars().all() возвращает список объектов модели
        result = await self.db.scalars(stmt)
        raw_messages = result.all()

        # Преобразуем ORM модели в TypedDict и реверсируем для правильного порядка
        messages: List[Message] = [
            Message(role=m.role, content=m.content) for m in reversed(raw_messages)
        ]
        log.debug("Found %d recent messages for user %s", len(messages), user_id)
        return messages
