from __future__ import annotations

import uuid

import pytest

API = "/api/v1"


@pytest.mark.asyncio
async def test_register_shares_the_ip_throttle(client):
    """Mass account creation from one IP hits the same window as login.

    Runs LAST (zz): it deliberately exhausts the shared test-client IP window.
    Earlier tests never trip it because each successful login clears the window.
    """
    last = None
    for _ in range(11):
        last = await client.post(
            f"{API}/auth/register",
            json={"email": f"spam{uuid.uuid4().hex[:10]}@test.dev",
                  "password": "pw12345678", "display_name": "Spam"},
        )
        if last.status_code == 429:
            break
    assert last.status_code == 429
    assert last.json()["error"]["code"] == "rate_limited"
