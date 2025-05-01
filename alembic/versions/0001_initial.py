# /app/alembic/versions/0001_initial.py (Исправленная версия)

"""Initial tables

Revision ID: 0001_initial # Оставляем для информации
Revises:                   # Оставляем для информации
Create Date: 2025-04-24 15:50:00.000000 # Оставляем для информации
"""
from typing import Sequence, Union # Импортируем типы для аннотаций

from alembic import op
import sqlalchemy as sa


# ------------- ДОБАВЛЕННЫЕ ПЕРЕМЕННЫЕ ALEMBIC -------------
# revision identifiers, used by Alembic.
revision: str = '0001_initial' # ID текущей ревизии (можно взять из имени файла или старого docstring)
down_revision: Union[str, None] = None # ID предыдущей ревизии (None для первой)
branch_labels: Union[str, Sequence[str], None] = None # Метки ветвей (обычно None)
depends_on: Union[str, Sequence[str], None] = None # Зависимости от других ревизий (обычно None)
# ---------------------------------------------------------


def upgrade() -> None:
    """Applies the changes to create the initial tables."""
    # Используем существующий код для создания таблиц
    # (Добавил комментарии для ясности)
    # Таблица Пользователей
    op.create_table(
        'users',
        sa.Column('id', sa.String(length=64), primary_key=True, index=True, comment="User ID (e.g., from external provider or internal)"), # Добавил длину и индекс
        sa.Column('name', sa.String(length=128), nullable=True), # Добавил длину
        sa.Column('timezone', sa.String(length=64), nullable=False, server_default='UTC'), # Добавил длину
        sa.Column('settings', sa.Text(), nullable=True, comment="User-specific settings (e.g., JSON)"),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.utcnow()), # Добавил server_default
        # Добавляем поля для Google OAuth токенов (зашифрованные)
        sa.Column('google_calendar_access_token_encrypted', sa.LargeBinary(), nullable=True),
        sa.Column('google_calendar_refresh_token_encrypted', sa.LargeBinary(), nullable=True),
        sa.Column('google_calendar_token_expiry', sa.DateTime(timezone=True), nullable=True),
        sa.Column('google_id', sa.String(length=255), nullable=True, unique=True, index=True, comment="Google User ID (sub)"), # Добавляем Google ID
        sa.Column('email', sa.String(length=255), nullable=True, index=True, comment="User email (verified from Google)"), # Добавляем email
    )

    # Таблица Сообщений
    op.create_table(
        'messages',
        sa.Column('id', sa.Integer(), primary_key=True, index=True), # Добавил индекс
        sa.Column('user_id', sa.String(length=64), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True), # Добавил длину и индекс
        sa.Column('role', sa.String(length=16), nullable=False), # Добавил длину (user/assistant)
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.utcnow()) # Добавил server_default
    )

    # Таблица Правил Ачивок
    op.create_table(
        'achievement_rules',
        sa.Column('code', sa.String(length=64), primary_key=True, index=True), # Добавил длину и индекс
        sa.Column('title', sa.String(length=128), nullable=False), # Добавил длину
        sa.Column('description', sa.String(length=256), nullable=True), # Добавил длину
        sa.Column('icon_url', sa.String(length=512), nullable=True) # Добавил длину, сделал nullable
    )

    # Таблица Полученных Ачивок
    op.create_table(
        'achievements',
        sa.Column('id', sa.Integer(), primary_key=True, index=True), # Добавил индекс
        # Добавил длину к user_id и code, добавил ForeignKey constraint name
        sa.Column('user_id', sa.String(length=64), sa.ForeignKey('users.id', ondelete='CASCADE', name='fk_achievements_user_id'), nullable=False, index=True),
        sa.Column('code', sa.String(length=64), sa.ForeignKey('achievement_rules.code', ondelete='CASCADE', name='fk_achievements_code'), nullable=False, index=True),
        sa.Column('title', sa.String(length=128), nullable=False), # Денормализованное поле
        sa.Column('icon_url', sa.String(length=512), nullable=True), # Денормализованное поле, nullable
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.utcnow()), # Добавил server_default
        # Добавляем уникальный индекс, чтобы пользователь не мог получить одну ачивку дважды
        sa.UniqueConstraint('user_id', 'code', name='uq_achievement_user_code')
    )

    # Таблица Напоминаний (Обновленная)
    op.create_table(
        'reminders',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('user_id', sa.String(length=64), sa.ForeignKey('users.id', ondelete='CASCADE', name='fk_reminders_user_id'), nullable=False, index=True),
        sa.Column('title', sa.String(length=255), nullable=False), # Добавил длину
        sa.Column('due_at', sa.DateTime(), nullable=False, index=True),
        sa.Column('sent', sa.Boolean(), nullable=False, server_default=sa.false(), index=True), # Добавил server_default=false
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.utcnow()),
        sa.Column('source_event_id', sa.String(length=255), nullable=True) # Добавил длину
    )
    op.create_index('ix_reminders_due_at_sent', 'reminders', ['due_at', 'sent'], unique=False)


def downgrade() -> None:
    """Reverts the initial schema creation."""
    # Удаляем в обратном порядке создания
    op.drop_index('ix_reminders_due_at_sent', table_name='reminders')
    op.drop_table('reminders')
    op.drop_table('achievements')
    op.drop_table('achievement_rules')
    op.drop_table('messages')
    op.drop_table('users')
