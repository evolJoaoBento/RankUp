from __future__ import annotations

from pydantic import BaseModel


class Page(BaseModel):
    limit: int = 20
    offset: int = 0
