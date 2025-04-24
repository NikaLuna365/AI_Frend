"""Initial tables

Revision ID: 0001_initial
Revises: 
Create Date: 2025-04-24 15:50:00.000000
"""
from alembic import op
import sqlalchemy as sa

def upgrade():
    op.create_table(
        'users',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('name', sa.String(), nullable=True),
        sa.Column('timezone', sa.String(), nullable=False, server_default='UTC'),
        sa.Column('settings', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False)
    )
    op.create_table(
        'messages',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.String(), sa.ForeignKey('users.id', ondelete='CASCADE')),
        sa.Column('role', sa.String(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False)
    )
    op.create_table(
        'achievement_rules',
        sa.Column('code', sa.String(), primary_key=True),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('icon_url', sa.String(), nullable=False),
        sa.Column('description', sa.String(), nullable=True)
    )
    op.create_table(
        'achievements',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.String(), sa.ForeignKey('users.id', ondelete='CASCADE')),
        sa.Column('code', sa.String(), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('icon_url', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False)
    )

def downgrade():
    op.drop_table('achievements')
    op.drop_table('achievement_rules')
    op.drop_table('messages')
    op.drop_table('users')
