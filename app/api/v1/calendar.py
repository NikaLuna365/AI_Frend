from __future__ import annotations

from typing import List

from fastapi import APIRouter
from pydantic import BaseModel

from app.core.calendar import get_calendar_provider

router = APIRouter(prefix="/v1/calendar", tags=["calendar"])


class EventOut(BaseModel):
    title: str
    start: str
    end: str | None = None


@router.get("/{user_id}", response_model=List[EventOut])
def get_calendar(user_id: str):
    prov = get_calendar_provider()
    events = prov.all_events(user_id)
    return [EventOut.model_validate(e) for e in events]
