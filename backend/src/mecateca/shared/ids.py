from __future__ import annotations

import os
import time
import uuid


def uuid7() -> uuid.UUID:
    """Time-ordered UUIDv7 (RFC 9562). Good PKs: sortable, index-friendly."""
    unix_ms = int(time.time() * 1000)
    rand = os.urandom(10)
    b = bytearray(16)
    b[0:6] = unix_ms.to_bytes(6, "big")
    b[6:16] = rand
    b[6] = (b[6] & 0x0F) | 0x70          # version 7
    b[8] = (b[8] & 0x3F) | 0x80          # variant
    return uuid.UUID(bytes=bytes(b))


def new_id() -> uuid.UUID:
    return uuid7()
