from __future__ import annotations
import logging

from fastapi import FastAPI

from app.api.v1.auth import router as auth_router
from app.api.v1.chat import router as chat_router
from app.api.v1.calendar import router as cal_router
from app.api.v1.audio import router as audio_router
from app.api.v1.health import router as health_router
from app.api.v1.achievements_api import router as achievements_router

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="AI Friend API")

# Include routers
app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(cal_router)
app.include_router(audio_router)
app.include_router(health_router)
app.include_router(achievements_router)


@app.get("/healthz", tags=["Health"])
async def health_check():
    return {"status": "ok"}
