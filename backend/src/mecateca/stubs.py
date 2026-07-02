from __future__ import annotations

from fastapi import APIRouter

# Designed-for, not built in v1. Interfaces exist; endpoints announce themselves.
router = APIRouter(tags=["not-implemented"])

_SOON = {"status": "not_implemented", "phase": "post-v1"}


@router.api_route("/evaluation/{path:path}", methods=["GET", "POST"], status_code=501)
async def evaluation_stub(path: str):
    return {**_SOON, "context": "evaluation"}


@router.api_route("/credentials/{path:path}", methods=["GET", "POST"], status_code=501)
async def credentials_stub(path: str):
    return {**_SOON, "context": "credentials"}
