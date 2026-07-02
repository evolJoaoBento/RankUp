from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from mecateca.contexts.catalog.models import QuestionTemplate
from mecateca.contexts.assessment.models import PracticeItem, PracticeSession

DEFAULT_N = 5


class PracticeTestActivity:
    """Activity plugin: instantiate practice items from the subject's templates."""

    type = "practice_test"

    async def generate(
        self,
        db: AsyncSession,
        session: PracticeSession,
        n: int = DEFAULT_N,
    ) -> list[PracticeItem]:
        q = select(QuestionTemplate).where(
            QuestionTemplate.subject_version_id == session.subject_version_id,
            QuestionTemplate.difficulty <= session.difficulty,
        )
        if session.focus_concept_id:
            q = q.where(QuestionTemplate.concept_id == session.focus_concept_id)
        templates = list((await db.execute(q.order_by(QuestionTemplate.difficulty.desc()).limit(n))).scalars())

        items: list[PracticeItem] = []
        for i, t in enumerate(templates):
            # v1: instantiate static payloads directly (AI generation can plug in here for source='ai')
            item = PracticeItem(
                session_id=session.id,
                concept_id=t.concept_id,
                question_template_id=t.id,
                kind=t.kind,
                difficulty=t.difficulty,
                payload=_public_payload(t.kind, t.payload),
                rubric_id=t.rubric_id,
                ordinal=i,
            )
            db.add(item)
            items.append(item)
        await db.flush()
        return items


def _public_payload(kind: str, payload: dict) -> dict:
    """Strip the answer key before sending an MCQ to the client."""
    if kind == "mcq":
        return {k: v for k, v in payload.items() if k not in ("answer_index", "why")}
    return payload
