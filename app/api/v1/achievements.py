# app/api/v1/achievements.py
from typing import List

from fastapi import APIRouter, HTTPException

from app.core.achievements.service import AchievementsService
from app.core.achievements.schemas import AchievementOut

router = APIRouter(prefix="/v1/achievements", tags=["Achievements"])


@router.get("/{user_id}", response_model=List[AchievementOut])
def get_achievements(user_id: str):
    svc = AchievementsService()
    return svc.list_user_achievements(user_id)
