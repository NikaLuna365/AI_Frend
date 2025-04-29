# app/core/auth/schemas.py

from __future__ import annotations # Обязательно для type hints

from pydantic import BaseModel, Field

class Token(BaseModel):
    """Схема для возврата JWT токена клиенту."""
    access_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    """
    Схема для данных, хранящихся внутри JWT токена.
    Содержит идентификатор пользователя нашего приложения.
    """
    # Мы будем использовать 'sub' как стандартное поле для user_id
    # но оставим user_id для явного доступа, если payload будет его содержать.
    user_id: str | None = Field(None, description="User ID within our application")

class TestLoginRequest(BaseModel):
    """Схема для временного тестового эндпоинта логина."""
    user_id: str = Field(..., description="User ID to login as (for testing)")
