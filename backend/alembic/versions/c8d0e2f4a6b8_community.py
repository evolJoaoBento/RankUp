"""community: avatars, direct messages, duel kudos

Revision ID: c8d0e2f4a6b8
Revises: b7c9d1e3f5a7
Create Date: 2026-07-04
"""
from alembic import op
import sqlalchemy as sa


revision = 'c8d0e2f4a6b8'
down_revision = 'b7c9d1e3f5a7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # preset avatar key ("" = fall back to the initial-letter circle)
    op.add_column('user', sa.Column('avatar', sa.String(24), server_default='', nullable=False))
    op.alter_column('user', 'avatar', server_default=None)

    op.create_table(
        'direct_message',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('from_id', sa.Uuid(), sa.ForeignKey('user.id', ondelete='CASCADE'), nullable=False),
        sa.Column('to_id', sa.Uuid(), sa.ForeignKey('user.id', ondelete='CASCADE'), nullable=False),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('read_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_direct_message_from_id', 'direct_message', ['from_id'])
    op.create_index('ix_direct_message_to_id', 'direct_message', ['to_id'])
    op.create_index('ix_dm_to_read', 'direct_message', ['to_id', 'read_at'])

    op.add_column('duel', sa.Column('kudos_challenger', sa.Boolean(), server_default=sa.false(), nullable=False))
    op.add_column('duel', sa.Column('kudos_opponent', sa.Boolean(), server_default=sa.false(), nullable=False))
    op.alter_column('duel', 'kudos_challenger', server_default=None)
    op.alter_column('duel', 'kudos_opponent', server_default=None)


def downgrade() -> None:
    op.drop_column('duel', 'kudos_opponent')
    op.drop_column('duel', 'kudos_challenger')
    op.drop_table('direct_message')
    op.drop_column('user', 'avatar')
