"""teacher announcements per discipline

Revision ID: d0e1f2a3b4c5
Revises: c8d0e2f4a6b8
Create Date: 2026-07-04
"""
from alembic import op
import sqlalchemy as sa


revision = 'd0e1f2a3b4c5'
down_revision = 'c8d0e2f4a6b8'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'announcement',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('subject_id', sa.Uuid(), sa.ForeignKey('subject.id', ondelete='CASCADE'), nullable=False),
        sa.Column('author_id', sa.Uuid(), sa.ForeignKey('user.id', ondelete='SET NULL'), nullable=True),
        sa.Column('text', sa.String(500), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_announcement_subject_id', 'announcement', ['subject_id'])


def downgrade() -> None:
    op.drop_table('announcement')
