from pydantic import BaseModel
from datetime import datetime

class AchievementOut(BaseModel):
    code: str
    title: str
    icon_url: str
    created_at: datetime
