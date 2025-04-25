from __future__ import annotations

import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, validator
from sqlalchemy.orm import Session

from app.core.calendar import get_calendar_provider
from app.core.llm import get_llm
from app.core.llm.base import Event, Message
from app.core.achievements.service import AchievementsService
from app.db.base import get_db_session

router = APIRouter(prefix="/v1/chat", tags=["chat"])
log = logging.getLogger(__name__)


class ChatRequest(BaseModel):
    user_id: str = Field(..., min_length=1)
    message_text: str = Field(..., min_length=1)


class EventOut(BaseModel):
    title: str
    start: str
    end: str | None = None


class ChatResponse(BaseModel):
    reply_text: str
    detected_events: List[EventOut]
    achievements: List[str]


@router.post("/", response_model=ChatResponse)
def chat_endpoint(payload: ChatRequest, db: Session = Depends(get_db_session)):
    llm = get_llm()

    reply, events = llm.chat(payload.message_text, [])

    prov = get_calendar_provider()
    for ev in events:
        if not isinstance(ev, Event):  # pragma: no cover
            raise HTTPException(status_code=500, detail="Invalid event type from LLM")
        prov.add_event(payload.user_id, ev.title, ev.start, ev.end)

    ach_svc = AchievementsService(db=db)
    unlocked_codes = ach_svc.check_and_award(payload.user_id, events, reply)

    resp = ChatResponse(
        reply_text=reply,
        detected_events=[EventOut.model_validate(e) for e in events],
        achievements=unlocked_codes,
    )
    log.info("[API] /chat user=%s events=%d achievements=%d", payload.user_id, len(events), len(unlocked_codes))
    return resp
