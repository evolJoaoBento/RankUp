from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from pydantic import BaseModel

from mecateca.contexts.duels import service
from mecateca.contexts.duels.schemas import AnswerIn, CreateDuelIn, PickMaterialIn, QuestionIn


class QueueIn(BaseModel):
    subject: str
from mecateca.contexts.identity.models import User
from mecateca.db.session import get_db
from mecateca.deps import current_user, get_llm_provider

router = APIRouter(tags=["duels"])


@router.get("/duels")
async def list_my_duels(user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    return await service.list_duels(db, user)


# ---- ranked: rating + matchmaking (per discipline) ----
@router.get("/duels/rating")
async def my_rating(subject: str, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    return await service.rating_view(db, user, subject)


@router.get("/duels/leaderboard")
async def duel_leaderboard(subject: str, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    return await service.leaderboard(db, subject)


@router.post("/duels/ranked/queue")
async def ranked_queue(body: QueueIn, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    return await service.join_queue(db, user, body.subject)


@router.get("/duels/ranked/status")
async def ranked_status(user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    return await service.queue_status(db, user)


@router.delete("/duels/ranked/queue", status_code=204)
async def ranked_leave(user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    await service.leave_queue(db, user)


@router.post("/duels")
async def create_duel(body: CreateDuelIn, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    duel = await service.create(db, user, body.opponent_id, body.subject)
    return {"id": str(duel.id)}


@router.get("/duels/{duel_id}")
async def get_duel(
    duel_id: uuid.UUID,
    user: User = Depends(current_user),
    provider=Depends(get_llm_provider),
    db: AsyncSession = Depends(get_db),
):
    return await service.get_view(db, provider, user, duel_id)


@router.post("/duels/{duel_id}/accept")
async def accept_duel(duel_id: uuid.UUID, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    await service.accept(db, user, duel_id)
    return {"ok": True}


@router.post("/duels/{duel_id}/cancel")
async def cancel_duel(duel_id: uuid.UUID, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    await service.cancel(db, user, duel_id)
    return {"ok": True}


@router.post("/duels/{duel_id}/decline")
async def decline_duel(duel_id: uuid.UUID, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    await service.decline(db, user, duel_id)
    return {"ok": True}


@router.post("/duels/{duel_id}/material")
async def pick_material(duel_id: uuid.UUID, body: PickMaterialIn, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    await service.pick_material(db, user, duel_id, body.material_id)
    return {"ok": True}


@router.post("/duels/{duel_id}/question")
async def submit_question(duel_id: uuid.UUID, body: QuestionIn, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    await service.submit_question(db, user, duel_id, body.text)
    return {"ok": True}


@router.post("/duels/{duel_id}/answer")
async def submit_answer(
    duel_id: uuid.UUID,
    body: AnswerIn,
    user: User = Depends(current_user),
    provider=Depends(get_llm_provider),
    db: AsyncSession = Depends(get_db),
):
    await service.submit_answer(db, provider, user, duel_id, body.text)
    return {"ok": True}


@router.post("/duels/{duel_id}/kudos")
async def duel_kudos(duel_id: uuid.UUID, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    await service.give_kudos(db, user, duel_id)
    return {"ok": True}


@router.get("/me/kudos")
async def my_kudos(user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    return {"received": await service.kudos_received(db, user.id)}


@router.post("/duels/{duel_id}/forfeit")
async def forfeit_duel(duel_id: uuid.UUID, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    await service.forfeit(db, user, duel_id)
    return {"ok": True}
