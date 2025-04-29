# app/core/auth/security.py

from __future__ import annotations # Обязательно

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional # Добавлена Any для payload

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings # Наш синглтон настроек
# Импортируем асинхронную зависимость для сессии
from app.db.base import get_async_db_session
# Импортируем модель пользователя для поиска в БД
from app.core.users.models import User

from .schemas import TokenData # Наша схема для данных токена

log = logging.getLogger(__name__)

# Определяем схему OAuth2. 'tokenUrl' здесь формальность,
# так как реальный логин будет через Google или тестовый эндпоинт.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/v1/auth/login/test") # Указали тестовый URL

# --- Функции для работы с JWT ---

def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """
    Создает JWT токен доступа.

    Args:
        data (dict): Данные для включения в payload токена.
                     Ключ 'user_id' будет использован как 'sub'.
        expires_delta (timedelta | None, optional): Время жизни токена.
                                                     Если None, используется значение из настроек.

    Returns:
        str: Сгенерированный JWT токен.
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
        )

    # Устанавливаем обязательные поля: время истечения и субъект (user_id)
    to_encode["exp"] = expire
    if "user_id" in to_encode:
        to_encode["sub"] = str(to_encode["user_id"]) # Убедимся, что sub - строка
        # Можно убрать user_id из корня, чтобы не дублировать
        if "sub" != "user_id":
             del to_encode["user_id"]
    elif "sub" not in to_encode:
        raise ValueError("Missing 'user_id' or 'sub' in data for JWT")


    try:
        encoded_jwt = jwt.encode(
            to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
        )
        log.debug("Created JWT token for sub: %s", to_encode.get("sub"))
        return encoded_jwt
    except Exception as e:
        log.exception("Failed to encode JWT token")
        raise e # Перебрасываем исключение

async def verify_token(token: str, credentials_exception: HTTPException) -> TokenData:
    """
    Асинхронно верифицирует JWT токен и возвращает данные из него.

    Args:
        token (str): JWT токен.
        credentials_exception (HTTPException): Исключение для выброса при ошибке.

    Returns:
        TokenData: Валидированные данные из токена.

    Raises:
        HTTPException: Если токен невалиден или истек.
    """
    try:
        # Декодируем токен
        payload: dict[str, Any] = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
            # Опционально: можно указать аудиторию (audience), если используется
            # options={"verify_aud": False} # Если аудитория не проверяется
        )

        # Извлекаем user_id из стандартного поля 'sub'
        user_id: str | None = payload.get("sub")

        if user_id is None:
            log.warning("Token verification failed: 'sub' (user_id) claim missing.")
            raise credentials_exception

        # Проверка срока действия уже выполнена jwt.decode, но для надежности:
        expire_timestamp = payload.get("exp")
        if expire_timestamp and datetime.now(timezone.utc) > datetime.fromtimestamp(expire_timestamp, timezone.utc):
             log.warning("Token verification failed: Token has expired (exp=%s).", expire_timestamp)
             raise credentials_exception # Токен истек

        # Валидируем данные через Pydantic модель
        token_data = TokenData(user_id=user_id)
        log.debug("Token verified successfully for user_id: %s", user_id)

    except JWTError as e:
        log.warning("Token verification failed: JWTError - %s", e)
        raise credentials_exception from e
    except ValidationError as e:
        log.warning("Token verification failed: ValidationError - %s", e)
        raise credentials_exception from e
    except Exception as e: # Ловим другие возможные ошибки
        log.exception("An unexpected error occurred during token verification.")
        raise credentials_exception from e

    return token_data

# --- FastAPI Dependency для получения текущего пользователя ---

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_async_db_session)
) -> User:
    """
    FastAPI зависимость для получения текущего аутентифицированного пользователя.

    Верифицирует токен, извлекает user_id и загружает пользователя из БД.

    Args:
        token (str): JWT токен из заголовка Authorization.
        db (AsyncSession): Асинхронная сессия БД.

    Returns:
        User: ORM объект текущего пользователя.

    Raises:
        HTTPException: status_code 401, если аутентификация не удалась.
                       status_code 404, если пользователь из токена не найден в БД.
    """
    # Определяем исключение здесь, чтобы оно было однотипным
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # Верифицируем токен и получаем данные
    token_data = await verify_token(token, credentials_exception)

    # Ищем пользователя в БД по ID из токена
    log.debug("Fetching user from DB with id: %s", token_data.user_id)
    user = await db.get(User, token_data.user_id)

    if user is None:
        # Если пользователь не найден в БД после успешной верификации токена
        log.error("User with id %s from valid token not found in DB.", token_data.user_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, # Используем 404, т.к. ресурс (пользователь) не найден
            detail=f"User with id {token_data.user_id} not found",
        )

    log.debug("Authenticated user retrieved: %r", user)
    return user

# Пример зависимости для получения ID текущего пользователя (если не нужна вся модель)
async def get_current_user_id(
    current_user: User = Depends(get_current_user)
) -> str:
    """
    FastAPI зависимость для получения только ID текущего пользователя.
    """
    return current_user.id


# Опционально: зависимость для активного пользователя (если добавите флаг is_active)
# async def get_current_active_user(
#     current_user: User = Depends(get_current_user)
# ) -> User:
#     if not getattr(current_user, 'is_active', True): # Проверяем is_active, считаем True если нет
#         log.warning("Authentication attempt by inactive user: %s", current_user.id)
#         raise HTTPException(status_code=403, detail="Inactive user") # 403 Forbidden
#     return current_user
