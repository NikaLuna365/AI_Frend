from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import List, Literal

# ────────────────────────────────────────────────────────────
#   публичные структуры   (просто dataclass → быстрее Pydantic)
# ────────────────────────────────────────────────────────────
Role = Literal["user", "assistant", "system"]


@dataclass
class Message:
    role: Role
    content: str


@dataclass
class Event:
    title: str
    start: datetime
    end: datetime | None = None


# ────────────────────────────────────────────────────────────
#   абстрактная база провайдера
# ────────────────────────────────────────────────────────────
class BaseLLM(ABC):
    @abstractmethod
    def generate(self, prompt: str, context: List[Message]) -> str: ...

    @abstractmethod
    def extract_events(self, text: str) -> List[Event]: ...

    # ── удобный helper для сервисов ─────────────────────────
    def chat(self, user_input: str, ctx: List[Message]) -> tuple[str, List[Event]]:
        reply = self.generate(user_input, ctx)
        events = self.extract_events(user_input)
        return reply, events
