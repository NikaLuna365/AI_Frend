from __future__ import annotations
import logging
from fastapi import FastAPI, status

from app.api.v1.auth import router as auth_router
from app.api.v1.chat import router as chat_router
from app.api.v1.health import router as health_router
from app.api.v1.achievements_api import router as achievements_router
from app.config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(module)s:%(lineno)d - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
log = logging.getLogger(__name__)

description = "AI-Friend API helps you manage your conversations and schedule."

tags_metadata = [
    {"name": "Authentication & Testing", "description": "User authentication and token issuance."},
    {"name": "chat", "description": "Endpoints for interacting with the AI chat."},
    {"name": "Achievements", "description": "Operations related to user achievements."},
    {"name": "Health", "description": "API health checks."},
]

app = FastAPI(
    title="AI-Friend API",
    description=description,
    version="0.2.1",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=tags_metadata,
)

app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(health_router)
app.include_router(achievements_router)

log.info("\U0001F331 FastAPI application configured. Environment: %s", settings.ENVIRONMENT)

@app.on_event("startup")
async def startup_event() -> None:
    log.info("\U0001F680 FastAPI application startup complete.")

@app.on_event("shutdown")
async def shutdown_event() -> None:
    log.info("\U0001F44B FastAPI application shutdown.")

@app.get("/healthz", tags=["Health"], status_code=status.HTTP_200_OK)
async def health_check():
    """Basic health check endpoint."""
    return {"status": "ok", "environment": settings.ENVIRONMENT}
