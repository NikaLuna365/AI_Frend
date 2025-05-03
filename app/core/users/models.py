# /app/app/core/users/models.py (или аналогичный)
# ... (импорты datetime, List, Optional, SQLAlchemy типы, Base) ...
from sqlalchemy.orm import Mapped, mapped_column, relationship # Убедимся, что relationship импортирован
from sqlalchemy.sql import func
from app.db.base import Base

# Импортируем типы из связанных модулей для аннотаций, но не сами классы напрямую в глобальную область
# Используем строки для relationship, чтобы избежать циклических импортов
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from app.core.achievements.models import Achievement # Только для type hinting

class User(Base):
    __tablename__ = 'users'

    id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    # Убираем поля Google на время MVP, как договорились
    # google_id: Mapped[Optional[str]] = mapped_column(String(255), unique=True, index=True, nullable=True)
    # email: Mapped[Optional[str]] = mapped_column(String(255), index=True, nullable=True)
    name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # --- СВЯЗИ ---
    messages: Mapped[List["Message"]] = relationship(
        # Используем полный путь к модели Message, если она в этом же файле, можно без "app.core.users.models."
        "Message",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    # --- ИСПРАВЛЕНИЕ ЗДЕСЬ: Используем полный путь к Achievement ---
    achievements: Mapped[List["Achievement"]] = relationship(
        "app.core.achievements.models.Achievement", # <-- Полный путь
        # back_populates="user", # Указываем back_populates, если он есть в Achievement
        cascade="all, delete-orphan"
    )
    # --------------------------------------------------------------


class Message(Base):
    __tablename__ = 'messages'
    # ... (определение полей Message) ...
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[str] = mapped_column(String(64), ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="messages") # Здесь можно без полного пути, т.к. User в этом же файле
