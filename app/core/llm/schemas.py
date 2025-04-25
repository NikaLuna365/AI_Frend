# app/core/llm/schemas.py
from datetime import datetime
from pydantic import BaseModel


class Message(BaseModel):
    role: str
    content: str


class Event(BaseModel):
    title: str
    start: datetime
    end_dt: datetime | None = None
    metadata: dict | None = None
