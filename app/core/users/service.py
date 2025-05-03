# /app/app/core/users/service.py (Обновленная версия)

from __future__ import annotations

import logging
from typing import List, Sequence, Optional # Добавили Optional

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
# Добавляем func для updated_at
from sqlalchemy.sql import func
# Добавляем исключение для обработки возможных конфликтов email/google_id
from sqlalchemy.exc import IntegrityError

from app.core.llm.message import Message
from app.core.users.models import User, Message as MessageModel

log = logging.getLogger(__name__)


class UsersService:
    """
    Асинхронный сервис для работы с данными пользователей и сообщениями.
    Включает логику для поиска/создания пользователя при Google Sign-In.
    """
    model = User

    def __init__(self, db_session: AsyncSession):
        """
        Инициализирует сервис с асинхронной сессией БД.

        Args:
            db_session (AsyncSession): Активная асинхронная сессия SQLAlchemy.
        """
        self.db: AsyncSession = db_session

    async def ensure_user_from_google(
        self,
        google_id: str,
        email: str | None,
        full_name: str | None
    ) -> User:
        """
        Находит пользователя по google_id или email, создает нового при необходимости,
        и обновляет email/имя при каждом входе.

        Предназначен для использования после успешной верификации Google ID токена.

        Args:
            google_id (str): Уникальный идентификатор пользователя Google ('sub').
            email (str | None): Email пользователя из Google токена (может быть None).
            full_name (str | None): Полное имя пользователя из Google токена (может быть None).

        Returns:
            User: Найденный или созданный/обновленный объект пользователя (ORM модель).

        Raises:
            HTTPException: Если возникает конфликт (например, google_id уже связан с другим email).
                           Хотя в данном флоу это менее вероятно.
            SQLAlchemyError: При других проблемах с БД.
        """
        log.debug("Ensuring user from Google: google_id=%s, email=%s", google_id, email)

        # 1. Поиск по google_id (самый надежный идентификатор)
        stmt_google = select(User).where(User.google_id == google_id)
        result_google = await self.db.execute(stmt_google)
        user: User | None = result_google.scalar_one_or_none()

        if user:
            log.info("Found existing user by google_id=%s (user_id=%s)", google_id, user.id)
            # Обновляем email и имя, если они изменились или отсутствовали
            update_needed = False
            if email and user.email != email:
                log.debug("Updating email for user %s", user.id)
                user.email = email
                update_needed = True
            if full_name and user.name != full_name:
                 log.debug("Updating name for user %s", user.id)
                 user.name = full_name
                 update_needed = True

            # Обновляем updated_at только если были реальные изменения
            # (поле updated_at в модели должно иметь onupdate=func.now())
            # if update_needed:
            #     user.updated_at = func.now() # Поле обновится само через onupdate

            # Добавляем в сессию для возможного обновления (если были изменения)
            if update_needed:
                self.db.add(user)
                await self.db.flush() # Применяем изменения в рамках транзакции
                await self.db.refresh(user)
            return user

        # 2. Если по google_id не нашли, ищем по email (если он есть)
        #    Это нужно на случай, если пользователь уже был у нас (с другим google_id? Маловероятно)
        #    Или если мы хотим связать новый google_id с существующим email.
        #    ОСТОРОЖНО: это может привести к конфликтам, если email не уникален или используется разными google_id.
        #    Для простоты MVP, можно пропустить этот шаг и всегда создавать нового, если google_id не найден.
        #    Но оставим пока для полноты картины.
        if email:
            log.debug("User not found by google_id, searching by email: %s", email)
            stmt_email = select(User).where(User.email == email)
            result_email = await self.db.execute(stmt_email)
            user = result_email.scalar_one_or_none()

            if user:
                # Найден пользователь с таким email, но другим/отсутствующим google_id
                log.warning(
                    "Found user user_id=%s by email=%s, but google_id did not match (or was null). "
                    "Linking google_id=%s to this existing user.",
                    user.id, email, google_id
                )
                # Обновляем google_id, имя, email
                user.google_id = google_id
                user.email = email # Обновляем на всякий случай
                if full_name:
                    user.name = full_name
                # user.updated_at = func.now() # Обновится через onupdate

                self.db.add(user)
                try:
                    await self.db.flush() # Применяем изменения
                    await self.db.refresh(user)
                    log.info("Linked google_id %s to existing user %s", google_id, user.id)
                    return user
                except IntegrityError as e:
                    # Возможен конфликт, если этот google_id УЖЕ занят другим пользователем
                    log.error(
                        "IntegrityError linking google_id %s to user %s (email %s): %s",
                        google_id, user.id, email, e
                    )
                    # Откатываем изменения для этого пользователя
                    await self.db.rollback() # <<< Важно откатить перед raise
                    # Можно выбросить специфическую ошибку, чтобы API вернул 409 Conflict
                    # raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Google ID conflict.")
                    # Пока просто перебрасываем общую ошибку
                    raise e


        # 3. Если пользователь не найден ни по google_id, ни по email - создаем нового
        log.info("User not found by google_id or email. Creating new user...")
        # Генерируем наш внутренний ID (можно использовать UUID)
        import uuid
        new_user_id = f"user_{uuid.uuid4().hex[:12]}" # Пример генерации ID

        new_user = User(
            id=new_user_id, # Наш внутренний ID
            google_id=google_id,
            email=email,
            name=full_name
            # created_at/updated_at установятся автоматически
        )
        self.db.add(new_user)
        await self.db.flush()
        await self.db.refresh(new_user)
        log.info("Created new user: %r", new_user)
        return new_user

    # --- Оставляем старые методы, но убедимся, что ensure_user больше не используется напрямую для логина ---
    # async def ensure_user(self, user_id: str) -> User:
    #    # Этот метод теперь лучше использовать только внутри системы, если ID уже известен
    #    # или переименовать в get_or_create_user_by_internal_id
    #    log.debug("DEPRECATED? Ensuring user by internal id=%s", user_id)
    #    user = await self.db.get(User, user_id)
    #    if not user:
    #        log.info("User with internal id=%s not found, creating placeholder.", user_id)
    #        user = User(id=user_id) # Создаем без google_id/email
    #        self.db.add(user)
    #        await self.db.flush()
    #        await self.db.refresh(user)
    #    return user

    async def save_message(self, user_id: str, message: Message) -> MessageModel:
        """
        Сохраняет новое сообщение в истории диалога пользователя.
        Предполагает, что пользователь с user_id уже существует (проверку не делает).

        Args:
            user_id (str): Внутренний идентификатор пользователя.
            message (Message): Сообщение (TypedDict) для сохранения.

        Returns:
            MessageModel: Сохраненный объект сообщения (ORM модель).
        """
        # Убрали ensure_user отсюда, т.к. пользователь должен быть создан при логине
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
