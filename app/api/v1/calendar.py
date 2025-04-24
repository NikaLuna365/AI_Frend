from fastapi import APIRouter
from typing import List
from datetime import datetime, timedelta
from app.core.calendar.base import get_calendar_provider
from app.core.calendar.models import EventOut

router = APIRouter()

@router.get('/{user_id}', response_model=List[EventOut])
def get_calendar(user_id: str):
    provider = get_calendar_provider()
    now = datetime.utcnow()
    future = now + timedelta(days=30)
    return provider.list_events(user_id, now, future)
