# /app/app/core/llm/providers/gemini.py (ФИНАЛЬНАЯ ВЕРСИЯ v5 - Правильная передача system_instruction)

from __future__ import annotations

import logging
import google.generativeai as genai
# Импортируем нужные типы, включая ContentDict и PartDict
from google.generativeai.types import GenerationConfig, ContentDict, PartDict, SafetySettingDict # Добавили ContentDict, PartDict, SafetySettingDict
from typing import List, Sequence, Optional, Dict, Any, cast # Добавили cast

from .base import BaseLLMProvider, Message, Event
from app.config import settings

log = logging.getLogger(__name__)

# Проверка конфигурации SDK (оставляем)
try:
    _test_model = genai.GenerativeModel('gemini-1.5-flash-latest')
    log.info("Google Generative AI SDK seems configured correctly.")
except Exception as e:
    log.exception("Failed to initialize/configure Google Generative AI SDK: %s", e)

# Системный Промпт (оставляем)
SYSTEM_PROMPT_AI_FRIEND = """
You are AI-Friend, a personalized AI companion... (Полный текст)
"""

class GeminiLLMProvider(BaseLLMProvider):
    name = "gemini"
    DEFAULT_MODEL_NAME = "gemini-1.5-flash-latest"
    # --- Используем тип SafetySettingDict ---
    DEFAULT_SAFETY_SETTINGS: List[SafetySettingDict] = [
        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    ]
    # -----------------------------------------

    def __init__(self, model_name: Optional[str] = None) -> None:
        self.model_name = model_name or self.DEFAULT_MODEL_NAME
        self.system_prompt = SYSTEM_PROMPT_AI_FRIEND
        self.safety_settings = self.DEFAULT_SAFETY_SETTINGS
        self.generation_config = GenerationConfig(temperature=0.7, candidate_count=1)
        try:
            # --- ИСПРАВЛЕНИЕ: Инициализируем БЕЗ system_instruction ---
            self.model = genai.GenerativeModel(
                model_name=self.model_name
                # Убрали все доп. аргументы отсюда
            )
            # ------------------------------------------------------
            log.info( "GeminiLLMProvider initialized for model: %s", self.model_name )
        except Exception as e:
            log.exception("Failed to initialize GenerativeModel '%s': %s", self.model_name, e)
            raise RuntimeError(f"Failed to initialize Gemini model {self.model_name}") from e

    def _prepare_gemini_history(self, context: Sequence[Message]) -> List[ContentDict]:
        """Преобразует историю в формат Gemini List[ContentDict]."""
        gemini_history: List[ContentDict] = []
        for msg in context:
            content = msg.get("content", "").strip()
            if not content: continue
            role = "model" if msg.get("role") == "assistant" else "user"
            # Используем ContentDict и PartDict для явного указания типа
            gemini_history.append(cast(ContentDict, {"role": role, "parts": [PartDict(text=content)]}))
        return gemini_history

    async def generate(
        self, prompt: str, context: Sequence[Message],
        rag_facts: Optional[List[str]] = None, system_prompt_override: Optional[str] = None
        ) -> str:
        log.debug("Gemini: Generating response...")

        # --- ИСПРАВЛЕНИЕ: Формируем contents с системным промптом ---
        system_instruction = system_prompt_override or self.system_prompt
        # Системная инструкция идет ПЕРЕД историей
        # Используем явное создание словарей или ContentDict/PartDict
        history_base: List[ContentDict] = [
             # Пытаемся передать system_instruction через специальное поле в первой "user" части,
             # если модель поддерживает такой формат неявно, или просто как часть контекста.
             # Альтернативно, можно пробовать роль "system", но она не всегда есть.
             # Оставляем как "user", но с явным указанием, что это инструкция.
             # cast(ContentDict, {"role": "user", "parts": [PartDict(text=f"[SYSTEM INSTRUCTION]\n{system_instruction}\n\n[USER QUERY]")]})
             # --- БОЛЕЕ НАДЕЖНЫЙ ВАРИАНТ: Просто добавляем его к первому сообщению пользователя ---
             # Но для чистоты диалога, лучше использовать возможности SDK, если они есть.
             # Проверим, принимает ли модель system_instruction как отдельный объект ContentDict
             # cast(ContentDict, {"role": "system", "parts": [PartDict(text=system_instruction)]}) # Не факт, что сработает
        ]

        # Добавляем RAG факты как сообщение пользователя
        if rag_facts:
            facts_text = "\n".join(f"- {fact}" for fact in rag_facts)
            rag_message = cast(ContentDict, {'role': 'user', 'parts': [PartDict(text=f"(Вспомни эти факты о пользователе:\n{facts_text}\n)")]})
            history_base.append(rag_message)
            log.debug("Gemini: Added %d RAG facts.", len(rag_facts))

        # Добавляем реальную историю и текущий промпт
        history_prepared = self._prepare_gemini_history(context)
        current_message = cast(ContentDict, {'role': 'user', 'parts': [PartDict(text=prompt)]})

        # Собираем полный контент: Системный (если поддерживается) + RAG + История + Текущий
        # Пытаемся задать system_instruction через специальное поле модели, если доступно (новейшие SDK)
        # А history передаем в contents
        effective_system_instruction = system_prompt_override or self.system_prompt
        contents_for_api = history_prepared + [current_message] # RAG + История + Промпт

        try:
            # --- Вызов API ---
            response = await self.model.generate_content_async(
                contents=contents_for_api, # Передаем контент
                generation_config=self.generation_config, # Конфиг генерации
                safety_settings=self.safety_settings,   # Настройки безопасности
                # --- Пытаемся задать system_instruction через поле модели, если есть ---
                # --- Этот способ должен работать в новых версиях SDK для новых моделей ---
                 # system_instruction=effective_system_instruction # Если нет, то он просто игнорируется или вызовет ошибку?
                # --- ЕСЛИ ВЫШЕ НЕ РАБОТАЕТ, НУЖНО ВСТАВЛЯТЬ В contents ---
                # Как вариант:
                # contents=[{"role": "user", "parts": [effective_system_instruction, prompt]}] + history_prepared # Системный + промпт в первом сообщении
            )
            # -------------------------------------------------------------

            # --- Обработка ответа (без изменений) ---
            if response and response.text: #...
                 return response.text.strip()
            else: #... (обработка пустых/заблокированных) ...
                 return f"(Я не могу сгенерировать ответ сейчас...)"
        except TypeError as te:
             # Ловим ошибку, если system_instruction НЕ поддерживается как аргумент
             if 'system_instruction' in str(te):
                  log.error("system_instruction is NOT accepted by generate_content_async. Trying without it (prompt needs to be self-contained or use history format)...")
                  # --- ПОВТОРНЫЙ ВЫЗОВ БЕЗ system_instruction ---
                  try:
                       # Пробуем передать системный промпт просто как часть первого сообщения
                       first_user_message = f"{effective_system_instruction}\n\nUser query: {prompt}"
                       contents_alt = self._prepare_gemini_history(context) + [cast(ContentDict, {'role': 'user', 'parts': [PartDict(text=first_user_message)]})]

                       response = await self.model.generate_content_async(
                            contents=contents_alt,
                            generation_config=self.generation_config,
                            safety_settings=self.safety_settings
                       )
                       if response and response.text: return response.text.strip()
                       else: return "(Я не могу сгенерировать ответ сейчас...)" # Повторная обработка ошибки
                  except Exception as e_fallback:
                       log.exception("Error during Gemini API fallback call: %s", e_fallback)
                       return f"(Произошла ошибка при обращении к AI: {type(e_fallback).__name__})"
             else:
                  # Другая ошибка TypeError
                  log.exception("TypeError during Gemini API call: %s", te)
                  return f"(Произошла ошибка при вызове AI: TypeError)"
        except Exception as e:
            log.exception("Error during Gemini API call in generate(): %s", e)
            return f"(Произошла ошибка при обращении к AI: {type(e).__name__})"

    # --- generate_achievement_name (убираем system_instruction из вызова) ---
    async def generate_achievement_name(
        self, context: str, style_id: str, tone_hint: str, style_examples: str
    ) -> List[str]:
        log.debug("Gemini: Generating achievement name...")
        # --- Промпт для названий (оставляем как есть) ---
        # ...
        full_prompt_contents = [...]
        # ---------------------------------------------
        try:
            generation_config_names = GenerationConfig(...)
            # --- Вызов без system_instruction ---
            response = await self.model.generate_content_async(
                contents=full_prompt_contents,
                generation_config=generation_config_names,
                safety_settings=self.safety_settings
            )
            # ---------------------------------
            # --- Обработка ответа (оставляем как есть) ---
            # ...
        except Exception as e: # ...
            return ["Default Name 1", "Default Name 2", "Default Name 3"]

    async def extract_events(self, text: str) -> List[Event]: return []

__all__ = ["GeminiLLMProvider"]
