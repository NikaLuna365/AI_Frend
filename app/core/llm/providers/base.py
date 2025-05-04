# /app/app/core/llm/providers/base.py (Добавляем generate_achievement_icon)

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Sequence, Optional # Добавили Optional

from app.core.llm.message import Message, Event

class BaseLLMProvider(ABC):
    """Абстрактный базовый класс для LLM провайдеров (АСИНХРОННЫЙ)."""
    name: str # Имя провайдера (e.g., 'stub', 'gemini')

    @abstractmethod
    async def generate(self, prompt: str, context: Sequence[Message]) -> str:
        """Генерирует текстовый ответ."""
        ...

    @abstractmethod
    async def extract_events(self, text: str) -> List[Event]:
        """Извлекает события календаря из текста."""
        ...

    @abstractmethod
    async def generate_achievement_name(
        self, context: str, style_id: str, tone_hint: str, style_examples: str
    ) -> List[str]:
        """Генерирует названия для ачивок."""
        ...

    # --- НОВЫЙ АБСТРАКТНЫЙ МЕТОД ---
    @abstractmethod
    async def generate_achievement_icon(
        self,
        context: str, # Текст для генерации иконки (тема/промпт)
        style_id: str, # Идентификатор стиля (для выбора пресета/промпта)
        style_keywords: str, # Ключевые слова для описания стиля
        palette_hint: str, # Подсказка по цветам
        shape_hint: str # Подсказка по форме
        ) -> bytes | None: # Возвращает байты PNG или None при ошибке
        """Генерирует иконку ачивки (PNG байты)."""
        ...
    # -------------------------------

# Экспорты остаются прежними
__all__ = ["BaseLLMProvider", "Message", "Event"]
