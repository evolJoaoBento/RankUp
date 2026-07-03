"""duel rating per subject

Revision ID: b7c9d1e3f5a7
Revises: f017075767fc
Create Date: 2026-07-04
"""
from alembic import op
import sqlalchemy as sa


revision = 'b7c9d1e3f5a7'
down_revision = 'f017075767fc'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('duel_rating', sa.Column('subject_id', sa.Uuid(), nullable=True))
    op.create_foreign_key(
        op.f('fk_duel_rating_subject_id_subject'), 'duel_rating', 'subject',
        ['subject_id'], ['id'], ondelete='CASCADE',
    )
    # backfill: attach each existing (global) rating to the discipline where the
    # player last played ranked — that is where those points were earned
    op.execute("""
        UPDATE duel_rating dr SET subject_id = (
            SELECT sv.subject_id FROM duel d
            JOIN subject_version sv ON sv.id = d.subject_version_id
            WHERE d.ranked AND (d.challenger_id = dr.user_id OR d.opponent_id = dr.user_id)
            ORDER BY d.created_at DESC LIMIT 1
        ) WHERE dr.subject_id IS NULL
    """)
    # rows with zero games carry no information — safe to drop; anything else
    # (shouldn't exist) is attached to the oldest subject rather than lost
    op.execute("DELETE FROM duel_rating WHERE subject_id IS NULL AND games = 0")
    op.execute("""
        UPDATE duel_rating SET subject_id = (SELECT id FROM subject ORDER BY created_at LIMIT 1)
        WHERE subject_id IS NULL
    """)
    op.execute("ALTER TABLE duel_rating DROP CONSTRAINT pk_duel_rating")
    op.execute("ALTER TABLE duel_rating ALTER COLUMN subject_id SET NOT NULL")
    op.execute("ALTER TABLE duel_rating ADD CONSTRAINT pk_duel_rating PRIMARY KEY (user_id, subject_id)")


def downgrade() -> None:
    # lossy by nature: keep each player's most-played subject row as the global one
    op.execute("""
        DELETE FROM duel_rating dr WHERE (dr.user_id, dr.games) NOT IN (
            SELECT user_id, MAX(games) FROM duel_rating GROUP BY user_id
        )
    """)
    op.execute("""
        DELETE FROM duel_rating a USING duel_rating b
        WHERE a.user_id = b.user_id AND a.subject_id > b.subject_id
    """)
    op.execute("ALTER TABLE duel_rating DROP CONSTRAINT pk_duel_rating")
    op.execute("ALTER TABLE duel_rating ADD CONSTRAINT pk_duel_rating PRIMARY KEY (user_id)")
    op.drop_constraint(op.f('fk_duel_rating_subject_id_subject'), 'duel_rating', type_='foreignkey')
    op.drop_column('duel_rating', 'subject_id')
