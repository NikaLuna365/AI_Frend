# app/api/v1/health.py
from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import text
import redis

from app.db.base import engine
from app.config import settings
from app.core.calendar.base import get_calendar_provider

router = APIRouter(tags=["Health"])


@router.get("/healthz")
def healthz():
    # DB
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"DB: {exc!s}")

    # Redis
    try:
        redis.Redis.from_url(settings.REDIS_URL).ping()
    except Exception as exc:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Redis: {exc!s}")

    # Calendar (если реальный)
    if settings.CALENDAR_PROVIDER != "noop":
        try:
            provider = get_calendar_provider()
            if hasattr(provider, "service"):
                provider.service.colors().get(calendarId="primary").execute()
        except Exception as exc:
            raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Calendar: {exc!s}")

    return {"status": "ok"}
