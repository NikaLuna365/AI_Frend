from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List
from app.core.llm.client import LLMClient, Message
from app.core.calendar.base import get_calendar_provider
from app.core.achievements.service import AchievementsService
from app.core.users.service import UsersService
from datetime import datetime

router = APIRouter()

class ChatRequest(BaseModel):
    user_id: str
    message_text: str

class EventOut(BaseModel):
    title: str
    start: datetime
    end: datetime | None = None

class ChatResponse(BaseModel):
    reply_text: str
    detected_events: List[EventOut]
    achievements: List[str]

@router.post('/', response_model=ChatResponse)
def chat(body: ChatRequest):
    svc_users = UsersService()
    svc_llm = LLMClient()
    calendar = get_calendar_provider()
    svc_ach = AchievementsService()

    svc_users.save_message(body.user_id, Message(role='user', content=body.message_text))

    try:
        context = svc_users.get_recent_messages(body.user_id)
        reply = svc_llm.generate(body.message_text, context)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'LLM error: {e}')

    events = []
    try:
        events = svc_llm.extract_events(reply)
        for ev in events:
            calendar.add_event(body.user_id, ev.title, ev.start, ev.end)
    except:
        events = []

    medals = svc_ach.check_and_award(body.user_id, events, reply)

    svc_users.save_message(body.user_id, Message(role='assistant', content=reply))

    return ChatResponse(
        reply_text=reply,
        detected_events=events,
        achievements=[m.code for m in medals]
    )
