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
async def test_user_search_and_public_profile(client):
    a, _ = await _make_user(client, "Xavier")
    b, _ = await _make_user(client, "Xenia")

    rows = (await client.get(f"{API}/users/search?q=Xen", headers=a)).json()
    assert any(r["display_name"] == "Xenia" for r in rows)
    target = next(r for r in rows if r["display_name"] == "Xenia")
    assert target["status"] == "none"

    # add straight from a search result (by id)
    r = await client.post(f"{API}/friends/requests", headers=a, json={"user_id": target["user_id"]})
    assert r.status_code == 200
    rows = (await client.get(f"{API}/users/search?q=Xen", headers=a)).json()
    assert next(r2 for r2 in rows if r2["display_name"] == "Xenia")["status"] == "outgoing"

    prof = (await client.get(f"{API}/users/{target['user_id']}/profile?subject=philosophy", headers=a)).json()
    assert prof["display_name"] == "Xenia"
    assert prof["status"] == "outgoing"
    assert {"kudos", "achievements_unlocked", "duel_wins", "member_since"} <= set(prof)


@pytest.mark.asyncio
async def test_photo_upload_is_ai_moderated(client):
    a, _ = await _make_user(client, "Yara")

    # FakeProvider rejects anything containing UNSAFE — fail-closed moderation path
    r = await client.post(
        f"{API}/me/photo", headers=a,
        files={"file": ("x.png", b"\x89PNG UNSAFE bytes", "image/png")},
    )
    assert r.status_code == 400
    assert "modera" in r.json()["error"]["message"]

    # clean image is approved and stored
    r = await client.post(
        f"{API}/me/photo", headers=a,
        files={"file": ("x.png", b"\x89PNG nice classroom portrait", "image/png")},
    )
    assert r.status_code == 200
    photo = r.json()["photo"]
    assert photo.endswith(".png")

    me = (await client.get(f"{API}/me", headers=a)).json()
    img = await client.get(f"{API}/users/{me['id']}/photo")
    assert img.status_code == 200

    r = await client.delete(f"{API}/me/photo", headers=a)
    assert r.json()["photo"] == ""

    # wrong content types bounce before moderation
    r = await client.post(
        f"{API}/me/photo", headers=a,
        files={"file": ("x.gif", b"GIF89a", "image/gif")},
    )
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_announcements_teacher_only(client, auth):
    # plain student cannot post
    r = await client.post(f"{API}/subjects/philosophy/announcements", headers=auth, json={"text": "olá"})
    assert r.status_code == 403

    # a teacher can — promote a fresh user via the seeded admin? use admin creds instead:
    r = await client.post(f"{API}/auth/login", json={"identifier": "admin", "password": "admin"})
    if r.status_code != 200:  # admin not seeded in the test DB -> skip gracefully
        pytest.skip("no seeded admin in test DB")
    admin = {"authorization": f"Bearer {r.json()['access']}"}
    r = await client.post(f"{API}/subjects/philosophy/announcements", headers=admin, json={"text": "Teste sexta-feira!"})
    assert r.status_code == 200
    ann_id = r.json()["id"]

    lst = (await client.get(f"{API}/subjects/philosophy/announcements", headers=auth)).json()
    assert any(a["id"] == ann_id for a in lst)

    # student cannot delete someone else's announcement
    r = await client.delete(f"{API}/announcements/{ann_id}", headers=auth)
    assert r.status_code == 403
    r = await client.delete(f"{API}/announcements/{ann_id}", headers=admin)
    assert r.status_code == 204


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
