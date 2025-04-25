# app/main.py
from fastapi import FastAPI

from app.api.v1.chat import router as chat_router
from app.api.v1.calendar import router as cal_router
from app.api.v1.achievements import router as ach_router
from app.api.v1.audio import router as audio_router
from app.api.health import router as health_router

app = FastAPI(title="AI-Friend")

app.include_router(chat_router)
app.include_router(cal_router)
app.include_router(ach_router)
app.include_router(audio_router)
app.include_router(health_router)
