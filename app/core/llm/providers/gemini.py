# /app/app/core/llm/providers/gemini.py

from __future__ import annotations

import logging
import google.generativeai as genai
from typing import List, Sequence, Optional # Добавляем Optional

# Импортируем базовый класс и типы
from .base import BaseLLMProvider, Message, Event # Event пока не используем в generate
from app.config import settings # Для доступа к API ключу

log = logging.getLogger(__name__)

# Настраиваем Google API ключ при загрузке модуля
if settings.GEMINI_API_KEY:
    try:
        genai.configure(api_key=settings.GEMINI_API_KEY)
        log.info("Google Generative AI SDK configured successfully.")
    except Exception as e:
        log.exception("Failed to configure Google Generative AI SDK: %s", e)
        # Можно решить, критична ли эта ошибка при старте
        # raise RuntimeError("Gemini API Key configuration failed") from e
else:
    log.warning("GEMINI_API_KEY not found in settings. GeminiLLMProvider will not work.")


class GeminiLLMProvider(BaseLLMProvider):
    """
    LLM Provider implementation using Google Gemini API.
    Focuses on the 'generate' method for conversational chat.
    """
    name = "gemini"
    # Указываем модель Gemini (можно вынести в config)
    # Используем 'gemini-1.5-flash' как более быстрый и дешевый вариант для старта
    # или 'gemini-1.5-pro' для более высокого качества
    DEFAULT_MODEL_NAME = "gemini-1.5-flash-latest" # или gemini-1.5-pro-latest

    def __init__(self, model_name: Optional[str] = None) -> None:
        """
        Initializes the Gemini provider.

        Args:
            model_name (Optional[str]): The specific Gemini model to use.
                                        Defaults to DEFAULT_MODEL_NAME.
        """
        if not settings.GEMINI_API_KEY:
            log.error("Cannot initialize GeminiLLMProvider: GEMINI_API_KEY is missing.")
            # Если ключ отсутствует, инициализация не имеет смысла
            raise ValueError("GEMINI_API_KEY must be configured to use GeminiLLMProvider")

        self.model_name = model_name or self.DEFAULT_MODEL_NAME
        try:
            # Создаем клиент для конкретной модели
            self.model = genai.GenerativeModel(self.model_name)
            log.info("GeminiLLMProvider initialized with model: %s", self.model_name)
            # TODO: Можно добавить проверку доступности модели здесь (тестовый вызов)
        except Exception as e:
            log.exception("Failed to initialize GenerativeModel '%s': %s", self.model_name, e)
            raise RuntimeError(f"Failed to initialize Gemini model {self.model_name}") from e

    async def generate(self, prompt: str, context: Sequence[Message]) -> str:
        """
        Generates a response using the Gemini model based on the prompt and context.

        Args:
            prompt (str): The latest user message or query.
            context (Sequence[Message]): The preceding conversation history.
                                         Format: [{'role': 'user'/'assistant', 'content': '...'}, ...]

        Returns:
            str: The generated text response from the Gemini model.

        Raises:
            Exception: If the API call fails.
        """
        if not self.model: # pragma: no cover
            log.error("Gemini model not initialized, cannot generate.")
            return "Error: LLM not initialized."

        log.debug("Generating response with Gemini model '%s'. Prompt: '%.50s...'", self.model_name, prompt)

        # --- Формируем историю для Gemini API ---
        # Gemini ожидает формат: [{'role': 'user'/'model', 'parts': [text]}]
        # 'model' используется вместо 'assistant'.
        gemini_history = []
        for msg in context:
            role = "model" if msg.get("role") == "assistant" else "user"
            gemini_history.append({'role': role, 'parts': [msg.get("content", "")]})

        # Добавляем текущий prompt пользователя в конец истории
        gemini_history.append({'role': 'user', 'parts': [prompt]})
        # ---------------------------------------

        try:
            # --- Вызываем Gemini API асинхронно ---
            # Используем generate_content_async
            # TODO: Добавить системный промпт из ТЗ, если он есть для Gemini
            # response = await self.model.generate_content_async(
            #     gemini_history,
            #     # system_instruction="Ты - AI-Friend, дружелюбный помощник..." # Пример
            # )

            # --- ИЛИ: Используем Chat Session для более простого управления историей ---
            # (Предпочтительный вариант для диалогов)
            chat_session = self.model.start_chat(history=gemini_history[:-1]) # Начинаем с истории БЕЗ последнего сообщения
            response = await chat_session.send_message_async(prompt) # Отправляем последнее сообщение
            # -------------------------------------------------------------------

            # Проверяем наличие текста в ответе
            if response and response.text:
                log.debug("Gemini response received: '%.50s...'", response.text)
                return response.text
            else:
                # Обработка случая, когда ответ пустой или заблокирован safety settings
                log.warning("Gemini returned an empty or blocked response: %s", response.prompt_feedback if response else "N/A")
                # TODO: Возвращать более информативное сообщение пользователю
                safety_reason = "Blocked by safety settings" if response and response.prompt_feedback.block_reason else "Unknown reason"
                return f"(Ответ не может быть сгенерирован: {safety_reason})"

        except Exception as e:
            log.exception("Error during Gemini API call: %s", e)
            # TODO: Возвращать более user-friendly ошибку
            # Перебрасываем ошибку или возвращаем сообщение об ошибке
            # return f"Error communicating with LLM: {type(e).__name__}"
            raise e # Позволяем обработчику ошибок FastAPI разобраться

    async def extract_events(self, text: str) -> List[Event]:
        """
        Extracts calendar events from text using Gemini.
        (Placeholder - Not implemented for MVP Core AI focus)

        Args:
            text (str): Text to extract events from.

        Returns:
            List[Event]: List of extracted events.
        """
        log.warning("GeminiLLMProvider.extract_events is not implemented in this phase.")
        # TODO: Реализовать логику извлечения событий, если/когда понадобится
        # Это может потребовать отдельного вызова к Gemini с промптом на извлечение.
        return [] # Возвращаем пустой список для MVP

    async def generate_achievement_name(
        self,
        context: str,
        style_id: str,
        tone_hint: str,
        style_examples: str
        ) -> List[str]:
        """
        Generates achievement names using the Gemini model.

        Args:
            context (str): Achievement description/context.
            style_id (str): Style identifier.
            tone_hint (str): Tone keywords.
            style_examples (str): Examples in the target style.

        Returns:
            List[str]: A list of 3 generated names.

        Raises:
            Exception: If the API call fails.
        """
        log.debug("Generating achievement name with Gemini model '%s'. Context: '%s'", self.model_name, context)

        # Формируем промпт для генерации названий согласно ТЗ №3
        system_prompt = "You are a highly creative naming expert specializing in crafting achievement titles. Your goal is to generate short, catchy, and style-consistent names based on the provided context and style guidance. Adhere strictly to the requested tone and format."
        user_prompt = f"""
Please generate achievement names based on the following details:

*   **Achievement Context:** "{context}"
*   **Target Style Identifier:** {style_id}
*   **Desired Tone/Keywords:** `{tone_hint}`
*   **Style Examples (for reference):**
{style_examples}

**Instructions:**
1.  Generate exactly 3 unique achievement name options.
2.  Each name must be short (maximum 4 words).
3.  The names must capture the essence of the "{context}".
4.  Crucially, the names must perfectly match the desired tone described by `{tone_hint}` and feel consistent with the provided `{style_examples}`.
5.  Output *only* a numbered list of the 3 names, with each name on a new line. Do not add any extra text, explanations, or greetings.
"""
        full_prompt = [
            {'role': 'user', 'parts': [system_prompt]}, # Используем user роль для системного промпта Gemini
            {'role': 'model', 'parts': ["Okay, I understand. Provide the details and I will generate the names."]}, # Пример ответа модели
            {'role': 'user', 'parts': [user_prompt]}
        ]


        try:
            # Вызываем Gemini API
            # Используем модель, инициализированную в __init__
            response = await self.model.generate_content_async(full_prompt)

            if response and response.text:
                # Парсим ответ - ожидаем нумерованный список
                lines = [line.strip() for line in response.text.strip().split('\n')]
                # Извлекаем текст после номера и точки (e.g., "1. Name One" -> "Name One")
                names = [
                    line.split('.', 1)[1].strip()
                    for line in lines
                    if '.' in line and line.split('.', 1)[0].strip().isdigit()
                ]
                # Возвращаем только первые 3 найденных имени
                valid_names = names[:3]
                log.info("Gemini generated %d achievement names: %s", len(valid_names), valid_names)
                # Дополняем до 3 заглушками, если Gemini вернул меньше
                while len(valid_names) < 3:
                    valid_names.append(f"Default Name {len(valid_names) + 1}")
                return valid_names
            else:
                log.warning("Gemini returned empty or blocked response for achievement names.")
                return ["Default Name 1", "Default Name 2", "Default Name 3"] # Возвращаем дефолтные

        except Exception as e:
            log.exception("Error during Gemini API call for achievement names: %s", e)
            # Возвращаем дефолтные имена при ошибке
            return ["Default Name 1", "Default Name 2", "Default Name 3"]


    # generate_achievement_icon - НЕ реализуем здесь, т.к. это задача Imagen/Vertex AI
