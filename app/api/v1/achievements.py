from fastapi import APIRouter
from typing import List
from app.core.achievements.service import AchievementsService
from app.core.achievements.schemas import AchievementOut

router = APIRouter()

@router.get('/{user_id}', response_model=List[AchievementOut])
def get_achievements(user_id: str):
    svc = AchievementsService()
    return svc.list_user_achievements(user_id)
