# /app/app/core/llm/providers/gemini.py (Версия v7 - Улучшенное логирование и обработка ошибок)

from __future__ import annotations

import asyncio
import logging
import base64
import google.generativeai as genai
# Используем явные типы из библиотеки
from google.generativeai.types import GenerationConfig, ContentDict, PartDict, SafetySettingDict, GenerateContentResponse
from typing import List, Sequence, Optional, Dict, Any, cast

# --- Импорты для Vertex AI (оставляем для generate_achievement_icon) ---
from google.cloud import aiplatform
from google.protobuf import json_format
from google.protobuf.struct_pb2 import Value
# ------------------------------------

from .base import BaseLLMProvider, Message, Event
from app.config import settings

log = logging.getLogger(__name__)

# Проверка конфигурации SDK
try:
    _test_model = genai.GenerativeModel('gemini-1.5-flash-latest') # Используем flash для теста
    log.info("Google Generative AI SDK seems configured correctly.")
except Exception as e:
    log.warning("Could not pre-initialize test model, potential config issue: %s", e) # Смягчаем до Warning

# Системный Промпт
SYSTEM_PROMPT_AI_FRIEND = """
You are AI-Friend, a personalized AI companion... (Полный текст)
"""

class GeminiLLMProvider(BaseLLMProvider):
    name = "gemini"
    # --- УКАЖИТЕ НУЖНУЮ МОДЕЛЬ ---
    DEFAULT_MODEL_NAME = "gemini-1.5-flash-latest" # Замените на "gemini-2.0-flash-lite", если она доступна
    # ---------------------------
    IMAGEN_MODEL_NAME = "imagegeneration@006"

    # --- Настройки Безопасности (Можно сделать менее строгими для теста) ---
    DEFAULT_SAFETY_SETTINGS: List[SafetySettingDict] = [
        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_ONLY_HIGH"}, # Менее строго
        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_ONLY_HIGH"}, # Менее строго
        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_ONLY_HIGH"}, # Менее строго
        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_ONLY_HIGH"}, # Менее строго
        # Или для теста: "BLOCK_NONE" для всех категорий
    ]
    # --------------------------------------------------------------------

    def __init__(self, model_name: Optional[str] = None) -> None:
        self.model_name = model_name or self.DEFAULT_MODEL_NAME
        self.system_prompt = SYSTEM_PROMPT_AI_FRIEND
        self.safety_settings = self.DEFAULT_SAFETY_SETTINGS
        self.generation_config = GenerationConfig(temperature=0.7, candidate_count=1)
        log.info(f"Attempting to initialize GeminiLLMProvider with model: {self.model_name}")
        try:
            # Инициализация БЕЗ system_instruction/safety/generation_config в конструкторе
            self.model = genai.GenerativeModel(model_name=self.model_name)
            log.info(f"GeminiLLMProvider initialized model {self.model_name} successfully.")
        except Exception as e:
            log.exception(f"Failed to initialize GenerativeModel '{self.model_name}': {e}")
            raise RuntimeError(f"Failed to initialize Gemini model {self.model_name}") from e

    def _prepare_gemini_history(self, context: Sequence[Message]) -> List[ContentDict]:
        # ... (код без изменений, создает List[ContentDict]) ...
        gemini_history: List[ContentDict] = []
        for msg in context:
            content = msg.get("content", "").strip();
            if not content: continue
            role = "model" if msg.get("role") == "assistant" else "user"
            gemini_history.append(cast(ContentDict, {"role": role, "parts": [PartDict(text=content)]}))
        return gemini_history

    async def generate(
        self, prompt: str, context: Sequence[Message],
        rag_facts: Optional[List[str]] = None, system_prompt_override: Optional[str] = None
    ) -> str:
        log.debug("Gemini: Generating response...")
        # ... (подготовка history_prepared, rag_message, contents_for_api как раньше) ...
        history_prepared = self._prepare_gemini_history(context)
        if rag_facts:
             facts_text = "\n".join(f"- {fact}" for fact in rag_facts)
             rag_message = cast(ContentDict, {'role': 'user', 'parts': [PartDict(text=f"(Context:\n{facts_text}\n)")]})
             history_prepared.append(rag_message)
        current_message = cast(ContentDict, {'role': 'user', 'parts': [PartDict(text=prompt)]})
        contents_for_api = history_prepared + [current_message]
        effective_system_instruction = system_prompt_override or self.system_prompt

        try:
            # --- Вызов API с подробным логированием ---
            log.debug(f"Calling generate_content_async for model '{self.model_name}'...")
            log.debug(f"  System Instruction: '{effective_system_instruction[:100]}...'") # Логгируем начало промпта
            log.debug(f"  Contents (last item): {contents_for_api[-1]}") # Логгируем последний элемент (промпт)
            log.debug(f"  Generation Config: {self.generation_config}")
            log.debug(f"  Safety Settings: {self.safety_settings}")

            response: GenerateContentResponse = await self.model.generate_content_async(
                contents=contents_for_api,
                generation_config=self.generation_config,
                safety_settings=self.safety_settings,
                system_instruction=effective_system_instruction # Передаем system instruction здесь
            )
            log.debug(f"Gemini API call completed. Response object: {response}") # Логгируем весь объект ответа
            # --------------------------------------------

            # --- УЛУЧШЕННАЯ ОБРАБОТКА ОТВЕТА ---
            try:
                # 1. Проверяем блокировку ДО проверки текста
                if response.prompt_feedback.block_reason:
                    reason = response.prompt_feedback.block_reason.name # Получаем имя причины
                    log.warning(f"Gemini response blocked by safety settings: {reason}")
                    return f"(Ответ был заблокирован: {reason})"

                # 2. Пытаемся извлечь текст (более безопасный доступ)
                # Проверяем наличие candidates и первого кандидата
                if not response.candidates:
                     log.warning("Gemini response missing 'candidates' field.")
                     return "(AI не вернул кандидатов ответа)"

                first_candidate = response.candidates[0]

                # Проверяем наличие content и parts
                if not first_candidate.content or not first_candidate.content.parts:
                     # Это может случиться, если safety сработал не на уровне prompt_feedback, а на уровне кандидата
                     finish_reason_name = first_candidate.finish_reason.name if first_candidate.finish_reason else "UNKNOWN"
                     log.warning(f"Gemini response candidate has no content/parts. Finish reason: {finish_reason_name}")
                     # Дополнительно проверяем safety_ratings кандидата
                     safety_ratings_str = ", ".join(f"{r.category.name}={r.probability.name}" for r in first_candidate.safety_ratings) if first_candidate.safety_ratings else "N/A"
                     log.warning(f"Candidate safety ratings: {safety_ratings_str}")
                     return f"(Ответ AI был отфильтрован или пуст. Причина: {finish_reason_name})"

                # Извлекаем текст
                response_text = first_candidate.content.parts[0].text.strip()
                log.info("Gemini response extracted successfully.") # Меняем на INFO для видимости
                return response_text

            except (AttributeError, IndexError, StopIteration, ValueError, KeyError) as parse_exc: # Добавляем KeyError
                # Ловим ЛЮБЫЕ ошибки при доступе к полям ответа
                log.exception(f"Error parsing Gemini response structure: {parse_exc}. Full Response Object: {response}")
                return f"(Ошибка при обработке ответа AI: {type(parse_exc).__name__})"
            # ---------------------------------------

        except TypeError as te:
            # Обработка ошибки, если generate_content_async НЕ принимает system_instruction
            if 'system_instruction' in str(te):
                 log.error(f"TypeError: generate_content_async for model '{self.model_name}' does not accept 'system_instruction'. Check SDK/model compatibility.")
                 # НЕ ДЕЛАЕМ FALLBACK, так как это явная ошибка конфигурации/вызова
                 return f"(Ошибка конфигурации AI: system_instruction)"
            else:
                 log.exception(f"TypeError during Gemini API call: {te}")
                 return f"(Произошла ошибка при вызове AI: TypeError)"
        except Exception as e:
            # Логируем полное исключение
            log.exception(f"Unhandled Error during Gemini API call in generate(): {e}")
            # Возвращаем более детальную информацию об ошибке
            return f"(Произошла ошибка при обращении к AI: {type(e).__name__}: {e})"

    # --- generate_achievement_name (также улучшаем логирование и обработку ошибок) ---
    async def generate_achievement_name(...) -> List[str]:
        # ... (как в #75, но с улучшенной обработкой ответа и логированием исключений) ...
        # ...
        try:
            response = await self.model.generate_content_async(...)
            try: # Улучшенная обработка ответа
                if response.prompt_feedback.block_reason: # ...
                if (response.candidates and ...): # ...
                   # ... (парсинг имен)
                   return valid_names
                else: # ...
                   return ["Default 1", "Default 2", "Default 3"]
            except (AttributeError, ...) as parse_exc: # ...
                 log.exception(...)
                 return ["Default 1", "Default 2", "Default 3"]
        except Exception as e:
             log.exception(f"Error generating achievement names: {e}") # Логируем полное исключение
             return ["Default 1", "Default 2", "Default 3"]


    # --- generate_achievement_icon (оставляем заглушкой) ---
    async def generate_achievement_icon(...) -> bytes | None: return None
    # --- extract_events (оставляем заглушкой) ---
    async def extract_events(self, text: str) -> List[Event]: return []

__all__ = ["GeminiLLMProvider"]
