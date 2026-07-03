from __future__ import annotations

import pytest

from test_social_duels import API, _befriend, _make_user


async def _pick_materials(client, duel_id, a, b):
    mats = (await client.get(f"{API}/subjects/philosophy/material", headers=a)).json()
    if not mats:  # test DB loads the pack only — add one study material
        r = await client.post(
            f"{API}/subjects/philosophy/material", headers=a,
            json={"title": "Validade e verdade", "body": "A validade aplica-se a argumentos; a verdade a proposições."},
        )
        assert r.status_code == 200, r.text
        mats = (await client.get(f"{API}/subjects/philosophy/material", headers=a)).json()
    assert mats
    for h in (a, b):
        r = await client.post(
            f"{API}/duels/{duel_id}/material", headers=h, json={"material_id": mats[0]["id"]}
        )
        assert r.status_code == 200, r.text


async def _play_round(client, duel_id, a, b):
    """One round: asker submits the question, both answer."""
    va = (await client.get(f"{API}/duels/{duel_id}", headers=a)).json()
    assert va["status"] == "active" and va["phase"] == "question"
    asker, other = (a, b) if va["current"]["i_am_asker"] else (b, a)
    r = await client.post(
        f"{API}/duels/{duel_id}/question", headers=asker,
        json={"text": "Explica a diferença entre validade e verdade."},
    )
    assert r.status_code == 200, r.text
    for h in (asker, other):
        r = await client.post(
            f"{API}/duels/{duel_id}/answer", headers=h,
            json={"text": "A validade aplica-se a argumentos porque depende da forma lógica."},
        )
        assert r.status_code == 200, r.text


@pytest.mark.asyncio
async def test_full_friendly_duel_is_judged_to_completion(client):
    a, _ = await _make_user(client, "Hugo")
    b, _ = await _make_user(client, "Ines")
    b_id = await _befriend(client, a, b)

    duel_id = (await client.post(
        f"{API}/duels", headers=a, json={"opponent_id": b_id, "subject": "philosophy"}
    )).json()["id"]
    await client.post(f"{API}/duels/{duel_id}/accept", headers=b)
    await _pick_materials(client, duel_id, a, b)

    v = (await client.get(f"{API}/duels/{duel_id}", headers=a)).json()
    total = v["total_rounds"]
    for _ in range(total):
        await _play_round(client, duel_id, a, b)

    v = (await client.get(f"{API}/duels/{duel_id}", headers=a)).json()
    assert v["status"] == "complete"
    assert len(v["history"]) == total
    # FakeProvider's judge returns no winner -> every round is a draw (1 pt each)
    assert v["result"] == "draw"
    assert v["my_points"] == v["opp_points"] == total
    # unranked duels never touch Elo
    ra = (await client.get(f"{API}/duels/rating", headers=a)).json()
    assert ra["rating"] == 1000 and ra["games"] == 0


@pytest.mark.asyncio
async def test_cancel_is_consequence_free(client):
    a, _ = await _make_user(client, "Leo")
    b, _ = await _make_user(client, "Mia")
    b_id = await _befriend(client, a, b)

    # pending: only the challenger can cancel; nobody wins
    duel_id = (await client.post(
        f"{API}/duels", headers=a, json={"opponent_id": b_id, "subject": "philosophy"}
    )).json()["id"]
    r = await client.post(f"{API}/duels/{duel_id}/cancel", headers=b)
    assert r.status_code in (400, 403)
    r = await client.post(f"{API}/duels/{duel_id}/cancel", headers=a)
    assert r.status_code == 200
    row = next(d for d in (await client.get(f"{API}/duels", headers=a)).json() if d["id"] == duel_id)
    assert row["status"] == "cancelled" and row["won"] is None

    # setup: inside the 3s grace either player may still leave freely
    d2 = (await client.post(
        f"{API}/duels", headers=a, json={"opponent_id": b_id, "subject": "philosophy"}
    )).json()["id"]
    await client.post(f"{API}/duels/{d2}/accept", headers=b)
    r = await client.post(f"{API}/duels/{d2}/cancel", headers=b)
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_ranked_matchmaking_and_elo_on_forfeit(client):
    a, _ = await _make_user(client, "Joao")
    b, _ = await _make_user(client, "Katia")

    r1 = (await client.post(f"{API}/duels/ranked/queue", headers=a, json={"subject": "philosophy"})).json()
    assert r1["state"] == "queued"
    r2 = (await client.post(f"{API}/duels/ranked/queue", headers=b, json={"subject": "philosophy"})).json()
    assert r2["state"] == "matched"
    duel_id = r2["duel_id"]

    # the first player learns about the match via status polling
    s = (await client.get(f"{API}/duels/ranked/status", headers=a)).json()
    assert s == {"state": "matched", "duel_id": duel_id}

    v = (await client.get(f"{API}/duels/{duel_id}", headers=a)).json()
    assert v["ranked"] is True

    # forfeit ends it and applies Elo (equal ratings -> +16 / -16)
    r = await client.post(f"{API}/duels/{duel_id}/forfeit", headers=a)
    assert r.status_code == 200
    ra = (await client.get(f"{API}/duels/rating", headers=a)).json()
    rb = (await client.get(f"{API}/duels/rating", headers=b)).json()
    assert (ra["rating"], ra["losses"], ra["games"]) == (984, 1, 1)
    assert (rb["rating"], rb["wins"], rb["games"]) == (1016, 1, 1)
