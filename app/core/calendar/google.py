# app/core/calendar/google.py

"""
Реализация CalendarProvider через Google Calendar API.
"""

from __future__ import annotations
import json, os
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from app.config import settings

class GoogleCalendarProvider:
    """Работает с реальным Google Calendar."""

    def __init__(self) -> None:
        # читаем JSON-файл сервакка
        creds_path = settings.GOOGLE_CALENDAR_CREDENTIALS_JSON
        if not os.path.exists(creds_path):
            raise FileNotFoundError(f"Service account JSON not found: {creds_path}")
        self.creds = Credentials.from_service_account_file(creds_path)
        self.service = build("calendar", "v3", credentials=self.creds)

    def add_event(self, user_id: str, title: str, start_dt: Any,
                  end_dt: Any = None, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        body: dict[str, Any] = {
            "summary": title,
            "start": {"dateTime": start_dt.isoformat()},
            "end": {"dateTime": (end_dt or start_dt).isoformat()},
        }
        if metadata:
            body.update(metadata)
        return self.service.events().insert(calendarId="primary", body=body).execute()

    def list_events(self, user_id: str, from_dt: Any, to_dt: Any) -> list[dict[str, Any]]:
        resp = self.service.events().list(
            calendarId="primary",
            timeMin=from_dt.isoformat(),
            timeMax=to_dt.isoformat(),
            singleEvents=True,
            orderBy="startTime",
        ).execute()
        return resp.get("items", [])
