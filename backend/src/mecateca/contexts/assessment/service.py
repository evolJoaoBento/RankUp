from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from mecateca.adapters.llm.base import LLMProvider
from mecateca.contexts.assessment.activity import PracticeTestActivity
from mecateca.contexts.assessment.graders import AIReasoningGrader, Grade, MCQGrader
from mecateca.contexts.assessment.models import Answer, PracticeItem, PracticeSession
from mecateca.contexts.assessment.schemas import AnswerResult
from mecateca.contexts.catalog import service as catalog_service
from mecateca.contexts.assessment.activity import _public_payload
from mecateca.contexts.catalog.models import Concept, Material, QuestionTemplate, Rubric, SubjectVersion, Test
from mecateca.contexts.metering import service as metering
from mecateca.contexts.progression import projector
from mecateca.shared.errors import Forbidden, NotFound


async def start_practice(
    db: AsyncSession,
    user_id: uuid.UUID,
    subject_key: str,
    concept_key: str | None,
    difficulty: int,
    count: int,
) -> tuple[PracticeSession, list[PracticeItem]]:
    sv = await catalog_service.current_version(db, subject_key)
    focus_id = None
    if concept_key:
        c = (
            await db.execute(
                select(Concept).where(Concept.subject_version_id == sv.id, Concept.key == concept_key)
            )
        ).scalar_one_or_none()
        if c is None:
            raise NotFound(f"concept '{concept_key}' not in subject")
        focus_id = c.id

    session = PracticeSession(
        user_id=user_id, subject_version_id=sv.id, focus_concept_id=focus_id, difficulty=difficulty
    )
    db.add(session)
    await db.flush()
    items = await PracticeTestActivity().generate(db, session, n=count)
    return session, items


async def start_from_test(
    db: AsyncSession, user_id: uuid.UUID, test_id: uuid.UUID
) -> tuple[PracticeSession, list[PracticeItem]]:
    test = await db.get(Test, test_id)
    if test is None:
        raise NotFound("test not found")
    templates = list(
        (
            await db.execute(
                select(QuestionTemplate)
                .where(QuestionTemplate.test_id == test_id)
                .order_by(QuestionTemplate.created_at)
            )
        ).scalars()
    )
    if not templates:
        raise NotFound("test has no questions yet")
    session = PracticeSession(
        user_id=user_id, subject_version_id=test.subject_version_id,
        difficulty=max(t.difficulty for t in templates), status="open",
    )
    db.add(session)
    await db.flush()
    items = []
    for i, t in enumerate(templates):
        item = PracticeItem(
            session_id=session.id, concept_id=t.concept_id, question_template_id=t.id,
            kind=t.kind, difficulty=t.difficulty, payload=_public_payload(t.kind, t.payload),
            rubric_id=t.rubric_id, ordinal=i,
        )
        db.add(item)
        items.append(item)
    await db.flush()
    return session, items


async def grade_question(db: AsyncSession, provider: LLMProvider, question_id: uuid.UUID, raw: dict, lang: str = "pt") -> dict:
    """Grade a single answer for flashcard practice — NO progression / EP awarded."""
    q = await db.get(QuestionTemplate, question_id)
    if q is None:
        raise NotFound("question not found")
    if q.kind == "mcq":
        grade = MCQGrader().grade(raw, q.payload)
        answer = {"answer_index": q.payload.get("answer_index"), "why": q.payload.get("why", ""),
                  "options": q.payload.get("options", [])}
    else:
        rubric = await db.get(Rubric, q.rubric_id) if q.rubric_id else None
        criteria = rubric.criteria if rubric else None
        material_body = None
        if q.material_id:
            mat = await db.get(Material, q.material_id)
            material_body = await catalog_service.material_full_text(db, mat) if mat else None
        grade = await AIReasoningGrader(provider).grade(raw, q.payload, criteria, material_body, lang)
        answer = {"reference": (material_body or "")[:1200]}
    return {"correct": grade.correct, "reasoning_score": float(grade.reasoning_score),
            "feedback": grade.feedback, "answer": answer}


async def get_session_owned(
    db: AsyncSession, user_id: uuid.UUID, session_id: uuid.UUID
) -> tuple[PracticeSession, list[PracticeItem]]:
    session = await db.get(PracticeSession, session_id)
    if session is None:
        raise NotFound("session not found")
    if session.user_id != user_id:
        raise Forbidden("not your session")
    items = list(
        (
            await db.execute(
                select(PracticeItem)
                .where(PracticeItem.session_id == session_id)
                .order_by(PracticeItem.ordinal)
            )
        ).scalars()
    )
    return session, items


async def submit_answer(
    db: AsyncSession,
    provider: LLMProvider,
    user_id: uuid.UUID,
    item_id: uuid.UUID,
    raw: dict,
    lang: str = "pt",
) -> AnswerResult:
    item = await db.get(PracticeItem, item_id)
    if item is None:
        raise NotFound("item not found")
    session = await db.get(PracticeSession, item.session_id)
    if session is None or session.user_id != user_id:
        raise Forbidden("not your item")

    existing = (
        await db.execute(select(Answer).where(Answer.item_id == item_id))
    ).scalar_one_or_none()
    if existing is not None:
        return AnswerResult(
            correct=existing.correct,
            reasoning_score=float(existing.reasoning_score),
            feedback=existing.grade.get("feedback", ""),
            xp_delta=0,
            xp_total=0,
            rank="",
            ranked_up=False,
            streak=0,
            already_answered=True,
        )

    template = await db.get(QuestionTemplate, item.question_template_id) if item.question_template_id else None
    ep_award = template.ep_award if template else None
    ep_wrong = template.ep_wrong if template else 0

    # grade
    if item.kind == "mcq":
        payload = template.payload if template else item.payload
        grade: Grade = MCQGrader().grade(raw, payload)
    else:
        rubric = await db.get(Rubric, item.rubric_id) if item.rubric_id else None
        criteria = rubric.criteria if rubric else None
        material_body = None
        if template and template.material_id:
            mat = await db.get(Material, template.material_id)
            material_body = await catalog_service.material_full_text(db, mat) if mat else None
        grade = await AIReasoningGrader(provider).grade(raw, item.payload, criteria, material_body, lang)

    answer = Answer(
        item_id=item.id,
        user_id=user_id,
        raw=raw,
        grade={"feedback": grade.feedback, **grade.detail},
        reasoning_score=grade.reasoning_score,
        correct=grade.correct,
        graded_by=grade.graded_by,
    )
    db.add(answer)
    await db.flush()

    sv = await db.get(SubjectVersion, session.subject_version_id)
    res = await projector.apply_answer_graded(
        db,
        user_id=user_id,
        subject_id=sv.subject_id,
        concept_id=item.concept_id,
        correct=grade.correct,
        reasoning_score=grade.reasoning_score,
        difficulty=item.difficulty,
        profile_key=sv.progression_profile,
        ep_award=ep_award,
        ep_wrong=ep_wrong,
    )

    if grade.usage:
        await metering.record(db, user_id, "grade_reasoning", grade.usage, ref_id=answer.id)

    return AnswerResult(
        correct=grade.correct,
        reasoning_score=grade.reasoning_score,
        feedback=grade.feedback,
        xp_delta=res.xp_delta,
        xp_total=res.xp_total,
        rank=res.rank,
        ranked_up=res.ranked_up,
        streak=res.streak,
    )


async def my_results(db: AsyncSession, user_id: uuid.UUID, limit: int = 10) -> list[dict]:
    """A student's recent test/practice sessions with score aggregates."""
    from sqlalchemy import Integer, String, cast, func

    rows = (
        await db.execute(
            select(
                PracticeSession.id,
                PracticeSession.created_at,
                func.count(Answer.id),
                func.sum(cast(Answer.correct, Integer)),
                func.avg(Answer.reasoning_score),
                # Postgres has no max(uuid) — aggregate as text; any test id of the session works
                func.max(cast(QuestionTemplate.test_id, String)),
            )
            .join(PracticeItem, PracticeItem.session_id == PracticeSession.id)
            .join(Answer, Answer.item_id == PracticeItem.id)
            .outerjoin(QuestionTemplate, QuestionTemplate.id == PracticeItem.question_template_id)
            .where(PracticeSession.user_id == user_id)
            .group_by(PracticeSession.id, PracticeSession.created_at)
            .order_by(PracticeSession.created_at.desc())
            .limit(limit)
        )
    ).all()
    test_ids = [uuid.UUID(tid) for *_x, tid in rows if tid]
    titles = {}
    if test_ids:
        for t_id, title in (await db.execute(select(Test.id, Test.title).where(Test.id.in_(test_ids)))).all():
            titles[str(t_id)] = title
    return [
        {
            "session_id": str(sid),
            "when": created.isoformat(),
            "answered": int(n),
            "correct": int(c or 0),
            "avg_reasoning": round(float(avg or 0), 2),
            "test_title": titles.get(tid),
        }
        for sid, created, n, c, avg, tid in rows
    ]


async def test_stats(db: AsyncSession, subject_key: str) -> list[dict]:
    """Per-test answer aggregates for teachers: attempts, distinct students, % correct."""
    from sqlalchemy import Integer, cast, func

    sv = await catalog_service.current_version(db, subject_key)
    rows = (
        await db.execute(
            select(
                QuestionTemplate.test_id,
                func.count(Answer.id),
                func.count(func.distinct(Answer.user_id)),
                func.avg(cast(Answer.correct, Integer)),
            )
            .join(PracticeItem, PracticeItem.question_template_id == QuestionTemplate.id)
            .join(Answer, Answer.item_id == PracticeItem.id)
            .where(
                QuestionTemplate.subject_version_id == sv.id,
                QuestionTemplate.test_id.is_not(None),
            )
            .group_by(QuestionTemplate.test_id)
        )
    ).all()
    return [
        {
            "test_id": str(t),
            "answers": int(n),
            "students": int(s),
            "pct_correct": round(float(avg or 0) * 100),
        }
        for t, n, s, avg in rows
    ]
