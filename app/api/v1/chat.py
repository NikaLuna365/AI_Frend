# app/api/v1/chat.py

from __future__ import annotations

import logging
from typing import List # Оставляем List для типизации

from fastapi import APIRouter, Depends, HTTPException, status, Body # Добавляем Body
# --- SQLAlchemy Async ---
from sqlalchemy.ext.asyncio import AsyncSession
# --- Модели Pydantic ---
from pydantic import BaseModel, Field # Убираем validator, если не используется

# --- Наши Модули ---
# Календарь (интерфейс и фабрика)
from app.core.calendar.base import BaseCalendarProvider, CalendarEvent, get_calendar_provider
# LLM (клиент)
from app.core.llm.client import LLMClient
# LLM (типы) - импортируем явно, если нужны здесь
from app.core.llm.message import Message, Event
# Сервис Ачивок
from app.core.achievements.service import AchievementsService
# Сервис Пользователей
from app.core.users.service import UsersService
# Модель пользователя для зависимости
from app.core.users.models import User
# --- ЗАВИСИМОСТИ ---
# Асинхронная сессия БД
from app.db.base import get_async_db_session
# Текущий пользователь (из JWT)
from app.core.auth.security import get_current_user

# --- Инициализация ---
router = APIRouter(prefix="/v1/chat", tags=["chat"])
log = logging.getLogger(__name__)


# --- Модели Запроса/Ответа ---

class ChatRequest(BaseModel):
    """Запрос к чату. User ID берется из токена."""
    message_text: str = Field(..., min_length=1, description="Text of the user's message")
    # user_id: str - УДАЛЕНО, берем из JWT

class EventOut(BaseModel):
    """Представление события для ответа API."""
    title: str
    start: str # Возвращаем как строку ISO для JSON
    end: str | None = None # Возвращаем как строку ISO для JSON

    # Используем model_validator для преобразования datetime в строки ISO
    # (Это Pydantic v2 стиль, но проще вернуть строки сразу)
    # Мы преобразуем в EventOut после получения данных

class ChatResponse(BaseModel):
    """Ответ чата."""
    reply_text: str = Field(..., description="AI assistant's reply")
    detected_events: List[EventOut] = Field(default_factory=list, description="Calendar events detected in the reply")
    unlocked_achievements: List[str] = Field(default_factory=list, description="List of achievement codes unlocked") # Переименовано


# --- Фабрика для LLM Клиента (Dependency) ---
# Выносим создание клиента в зависимость для гибкости и тестирования
def get_llm_client() -> LLMClient:
    # Пока просто создаем новый экземпляр
    # В будущем можно реализовать как синглтон или более сложную логику
    return LLMClient()

# --- Эндпоинт Чата ---

@router.post(
    "/", # Убрали user_id из пути
    response_model=ChatResponse,
    summary="Send message to AI and get reply",
    description="Sends user message, gets AI reply, detects events, checks achievements."
)
async def chat_endpoint(
    # --- Зависимости ---
    db: AsyncSession = Depends(get_async_db_session),
    current_user: User = Depends(get_current_user), # Получаем пользователя из JWT
    llm: LLMClient = Depends(get_llm_client), # Получаем LLM клиент
    calendar_provider: BaseCalendarProvider = Depends(get_calendar_provider), # Получаем провайдер календаря
    # --- Тело запроса ---
    payload: ChatRequest = Body(...) # Указываем, что payload из тела
) -> ChatResponse:
    """
    Основной эндпоинт чата:
    1. Получает сообщение пользователя.
    2. Получает историю сообщений.
    3. Вызывает LLM для генерации ответа и извлечения событий.
    4. Добавляет события в календарь.
    5. Сохраняет сообщение пользователя и ответ AI в историю.
    6. Проверяет и выдает достижения.
    7. Возвращает ответ AI, события и новые ачивки.
    """
    user_id = current_user.id # Берем ID из аутентифицированного пользователя
    log.info("[API /chat] User '%s' sent message: '%.50s...'", user_id, payload.message_text)

    # Инициализируем сервисы с текущей сессией
    user_service = UsersService(db)
    ach_service = AchievementsService(db_session=db, llm_client=llm) # Передаем и сессию, и LLM

    try:
        # 1. Получить историю сообщений
        # TODO: Определить, нужна ли история для `llm.generate` или оно само её получит
        #       Сейчас `llm.generate` принимает `context`, передадим ему историю.
        #       Провайдер Gemini может использовать свой history management.
        history: List[Message] = await user_service.get_recent_messages(user_id, limit=20) # Пример лимита

        # 2. Вызвать LLM (с историей)
        # TODO: Пересмотреть API LLMClient, возможно, ему не нужен prompt+context,
        #       а только новое сообщение, а историю он получит сам или через Gemini API.
        #       Пока используем как есть.
        log.debug("[API /chat] Calling LLM generate for user '%s'", user_id)
        ai_reply_text = await llm.generate(payload.message_text, history)
        log.debug("[API /chat] LLM generate completed for user '%s'", user_id)

        # 3. Извлечь события из ответа AI
        log.debug("[API /chat] Calling LLM extract_events for user '%s'", user_id)
        detected_raw_events: List[Event] = await llm.extract_events(ai_reply_text)
        log.debug("[API /chat] LLM extracted %d events for user '%s'", len(detected_raw_events), user_id)

        # 4. Добавить события в календарь
        processed_events_out: List[EventOut] = []
        if detected_raw_events:
            log.info("[API /chat] Adding %d detected events to calendar for user '%s'", len(detected_raw_events), user_id)
            for ev in detected_raw_events:
                # Простая проверка типа (можно добавить Pydantic валидацию)
                if not isinstance(ev, dict) or "title" not in ev or "start" not in ev:
                    log.error("[API /chat] Invalid event format from LLM: %s", ev)
                    continue # Пропускаем невалидное событие
                try:
                    # Используем асинхронный метод провайдера
                    added_event: CalendarEvent = await calendar_provider.add_event(
                        user_id=user_id,
                        title=ev["title"],
                        start=ev["start"],
                        end=ev.get("end"),
                        description=f"Detected by AI-Friend from chat: {ai_reply_text}" # Пример описания
                    )
                    # Преобразуем в EventOut для ответа API
                    processed_events_out.append(
                        EventOut(
                            title=added_event["title"],
                            start=added_event["start"].isoformat(),
                            end=added_event["end"].isoformat() if added_event["end"] else None
                        )
                    )
                    log.debug("[API /chat] Added event '%s' for user '%s'", added_event["title"], user_id)
                except Exception as e_cal:
                    log.exception(
                        "[API /chat] Failed to add event '%s' to calendar for user '%s': %s",
                        ev.get('title', 'N/A'), user_id, e_cal
                    )
                    # Не прерываем весь запрос из-за ошибки календаря

        # 5. Сохранить сообщение пользователя и ответ AI в историю
        log.debug("[API /chat] Saving messages to history for user '%s'", user_id)
        try:
            # Сохраняем сообщение пользователя
            await user_service.save_message(user_id, Message(role="user", content=payload.message_text))
            # Сохраняем ответ AI
            await user_service.save_message(user_id, Message(role="assistant", content=ai_reply_text))
            log.debug("[API /chat] Messages saved for user '%s'", user_id)
        except Exception as e_db_hist:
            log.exception("[API /chat] Failed to save message history for user '%s': %s", user_id, e_db_hist)
            # Можно решить, критична ли эта ошибка (вероятно, да)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to save message history."
            ) from e_db_hist

        # 6. Проверить и выдать достижения
        log.debug("[API /chat] Checking achievements for user '%s'", user_id)
        unlocked_codes: List[str] = []
        try:
            # Передаем контекст события (события из LLM, ответ)
            unlocked_codes = await ach_service.check_and_award(
                user_id=user_id,
                events=detected_raw_events,
                reply_text=ai_reply_text,
                trigger_key="chat_reply" # Пример ключа триггера
            )
            log.debug("[API /chat] Achievement check completed for user '%s', unlocked: %s", user_id, unlocked_codes)
        except Exception as e_ach:
            log.exception("[API /chat] Failed during achievement check for user '%s': %s", user_id, e_ach)
            # Не критично, продолжаем выполнение

        # 7. Сформировать и вернуть ответ
        response = ChatResponse(
            reply_text=ai_reply_text,
            detected_events=processed_events_out,
            unlocked_achievements=unlocked_codes,
        )
        log.info(
            "[API /chat] Response ready for user '%s'. Events: %d, New Achievements: %d",
            user_id, len(response.detected_events), len(response.unlocked_achievements)
        )
        # Коммит транзакции произойдет автоматически при выходе из get_async_db_session
        return response

    except Exception as e_main:
        # Ловим любые другие непредвиденные ошибки
        log.exception("[API /chat] Unhandled error processing chat for user '%s': %s", user_id, e_main)
        # Откат транзакции произойдет автоматически в get_async_db_session
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An internal error occurred: {type(e_main).__name__}"
        )
