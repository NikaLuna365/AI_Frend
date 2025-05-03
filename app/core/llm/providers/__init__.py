# /app/app/core/llm/providers/__init__.py (Обновленная версия)

from __future__ import annotations

import importlib
import logging
import sys
from typing import Dict, Type # Добавили Type

from app.config import settings # Нужен для определения провайдера
from .base import BaseLLMProvider # Импортируем базовый класс

# --- Получаем логгер ---
log = logging.getLogger(__name__)

# --- Функция ленивого импорта ---
def _lazy_import(module_suffix: str, class_name: str) -> Type[BaseLLMProvider]:
    """
    Импортирует класс провайдера по относительному пути модуля.

    Пример: _lazy_import(".gemini", "GeminiLLMProvider")

    Args:
        module_suffix (str): Относительный путь к модулю (начинается с точки).
        class_name (str): Имя класса провайдера внутри модуля.

    Returns:
        Type[BaseLLMProvider]: Класс провайдера.

    Raises:
        ImportError: Если модуль или класс не найдены.
        AttributeError: Если класс не найден в модуле.
    """
    # Полное имя модуля для импорта (e.g., 'app.core.llm.providers.gemini')
    # __name__ здесь будет 'app.core.llm.providers'
    module_name = f"{__name__}{module_suffix}"
    try:
        # Импортируем модуль
        module = importlib.import_module(module_name)
        # Получаем класс из модуля
        provider_class = getattr(module, class_name)
        # Проверяем, является ли он подклассом BaseLLMProvider (опционально)
        if not issubclass(provider_class, BaseLLMProvider):
            raise TypeError(f"Class {class_name} is not a subclass of BaseLLMProvider") # pragma: no cover
        log.debug("Successfully lazy-imported %s from %s", class_name, module_name)
        return provider_class
    except ModuleNotFoundError:
        log.error("Failed to lazy-import module %s. Is it installed/available?", module_name)
        raise # Перебрасываем ошибку
    except AttributeError:
        log.error("Class %s not found in module %s.", class_name, module_name)
        raise # Перебрасываем ошибку
    except Exception as e:
        log.exception("Unexpected error during lazy import of %s.%s", module_name, class_name)
        raise e


# --- Реестр доступных провайдеров ---
# Используем словарь: имя_провайдера (lower case) -> функция для его загрузки
# Заглушка ('stub') загружается всегда.
# Gemini загружается только если выбран или есть ключ (для надежности).

_PROVIDER_LOADERS: Dict[str, function] = {
    "stub": lambda: _lazy_import(".stub", "StubLLMProvider"),
    # Добавляем Gemini, но загружаем только если ключ есть или он выбран
    # (проверка ключа будет внутри __init__ GeminiLLMProvider)
    "gemini": lambda: _lazy_import(".gemini", "GeminiLLMProvider"),
}

# --- Публичная Фабрика ---
_provider_instance = None # Кэшируем инстанс для синглтона

def get_llm_provider() -> BaseLLMProvider:
    """
    Фабрика для получения ЕДИНСТВЕННОГО экземпляра LLM провайдера.

    Выбирает провайдера на основе `settings.LLM_PROVIDER`.
    Использует ленивую загрузку и кэширование экземпляра.

    Returns:
        BaseLLMProvider: Экземпляр выбранного LLM провайдера.

    Raises:
        ValueError: Если указан неизвестный провайдер или не удалось
                    инициализировать выбранного провайдера (например, нет ключа).
    """
    global _provider_instance
    if _provider_instance is None:
        provider_key = settings.LLM_PROVIDER.lower()
        log.info("Attempting to initialize LLM provider: %s", provider_key)

        loader = _PROVIDER_LOADERS.get(provider_key)
        if not loader:
            log.error("Unknown LLM_PROVIDER specified in settings: '%s'", settings.LLM_PROVIDER)
            raise ValueError(f"Unknown LLM provider: {settings.LLM_PROVIDER}")

        try:
            # Вызываем функцию-загрузчик, чтобы получить КЛАСС провайдера
            provider_class: Type[BaseLLMProvider] = loader()
            # Создаем ЭКЗЕМПЛЯР провайдера
            # (здесь могут возникнуть ошибки, если, например, нет API ключа)
            _provider_instance = provider_class()
            log.info("Successfully initialized LLM provider instance: %s", _provider_instance.name)
        except (ImportError, AttributeError, ValueError, RuntimeError, TypeError) as e:
            # Ловим ошибки импорта, инициализации или конфигурации
            log.exception(
                "Failed to initialize LLM provider '%s': %s",
                 provider_key, e
            )
            # Перебрасываем ошибку, т.к. без LLM приложение работать не сможет
            raise ValueError(f"Failed to initialize LLM provider '{provider_key}': {e}") from e
        except Exception as e: # Ловим другие неожиданные ошибки
             log.exception("Unexpected error initializing LLM provider '%s'", provider_key)
             raise e

    return _provider_instance

# --- Экспорты ---
# Экспортируем фабрику и базовый класс для удобства
__all__ = [
    "BaseLLMProvider",
    "get_llm_provider",
]
