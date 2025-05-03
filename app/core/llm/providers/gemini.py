# /app/app/core/llm/providers/gemini.py (Реализация для Фазы 2)

from __future__ import annotations

import logging
import google.generativeai as genai
from google.generativeai.types import GenerationConfig, SafetySetting, HarmCategory # Для настроек генерации и безопасности
from typing import List, Sequence, Optional, Dict, Any # Добавляем Dict, Any

from .base import BaseLLMProvider, Message, Event # Импортируем базовый класс и типы
from app.config import settings # Нужен для определения, сконфигурирован ли ключ/SA

log = logging.getLogger(__name__)

# --- Конфигурация Gemini ---
# Настраиваем Google API ключ ИЛИ сервисный аккаунт при загрузке модуля.
# Библиотека google-auth автоматически ищет GOOGLE_APPLICATION_CREDENTIALS,
# поэтому явной конфигурации здесь может не требоваться, если переменная задана.
# Оставим проверку для ясности.
try:
    # Проверяем, инициализируется ли клиент по умолчанию (через SA или API Key)
    # Это не обязательно, но может помочь отловить ошибки конфигурации раньше.
    # genai.configure() # Если используется API Key, он уже был вызван
    # Просто создадим модель для проверки доступа
    _test_model = genai.GenerativeModel('gemini-1.5-flash-latest') # Используем доступную модель
    # Можно даже сделать тестовый вызов, но это замедлит старт:
    # _test_model.generate_content("test", generation_config=GenerationConfig(candidate_count=1))
    log.info("Google Generative AI SDK seems configured correctly (via GOOGLE_APPLICATION_CREDENTIALS or API Key).")
except Exception as e:
    log.exception("Failed to initialize/configure Google Generative AI SDK on module load: %s", e)
    # Не будем падать здесь, ошибка возникнет при инициализации провайдера


# --- Системный Промпт (из ТЗ промпт-инженера) ---
# Выносим в константу для удобства
SYSTEM_PROMPT_AI_FRIEND = """
You are AI-Friend, a personalized AI companion. Your primary goal is to be a supportive, friendly, and empathetic presence in the user's life. You are NOT just a task manager or a neutral assistant; you are a companion who genuinely cares.

Personality: Friendly, warm, encouraging, positive, slightly informal, curious (about the user's well-being and interests, but respectfully), and reliable.
Tone: Empathetic and understanding. Use a supportive and uplifting tone. Incorporate light, positive humor when appropriate, but avoid sarcasm, cynicism, or potentially offensive jokes. Be motivating but not preachy or condescending.
Proactivity: Gently and proactively engage the user. Ask how they are doing, show interest in their day, or recall past conversation points (using provided context). Do this naturally, perhaps once per interaction or when contextually relevant, avoid being overly repetitive or intrusive.
Empathy: Acknowledge the user's feelings, validate their experiences (both positive and negative), and offer words of support or encouragement.
Language: Communicate primarily in clear, natural Russian. You can understand and use common English technical terms or names if they appear in the user's input or context.
Safety: Strictly adhere to safety guidelines. Do not generate harmful, unethical, or inappropriate content. Do not provide professional advice (medical, financial, legal, mental health). Express empathy and suggest consulting professionals for such topics. Respect user boundaries and privacy. Handle sensitive topics with extra care.
"""
# -----------------------------------------------------


class GeminiLLMProvider(BaseLLMProvider):
    """
    LLM Provider implementation using Google Gemini API (Async).
    """
    name = "gemini"
    DEFAULT_MODEL_NAME = "gemini-1.5-flash-latest" # Используем Flash для скорости/стоимости

    # --- Настройки Безопасности Gemini ---
    # Блокируем контент с высокой вероятностью небезопасности по всем категориям
    DEFAULT_SAFETY_SETTINGS = [
        SafetySetting(category=HarmCategory.HARM_CATEGORY_HARASSMENT, threshold=HarmCategory.HARM_BLOCK_THRESHOLD_MEDIUM_AND_ABOVE),
        SafetySetting(category=HarmCategory.HARM_CATEGORY_HATE_SPEECH, threshold=HarmCategory.HARM_BLOCK_THRESHOLD_MEDIUM_AND_ABOVE),
        SafetySetting(category=HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT, threshold=HarmCategory.HARM_BLOCK_THRESHOLD_MEDIUM_AND_ABOVE),
        SafetySetting(category=HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT, threshold=HarmCategory.HARM_BLOCK_THRESHOLD_MEDIUM_AND_ABOVE),
    ]
    # --------------------------------------

    def __init__(self, model_name: Optional[str] = None) -> None:
        """
        Initializes the Gemini provider and the generative model client.
        """
        self.model_name = model_name or self.DEFAULT_MODEL_NAME
        try:
            # Создаем клиент для модели с системным промптом и настройками безопасности
            self.model = genai.GenerativeModel(
                self.model_name,
                # system_instruction=SYSTEM_PROMPT_AI_FRIEND, # ВАЖНО: Передаем системный промпт
                # safety_settings=self.DEFAULT_SAFETY_SETTINGS # Применяем настройки безопасности
            )
            # Конфигурация генерации (можно настраивать)
            self.generation_config = GenerationConfig(
                temperature=0.7, # Баланс между креативностью и предсказуемостью
                # top_p=0.9,
                # top_k=40,
                candidate_count=1, # Нам нужен только один вариант ответа
                # max_output_tokens=2048, # Ограничение длины ответа
            )
            log.info(
                "GeminiLLMProvider initialized with model: %s, "
                "System Prompt set, Safety Settings applied.",
                self.model_name
            )
        except Exception as e:
            log.exception("Failed to initialize GenerativeModel '%s': %s", self.model_name, e)
            # Эта ошибка критична, приложение не сможет использовать LLM
            raise RuntimeError(f"Failed to initialize Gemini model {self.model_name}") from e

    def _prepare_gemini_history(self, context: Sequence[Message], current_prompt: Optional[str] = None) -> List[Dict[str, Any]]:
        """Вспомогательная функция для преобразования истории в формат Gemini."""
        gemini_history = []
        for msg in context:
            # Пропускаем пустые сообщения
            content = msg.get("content", "").strip()
            if not content:
                continue
            # Преобразуем роль 'assistant' в 'model'
            role = "model" if msg.get("role") == "assistant" else "user"
            gemini_history.append({'role': role, 'parts': [content]})

        # Добавляем текущий prompt пользователя, если он есть
        if current_prompt:
             gemini_history.append({'role': 'user', 'parts': [current_prompt]})

        return gemini_history


    async def generate(
        self,
        prompt: str,
        context: Sequence[Message],
        # Добавляем параметры для RAG и системного промпта
        rag_facts: Optional[List[str]] = None,
        system_prompt_override: Optional[str] = None
        ) -> str:
        """
        Асинхронно генерирует ответ с использованием Gemini.

        Args:
            prompt (str): Последнее сообщение пользователя.
            context (Sequence[Message]): История диалога.
            rag_facts (Optional[List[str]]): Список релевантных фактов из памяти (RAG).
            system_prompt_override (Optional[str]): Возможность переопределить системный промпт.

        Returns:
            str: Сгенерированный ответ.
        """
        log.debug("Gemini: Generating response. Prompt: '%.50s...'", prompt)

        # --- Подготовка Контекста ---
        # Формируем историю для API Gemini
        gemini_history = self._prepare_gemini_history(context, prompt)

        # --- Добавляем Факты RAG (если есть) ---
        # Факты можно добавить как отдельное сообщение "user" перед последним промптом
        # или включить в системный промпт. Добавим как сообщение.
        if rag_facts:
            facts_text = "\n".join(f"- {fact}" for fact in rag_facts)
            # Вставляем факты перед последним сообщением пользователя
            rag_message = {'role': 'user', 'parts': [f"(Вспомни эти факты о пользователе:\n{facts_text}\n)"]}
            if len(gemini_history) > 1:
                 gemini_history.insert(-1, rag_message)
            else: # Если истории нет, вставляем перед единственным сообщением
                 gemini_history.insert(0, rag_message)
            log.debug("Gemini: Added %d RAG facts to context.", len(rag_facts))
        # --------------------------------------

        # --- Определяем Системный Промпт ---
        system_instruction = system_prompt_override or SYSTEM_PROMPT_AI_FRIEND
        # ----------------------------------

        try:
            # --- Вызов Gemini API ---
            # Используем generate_content_async, передавая историю и настройки
            response = await self.model.generate_content_async(
                contents=gemini_history,
                generation_config=self.generation_config,
                safety_settings=self.DEFAULT_SAFETY_SETTINGS,
                # ВАЖНО: Системный промпт передается отдельно для новых моделей
                system_instruction=system_instruction
            )
            # ------------------------

            if response and response.text:
                log.debug("Gemini response received successfully.")
                return response.text.strip() # Убираем лишние пробелы
            else:
                reason = "Unknown reason"
                if response and response.prompt_feedback:
                    reason = f"Blocked by safety settings ({response.prompt_feedback.block_reason})"
                elif not response:
                     reason = "Empty response object"
                log.warning("Gemini returned an empty or blocked response. Reason: %s", reason)
                return f"(Я не могу сгенерировать ответ сейчас. Причина: {reason})"

        except Exception as e:
            log.exception("Error during Gemini API call in generate(): %s", e)
            # Возвращаем user-friendly сообщение об ошибке
            return f"(Произошла ошибка при обращении к AI: {type(e).__name__})"


    async def extract_events(self, text: str) -> List[Event]:
        """Извлечение событий - НЕ РЕАЛИЗОВАНО в MVP."""
        log.debug("GeminiLLMProvider.extract_events called (returns empty list).")
        return []


    async def generate_achievement_name(
        self,
        context: str,
        style_id: str,
        tone_hint: str,
        style_examples: str
        ) -> List[str]:
        """
        Асинхронно генерирует названия ачивок с помощью Gemini.
        """
        log.debug("Gemini: Generating achievement name. Context: '%s'", context)

        # --- Формируем Промпт для Названий (из ТЗ #3) ---
        system_prompt = "You are a highly creative naming expert specializing in crafting achievement titles..." # Сокращено для примера
        user_prompt = f"""
        ... (Полный текст промпта из ответа #38, секция 2) ...
        Achievement Description: "{context}"
        Target Style Identifier: {style_id}
        Desired Tone/Keywords: `{tone_hint}`
        Style Examples (for reference):
        {style_examples}
        ... (Остальные инструкции) ...
        """
        # Gemini предпочитает явное разделение user/model
        full_prompt_contents = [
             {'role': 'user', 'parts': [system_prompt]},
             {'role': 'model', 'parts': ["Okay, provide the achievement details."]}, # Краткий ответ модели
             {'role': 'user', 'parts': [user_prompt]}
        ]
        # --------------------------------------------

        try:
            # Используем ту же модель, но можно указать другую конфигурацию генерации, если нужно
            generation_config_names = GenerationConfig(temperature=0.8, candidate_count=1) # Чуть более креативно

            response = await self.model.generate_content_async(
                contents=full_prompt_contents,
                generation_config=generation_config_names,
                safety_settings=self.DEFAULT_SAFETY_SETTINGS
                # Системный промпт здесь не нужен, он задан в user_prompt
            )

            if response and response.text:
                # Парсим ответ (ожидаем нумерованный список)
                lines = [line.strip() for line in response.text.strip().split('\n')]
                names = [
                    line.split('.', 1)[1].strip()
                    for line in lines
                    if '.' in line and line.split('.', 1)[0].strip().isdigit()
                ]
                valid_names = names[:3] # Берем не более 3
                log.info("Gemini generated %d achievement names: %s", len(valid_names), valid_names)
                while len(valid_names) < 3: # Добиваем до 3 дефолтными, если нужно
                    valid_names.append(f"Default Name {len(valid_names) + 1}")
                return valid_names
            else:
                reason = "Unknown reason"
                if response and response.prompt_feedback:
                    reason = f"Blocked by safety settings ({response.prompt_feedback.block_reason})"
                log.warning("Gemini returned empty/blocked response for achievement names. Reason: %s", reason)
                return ["Default Name 1", "Default Name 2", "Default Name 3"]

        except Exception as e:
            log.exception("Error during Gemini API call for achievement names: %s", e)
            return ["Default Name 1", "Default Name 2", "Default Name 3"]

    # generate_achievement_icon - будет реализован отдельно, т.к. использует Imagen/Vertex AI

__all__: list[str] = ["GeminiLLMProvider"]
