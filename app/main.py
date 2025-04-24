from fastapi import FastAPI
from app.config import settings
from app.api.v1 import chat, achievements, calendar, audio
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)

app = FastAPI(title="AI-Drug", version=settings.APP_VERSION)
app.include_router(chat.router, prefix="/v1/chat", tags=["chat"])
app.include_router(achievements.router, prefix="/v1/achievements", tags=["achievements"])
app.include_router(calendar.router, prefix="/v1/calendar", tags=["calendar"])
app.include_router(audio.router, prefix="/v1/chat_audio", tags=["audio"])

@app.get("/healthz")
def health_check():
    """Health check endpoint"""
    return {"status": "ok"}
