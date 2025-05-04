# /app/app/core/llm/providers/gemini.py (Версия v6 - Исправлено форматирование истории)

from __future__ import annotations

import logging
import google.generativeai as genai
# Используем явные типы из библиотеки для большей надежности
from google.generativeai.types import GenerationConfig, ContentDict, PartDict, SafetySettingDict
from typing import List, Sequence, Optional, Dict, Any, cast

from .base import BaseLLMProvider, Message, Event # Убедимся, что Message импортирован
from app.config import settings

log = logging.getLogger(__name__)

# ... (Проверка конфигурации SDK и Системный Промпт без изменений) ...
SYSTEM_PROMPT_AI_FRIEND = """..."""

class GeminiLLMProvider(BaseLLMProvider):
    name = "gemini"
    DEFAULT_MODEL_NAME = "gemini-1.5-flash-latest"
    DEFAULT_SAFETY_SETTINGS: List[SafetySettingDict] = [
        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        # ... (остальные настройки безопасности) ...
    ]

    def __init__(self, model_name: Optional[str] = None) -> None:
        # ... (Код __init__ без изменений - system_instruction в GenerativeModel) ...
        self.model_name = model_name or self.DEFAULT_MODEL_NAME
        self.system_prompt = SYSTEM_PROMPT_AI_FRIEND
        self.safety_settings = self.DEFAULT_SAFETY_SETTINGS
        self.generation_config = GenerationConfig(temperature=0.7, candidate_count=1)
        try:
            self.model = genai.GenerativeModel(
                model_name=self.model_name,
                system_instruction=self.system_prompt,
                safety_settings=self.safety_settings # Передаем здесь, если конструктор принимает
            )
            log.info(...)
        except TypeError: # Fallback, если safety_settings не принимаются в конструкторе
             log.warning(...)
             self.model = genai.GenerativeModel(
                  model_name=self.model_name,
                  system_instruction=self.system_prompt
             )
             log.info("GeminiLLMProvider initialized (safety/generation config in generate_content).")
        except Exception as e:
            log.exception(...)
            raise RuntimeError(...) from e


    # --- ИСПРАВЛЕННАЯ ВЕРСИЯ ФОРМАТИРОВАНИЯ ---
    def _prepare_gemini_history(self, context: Sequence[Message]) -> List[ContentDict]:
        """Преобразует историю в формат Gemini List[ContentDict]."""
        gemini_history: List[ContentDict] = []
        for msg in context:
            content = msg.get("content", "").strip()
            if not content:
                continue # Пропускаем пустые сообщения
            # Преобразуем роль 'assistant' в 'model'
            role = "model" if msg.get("role") == "assistant" else "user"
            # Создаем словарь ContentDict с правильной структурой parts
            gemini_history.append(
                # Используем cast для помощи mypy, если нужно
                cast(ContentDict, {"role": role, "parts": [PartDict(text=content)]})
                # ИЛИ явно создаем словари:
                # {"role": role, "parts": [{"text": content}]}
            )
        return gemini_history
    # ------------------------------------------

    async def generate(
        self, prompt: str, context: Sequence[Message],
        rag_facts: Optional[List[str]] = None, system_prompt_override: Optional[str] = None
    ) -> str:
        log.debug("Gemini: Generating response...")

        # Готовим историю и добавляем RAG, если есть
        history_prepared = self._prepare_gemini_history(context)
        if rag_facts:
            facts_text = "\n".join(f"- {fact}" for fact in rag_facts)
            # Используем явное создание словаря PartDict
            rag_message = cast(ContentDict, {'role': 'user', 'parts': [PartDict(text=f"(Context:\n{facts_text}\n)")]})
            history_prepared.append(rag_message)
            log.debug("Gemini: Added %d RAG facts.", len(rag_facts))

        # Добавляем текущий промпт пользователя как последний элемент
        current_message = cast(ContentDict, {'role': 'user', 'parts': [PartDict(text=prompt)]})
        contents_for_api = history_prepared + [current_message]

        # Используем системный промпт из __init__
        # system_instruction = system_prompt_override or self.system_prompt # Не нужен здесь

        try:
            # --- Вызов API (без system_instruction как аргумента) ---
            log.debug(f"Calling generate_content_async with contents: {contents_for_api}") # Логируем передаваемые данные
            response = await self.model.generate_content_async(
                contents=contents_for_api,
                generation_config=self.generation_config,
                safety_settings=self.safety_settings
            )
            # ---------------------------------------------------------

            # --- Обработка ответа (без изменений) ---
            if response and response.text:
                log.debug("Gemini response received successfully.")
                return response.text.strip()
            else:
                reason = "Unknown reason"; # ... (код определения reason) ...
                log.warning("Gemini returned an empty or blocked response. Reason: %s", reason)
                return f"(Я не могу сгенерировать ответ сейчас. Причина: {reason})"
            # ---------------------------------------

        except Exception as e:
            # Логируем ошибку и тип передаваемых данных на всякий случай
            log.exception(f"Error during Gemini API call. Contents type: {type(contents_for_api)}. Error: {e}")
            return f"(Произошла ошибка при обращении к AI: {type(e).__name__})"

    # --- generate_achievement_name (оставляем как есть, т.к. там промпт уже форматировался) ---
    async def generate_achievement_name(
        self, context: str, style_id: str, tone_hint: str, style_examples: str
    ) -> List[str]:
        # ... (код без изменений, но вызов generate_content_async БЕЗ system_instruction) ...
        # ... (убедитесь, что full_prompt_contents имеет правильный формат List[ContentDict]) ...
        log.debug("Gemini: Generating achievement name...")
        system_prompt = "You are a highly creative naming expert..."
        user_prompt = f"""..."""
        # ПРОВЕРКА ФОРМАТА:
        full_prompt_contents: List[ContentDict] = [
             cast(ContentDict, {'role': 'user', 'parts': [PartDict(text=system_prompt)]}),
             cast(ContentDict, {'role': 'model', 'parts': [PartDict(text="Okay, provide the achievement details.")]}),
             cast(ContentDict, {'role': 'user', 'parts': [PartDict(text=user_prompt)]})
        ]
        try:
            generation_config_names = GenerationConfig(temperature=0.8, candidate_count=1)
            response = await self.model.generate_content_async(
                contents=full_prompt_contents, # Передаем отформатированный промпт
                generation_config=generation_config_names,
                safety_settings=self.safety_settings
            )
            # ... (обработка ответа) ...
            if response and response.text:
                # ... (парсинг имен) ...
                 return valid_names
            else:
                 # ... (обработка пустых/заблокированных) ...
                 return ["Default Name 1", "Default Name 2", "Default Name 3"]
        except Exception as e:
            log.exception(...)
            return ["Default Name 1", "Default Name 2", "Default Name 3"]


    async def extract_events(self, text: str) -> List[Event]: return []

__all__ = ["GeminiLLMProvider"]
