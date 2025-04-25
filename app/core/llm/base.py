from __future__ import annotations

from datetime import datetime
from typing import List

from pydantic import BaseModel


class Message(BaseModel):
    role: str
    content: str


class Event(BaseModel):
    title: str
    start: datetime
    end: datetime | None = None


class BaseLLM:
    """Минимальный контракт."""

    def chat(self, user_text: str, ctx: List[Message]) -> tuple[str, List[Event]]: ...  # noqa: D401
