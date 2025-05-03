# /app/app/api/v1/chat.py (Версия с JWT Auth)

from __future__ import annotations

import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

# --- Наши Модули ---
from app.core.calendar.base import BaseCalendarProvider, CalendarEvent, get_calendar_provider
from app.core.llm.client import LLMClient
from app.core.llm.message import Message, Event
from app.core.achievements.service import AchievementsService
from app.core.users.service import UsersService
# --- ИМПОРТИРУЕМ МОДЕЛЬ User ---
from app.core.users.models import User # <--- Нужно для get_current_user
# --- ЗАВИСИМОСТИ ---
from app.db.base import get_async_db_session
# --- ИМПОРТИРУЕМ ЗАВИСИМОСТЬ АУТЕНТИФИКАЦИИ ---
from app.core.auth.security import get_current_user # <--- Добавили
# --- КОНЕЦ ИМПОРТОВ ---

router = APIRouter(
    prefix="/v1/chat",
    tags=["chat"],
    # Добавляем зависимость аутентификации на уровне всего роутера
    dependencies=[Depends(get_current_user)]
)
log = logging.getLogger(__name__)


# --- Модели Запроса/Ответа (остаются как были) ---

class ChatRequest(BaseModel):
    message_text: str = Field(..., min_length=1, description="Text of the user's message")
    # user_id УДАЛЕН

class EventOut(BaseModel):
    title: str
    start: str
    end: str | None = None

class ChatResponse(BaseModel):
    reply_text: str
    detected_events: List[EventOut] = Field(default_factory=list)
    unlocked_achievements: List[str] = Field(default_factory=list)


# --- Фабрика LLM Клиента (остается как была) ---
def get_llm_client() -> LLMClient:
    return LLMClient()

# --- Эндпоинт Чата (Обновлен) ---

@router.post(
    "/", # Путь остается, user_id больше не нужен
    response_model=ChatResponse,
    summary="Send message to AI (Authenticated)",
    description="Sends user message, requires JWT authentication."
)
async def chat_endpoint(
    # --- Зависимости ---
    db: AsyncSession = Depends(get_async_db_session),
    # --- ПОЛУЧАЕМ ПОЛЬЗОВАТЕЛЯ ИЗ ЗАВИСИМОСТИ ---
    current_user: User = Depends(get_current_user), # <--- Используем здесь
    llm: LLMClient = Depends(get_llm_client),
    calendar_provider: BaseCalendarProvider = Depends(get_calendar_provider),
    # --- Тело запроса ---
    payload: ChatRequest = Body(...)
) -> ChatResponse:
    """
    Основной эндпоинт чата (требует аутентификации).
    """
    # --- ПОЛУЧАЕМ user_id ИЗ current_user ---
    user_id = current_user.id # <--- Вот так
    # ---------------------------------------
    log.info("[API /chat] User '%s' sent message: '%.50s...'", user_id, payload.message_text)

    # Инициализация сервисов
    user_service = UsersService(db)
    # Передаем AsyncSession и LLMClient в AchievementsService
    ach_service = AchievementsService(db_session=db, llm_client=llm)

    try:
        # 1. Получить историю сообщений
        log.debug("[API /chat] Getting history for user '%s'", user_id)
        history: List[Message] = await user_service.get_recent_messages(user_id, limit=20)

        # 2. Вызвать LLM
        log.debug("[API /chat] Calling LLM generate for user '%s'", user_id)
        ai_reply_text = await llm.generate(payload.message_text, history)
        log.debug("[API /chat] LLM generate completed for user '%s'", user_id)

        # 3. Извлечь события (Отложено для MVP, но код оставим закомментированным)
        detected_raw_events: List[Event] = []
        # log.debug("[API /chat] Calling LLM extract_events for user '%s'", user_id)
        # detected_raw_events = await llm.extract_events(ai_reply_text) # <--- Закомментировано
        # log.debug("[API /chat] LLM extracted %d events for user '%s'", len(detected_raw_events), user_id)

        # 4. Добавить события в календарь (Отложено для MVP)
        processed_events_out: List[EventOut] = []
        # if detected_raw_events:
        #     log.info("[API /chat] Adding %d detected events to calendar for user '%s'", len(detected_raw_events), user_id)
        #     for ev in detected_raw_events:
        #         # ... (код добавления события закомментирован) ...
        #         pass # <--- Заглушка

        # 5. Сохранить сообщение пользователя и ответ AI в историю
        log.debug("[API /chat] Saving messages to history for user '%s'", user_id)
        await user_service.save_message(user_id, Message(role="user", content=payload.message_text))
        await user_service.save_message(user_id, Message(role="assistant", content=ai_reply_text))
        log.debug("[API /chat] Messages saved for user '%s'", user_id)

        # 6. Проверить и выдать достижения
        log.debug("[API /chat] Checking achievements for user '%s'", user_id)
        unlocked_codes: List[str] = await ach_service.check_and_award(
            user_id=user_id,
            events=detected_raw_events, # Передаем пустой список
            reply_text=ai_reply_text,
            trigger_key="chat_reply"
        )
        log.debug("[API /chat] Achievement check completed, unlocked: %s", unlocked_codes)

        # 7. Сформировать и вернуть ответ
        response = ChatResponse(
            reply_text=ai_reply_text,
            detected_events=processed_events_out, # Будет пустым
            unlocked_achievements=unlocked_codes,
        )
        log.info(
            "[API /chat] Response ready for user '%s'. Events: %d, New Achievements: %d",
            user_id, len(response.detected_events), len(response.unlocked_achievements)
        )
        return response

    except HTTPException: # Перебрасываем HTTPException дальше
        raise
    except Exception as e_main:
        log.exception("[API /chat] Unhandled error processing chat for user '%s': %s", user_id, e_main)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An internal error occurred: {type(e_main).__name__}"
        ) from e_main
