"""moderated profile photos

Revision ID: e1f2a3b4c5d6
Revises: d0e1f2a3b4c5
Create Date: 2026-07-06
"""
from alembic import op
import sqlalchemy as sa


revision = 'e1f2a3b4c5d6'
down_revision = 'd0e1f2a3b4c5'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('user', sa.Column('photo', sa.String(40), server_default='', nullable=False))
    op.alter_column('user', 'photo', server_default=None)


def downgrade() -> None:
    op.drop_column('user', 'photo')
