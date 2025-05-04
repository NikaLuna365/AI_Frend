# /app/app/core/llm/providers/gemini.py (Добавляем generate_achievement_icon)

from __future__ import annotations

import logging
import base64 # Для декодирования ответа Imagen
import google.generativeai as genai
from google.generativeai.types import GenerationConfig, ContentDict, PartDict, SafetySettingDict
from typing import List, Sequence, Optional, Dict, Any, cast

# --- ИМПОРТЫ ДЛЯ VERTEX AI (IMAGEN) ---
from google.cloud import aiplatform
from google.protobuf import json_format # Для работы с ответом API
from google.protobuf.struct_pb2 import Value
# ------------------------------------

from .base import BaseLLMProvider, Message, Event
from app.config import settings

log = logging.getLogger(__name__)

# --- Конфигурация SDK и Системный Промпт (как в предыдущей версии) ---
# ...

class GeminiLLMProvider(BaseLLMProvider):
    name = "gemini"
    DEFAULT_MODEL_NAME = "gemini-1.5-flash-latest"
    # --- ID Модели Imagen (можно вынести в config) ---
    IMAGEN_MODEL_NAME = "imagegeneration@006" # Укажите актуальную версию модели
    # -------------------------------------------------

    # ... (__init__, _prepare_gemini_history, generate, extract_events, generate_achievement_name) ...
    # --- Код предыдущих методов без изменений ---
    # ...

    # --- НОВЫЙ МЕТОД: Генерация Иконки ---
    async def generate_achievement_icon(
        self,
        context: str, # Текст для генерации иконки (тема/промпт)
        style_id: str, # Идентификатор стиля (для выбора пресета/промпта)
        style_keywords: str, # Ключевые слова для описания стиля
        palette_hint: str, # Подсказка по цветам
        shape_hint: str # Подсказка по форме
        ) -> bytes | None:
        """
        Генерирует иконку ачивки (PNG байты) с помощью Vertex AI Imagen API.

        Args:
            context (str): Основная тема/описание ачивки для изображения.
            style_id (str): Идентификатор стиля (пока не используется).
            style_keywords (str): Ключевые слова для промпта Imagen.
            palette_hint (str): Подсказка по цветам для промпта Imagen.
            shape_hint (str): Подсказка по форме для промпта Imagen.

        Returns:
            bytes | None: PNG изображение в виде байтов или None в случае ошибки.
        """
        log.info(f"GeminiProvider (Imagen): Generating icon. Context: '{context}'")

        # Проверяем наличие необходимых настроек Vertex AI
        if not settings.VERTEX_AI_PROJECT or not settings.VERTEX_AI_LOCATION:
            log.error("VERTEX_AI_PROJECT or VERTEX_AI_LOCATION not configured in settings.")
            return None

        try:
            # Инициализируем клиента Vertex AI
            # Аутентификация происходит через GOOGLE_APPLICATION_CREDENTIALS
            aiplatform.init(project=settings.VERTEX_AI_PROJECT, location=settings.VERTEX_AI_LOCATION)

            # Получаем модель Imagen
            # Используем Model Garden для получения ссылки на модель
            model = aiplatform.ImageGenerationModel.from_pretrained(self.IMAGEN_MODEL_NAME)

            # --- Формируем Промпт для Imagen на основе ТЗ №3 ---
            # Собираем детали стиля в одну строку
            style_details = f"{style_keywords}. Colors: {palette_hint}. Border shape: {shape_hint}."
            # Основной промпт
            prompt = f"""
Create a flat minimalistic achievement badge icon representing '{context}'.
Strictly adhere to these visual characteristics: {style_details}.
Style: bold outline, simple geometry, no gradients, no shadows, solid fills.
Layout: A central emblem symbolizing the achievement concept, enclosed within the specified border shape.
Absolutely no text or numbers within the icon.
Clean edges suitable for web use.
"""
            # ----------------------------------------------------
            log.debug(f"Imagen prompt: {prompt}")

            # --- Параметры генерации Imagen ---
            # Возвращаем 1 изображение размером 512x512 в формате PNG (base64)
            imagen_parameters = {
                "number_of_images": 1,
                "output_format": "png", # Запрашиваем PNG
                "output_storage_uri": None, # Не сохраняем в GCS через API, получим байты
                "base_image": None,
                # Дополнительные параметры стиля/качества, если нужны
                # "aspect_ratio": "1:1", # Обычно иконки квадратные
                 "guidance_scale": 7 # Примерный параметр для стиля
            }
            # ----------------------------------

            # --- Асинхронный вызов Imagen API ---
            # Используем predict_async или images_generate_async, в зависимости от версии SDK/модели
            # В новых версиях часто используется метод predict/generate напрямую
            # Обернем синхронный вызов predict в run_in_executor для асинхронности
            loop = asyncio.get_running_loop()
            response = await loop.run_in_executor(
                None, # Дефолтный executor
                lambda: model.generate_images(
                    prompt=prompt,
                    # Дополнительные параметры передаем здесь
                    **imagen_parameters
                )
            )
            # -----------------------------------

            if response and response.images:
                # Ответ содержит список объектов изображений. Берем первый.
                generated_image = response.images[0]
                # Изображение возвращается как base64 строка в _blob
                png_bytes = generated_image._blob # Получаем байты PNG
                log.info(f"Imagen generated icon successfully ({len(png_bytes)} bytes).")
                return png_bytes
            else:
                log.warning("Imagen API returned no images or an unexpected response.")
                return None

        except ImportError:
             log.error("google-cloud-aiplatform library not found. Cannot generate icons.")
             return None
        except Exception as e:
            log.exception(f"Error during Imagen API call: {e}")
            return None
    # -------------------------------

__all__ = ["GeminiLLMProvider"]
