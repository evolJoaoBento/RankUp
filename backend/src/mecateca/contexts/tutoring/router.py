from __future__ import annotations

import json
import uuid
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from mecateca.contexts.identity.models import User
from mecateca.contexts.metering import quota
from mecateca.contexts.metering import service as metering
from mecateca.contexts.tutoring import service
from mecateca.contexts.tutoring.activity import SocraticChatActivity
from mecateca.contexts.tutoring.models import TutorMessage
from mecateca.contexts.tutoring.schemas import (
    MessageIn,
    MessageOut,
    RenameSessionIn,
    SessionListItem,
    SessionOut,
    StartSessionIn,
)
from mecateca.db.engine import get_sessionmaker
from mecateca.db.session import get_db
from mecateca.shared.lang import norm_lang
from mecateca.deps import current_user, get_llm_provider, require_role

router = APIRouter(tags=["tutoring"])


@router.post("/tutor/sessions", response_model=SessionOut)
async def start(body: StartSessionIn, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    s = await service.start_session(db, user.id, body.subject, body.material)
    return SessionOut(id=s.id, subject_version_id=s.subject_version_id, material_id=s.material_id, title=s.title, status=s.status)


@router.get("/tutor/sessions", response_model=list[SessionListItem])
async def list_sessions(user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    rows = await service.list_sessions(db, user.id)
    return [SessionListItem(id=s.id, title=s.title, material_id=s.material_id) for s in rows]


@router.delete("/tutor/sessions/{session_id}", status_code=204)
async def delete_session(session_id: uuid.UUID, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    await service.soft_delete(db, user.id, session_id)


@router.patch("/tutor/sessions/{session_id}", response_model=SessionListItem)
async def rename_session(session_id: uuid.UUID, body: RenameSessionIn, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    s = await service.rename(db, user.id, session_id, body.title)
    return SessionListItem(id=s.id, title=s.title, material_id=s.material_id)


# ---- admin: deleted-chat recovery ----
@router.get("/admin/tutor/deleted", dependencies=[Depends(require_role("admin"))])
async def list_deleted_chats(db: AsyncSession = Depends(get_db)):
    return await service.list_deleted(db)


@router.post("/admin/tutor/deleted/{session_id}/restore", status_code=204, dependencies=[Depends(require_role("admin"))])
async def restore_chat(session_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    await service.restore(db, session_id)


@router.get("/tutor/sessions/{session_id}", response_model=list[MessageOut])
async def history(session_id: uuid.UUID, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    await service.get_owned(db, user.id, session_id)
    rows = list(
        (
            await db.execute(
                select(TutorMessage)
                .where(TutorMessage.session_id == session_id)
                .order_by(TutorMessage.created_at.asc())
            )
        ).scalars()
    )
    return [MessageOut(id=m.id, role=m.role, content=m.content) for m in rows]


@router.post("/tutor/sessions/{session_id}/messages")
async def post_message(
    session_id: uuid.UUID,
    body: MessageIn,
    request: Request,
    user: User = Depends(current_user),
    provider=Depends(get_llm_provider),
):
    lang = norm_lang(request.headers.get("x-lang"))
    # Own DB session for the lifetime of the stream (request-scoped one closes early).
    sm = get_sessionmaker()

    async def event_stream() -> AsyncIterator[bytes]:
        async with sm() as db:
            session = await service.get_owned(db, user.id, session_id)
            await quota.check_tutor(db, user.id, user.plan)

            db.add(TutorMessage(session_id=session.id, role="user", content=body.text))
            if session.title in ("Tópico livre", "Nova conversa"):
                session.title = body.text[:60]
            await db.flush()

            activity = SocraticChatActivity(provider)
            gen, collected, holder = await activity.stream_reply(db, session, body.text, lang)

            async for chunk in gen:
                yield _sse("token", {"text": chunk})

            text = "".join(collected)
            usage = holder.usage
            msg = TutorMessage(
                session_id=session.id,
                role="assistant",
                content=text,
                tokens_in=usage.tokens_in if usage else 0,
                tokens_out=usage.tokens_out if usage else 0,
                model=usage.model if usage else "",
            )
            db.add(msg)
            await db.flush()
            if usage:
                await metering.record(db, user.id, "tutor_message", usage, ref_id=msg.id)
            await db.commit()
            yield _sse("done", {"message_id": str(msg.id)})

    return StreamingResponse(event_stream(), media_type="text/event-stream")


def _sse(event: str, data: dict) -> bytes:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n".encode()
