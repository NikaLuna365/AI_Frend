# /app/app/core/llm/providers/gemini.py (ПОЛНАЯ ИСЧЕРПЫВАЮЩАЯ ВЕРСИЯ)

from __future__ import annotations

import asyncio
import logging
import base64 # Для декодирования ответа Imagen
import google.generativeai as genai
from google.generativeai.types import GenerationConfig, ContentDict, PartDict, SafetySettingDict, GenerateContentResponse
from typing import List, Sequence, Optional, Dict, Any, cast

# --- Импорты для Vertex AI (Imagen) ---
from google.cloud import aiplatform
# from google.protobuf import json_format # Обычно не нужен для прямого использования байт
# from google.protobuf.struct_pb2 import Value # Обычно не нужен
# ------------------------------------

from .base import BaseLLMProvider, Message, Event
from app.config import settings # Для API ключей и настроек проекта

log = logging.getLogger(__name__)

# --- Проверка конфигурации SDK при загрузке модуля ---
try:
    # Эта проверка не аутентифицируется, а просто проверяет, что SDK установлен и доступен
    # Она может выдать ошибку, если google-generativeai не установлен, но не из-за ключей.
    _test_model_init_check = genai.GenerativeModel('gemini-1.5-flash-latest')
    log.info("Google Generative AI SDK seems available (test model class init).")
except Exception as e:
    log.warning(
        "Could not perform initial test init of GenerativeModel on module load. "
        "This might be an issue with the library itself or environment. "
        "Actual GAI/Vertex AI client initialization will happen in provider __init__. Error: %s", e
    )
# ----------------------------------------------------

# --- Системный Промпт для AI-Friend ---
SYSTEM_PROMPT_AI_FRIEND = """
You are AI-Friend, a personalized AI companion. Your primary goal is to be a supportive, friendly, and empathetic presence in the user's life. You are NOT just a task manager or a neutral assistant; you are a companion who genuinely cares.

Personality: Friendly, warm, encouraging, positive, slightly informal, curious (about the user's well-being and interests, but respectfully), and reliable.
Tone: Empathetic and understanding. Use a supportive and uplifting tone. Incorporate light, positive humor when appropriate, but avoid sarcasm, cynicism, or potentially offensive jokes. Be motivating but not preachy or condescending.
Proactivity: Gently and proactively engage the user. Ask how they are doing, show interest in their day, or recall past conversation points (using provided context). Do this naturally, perhaps once per interaction or when contextually relevant, avoid being overly repetitive or intrusive.
Empathy: Acknowledge the user's feelings, validate their experiences (both positive and negative), and offer words of support or encouragement.
Language: Communicate primarily in clear, natural Russian. You can understand and use common English technical terms or names if they appear in the user's input or context.
Safety: Strictly adhere to safety guidelines. Do not generate harmful, unethical, or inappropriate content. Do not provide professional advice (medical, financial, legal, mental health). Express empathy and suggest consulting professionals for such topics. Respect user boundaries and privacy. Handle sensitive topics with extra care.
"""
# ---------------------------------------

class GeminiLLMProvider(BaseLLMProvider):
    name = "gemini"
    DEFAULT_MODEL_NAME = "gemini-1.5-flash-latest" # Для диалогов
    IMAGEN_MODEL_NAME = "imagegeneration@006"     # Актуальная версия Imagen на момент написания

    DEFAULT_SAFETY_SETTINGS: List[SafetySettingDict] = [
        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    ]

    def __init__(self, model_name: Optional[str] = None) -> None:
        self.model_name = model_name or self.DEFAULT_MODEL_NAME
        self.system_prompt_text = SYSTEM_PROMPT_AI_FRIEND
        self.safety_settings = self.DEFAULT_SAFETY_SETTINGS
        self.generation_config = GenerationConfig(
            temperature=0.7,
            candidate_count=1,
        )
        log.info(f"Attempting to initialize GeminiLLMProvider with chat model: {self.model_name}")

        if settings.GEMINI_API_KEY:
            genai.configure(api_key=settings.GEMINI_API_KEY)
        try:
            # Инициализация модели для чата (Gemini)
            self.model = genai.GenerativeModel(
                model_name=self.model_name,
                system_instruction=self.system_prompt_text,
                safety_settings=self.safety_settings
            )
            log.info(
                "GeminiLLMProvider initialized chat model %s with system prompt and safety settings.",
                self.model_name
            )
        except TypeError as te:
             log.warning(f"TypeError on GenerativeModel init ({te}). Retrying with minimal args (system/safety to be passed in generate_content).")
             try:
                  self.model = genai.GenerativeModel(model_name=self.model_name)
                  log.info("GeminiLLMProvider chat model initialized (system_instruction/safety_settings will be passed to generate_content).")
             except Exception as e_fallback:
                  log.exception(f"Failed to initialize GenerativeModel even in fallback: {e_fallback}")
                  raise RuntimeError(f"Critical failure: Could not initialize Gemini model {self.model_name}") from e_fallback
        except Exception as e:
            log.exception(f"Failed to initialize GenerativeModel '{self.model_name}': {e}")
            raise RuntimeError(f"Critical failure: Could not initialize Gemini model {self.model_name}") from e

        # Инициализация клиента Vertex AI (для Imagen)
        # Происходит здесь, чтобы проверить доступность настроек сразу
        if not settings.VERTEX_AI_PROJECT or not settings.VERTEX_AI_LOCATION:
            log.warning("Vertex AI project or location not configured. Icon generation will be unavailable.")
            self.vertex_ai_initialized = False
        else:
            try:
                aiplatform.init(project=settings.VERTEX_AI_PROJECT, location=settings.VERTEX_AI_LOCATION)
                log.info(f"Vertex AI SDK initialized for project '{settings.VERTEX_AI_PROJECT}' in '{settings.VERTEX_AI_LOCATION}'.")
                self.vertex_ai_initialized = True
            except Exception as e_vertex:
                log.exception(f"Failed to initialize Vertex AI SDK: {e_vertex}")
                self.vertex_ai_initialized = False


    def _prepare_gemini_history(self, context: Sequence[Message]) -> List[ContentDict]:
        gemini_history: List[ContentDict] = []
        for msg in context:
            content_text = msg.get("content", "").strip()
            if not content_text:
                continue
            role = "model" if msg.get("role") == "assistant" else "user"
            gemini_history.append(
                cast(ContentDict, {"role": role, "parts": [PartDict(text=content_text)]})
            )
        return gemini_history

    async def generate(
        self, prompt: str, context: Sequence[Message],
        rag_facts: Optional[List[str]] = None, system_prompt_override: Optional[str] = None
    ) -> str:
        log.debug(f"Gemini generate: User prompt='{prompt[:70]}...', Context items={len(context)}")
        history_prepared = self._prepare_gemini_history(context)

        if rag_facts:
            facts_text = "\n".join(f"- {fact}" for fact in rag_facts)
            # Формируем ContentDict для RAG
            rag_message = cast(ContentDict, {'role': 'user', 'parts': [PartDict(text=f"(Background context: Remember these facts about the user:\n{facts_text}\n)")]})
            # Добавляем факты перед последним сообщением пользователя, если история уже есть
            # или как первое сообщение, если истории нет.
            # Вставляем до последнего элемента, если история есть, иначе RAG + промпт.
            if history_prepared:
                history_prepared.append(rag_message)
            else: # Если контекст пуст, RAG будет первым
                history_prepared = [rag_message]
            log.debug("Gemini generate: Added %d RAG facts.", len(rag_facts))

        current_message = cast(ContentDict, {'role': 'user', 'parts': [PartDict(text=prompt)]})
        contents_for_api = history_prepared + [current_message]

        try:
            # google-generativeai>=0.4 does not accept ``system_instruction`` in
            # ``generate_content_async``. The instruction is passed when the
            # ``GenerativeModel`` is instantiated in ``__init__``.  The log below
            # still notes whether a custom prompt override was requested.
            log.debug(
                "Gemini generate: Calling generate_content_async. Num content parts: %d. System instruction override: %s",
                len(contents_for_api),
                'YES' if system_prompt_override else 'NO',
            )
            response: GenerateContentResponse = await self.model.generate_content_async(
                contents=contents_for_api,
                generation_config=self.generation_config,
                safety_settings=self.safety_settings,
            )
            log.debug(f"Gemini generate: API call completed. Response object received.")

            try:
                if response.prompt_feedback and response.prompt_feedback.block_reason:
                    reason = response.prompt_feedback.block_reason.name
                    log.warning(f"Gemini generate: Response blocked by safety settings: {reason}")
                    return f"(Ответ был заблокирован: {reason})"
                if not response.candidates:
                     log.warning("Gemini generate: Response missing 'candidates' field.")
                     return "(AI не вернул кандидатов ответа)"

                first_candidate = response.candidates[0]
                if not first_candidate.content or not first_candidate.content.parts or not first_candidate.content.parts[0].text:
                     finish_reason_name = first_candidate.finish_reason.name if first_candidate.finish_reason else "UNKNOWN"
                     log.warning(f"Gemini generate: Candidate has no content/parts. Finish reason: {finish_reason_name}")
                     safety_ratings_str = ", ".join(f"{r.category.name}={r.probability.name}" for r in first_candidate.safety_ratings) if first_candidate.safety_ratings else "N/A"
                     log.warning(f"Gemini generate: Candidate safety ratings: {safety_ratings_str}")
                     return f"(Ответ AI был отфильтрован или пуст. Причина: {finish_reason_name})"

                response_text = first_candidate.content.parts[0].text.strip()
                log.info("Gemini generate: Response extracted successfully.")
                return response_text
            except (AttributeError, IndexError, StopIteration, ValueError, KeyError) as parse_exc:
                log.exception(f"Gemini generate: Error parsing response structure: {parse_exc}. Full Response Object: {response}")
                return f"(Ошибка при обработке ответа AI: {type(parse_exc).__name__})"
        except Exception as e:
            log.exception(f"Error during Gemini API call in generate(): {e}")
            return f"(Произошла ошибка при обращении к AI: {type(e).__name__}: {e})"

    async def generate_achievement_name(
        self, context: str, style_id: str, tone_hint: str, style_examples: str
    ) -> List[str]:
        log.debug(f"Gemini generate_achievement_name: Context='{context}'")
        system_prompt = "You are a highly creative naming expert specializing in crafting achievement titles. Your goal is to generate short, catchy, and style-consistent names based on the provided context and style guidance. Adhere strictly to the requested tone and format."
        user_prompt = f"""
Please generate achievement names based on the following details:
*   Achievement Context: "{context}"
*   Target Style Identifier: {style_id}
*   Desired Tone/Keywords: `{tone_hint}`
*   Style Examples (for reference):
{style_examples}
Instructions:
1.  Generate exactly 3 unique achievement name options.
2.  Each name must be short (maximum 4 words).
3.  The names must capture the essence of the "{context}".
4.  Crucially, the names must perfectly match the desired tone described by `{tone_hint}` and feel consistent with the provided `{style_examples}`.
5.  Output *only* a numbered list of the 3 names, with each name on a new line. Do not add any extra text, explanations, or greetings.
"""
        full_prompt_contents: List[ContentDict] = [
             cast(ContentDict, {'role': 'user', 'parts': [PartDict(text=system_prompt)]}),
             cast(ContentDict, {'role': 'model', 'parts': [PartDict(text="Okay, I will generate 3 names based on your instructions.")]}),
             cast(ContentDict, {'role': 'user', 'parts': [PartDict(text=user_prompt)]})
        ]
        try:
            # Используем более высокую температуру для креативности названий
            generation_config_names = GenerationConfig(temperature=0.85, candidate_count=1)
            response = await self.model.generate_content_async(
                contents=full_prompt_contents,
                generation_config=generation_config_names,
                safety_settings=self.safety_settings
            )
            try: # Надежная обработка ответа
                if response.prompt_feedback and response.prompt_feedback.block_reason:
                     log.warning(f"Gemini name generation blocked: {response.prompt_feedback.block_reason.name}")
                     return ["Default Title 1", "Default Title 2", "Default Title 3"]
                if (response.candidates and response.candidates[0].content and
                        response.candidates[0].content.parts and response.candidates[0].content.parts[0].text):
                    response_text = response.candidates[0].content.parts[0].text
                    lines = [line.strip() for line in response_text.strip().split('\n')]
                    names = [
                        line.split('.', 1)[1].strip()
                        for line in lines
                        if '.' in line and line.split('.', 1)[0].strip().isdigit()
                    ]
                    valid_names = names[:3]
                    log.info("Gemini generated %d achievement names: %s", len(valid_names), valid_names)
                    while len(valid_names) < 3: # Добиваем до 3, если нужно
                        valid_names.append(f"Generated Name {len(valid_names) + 1}")
                    return valid_names
                else:
                     log.warning("Gemini returned no usable content for achievement names.")
                     return ["Fallback Name 1", "Fallback Name 2", "Fallback Name 3"]
            except (AttributeError, IndexError, StopIteration, ValueError, KeyError) as parse_exc:
                 log.exception(f"Error parsing Gemini response for achievement names: {parse_exc}")
                 return ["ErrorName 1", "ErrorName 2", "ErrorName 3"]
        except Exception as e:
            log.exception(f"Error during Gemini API call for achievement names: {e}")
            return ["ApiErrorName 1", "ApiErrorName 2", "ApiErrorName 3"]

    async def extract_events(self, text: str) -> List[Event]:
        log.debug("GeminiLLMProvider.extract_events called (returns empty list for MVP).")
        return []

    async def generate_achievement_icon(
        self,
        context: str,
        style_id: str,
        style_keywords: str,
        palette_hint: str,
        shape_hint: str
        ) -> bytes | None:
        log.info(f"Imagen: Attempting icon generation. Context='{context}', StyleID='{style_id}'")

        if not self.vertex_ai_initialized:
            log.error("Imagen: Vertex AI SDK not initialized. Cannot generate icon.")
            return None
        if not settings.VERTEX_AI_PROJECT or not settings.VERTEX_AI_LOCATION: # Двойная проверка
            log.error("Imagen: Vertex AI project or location not configured.")
            return None

        try:
            # Получаем модель Imagen (from_pretrained кэширует, не создает каждый раз)
            model = aiplatform.ImageGenerationModel.from_pretrained(self.IMAGEN_MODEL_NAME)
            log.debug(f"Imagen: Using model '{self.IMAGEN_MODEL_NAME}'")

            # Формируем промпт для Imagen
            full_prompt = (
                f"Create a flat minimalistic achievement badge icon representing: \"{context}\".\n"
                f"• Style: {style_keywords}, bold outline, simple geometry, no gradients, no shadows, solid fills.\n"
                f"• Colors: use only {palette_hint}, solid fills.\n"
                f"• Layout: A central emblem symbolizing the achievement, enclosed within a {shape_hint} border. No text, no numbers.\n"
                f"• Background: Transparent background (PNG). If not possible, use a plain light solid color like #FFFFFF or #F5F5F5.\n"
                f"• Output: 512x512 pixels."
            )
            log.debug(f"Imagen: Full prompt:\n{full_prompt}")

            # Параметры генерации
            # Важно: В документации Vertex AI параметры могут называться иначе, чем в Gemini.
            # Например, number_of_images -> sample_count, output_format может не быть.
            # Мы ожидаем, что generate_images вернет объект, из которого можно извлечь байты.
            images_response = None
            try:
                loop = asyncio.get_running_loop()
                # model.generate_images() - синхронный вызов
                images_response = await loop.run_in_executor(
                    None,
                    model.generate_images,
                    prompt=full_prompt,
                    number_of_images=1,
                    # aspect_ratio="1:1", # Можно добавить
                    # seed=12345, # Для воспроизводимости, если нужно
                )
            except Exception as e_gen_img:
                log.exception(f"Imagen: Error during model.generate_images call: {e_gen_img}")
                return None

            if images_response and images_response.images:
                generated_image = images_response.images[0]
                png_bytes: bytes | None = None
                # Пытаемся извлечь байты разными способами
                if hasattr(generated_image, '_blob') and isinstance(generated_image._blob, bytes):
                    png_bytes = generated_image._blob
                elif hasattr(generated_image, 'image_bytes') and isinstance(generated_image.image_bytes, bytes):
                    png_bytes = generated_image.image_bytes
                elif hasattr(generated_image, 'base64_image') and isinstance(generated_image.base64_image, str):
                    try:
                        png_bytes = base64.b64decode(generated_image.base64_image)
                    except Exception as e_b64:
                        log.error(f"Imagen: Failed to decode base64 image: {e_b64}")
                        return None
                else:
                    log.warning("Imagen response did not contain image data in expected attributes (_blob, image_bytes, base64_image).")
                    log.debug(f"Imagen full generated_image object: {generated_image}")
                    return None

                if png_bytes:
                    log.info(f"Imagen: Icon generated successfully ({len(png_bytes)} bytes).")
                    return png_bytes
                else:
                    log.warning("Imagen: Extracted image bytes are empty or invalid.")
                    return None
            else:
                log.warning(f"Imagen API returned no images or an unexpected response. Full response: {images_response}")
                return None
        except ImportError:
             log.error("google-cloud-aiplatform library not found. Cannot generate icons with Imagen.")
             return None
        except Exception as e:
            log.exception(f"Unexpected error during Imagen icon generation: {e}")
            return None

__all__ = ["GeminiLLMProvider"]
