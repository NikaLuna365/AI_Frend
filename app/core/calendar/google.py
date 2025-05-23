# app/core/calendar/google.py

"""
Реализация CalendarProvider через Google Calendar API (v3).
"""

from __future__ import annotations

import os
from typing import Any, List  # ← исправлено: убрали «dict»

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

from app.config import settings


class GoogleCalendarProvider:
    """
    Провайдер для работы с Google Calendar.
    Требует путь к JSON-файлу сервисного аккаунта:
        settings.GOOGLE_CALENDAR_CREDENTIALS_JSON
    """

    def __init__(self) -> None:
        creds_path = settings.GOOGLE_CALENDAR_CREDENTIALS_JSON
        if not os.path.isfile(creds_path):
            raise FileNotFoundError(f"Google credentials not found: {creds_path}")

        self.creds = Credentials.from_service_account_file(creds_path)
        self.service = build("calendar", "v3", credentials=self.creds)

    # --------------------------------------------------------------------- #
    # CalendarProvider interface
    # --------------------------------------------------------------------- #

    def add_event(
        self,
        user_id: str,
        title: str,
        start_dt: Any,
        end_dt: Any | None = None,
        metadata: dict[str, Any] | None = None,  # PEP-585: можно dict[str, Any]
    ) -> dict[str, Any]:
        """Создаёт событие в основном календаре (primary)."""
        body: dict[str, Any] = {
            "summary": title,
            "start": {"dateTime": start_dt.isoformat()},
            "end": {"dateTime": (end_dt or start_dt).isoformat()},
        }
        if metadata:
            body.update(metadata)

        return (
            self.service.events()
            .insert(calendarId="primary", body=body)
            .execute()
        )

    def list_events(
        self,
        user_id: str,
        from_dt: Any,
        to_dt: Any,
    ) -> List[dict[str, Any]]:
        """Возвращает список событий за указанный диапазон."""
        resp = (
            self.service.events()
            .list(
                calendarId="primary",
                timeMin=from_dt.isoformat(),
                timeMax=to_dt.isoformat(),
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )
        return resp.get("items", [])
