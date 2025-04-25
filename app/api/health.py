# app/api/health.py
from fastapi import APIRouter, status, HTTPException
import redis
from sqlalchemy import text

from app.db.base import engine
from app.config import settings
from app.core.calendar.base import get_calendar_provider

router = APIRouter(tags=["Health"])


@router.get("/healthz", status_code=status.HTTP_200_OK)
def healthcheck():
    # DB
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as e:
        raise HTTPException(500, detail=f"DB error: {e}")

    # Redis
    try:
        r = redis.from_url(settings.REDIS_URL)
        r.ping()
    except Exception as e:
        raise HTTPException(500, detail=f"Redis error: {e}")

    # Calendar (если не noop)
    if settings.CALENDAR_PROVIDER != "noop":
        try:
            prov = get_calendar_provider()
            _ = prov.list_events("health", None, None)  # лёгкий вызов
        except Exception as e:
            raise HTTPException(500, detail=f"Calendar error: {e}")

    return {"status": "ok"}
