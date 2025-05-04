# app/core/llm/gemini.py
"""
Реальная обёртка над Google Gemini.
"""

from __future__ import annotations

import os
from typing import List

import google.generativeai as genai

from app.core.llm.schemas import Message, Event
import dateparser.search


# /app/app/core/llm/providers/gemini.py (Исправлена Сигнатура v7)

# ... (импорты, определение класса, __init__, _prepare_gemini_history, generate, generate_achievement_name, extract_events - БЕЗ ИЗМЕНЕНИЙ по сравнению с #75) ...

    # --- ИСПРАВЛЕНИЕ: Заменяем '...' на реальные аргументы ---
    async def generate_achievement_icon(
        self,
        context: str, # Текст для генерации иконки (тема/промпт)
        style_id: str, # Идентификатор стиля (для выбора пресета/промпта)
        style_keywords: str, # Ключевые слова для описания стиля
        palette_hint: str, # Подсказка по цветам
        shape_hint: str # Подсказка по форме
        ) -> bytes | None:
    # ------------------------------------------------------
        """
        Генерирует иконку ачивки (PNG байты) с помощью Vertex AI Imagen API.
        """
        log.info(f"GeminiProvider (Imagen): Generating icon. Context: '{context}'")
        # ... (остальной код метода generate_achievement_icon БЕЗ ИЗМЕНЕНИЙ, как в #71) ...
        if not settings.VERTEX_AI_PROJECT or not settings.VERTEX_AI_LOCATION: return None
        try:
            aiplatform.init(...)
            model = aiplatform.ImageGenerationModel.from_pretrained(...)
            # Формируем промпт на основе context, style_keywords, palette_hint, shape_hint
            prompt = f"""..."""
            imagen_parameters = {...}
            loop = asyncio.get_running_loop()
            response = await loop.run_in_executor(None, lambda: model.generate_images(...))
            if response and response.images:
                 return response.images[0]._blob
            else: return None
        except ImportError: return None
        except Exception as e: log.exception(...); return None

__all__ = ["GeminiLLMProvider"]
