from __future__ import annotations

import logging

from fastapi import FastAPI

from app.api.v1.chat import router as chat_router
from app.api.v1.calendar import router as cal_router
from app.api.v1.audio import router as audio_router
from app.api.v1.health import router as health_router
from app.config import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

app = FastAPI(title="AI-Friend API", version="0.1.0", docs_url="/docs")

app.include_router(chat_router)
app.include_router(cal_router)
app.include_router(audio_router)
app.include_router(health_router)

logging.getLogger(__name__).info("🌱 FastAPI started in %s mode", settings.ENVIRONMENT)
