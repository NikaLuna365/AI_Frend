"""initial

Revision ID: 0001_initial
Revises:
Create Date: 2024-06-20

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "users",
        sa.Column("id", sa.String, primary_key=True),
    )

    op.create_table(
        "messages",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.String, nullable=False),
        sa.Column("text", sa.String, nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False),
    )

    op.create_table(
        "reminders",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.String, nullable=False),
        sa.Column("text", sa.String, nullable=False),
        sa.Column("due_at", sa.DateTime, nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False),
    )

    op.create_table(
        "achievement_rules",
        sa.Column("code", sa.String, primary_key=True),
        sa.Column("title", sa.String, nullable=False),
        sa.Column("description", sa.String, nullable=False),
        sa.Column("icon_url", sa.String),
    )

    op.create_table(
        "achievements",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.String, nullable=False),
        sa.Column("code", sa.String, nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False),
    )


def downgrade():
    op.drop_table("achievements")
    op.drop_table("achievement_rules")
    op.drop_table("reminders")
    op.drop_table("messages")
    op.drop_table("users")
