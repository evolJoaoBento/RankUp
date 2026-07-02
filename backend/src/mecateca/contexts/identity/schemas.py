from __future__ import annotations

import uuid

from pydantic import BaseModel, EmailStr, Field


class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    display_name: str = Field(min_length=1, max_length=120)


class LoginIn(BaseModel):
    identifier: str  # email or username
    password: str


class ChangePasswordIn(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)


class RefreshIn(BaseModel):
    refresh: str


class TokenPair(BaseModel):
    access: str
    refresh: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: uuid.UUID
    email: EmailStr
    username: str | None = None
    display_name: str
    role: str
    plan: str
    locale: str
    background: str | None = None


class AdminUserOut(BaseModel):
    id: uuid.UUID
    email: EmailStr
    username: str | None = None
    display_name: str
    role: str
    plan: str
    background: str | None = None


class UpdateUserIn(BaseModel):
    role: str | None = None
    plan: str | None = None
    background: str | None = None
    set_background: bool = False  # explicit flag so null = clear


class BackgroundIn(BaseModel):
    background: str | None = None  # rank name, or null to clear (auto)
