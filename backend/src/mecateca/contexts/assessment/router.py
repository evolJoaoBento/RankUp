from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from mecateca.contexts.assessment import service
from mecateca.contexts.assessment.schemas import (
    AnswerIn,
    AnswerResult,
    ItemOut,
    PracticeSessionOut,
    StartPracticeIn,
)
from mecateca.contexts.identity.models import User
from mecateca.db.session import get_db
from mecateca.deps import current_user, get_llm_provider, require_role
from mecateca.shared.lang import norm_lang

router = APIRouter(tags=["assessment"])


@router.get("/teacher/test-stats/{subject}", dependencies=[Depends(require_role("teacher", "admin"))])
async def teacher_test_stats(subject: str, db: AsyncSession = Depends(get_db)):
    return await service.test_stats(db, subject)


def _items_out(items) -> list[ItemOut]:
    return [
        ItemOut(
            id=i.id, concept_id=i.concept_id, kind=i.kind,
            difficulty=i.difficulty, payload=i.payload, ordinal=i.ordinal,
        )
        for i in items
    ]


@router.post("/practice/sessions", response_model=PracticeSessionOut)
async def start(
    body: StartPracticeIn, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)
):
    session, items = await service.start_practice(
        db, user.id, body.subject, body.concept, body.difficulty, body.count
    )
    return PracticeSessionOut(
        id=session.id, subject_version_id=session.subject_version_id,
        difficulty=session.difficulty, items=_items_out(items),
    )


@router.post("/tests/{test_id}/start", response_model=PracticeSessionOut)
async def start_test(test_id: uuid.UUID, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    session, items = await service.start_from_test(db, user.id, test_id)
    return PracticeSessionOut(
        id=session.id, subject_version_id=session.subject_version_id,
        difficulty=session.difficulty, items=_items_out(items),
    )


@router.get("/practice/sessions/{session_id}", response_model=PracticeSessionOut)
async def get(session_id: uuid.UUID, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    session, items = await service.get_session_owned(db, user.id, session_id)
    return PracticeSessionOut(
        id=session.id, subject_version_id=session.subject_version_id,
        difficulty=session.difficulty, items=_items_out(items),
    )


@router.post("/questions/{question_id}/grade")
async def grade_question(
    question_id: uuid.UUID,
    body: AnswerIn,
    request: Request,
    user: User = Depends(current_user),
    provider=Depends(get_llm_provider),
    db: AsyncSession = Depends(get_db),
):
    return await service.grade_question(db, provider, question_id, body.raw, norm_lang(request.headers.get("x-lang")))


@router.post("/practice/items/{item_id}/answer", response_model=AnswerResult)
async def answer(
    item_id: uuid.UUID,
    body: AnswerIn,
    request: Request,
    user: User = Depends(current_user),
    provider=Depends(get_llm_provider),
    db: AsyncSession = Depends(get_db),
):
    return await service.submit_answer(db, provider, user.id, item_id, body.raw, norm_lang(request.headers.get("x-lang")))
