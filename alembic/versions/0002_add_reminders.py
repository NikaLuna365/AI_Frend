"""Add reminders table

Revision ID: 0002_add_reminders
Revises: 0001_initial
Create Date: 2025-04-24 16:20:00.000000
"""
from alembic import op
import sqlalchemy as sa

def upgrade():
    op.create_table(
        'reminders',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.String(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('event_id', sa.String(), nullable=False),
        sa.Column('sent_at', sa.DateTime(), nullable=False)
    )

def downgrade():
    op.drop_table('reminders')
