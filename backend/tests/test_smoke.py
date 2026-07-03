from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_health(client):
    r = await client.get("/healthz")
    assert r.status_code == 200
    assert r.json()["llm"] == "fake"


@pytest.mark.asyncio
async def test_graph(client, auth):
    r = await client.get("/api/v1/subjects/philosophy/graph", headers=auth)
    assert r.status_code == 200
    body = r.json()
    assert body["subject"] == "philosophy"
    keys = {c["key"] for c in body["concepts"]}
    assert "epistemologia.cvj" in keys
    assert len(body["edges"]) >= 2  # prerequisite DAG present


@pytest.mark.asyncio
async def test_practice_mcq_awards_xp(client, auth):
    # start a practice session
    r = await client.post(
        "/api/v1/practice/sessions",
        headers=auth,
        json={"subject": "philosophy", "difficulty": 2, "count": 5},
    )
    assert r.status_code == 200
    items = r.json()["items"]
    mcq = next(i for i in items if i["kind"] == "mcq" and "options" in i["payload"])
    # answer-key must NOT leak to the client
    assert "answer_index" not in mcq["payload"]

    # answer correctly (cvj question -> index 1; fall back to 1 for the boolean one)
    payload = mcq["payload"]
    correct_idx = 1 if "verdade" in " ".join(payload["options"]).lower() else 1
    r2 = await client.post(
        f"/api/v1/practice/items/{mcq['id']}/answer",
        headers=auth,
        json={"raw": {"selected_index": correct_idx}},
    )
    assert r2.status_code == 200
    res = r2.json()
    assert "xp_total" in res and "rank" in res

    # idempotency: same item again -> already_answered, no new xp
    r3 = await client.post(
        f"/api/v1/practice/items/{mcq['id']}/answer",
        headers=auth,
        json={"raw": {"selected_index": correct_idx}},
    )
    assert r3.json()["already_answered"] is True
    assert r3.json()["xp_delta"] == 0


@pytest.mark.asyncio
async def test_my_results_lists_graded_sessions(client, auth):
    r = await client.get("/api/v1/me/results", headers=auth)
    assert r.status_code == 200
    rows = r.json()
    assert rows and rows[0]["answered"] >= 1  # session graded in the mcq test above
    assert {"session_id", "when", "correct", "avg_reasoning", "test_title"} <= set(rows[0])


@pytest.mark.asyncio
async def test_reasoning_grading_offline(client, auth):
    r = await client.post(
        "/api/v1/practice/sessions",
        headers=auth,
        json={"subject": "philosophy", "difficulty": 3, "count": 5},
    )
    items = r.json()["items"]
    reasoning = next(i for i in items if i["kind"] == "reasoning")
    long_answer = (
        "Um agente vê um relógio parado que por acaso marca a hora certa; "
        "tem crença verdadeira justificada mas não conhecimento, porque chegou à verdade por sorte."
    )
    r2 = await client.post(
        f"/api/v1/practice/items/{reasoning['id']}/answer",
        headers=auth,
        json={"raw": {"text": long_answer}},
    )
    assert r2.status_code == 200
    assert 0.0 <= r2.json()["reasoning_score"] <= 1.0
