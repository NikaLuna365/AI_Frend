# /app/app/api/v1/auth.py (Версия с тестовым логином)

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.ext.asyncio import AsyncSession

# Импорты для аутентификации
# Token - для ответа, TestLoginRequest - для запроса
from app.core.auth.schemas import Token, TestLoginRequest
# Функция для создания JWT
from app.core.auth.security import create_access_token
# Сервис пользователей для создания/поиска пользователя
from app.core.users.service import UsersService
# Асинхронная сессия БД
from app.db.base import get_async_db_session

# Создаем роутер
router = APIRouter(prefix="/v1/auth", tags=["Authentication"])
log = logging.getLogger(__name__)

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
    # Получаем user_id из тела запроса
    login_data: TestLoginRequest = Body(...),
    # Получаем асинхронную сессию БД через зависимость
    db: AsyncSession = Depends(get_async_db_session)
) -> Token:
    """
    Генерирует JWT для тестового входа по внутреннему user_id.

    Args:
        login_data (TestLoginRequest): Тело запроса с `user_id`.
        db (AsyncSession): Зависимость сессии БД.

    Returns:
        Token: Объект с `access_token`.

    Raises:
        HTTPException: 500, если произошла ошибка при работе с БД.
    """
    user_id = login_data.user_id
    log.warning(
        "Executing TEST login for user_id: %s. Ensure this is NOT production!",
        user_id
    )

    # Инициализируем сервис с текущей сессией
    user_service = UsersService(db)
    try:
        # Убедимся, что пользователь существует или будет создан
        # Используем get_or_create_user из обновленного UsersService
        user = await user_service.get_or_create_user(user_id)
        log.info("User ensured for test login: id=%s", user.id)
        # Коммит транзакции произойдет автоматически при выходе из get_async_db_session

    except Exception as e:
        log.exception("Failed to ensure user during test login for user_id: %s", user_id)
        # Откат произойдет автоматически в get_async_db_session
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error while ensuring user: {type(e).__name__}"
        ) from e

    # Генерируем JWT токен для этого пользователя
    # В payload передаем наш внутренний user_id
    access_token = create_access_token(data={"user_id": user.id})

    log.info("Generated test JWT for user_id: %s", user.id)
    return Token(access_token=access_token, token_type="bearer")

# --- Место для будущих эндпоинтов (Google Callback и т.д.) ---
# @router.post("/google/callback") ...
# -----------------------------------------------------------
