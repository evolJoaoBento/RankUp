from __future__ import annotations

import uuid

import pytest

API = "/api/v1"


async def _make_user(client, name: str) -> tuple[dict, str]:
    """Register + login a fresh user; returns (auth headers, email)."""
    email = f"{name}{uuid.uuid4().hex[:8]}@test.dev"
    r = await client.post(
        f"{API}/auth/register",
        json={"email": email, "password": "pw12345678", "display_name": name},
    )
    assert r.status_code == 201, r.text
    r = await client.post(f"{API}/auth/login", json={"identifier": email, "password": "pw12345678"})
    return {"authorization": f"Bearer {r.json()['access']}"}, email


@pytest.mark.asyncio
async def test_friend_request_flow(client):
    a, _ = await _make_user(client, "Ana")
    b, b_email = await _make_user(client, "Bruno")

    # send request by email
    r = await client.post(f"{API}/friends/requests", headers=a, json={"identifier": b_email})
    assert r.status_code == 200
    assert len(r.json()["outgoing"]) == 1

    # addressee sees it incoming and accepts
    view = (await client.get(f"{API}/friends", headers=b)).json()
    assert len(view["incoming"]) == 1
    req_id = view["incoming"][0]["id"]
    r = await client.post(f"{API}/friends/requests/{req_id}/accept", headers=b)
    assert r.status_code == 200
    assert len(r.json()["friends"]) == 1

    # both sides now list each other
    va = (await client.get(f"{API}/friends", headers=a)).json()
    assert va["friends"][0]["display_name"] == "Bruno"

    # removing works and is mutual
    other_id = va["friends"][0]["user_id"]
    r = await client.delete(f"{API}/friends/{other_id}", headers=a)
    assert r.status_code == 200
    assert r.json()["friends"] == []
    vb = (await client.get(f"{API}/friends", headers=b)).json()
    assert vb["friends"] == []


async def _befriend(client, a, b):
    """a sends, b accepts."""
    me_b = (await client.get(f"{API}/me", headers=b)).json()
    await client.post(f"{API}/friends/requests", headers=a, json={"identifier": me_b["email"]})
    view = (await client.get(f"{API}/friends", headers=b)).json()
    await client.post(f"{API}/friends/requests/{view['incoming'][0]['id']}/accept", headers=b)
    return me_b["id"]


@pytest.mark.asyncio
async def test_duel_requires_friendship(client):
    a, _ = await _make_user(client, "Carla")
    b, _ = await _make_user(client, "Dino")
    me_b = (await client.get(f"{API}/me", headers=b)).json()
    r = await client.post(f"{API}/duels", headers=a, json={"opponent_id": me_b["id"], "subject": "philosophy"})
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_duel_invite_accept_decline(client):
    a, _ = await _make_user(client, "Eva")
    b, _ = await _make_user(client, "Fabio")
    b_id = await _befriend(client, a, b)

    # invite: pending, invitee must act
    r = await client.post(f"{API}/duels", headers=a, json={"opponent_id": b_id, "subject": "philosophy"})
    assert r.status_code == 200, r.text
    duel_id = r.json()["id"]
    mine = (await client.get(f"{API}/duels", headers=b)).json()
    row = next(d for d in mine if d["id"] == duel_id)
    assert row["status"] == "pending" and row["needs_my_action"] is True

    # only the invitee can accept
    r = await client.post(f"{API}/duels/{duel_id}/accept", headers=a)
    assert r.status_code in (400, 403)
    r = await client.post(f"{API}/duels/{duel_id}/accept", headers=b)
    assert r.status_code == 200
    mine = (await client.get(f"{API}/duels", headers=b)).json()
    assert next(d for d in mine if d["id"] == duel_id)["status"] == "setup"

    # a fresh invite can be declined
    r = await client.post(f"{API}/duels", headers=a, json={"opponent_id": b_id, "subject": "philosophy"})
    d2 = r.json()["id"]
    r = await client.post(f"{API}/duels/{d2}/decline", headers=b)
    assert r.status_code == 200
    mine = (await client.get(f"{API}/duels", headers=b)).json()
    assert next(d for d in mine if d["id"] == d2)["status"] == "declined"


@pytest.mark.asyncio
async def test_rating_starts_at_1000_and_leaderboard_hides_unplayed(client):
    a, _ = await _make_user(client, "Gil")
    r = await client.get(f"{API}/duels/rating", headers=a)
    assert r.status_code == 200
    body = r.json()
    assert body["rating"] == 1000 and body["games"] == 0

    lb = (await client.get(f"{API}/duels/leaderboard", headers=a)).json()
    assert all(x["name"] != "Gil" for x in lb)  # games == 0 -> not listed
