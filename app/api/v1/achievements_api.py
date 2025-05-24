# /app/app/api/v1/achievements_api.py

from __future__ import annotations

import logging
from typing import List, Optional, Sequence # Добавил Sequence
from datetime import datetime # Для Pydantic модели

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field # Для моделей запроса/ответа
from sqlalchemy.ext.asyncio import AsyncSession

# --- Наши Модули ---
from app.core.achievements.service import AchievementsService
# Импортируем ORM модель Achievement для типизации в сервисе, если он ее возвращает напрямую
from app.core.achievements.models import Achievement as AchievementORM
# Модель пользователя для зависимости get_current_user
from app.core.users.models import User
# --- ЗАВИСИМОСТИ ---
from app.db.base import get_async_db_session
from app.core.auth.security import get_current_user

# --- Инициализация ---
router = APIRouter(
    prefix="/v1/achievements", # Общий префикс для всех эндпоинтов ачивок
    tags=["Achievements"],
    dependencies=[Depends(get_current_user)] # Все эндпоинты здесь требуют аутентификации
)
log = logging.getLogger(__name__)


# --- Pydantic Модель для Ответа API ---
class AchievementOut(BaseModel):
    """
    Схема для отображения информации об ачивке пользователю.
    """
    code: str = Field(..., description="Unique code of the achievement")
    title: Optional[str] = Field(None, description="Generated title of the achievement")
    badge_png_url: Optional[str] = Field(None, description="URL to the achievement badge icon (PNG)")
    # description: Optional[str] = Field(None, description="User-facing description of the achievement") # Можно добавить позже из "зашитого" правила
    status: str = Field(..., description="Current status of the achievement (e.g., COMPLETED, PENDING_GENERATION)")
    created_at: datetime = Field(..., description="Timestamp when the achievement record was first created or triggered")
    updated_at: datetime = Field(..., description="Timestamp of the last update to the achievement record")

    # Конфигурация для преобразования из ORM объекта
    # Удаляем, т.к. будем создавать вручную
    # class Config:
    #     from_attributes = True


# --- Эндпоинт для Получения Ачивок Текущего Пользователя ---
@router.get(
    "/me", # Путь будет /v1/achievements/me
    response_model=List[AchievementOut],
    summary="Get my unlocked achievements",
    description="Retrieves a list of achievements that the currently authenticated user has earned and are fully generated (status COMPLETED)."
)
async def get_my_achievements(
    current_user: User = Depends(get_current_user), # Получаем текущего пользователя
    db: AsyncSession = Depends(get_async_db_session)  # Получаем сессию БД
) -> List[AchievementOut]:
    """
    Возвращает список завершенных (статус COMPLETED) ачивок
    для аутентифицированного пользователя.
    """
    log.info(f"API: User '{current_user.id}' requesting their achievements.")
    ach_service = AchievementsService(db_session=db)
    
    try:
        # AchievementsService.get_user_achievements должен возвращать Sequence[AchievementORM]
        # со статусом COMPLETED
        user_achievements_orm: Sequence[AchievementORM] = await ach_service.get_user_achievements(current_user.id)
        
        # Преобразуем ORM объекты в Pydantic модели AchievementOut
        achievements_out: List[AchievementOut] = []
        for ach_orm in user_achievements_orm:
            achievements_out.append(
                AchievementOut(
                    code=ach_orm.code,
                    title=ach_orm.title,
                    badge_png_url=ach_orm.badge_png_url,
                    status=ach_orm.status,
                    created_at=ach_orm.created_at,
                    updated_at=ach_orm.updated_at
                )
            )
        
        log.info(f"API: Found {len(achievements_out)} completed achievements for user '{current_user.id}'.")
        return achievements_out
    except Exception as e:
        log.exception(f"API: Error retrieving achievements for user '{current_user.id}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not retrieve achievements."
        )
