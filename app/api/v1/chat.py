# app/api/v1/chat.py
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.base import get_db_session
from app.core.llm.schemas import Message
from app.core.llm.client import LLMClient
from app.core.calendar.base import get_calendar_provider
from app.core.achievements.service import AchievementsService

router = APIRouter(prefix="/v1/chat", tags=["Chat"])


class ChatRequest(BaseModel):
    user_id: str
    message_text: str


class ChatResponse(BaseModel):
    reply_text: str
    detected_events: List[str] | None = None
    achievements: List[str] | None = None


@router.post("/", response_model=ChatResponse)
def chat_endpoint(
    payload: ChatRequest,
    db: Session = Depends(get_db_session),
):
    llm = LLMClient()
    reply = llm.generate(payload.message_text, [])
    events = llm.extract_events(payload.message_text)

    prov = get_calendar_provider()
    for ev in events:
        prov.add_event(payload.user_id, ev.title, ev.start)

    ach_service = AchievementsService(db)
    new_ach = ach_service.check_and_award(payload.user_id, events, reply)

    return ChatResponse(
        reply_text=reply,
        detected_events=[e.title for e in events] or None,
        achievements=[a.code for a in new_ach] or None,
    )
