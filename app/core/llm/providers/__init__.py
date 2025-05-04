# /app/app/core/llm/providers/__init__.py (Версия из ответа #67 - ПРАВИЛЬНАЯ)

from __future__ import annotations

import importlib
import logging
import sys
from typing import Dict, Type

from app.config import settings
# --- ИМПОРТИРУЕМ ТОЛЬКО BaseLLMProvider ---
from .base import BaseLLMProvider
# ------------------------------------------

log = logging.getLogger(__name__)

# --- Функция _lazy_import (без изменений) ---
def _lazy_import(module_suffix: str, class_name: str) -> Type[BaseLLMProvider]:
    # ... (код функции _lazy_import) ...
    module_name = f"{__name__}{module_suffix}"
    try:
        module = importlib.import_module(module_name)
        provider_class = getattr(module, class_name)
        if not issubclass(provider_class, BaseLLMProvider):
            raise TypeError(f"Class {class_name} is not a subclass of BaseLLMProvider") # pragma: no cover
        log.debug("Successfully lazy-imported %s from %s", class_name, module_name)
        return provider_class
    # ... (обработка ошибок import/attribute) ...
    except (ModuleNotFoundError, AttributeError) as e:
         log.error("Failed to lazy-import provider '%s%s': %s", module_suffix, class_name, e)
         raise ImportError(f"Could not import provider {class_name} from {module_name}") from e
    except Exception as e:
        log.exception("Unexpected error during lazy import of %s.%s", module_name, class_name)
        raise e


# --- Реестр доступных провайдеров ---
_PROVIDER_LOADERS: Dict[str, function] = {
    "stub": lambda: _lazy_import(".stub", "StubLLMProvider"),
    "gemini": lambda: _lazy_import(".gemini", "GeminiLLMProvider"),
}

# --- Публичная Фабрика ---
_provider_instance = None

def get_llm_provider() -> BaseLLMProvider:
    """Фабрика для получения ЕДИНСТВЕННОГО экземпляра LLM провайдера."""
    global _provider_instance
    if _provider_instance is None:
        provider_key = settings.LLM_PROVIDER.lower()
        log.info("Attempting to initialize LLM provider: %s", provider_key)
        loader = _PROVIDER_LOADERS.get(provider_key)
        if not loader:
            raise ValueError(f"Unknown LLM provider: {settings.LLM_PROVIDER}")
        try:
            provider_class: Type[BaseLLMProvider] = loader()
            _provider_instance = provider_class() # Инициализация здесь
            log.info("Successfully initialized LLM provider instance: %s", _provider_instance.name)
        # ... (обработка ошибок инициализации) ...
        except (ImportError, ValueError, RuntimeError, TypeError) as e:
             log.exception("Failed to initialize LLM provider '%s': %s", provider_key, e)
             raise ValueError(f"Failed to initialize LLM provider '{provider_key}': {e}") from e
        except Exception as e:
             log.exception("Unexpected error initializing LLM provider '%s'", provider_key)
             raise e

    return _provider_instance

# --- Экспорты из ЭТОГО модуля ---
__all__ = [
    "BaseLLMProvider",    # Экспортируем базовый класс
    "get_llm_provider", # Экспортируем фабрику
]
