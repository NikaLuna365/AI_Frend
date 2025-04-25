from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from redis import Redis
from redis.exceptions import RedisError

from app.db.base import engine
from app.config import settings
from app.core.calendar import get_calendar_provider

router = APIRouter(tags=["infra"])
log = logging.getLogger(__name__)


@router.get("/healthz")
def healthz():
    out: dict[str, str] = {}

    # DB
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        out["db"] = "ok"
    except SQLAlchemyError as exc:
        log.exception("DB health check failed")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="db error") from exc

    # Redis
    try:
        r = Redis.from_url(settings.CELERY_BROKER_URL, socket_connect_timeout=2)
        assert r.ping()
        out["cache"] = "ok"
    except (RedisError, AssertionError) as exc:
        log.exception("Redis health check failed")
        raise HTTPException(status_code=500, detail="cache error") from exc

    # Calendar (only if не noop)
    prov = get_calendar_provider()
    if prov.__class__.__name__ != "NoopCalendarProvider":  # pragma: no cover
        try:
            prov.list_events("dummy")  # лёгкий запрос
            out["calendar"] = "ok"
        except Exception as exc:  # noqa: BLE001
            log.exception("Calendar health check failed")
            raise HTTPException(status_code=500, detail="calendar error") from exc
    else:
        out["calendar"] = "noop"

    return out
