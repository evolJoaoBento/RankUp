from __future__ import annotations

import hashlib
import uuid
from datetime import timedelta

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from mecateca.config import get_settings
from mecateca.shared.clock import now

_ph = PasswordHasher()


def hash_password(pw: str) -> str:
    return _ph.hash(pw)


def verify_password(pw: str, hashed: str) -> bool:
    try:
        return _ph.verify(hashed, pw)
    except VerifyMismatchError:
        return False


def needs_rehash(hashed: str) -> bool:
    try:
        return _ph.check_needs_rehash(hashed)
    except Exception:
        return False


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def make_access_token(user_id: uuid.UUID, role: str) -> str:
    s = get_settings()
    payload = {
        "sub": str(user_id),
        "role": role,
        "type": "access",
        "exp": now() + timedelta(minutes=s.jwt_access_ttl_min),
        "iat": now(),
    }
    return jwt.encode(payload, s.jwt_secret, algorithm=s.jwt_alg)


def decode_access_token(token: str) -> dict:
    s = get_settings()
    return jwt.decode(token, s.jwt_secret, algorithms=[s.jwt_alg])
