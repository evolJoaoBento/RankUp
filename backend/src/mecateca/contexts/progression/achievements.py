from __future__ import annotations

"""Computed achievements — derived live from existing data, no extra tables.

Each entry: key, unlocked, value (current progress) and target. Titles and
descriptions live in the frontend so they translate with the UI language.
"""

import uuid

from sqlalchemy import Integer, cast, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from mecateca.contexts.assessment.models import Answer, PracticeItem
from mecateca.contexts.duels.models import Duel
from mecateca.contexts.progression.models import UserSubjectProgress


async def compute(db: AsyncSession, user_id: uuid.UUID) -> list[dict]:
    answers, correct = (
        await db.execute(
            select(func.count(Answer.id), func.coalesce(func.sum(cast(Answer.correct, Integer)), 0))
            .where(Answer.user_id == user_id)
        )
    ).one()

    # best single session: needs >= 5 answers, all correct
    perfect = (
        await db.execute(
            select(func.count())
            .select_from(
                select(PracticeItem.session_id)
                .join(Answer, Answer.item_id == PracticeItem.id)
                .where(Answer.user_id == user_id)
                .group_by(PracticeItem.session_id)
                .having(
                    func.count(Answer.id) >= 5,
                    func.count(Answer.id) == func.sum(cast(Answer.correct, Integer)),
                )
                .subquery()
            )
        )
    ).scalar_one()

    duel_wins = (
        await db.execute(
            select(func.count()).select_from(Duel).where(
                Duel.winner_id == user_id, Duel.status.in_(("complete", "forfeited"))
            )
        )
    ).scalar_one()
    duels_played = (
        await db.execute(
            select(func.count()).select_from(Duel).where(
                or_(Duel.challenger_id == user_id, Duel.opponent_id == user_id),
                Duel.status.in_(("complete", "forfeited")),
            )
        )
    ).scalar_one()

    progress_rows = list(
        (
            await db.execute(
                select(UserSubjectProgress).where(UserSubjectProgress.user_id == user_id)
            )
        ).scalars()
    )
    best_xp = max((p.xp for p in progress_rows), default=0)
    best_streak = max((p.streak for p in progress_rows), default=0)
    subjects_active = sum(1 for p in progress_rows if p.xp > 0)

    def a(key: str, value: int, target: int) -> dict:
        return {"key": key, "value": min(value, target), "target": target, "unlocked": value >= target}

    return [
        a("first-answer", answers, 1),
        a("ten-answers", answers, 10),
        a("hundred-answers", answers, 100),
        a("fifty-correct", int(correct), 50),
        a("perfect-test", int(perfect), 1),
        a("streak-5", best_streak, 5),
        a("first-duel", duels_played, 1),
        a("duel-winner", duel_wins, 1),
        a("duel-champion", duel_wins, 5),
        a("ep-100", best_xp, 100),
        a("ep-500", best_xp, 500),
        a("two-subjects", subjects_active, 2),
    ]
