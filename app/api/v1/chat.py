# /app/app/api/v1/chat.py (Интеграция AchievementsService)

from __future__ import annotations

import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

# --- Наши Модули ---
# LLM (клиент и типы)
from app.core.llm.client import LLMClient
from app.core.llm.message import Message, Event
# Сервисы
from app.core.achievements.service import AchievementsService # <--- ИМПОРТИРУЕМ СЕРВИС АЧИВОК
from app.core.users.service import UsersService
# Модели
from app.core.users.models import User # Для get_current_user
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


# --- Модели Запроса/Ответа (остаются как были) ---
class ChatRequest(BaseModel):
    message_text: str = Field(..., min_length=1)

class EventOut(BaseModel):
    title: str
    start: str
    end: str | None = None

class ChatResponse(BaseModel):
    reply_text: str
    detected_events: List[EventOut] = Field(default_factory=list)
    unlocked_achievements: List[str] = Field(default_factory=list) # Список кодов новых ачивок


# --- Фабрика LLM Клиента (остается как была) ---
def get_llm_client() -> LLMClient:
    return LLMClient()

# --- Эндпоинт Чата (Обновлен) ---
@router.post(
    "/",
    response_model=ChatResponse,
    summary="Send message to AI (Authenticated)",
    description="Sends user message, gets AI reply, and checks for achievements."
)
async def chat_endpoint(
    # --- Зависимости ---
    db: AsyncSession = Depends(get_async_db_session),
    current_user: User = Depends(get_current_user),
    llm: LLMClient = Depends(get_llm_client),
    # Убираем calendar_provider для MVP
    # --- Тело запроса ---
    payload: ChatRequest = Body(...)
) -> ChatResponse:
    user_id = current_user.id
    log.info("[API /chat] User '%s' request: '%.50s...'", user_id, payload.message_text)

    # Инициализация сервисов
    user_service = UsersService(db)
    # --- ИНИЦИАЛИЗИРУЕМ AchievementsService ---
    ach_service = AchievementsService(db_session=db) # LLMClient ему не нужен напрямую
    # -----------------------------------------

    try:

        # 2. Вызвать LLM
        # Передаем полную историю для LLM
        full_history: List[Message] = await user_service.get_recent_messages(user_id, limit=20)
        log.debug("[API /chat] Calling llm.generate for user '%s' with %d history items", user_id, len(full_history))
        ai_reply_text = await llm.generate(payload.message_text, full_history)
        log.info("[API /chat] LLM reply for user '%s': '%.50s...'", user_id, ai_reply_text)

        # 3. Извлечь события из ответа LLM
        detected_raw_events: List[Event] = await llm.extract_events(ai_reply_text)
        processed_events_out: List[EventOut] = []
        for e in detected_raw_events:
            if e:
                processed_events_out.append(
                    EventOut(
                        title=e["title"],
                        start=e["start"].isoformat(),
                        end=e["end"].isoformat() if e.get("end") else None,
                    )
                )

        # 4. Добавить события в календарь (Пропускаем для MVP)

        # 5. Сохранить сообщение пользователя и ответ AI в историю
        log.debug("[API /chat] Saving messages to history for user '%s'", user_id)
        await user_service.save_message(user_id, Message(role="user", content=payload.message_text))
        await user_service.save_message(user_id, Message(role="assistant", content=ai_reply_text))
        log.debug("[API /chat] Messages saved for user '%s'", user_id)

        # 6. Получить актуальное число пользовательских сообщений и проверить ачивки
        user_message_count = await user_service.get_user_message_count(user_id)
        log.debug("[API /chat] Checking achievements for user '%s' with count %d", user_id, user_message_count)

        unlocked_codes: List[str] = await ach_service.check_and_award(
            user_id=user_id,
            message_text=payload.message_text,
            user_message_count=user_message_count,
        )
        log.debug("[API /chat] Achievement check completed, tasks dispatched for: %s", unlocked_codes)
        # -----------------------------------------------------------------------------------

        # 7. Сформировать и вернуть ответ
        response = ChatResponse(
            reply_text=ai_reply_text,
            detected_events=processed_events_out,
            unlocked_achievements=unlocked_codes, # Передаем коды ачивок, для которых запущены задачи
        )
        log.info(
            "[API /chat] Response ready for user '%s'. New Achievement Tasks: %s",
            user_id, response.unlocked_achievements
        )
        return response

    except HTTPException:
        raise
    except Exception as e_main:
        log.exception("[API /chat] Unhandled error processing chat for user '%s': %s", user_id, e_main)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An internal error occurred: {type(e_main).__name__}"
        ) from e_main
