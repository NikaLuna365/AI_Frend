# /app/app/api/v1/auth.py (Дополненная версия)

from __future__ import annotations

import logging
from typing import List # Добавляем List

from fastapi import APIRouter, Depends, HTTPException, status, Body
from pydantic import BaseModel, Field # Добавляем BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

# Импорты для аутентификации
from app.core.auth.schemas import Token, TestLoginRequest
from app.core.auth.security import create_access_token
# Импорт сервиса пользователей
from app.core.users.service import UsersService
# Импорт зависимости для сессии БД
from app.db.base import get_async_db_session
# --- ДОБАВЛЯЕМ ИМПОРТ LLM КЛИЕНТА ---
from app.core.llm.client import LLMClient
# --- Добавляем зависимость для LLM клиента ---
from app.api.v1.chat import get_llm_client # Используем ту же фабрику, что и в chat.py
# -----------------------------------------

# Создаем роутер
router = APIRouter(prefix="/v1/auth", tags=["Authentication & Testing"]) # Обновили тег
log = logging.getLogger(__name__)

# --- Модель для запроса теста генерации имени ачивки ---
class GenerateNameTestRequest(BaseModel):
    context: str = Field("User sent their 10th message", description="Achievement context/description")
    style_id: str = Field("cartoon_absurd", description="Style identifier")
    tone_hint: str = Field("playful, punny, excited", description="Tone keywords")
    style_examples: str = Field("1. First Drop!\n2. Chatterbox Supreme\n3. Calendar Conqueror", description="Examples in target style")
# ----------------------------------------------------


@router.post(
    "/login/test",
    response_model=Token,
    summary="[Development Only] Get JWT for a user ID",
    description=(
        "**WARNING:** Use only for development/testing. "
        "Creates a user (if doesn't exist) and returns a JWT token "
        "for the given internal `user_id`."
        "\n\n**DO NOT EXPOSE IN PRODUCTION!**"
    )
)
async def test_login_for_access_token(
    login_data: TestLoginRequest = Body(...),
    db: AsyncSession = Depends(get_async_db_session)
) -> Token:
    # --- Код этого эндпоинта остается без изменений ---
    user_id = login_data.user_id
    log.warning(
        "Executing TEST login for user_id: %s. Ensure this is NOT production!",
        user_id
    )
    user_service = UsersService(db)
    try:
        user = await user_service.get_or_create_user(user_id)
        log.info("User ensured for test login: id=%s", user.id)
    except Exception as e:
        log.exception("Failed to ensure user during test login for user_id: %s", user_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error while ensuring user: {type(e).__name__}"
        ) from e
    access_token = create_access_token(data={"user_id": user.id})
    log.info("Generated test JWT for user_id: %s", user.id)
    return Token(access_token=access_token, token_type="bearer")


# --- НОВЫЙ ТЕСТОВЫЙ ЭНДПОИНТ ---
@router.post(
    "/test/generate_achievement_name",
    response_model=List[str], # Возвращаем список строк
    summary="[Development Only] Test achievement name generation",
    description=(
        "**WARNING:** Use only for development/testing. "
        "Calls the configured LLM provider (e.g., Gemini) to generate "
        "achievement names based on the provided context and style hints."
        "\n\n**DO NOT EXPOSE IN PRODUCTION!**"
    )
    # Этот эндпоинт НЕ ТРЕБУЕТ аутентификации для простоты тестирования
)
async def test_generate_achievement_name(
    request_data: GenerateNameTestRequest = Body(...),
    llm: LLMClient = Depends(get_llm_client) # Получаем LLM клиент
) -> List[str]:
    """
    Тестирует вызов LLMClient.generate_achievement_name.

    Args:
        request_data (GenerateNameTestRequest): Параметры для генерации имени.
        llm (LLMClient): Зависимость LLM клиента.

    Returns:
        List[str]: Список из 3 сгенерированных названий.

    Raises:
        HTTPException: 500, если произошла ошибка при вызове LLM.
    """
    log.warning("Executing TEST generate_achievement_name. Ensure this is NOT production!")
    try:
        generated_names = await llm.generate_achievement_name(
            context=request_data.context,
            style_id=request_data.style_id,
            tone_hint=request_data.tone_hint,
            style_examples=request_data.style_examples
        )
        log.info("Test achievement name generation returned: %s", generated_names)
        return generated_names
    except NotImplementedError as e:
         log.error("LLM provider does not support name generation: %s", e)
         raise HTTPException(
             status_code=status.HTTP_501_NOT_IMPLEMENTED,
             detail=f"The configured LLM provider ({llm.provider.name}) does not support achievement name generation."
         ) from e
    except Exception as e:
        log.exception("Error during test achievement name generation: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"LLM API error: {type(e).__name__}"
        ) from e

# ------------------------------------
