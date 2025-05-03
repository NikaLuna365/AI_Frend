# /app/app/api/v1/chat.py (Версия для Фазы 2)

from __future__ import annotations

import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

# --- Наши Модули ---
# Убираем импорты Calendar, т.к. он отложен
# from app.core.calendar.base import BaseCalendarProvider, CalendarEvent, get_calendar_provider
# LLM (клиент и типы)
from app.core.llm.client import LLMClient
from app.core.llm.message import Message, Event # Event импортируем, но не используем активно
# Сервисы
from app.core.achievements.service import AchievementsService
from app.core.users.service import UsersService
# Модели
from app.core.users.models import User
# --- ЗАВИСИМОСТИ ---
from app.db.base import get_async_db_session
from app.core.auth.security import get_current_user

# --- Инициализация ---
router = APIRouter(
    prefix="/v1/chat",
    tags=["chat"],
    dependencies=[Depends(get_current_user)] # Защищаем весь роутер
)
log = logging.getLogger(__name__)


# --- Модели Запроса/Ответа ---
class ChatRequest(BaseModel):
    message_text: str = Field(..., min_length=1)

class EventOut(BaseModel): # Оставляем модель, но список будет пуст
    title: str
    start: str
    end: str | None = None

class ChatResponse(BaseModel):
    reply_text: str
    detected_events: List[EventOut] = Field(default_factory=list) # Будет пустым
    unlocked_achievements: List[str] = Field(default_factory=list)


# --- Фабрика LLM Клиента (Dependency) ---
def get_llm_client() -> LLMClient:
    # Фабрика возвращает синглтон LLMClient, который внутри себя
    # содержит синглтон провайдера (Gemini или Stub)
    return LLMClient()

# --- Эндпоинт Чата ---
@router.post(
    "/",
    response_model=ChatResponse,
    summary="Send message to AI (Authenticated)",
    description="Sends user message to the configured LLM (Gemini or Stub), requires JWT auth."
)
async def chat_endpoint(
    # --- Зависимости ---
    db: AsyncSession = Depends(get_async_db_session),
    current_user: User = Depends(get_current_user),
    llm: LLMClient = Depends(get_llm_client), # Используем LLMClient
    # calendar_provider: BaseCalendarProvider = Depends(get_calendar_provider), # Убрали Calendar
    # --- Тело запроса ---
    payload: ChatRequest = Body(...)
) -> ChatResponse:
    user_id = current_user.id
    log.info("[API /chat] User '%s' request: '%.50s...'", user_id, payload.message_text)

    # Инициализация сервисов
    user_service = UsersService(db)
    # AchievementsService теперь тоже зависит от LLMClient для генерации названий
    ach_service = AchievementsService(db_session=db, llm_client=llm)

    try:
        # 1. Получить историю сообщений
        log.debug("[API /chat] Getting history for user '%s'", user_id)
        history: List[Message] = await user_service.get_recent_messages(user_id, limit=20) # TODO: Настроить лимит истории

        # 2. Вызвать LLM (Gemini или Stub через LLMClient)
        log.debug("[API /chat] Calling llm.generate for user '%s'", user_id)
        # --- УБЕДИМСЯ, ЧТО ВЫЗОВ АСИНХРОННЫЙ ---
        ai_reply_text = await llm.generate(payload.message_text, history)
        # -----------------------------------------
        log.info("[API /chat] LLM reply for user '%s': '%.50s...'", user_id, ai_reply_text)

        # 3. Извлечь события (Пропускаем для MVP)
        detected_raw_events: List[Event] = [] # Всегда пустой список
        processed_events_out: List[EventOut] = []

        # 4. Добавить события в календарь (Пропускаем для MVP)

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
            detected_events=processed_events_out, # Пустой список
            unlocked_achievements=unlocked_codes,
        )
        log.info("[API /chat] Response ready for user '%s'.", user_id)
        return response

    except HTTPException:
        raise # Перебрасываем HTTP исключения
    except Exception as e_main:
        log.exception("[API /chat] Unhandled error processing chat for user '%s': %s", user_id, e_main)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An internal error occurred: {type(e_main).__name__}"
        ) from e_main
