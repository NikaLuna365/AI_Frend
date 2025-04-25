from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from typing import List

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

from app.config import settings
from ..base import BaseCalendarProvider, EventOut

log = logging.getLogger(__name__)


class GoogleCalendarProvider(BaseCalendarProvider):
    def __init__(self) -> None:  # noqa: D401
        creds_json_path = settings.GOOGLE_CALENDAR_CREDENTIALS_JSON
        if not os.path.exists(creds_json_path):  # pragma: no cover
            raise RuntimeError(f"Google service account json not found: {creds_json_path}")

        with open(creds_json_path, "r", encoding="utf-8") as fh:
            info = json.load(fh)
        creds = Credentials.from_service_account_info(info, scopes=["https://www.googleapis.com/auth/calendar"])

        self._svc = build("calendar", "v3", credentials=creds)
        self._calendar_id = "primary"

    # ─────────────────────────────────────────────────────
    def add_event(self, user_id: str, title: str, start: datetime, end: datetime | None = None) -> None:
        body = {
            "summary": title,
            "start": {"dateTime": start.isoformat()},
            "end": {"dateTime": (end or start).isoformat()},
        }
        self._svc.events().insert(calendarId=self._calendar_id, body=body, sendUpdates="none").execute()
        log.info("[Calendar] insert event for %s: %s @ %s", user_id, title, start.isoformat())

    def list_events(
        self, user_id: str, from_dt: datetime | None = None, to_dt: datetime | None = None
    ) -> List[EventOut]:
        params: dict = {"calendarId": self._calendar_id, "singleEvents": True, "orderBy": "startTime"}
        if from_dt:
            params["timeMin"] = from_dt.isoformat()
        if to_dt:
            params["timeMax"] = to_dt.isoformat()

        resp = self._svc.events().list(**params).execute()
        items = resp.get("items", [])
        out: List[EventOut] = []
        for it in items:
            out.append(
                EventOut(
                    title=it["summary"],
                    start=datetime.fromisoformat(it["start"]["dateTime"]),
                    end=datetime.fromisoformat(it["end"]["dateTime"]),
                )
            )
        return out
