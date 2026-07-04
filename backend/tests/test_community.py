from __future__ import annotations

import pytest

from test_social_duels import API, _befriend, _make_user


@pytest.mark.asyncio
async def test_update_me_name_username_avatar(client):
    a, _ = await _make_user(client, "Nuno")
    b, _ = await _make_user(client, "Olga")

    r = await client.patch(f"{API}/me", headers=a, json={"display_name": "Nuno M.", "username": "nuno_m", "avatar": "owl"})
    assert r.status_code == 200
    body = r.json()
    assert (body["display_name"], body["username"], body["avatar"]) == ("Nuno M.", "nuno_m", "owl")

    # username uniqueness
    r = await client.patch(f"{API}/me", headers=b, json={"username": "nuno_m"})
    assert r.status_code == 409
    # invalid characters rejected by validation
    r = await client.patch(f"{API}/me", headers=b, json={"username": "Olga Silva!"})
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_direct_messages_friends_only(client):
    a, _ = await _make_user(client, "Rui")
    b, _ = await _make_user(client, "Sara")
    me_b = (await client.get(f"{API}/me", headers=b)).json()

    # not friends yet -> blocked
    r = await client.post(f"{API}/messages/{me_b['id']}", headers=a, json={"text": "olá"})
    assert r.status_code == 403

    b_id = await _befriend(client, a, b)
    r = await client.post(f"{API}/messages/{b_id}", headers=a, json={"text": "olá Sara!"})
    assert r.status_code == 200

    # unread for Sara until she opens the thread
    u = (await client.get(f"{API}/messages/unread", headers=b)).json()
    assert u["total"] == 1
    thread = (await client.get(f"{API}/messages/{r.json()['from_id']}", headers=b)).json()
    assert thread[-1]["text"] == "olá Sara!"
    u = (await client.get(f"{API}/messages/unread", headers=b)).json()
    assert u["total"] == 0


@pytest.mark.asyncio
async def test_duel_kudos_once_per_player(client):
    a, _ = await _make_user(client, "Tomas")
    b, _ = await _make_user(client, "Vera")
    b_id = await _befriend(client, a, b)
    duel_id = (await client.post(
        f"{API}/duels", headers=a, json={"opponent_id": b_id, "subject": "philosophy"}
    )).json()["id"]
    await client.post(f"{API}/duels/{duel_id}/accept", headers=b)

    # not finished yet
    r = await client.post(f"{API}/duels/{duel_id}/kudos", headers=a)
    assert r.status_code == 400

    await client.post(f"{API}/duels/{duel_id}/forfeit", headers=b)
    r = await client.post(f"{API}/duels/{duel_id}/kudos", headers=a)
    assert r.status_code == 200
    r = await client.post(f"{API}/duels/{duel_id}/kudos", headers=a)
    assert r.status_code == 400  # only once

    k = (await client.get(f"{API}/me/kudos", headers=b)).json()
    assert k["received"] == 1
