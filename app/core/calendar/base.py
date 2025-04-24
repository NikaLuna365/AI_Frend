from abc import ABC, abstractmethod
from typing import List
from datetime import datetime
from .models import EventOut

class CalendarProvider(ABC):
    @abstractmethod
    def add_event(self, user_id: str, title: str, start_dt: datetime, end_dt: datetime | None = None):
        pass

    @abstractmethod
    def list_events(self, user_id: str, from_dt: datetime, to_dt: datetime) -> List[EventOut]:
        pass


def get_calendar_provider() -> CalendarProvider:
    from app.config import settings
    if settings.CALENDAR_PROVIDER == 'google':
        from app.core.calendar.google import GoogleCalendarProvider
        return GoogleCalendarProvider()
    raise ValueError(f'Unknown CALENDAR_PROVIDER={settings.CALENDAR_PROVIDER}')
