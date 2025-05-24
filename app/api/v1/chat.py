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
        # 1. Получить историю сообщений (и количество для триггера "первое сообщение")
        log.debug("[API /chat] Getting history for user '%s'", user_id)
        # Если get_recent_messages не возвращает общее количество, нужно будет добавить отдельный запрос
        # или модифицировать UsersService. Пока предположим, что мы можем его получить.
        # Для простоты MVP, давайте передадим user_message_count=1 для первого сообщения
        # и >1 для последующих. Это можно определить по истории.
        history: List[Message] = await user_service.get_recent_messages(user_id, limit=1) # Получаем только последнее (или 0)
        user_message_count = 1 # Предполагаем, что это новое сообщение
        if history: # Если история не пуста, значит, это не первое сообщение
             # Для более точного подсчета, UsersService должен бы возвращать count
             # или здесь нужно загрузить всю историю и посчитать.
             # Для MVP триггера "первое сообщение", можно просто проверить, есть ли уже сообщения.
             # Если мы сохраним это сообщение ДО вызова ачивок, то user_message_count будет >= 1
             # Если ПОСЛЕ, то для первого сообщения count будет 0.
             # Давайте сначала сохраним, потом вызовем ачивки.
             # Тогда user_message_count нужно будет получить запросом ПОСЛЕ сохранения.
             pass # Логику подсчета user_message_count уточним ниже

        # 2. Вызвать LLM
        # Передаем полную историю для LLM
        full_history: List[Message] = await user_service.get_recent_messages(user_id, limit=20)
        log.debug("[API /chat] Calling llm.generate for user '%s' with %d history items", user_id, len(full_history))
        ai_reply_text = await llm.generate(payload.message_text, full_history)
        log.info("[API /chat] LLM reply for user '%s': '%.50s...'", user_id, ai_reply_text)

        # 3. Извлечь события (Пропускаем для MVP)
        detected_raw_events: List[Event] = []
        processed_events_out: List[EventOut] = []

        # 4. Добавить события в календарь (Пропускаем для MVP)

        # 5. Сохранить сообщение пользователя и ответ AI в историю
        log.debug("[API /chat] Saving messages to history for user '%s'", user_id)
        await user_service.save_message(user_id, Message(role="user", content=payload.message_text))
        await user_service.save_message(user_id, Message(role="assistant", content=ai_reply_text))
        log.debug("[API /chat] Messages saved for user '%s'", user_id)

        # --- ПОЛУЧАЕМ АКТУАЛЬНОЕ КОЛИЧЕСТВО СООБЩЕНИЙ ПОЛЬЗОВАТЕЛЯ ПОСЛЕ СОХРАНЕНИЯ ---
        # Это нужно для триггера "первое сообщение"
        # TODO: UsersService должен иметь метод get_user_message_count(user_id)
        # Временное решение: если до этого история была пуста, значит это первое (примерно)
        # Более надежно: добавить счетчик в модель User или специальный запрос.
        # Для MVP: если `full_history` была пуста до добавления текущего сообщения, это "первое".
        # Так как мы уже сохранили, `full_history` будет содержать как минимум 2 сообщения (user+AI)
        # для первого реального взаимодействия.
        # Правильнее всего иметь отдельный счетчик или флаг "first_message_sent" в User.
        # Пока сделаем упрощенно: если до этого вызов get_recent_messages(limit=1) вернул 0.
        is_first_ever_message_pair = not history # Если история (до текущего запроса) была пуста

        # 6. Проверить и выдать достижения
        log.debug("[API /chat] Checking achievements for user '%s'", user_id)
        # Передаем user_message_count. Если это первое сообщение, count = 1.
        # Для MVP, если is_first_ever_message_pair, то это считается как 1-е сообщение.
        message_count_for_trigger = 1 if is_first_ever_message_pair else 2 # или больше

        unlocked_codes: List[str] = await ach_service.check_and_award(
            user_id=user_id,
            message_text=payload.message_text, # Передаем текст пользователя для анализа
            user_message_count=message_count_for_trigger
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
