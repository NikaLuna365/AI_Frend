# app/api/v1/auth.py

from __future__ import annotations # Обязательно

import logging

from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.ext.asyncio import AsyncSession

# Импорты для аутентификации
from app.core.auth.schemas import Token, TestLoginRequest
from app.core.auth.security import create_access_token
# Импорт сервиса пользователей для ensure_user
from app.core.users.service import UsersService
# Импорт зависимости для сессии БД
from app.db.base import get_async_db_session

# Создаем новый роутер для аутентификации
router = APIRouter(prefix="/v1/auth", tags=["Authentication"])
log = logging.getLogger(__name__)

@router.post(
    "/login/test",
    response_model=Token,
    summary="[Development Only] Get JWT for a user",
    description=(
        "**WARNING:** This endpoint is for development and testing purposes only. "
        "It allows obtaining a JWT for any user ID without actual authentication. "
        "**DO NOT EXPOSE IN PRODUCTION!**"
    )
)
async def test_login_for_access_token(
    # Используем Body(...) для явного указания, что данные берем из тела запроса
    login_data: TestLoginRequest = Body(...),
    db: AsyncSession = Depends(get_async_db_session)
) -> Token:
    """
    Временный эндпоинт для получения JWT токена по user_id.
    Предназначен **только для разработки и тестирования**.

    Принимает `user_id`, проверяет/создает пользователя в БД и возвращает
    валидный JWT `access_token`.

    Args:
        login_data (TestLoginRequest): Данные с `user_id`.
        db (AsyncSession): Зависимость сессии БД.

    Returns:
        Token: Объект с `access_token` и `token_type`.
    """
    user_id = login_data.user_id
    log.warning(
        "Executing TEST login for user_id: %s. Ensure this is not a production environment!",
        user_id
    )

    user_service = UsersService(db)
    try:
        # Убедимся, что пользователь существует или будет создан
        user = await user_service.ensure_user(user_id)
        # Коммит здесь не нужен, т.к. ensure_user делает flush, а get_async_db_session
        # управляет транзакцией (хотя для тестового эндпоинта можно было бы и коммитить)
        log.info("User ensured for test login: %r", user)

    except Exception as e:
        # Ловим возможные ошибки БД при создании пользователя
        log.exception("Failed to ensure user during test login for user_id: %s", user_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error while ensuring user: {e}"
        ) from e

    # Генерируем токен для найденного/созданного пользователя
    access_token = create_access_token(data={"user_id": user.id}) # Используем user.id из ORM

    return Token(access_token=access_token, token_type="bearer")

# --- Место для будущих эндпоинтов ---
# Например:
# @router.post("/google/callback") ...
# @router.post("/google/calendar/callback") ...
# ------------------------------------
