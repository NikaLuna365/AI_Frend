# app/api/v1/chat.py

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.calendar import get_calendar_provider
from app.core.llm.client import LLMClient, Message
from app.core.calendar import get_calendar_provider
from app.core.achievements import AchievementsService    # ← импорт из __init__.py
from app.core.users.service import UsersService
from app.db.base import get_db_session
from app.core.calendar.schemas import EventOut
from app.core.achievements.schemas import AchievementOut

router = APIRouter(prefix="/v1/chat", tags=["Chat"])

# ----------------------------- схемы -----------------------------


class ChatRequest(Message):  # наследуем поля role, content
    """Запрос: user_id и текст сообщения."""
    user_id: int


class ChatResponse(Message):  # наследуем поля role, content
    """Ответ бота + опциональные события и достижения."""
    detected_events: list[EventOut] | None = None
    achievements: list[AchievementOut] | None = None


# ----------------------------- эндпоинт ---------------------------


@router.post("/", response_model=ChatResponse, status_code=status.HTTP_200_OK)
def chat_endpoint(
    req: ChatRequest,
    db=Depends(get_db_session),
) -> ChatResponse:
    """Основной чат-эндпоинт: принимает текст, отдаёт ответ Gemini."""
    users_svc = UsersService(db)
    ach_svc = AchievementsService(db)

    # Шаг 1 — сохраняем входящее сообщение
    users_svc.save_message(req.user_id, Message(role="user", content=req.content))

    # Шаг 2 — генерируем ответ LLM
    llm = LLMClient()
    reply_text: str = llm.generate(req.content, context=users_svc.get_context(req.user_id))

    # Шаг 3 — вытаскиваем события из ответа
    events: list[EventOut] = llm.extract_events(reply_text)
    cal = get_calendar_provider()
    for ev in events:
        cal.add_event(req.user_id, ev.title, ev.start_dt, ev.end_dt, ev.metadata)

    # Шаг 4 — проверяем достижения
    achievements: list[AchievementOut] = ach_svc.check_and_grant(req.user_id, events)

    # Шаг 5 — сохраняем ответ бота
    users_svc.save_message(req.user_id, Message(role="assistant", content=reply_text))

    return ChatResponse(
        role="assistant",
        content=reply_text,
        detected_events=events or None,
        achievements=achievements or None,
    )
