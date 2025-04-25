# app/api/v1/calendar.py
from datetime import datetime, timedelta
from typing import List

from fastapi import APIRouter
from pydantic import BaseModel

from app.core.calendar.base import get_calendar_provider

router = APIRouter(prefix="/v1/calendar", tags=["Calendar"])


class EventOut(BaseModel):
    title: str
    start: datetime
    end: datetime | None = None


@router.get("/{user_id}", response_model=List[EventOut])
def list_events(user_id: str):
    prov = get_calendar_provider()
    now = datetime.utcnow()
    week = now + timedelta(days=7)
    return prov.list_events(user_id, now, week)
