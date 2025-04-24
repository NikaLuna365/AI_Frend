from pydantic import BaseModel
from datetime import datetime

class EventOut(BaseModel):
    title: str
    start: datetime
    end: datetime | None = None
