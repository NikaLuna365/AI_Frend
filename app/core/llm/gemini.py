# /app/app/core/llm/providers/gemini.py (Полная версия с исправленной сигнатурой generate_achievement_icon)

# --- Начало файла: Импорты, Проверка SDK, SYSTEM_PROMPT_AI_FRIEND ---
from __future__ import annotations
import asyncio
import logging
import base64
import google.generativeai as genai
from google.generativeai.types import GenerationConfig, ContentDict, PartDict, SafetySettingDict
from typing import List, Sequence, Optional, Dict, Any, cast
from google.cloud import aiplatform
from google.protobuf import json_format
from google.protobuf.struct_pb2 import Value
from .base import BaseLLMProvider, Message, Event
from app.config import settings
log = logging.getLogger(__name__)
try:
    _test_model = genai.GenerativeModel('gemini-1.5-flash-latest')
    log.info("Google Generative AI SDK seems configured correctly.")
except Exception as e:
    log.exception(...)
SYSTEM_PROMPT_AI_FRIEND = """..."""
# --- Конец начального блока ---

class GeminiLLMProvider(BaseLLMProvider):
    name = "gemini"
    DEFAULT_MODEL_NAME = "gemini-1.5-flash-latest"
    IMAGEN_MODEL_NAME = "imagegeneration@006"
    DEFAULT_SAFETY_SETTINGS: List[SafetySettingDict] = [...] # Как в #75

    def __init__(self, model_name: Optional[str] = None) -> None:
        # --- Инициализация БЕЗ system_instruction ---
        self.model_name = model_name or self.DEFAULT_MODEL_NAME
        self.system_prompt = SYSTEM_PROMPT_AI_FRIEND
        self.safety_settings = self.DEFAULT_SAFETY_SETTINGS
        self.generation_config = GenerationConfig(...)
        try:
            self.model = genai.GenerativeModel(model_name=self.model_name)
            log.info(...)
        except Exception as e:
            log.exception(...)
            raise RuntimeError(...) from e
        # --- Конец __init__ ---

    def _prepare_gemini_history(self, context: Sequence[Message]) -> List[ContentDict]:
        # --- Код без изменений (как в #75) ---
        gemini_history: List[ContentDict] = []
        # ... (цикл по context, создание словарей) ...
        return gemini_history

    async def generate(
        self, prompt: str, context: Sequence[Message],
        rag_facts: Optional[List[str]] = None, system_prompt_override: Optional[str] = None
    ) -> str:
        # --- Код без изменений (как в #75, system_instruction передается в generate_content_async) ---
        log.debug("Gemini: Generating response...")
        # ... (подготовка contents_for_api) ...
        effective_system_instruction = system_prompt_override or self.system_prompt
        try:
            response = await self.model.generate_content_async(
                contents=contents_for_api,
                generation_config=self.generation_config,
                safety_settings=self.safety_settings,
                system_instruction=effective_system_instruction # <-- Передаем здесь
            )
            # ... (надежная обработка ответа) ...
            # ... return response_text или сообщение об ошибке ...
        except TypeError as te:
             if 'system_instruction' in str(te): # Fallback
                  # ... (повторный вызов без system_instruction) ...
                  pass # Заглушка
             else: # Другая TypeError
                  # ... (логирование и возврат ошибки) ...
                  pass # Заглушка
        except Exception as e:
            # ... (логирование и возврат ошибки) ...
            pass # Заглушка
        return "(Placeholder Error)" # Заглушка

    async def generate_achievement_name(
        self, context: str, style_id: str, tone_hint: str, style_examples: str
    ) -> List[str]:
        # --- Код без изменений (как в #75) ---
        log.debug("Gemini: Generating achievement name...")
        # ... (формирование full_prompt_contents) ...
        try:
            # ... (вызов generate_content_async БЕЗ system_instruction) ...
            # ... (надежная обработка ответа) ...
            # ... return valid_names или дефолтные ...
            pass # Заглушка
        except Exception as e:
            # ... (логирование и возврат дефолтных) ...
            pass # Заглушка
        return ["Default 1", "Default 2", "Default 3"] # Заглушка

    async def extract_events(self, text: str) -> List[Event]:
        # --- Код без изменений ---
        log.debug("GeminiLLMProvider.extract_events called (returns empty list).")
        return []

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
        (Реализация пока заглушка, возвращает None)
        """
        log.warning(f"generate_achievement_icon called for '{context}', but not implemented yet. Returning None.")
        # --- ЗДЕСЬ БУДЕТ КОД ВЫЗОВА VERTEX AI IMAGEN ---
        # try:
        #     aiplatform.init(...)
        #     model = aiplatform.ImageGenerationModel.from_pretrained(...)
        #     prompt = f"..." # Формируем промпт
        #     imagen_parameters = {...}
        #     loop = asyncio.get_running_loop()
        #     response = await loop.run_in_executor(None, lambda: model.generate_images(...))
        #     if response and response.images:
        #          return response.images[0]._blob
        # except Exception as e:
        #      log.exception(...)
        # ---------------------------------------------
        return None # Возвращаем None, пока не реализовано

__all__ = ["GeminiLLMProvider"]
