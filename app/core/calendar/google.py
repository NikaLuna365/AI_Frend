from datetime import datetime, timedelta
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from app.config import settings
from .base import CalendarProvider
from .models import EventOut

class GoogleCalendarProvider(CalendarProvider):
    def __init__(self):
        creds_info = settings.GOOGLE_CALENDAR_CREDENTIALS_JSON
        creds = Credentials.from_service_account_info(creds_info)
        self.service = build('calendar', 'v3', credentials=creds)

    def add_event(self, user_id: str, title: str, start_dt: datetime, end_dt: datetime | None = None):
        event = {
            'summary': title,
            'start': {'dateTime': start_dt.isoformat()},
            'end': {'dateTime': (end_dt or start_dt + timedelta(hours=1)).isoformat()},
        }
        return self.service.events().insert(calendarId='primary', body=event).execute()

    def list_events(self, user_id: str, from_dt: datetime, to_dt: datetime) -> list[EventOut]:
        response = self.service.events().list(
            calendarId='primary',
            timeMin=from_dt.isoformat(),
            timeMax=to_dt.isoformat(),
            singleEvents=True
        ).execute()
        items = response.get('items', [])
        events: list[EventOut] = []
        for item in items:
            start_raw = item['start'].get('dateTime') or item['start'].get('date')
            end_raw = item['end'].get('dateTime') or item['end'].get('date')
            start_dt = datetime.fromisoformat(start_raw)
            end_dt = datetime.fromisoformat(end_raw) if end_raw else None
            events.append(EventOut(
                title=item.get('summary', ''),
                start=start_dt,
                end=end_dt
            ))
        return events
