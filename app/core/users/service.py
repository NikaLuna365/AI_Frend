from app.db.base import SessionLocal
from app.core.users.models import User, Message as MsgModel
from app.core.llm.client import Message
from typing import List

class UsersService:
    """Работа с данными пользователей и сообщениями"""
    model = User
    def __init__(self):
        self.db = SessionLocal()

    def ensure_user(self, user_id: str) -> User:
        user = self.db.query(User).get(user_id)
        if not user:
            user = User(id=user_id)
            self.db.add(user)
            self.db.commit()
            self.db.refresh(user)
        return user

    def save_message(self, user_id: str, message: Message):
        self.ensure_user(user_id)
        db_msg = MsgModel(user_id=user_id, role=message.role, content=message.content)
        self.db.add(db_msg)
        self.db.commit()

    def get_recent_messages(self, user_id: str, limit: int = 20) -> List[Message]:
        raw = (
            self.db.query(MsgModel)
            .filter(MsgModel.user_id == user_id)
            .order_by(MsgModel.created_at.desc())
            .limit(limit)
            .all()
        )
        # реверсируем для хронологического порядка
        return [Message(role=m.role, content=m.content) for m in reversed(raw)]
