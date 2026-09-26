"""The double-click suite: idempotency key + entity lock, end to end."""

import uuid

from sqlalchemy import create_engine
from sqlalchemy.orm import Session


def _headers(key: str) -> dict:
    return {"Idempotency-Key": key}


def _payload(tenant_id: str, agent_id: str, ticket: str = "123") -> dict:
    return {
        "tenant_id": tenant_id,
        "agent_id": agent_id,
        "entity_type": "ticket",
        "entity_id": ticket,
        "input": {"question": "should we refund?"},
    }


def test_healthz(client):
    assert client.get("/healthz").json() == {"status": "ok"}


def test_create_run_is_accepted_and_queryable(client, tenant_and_agent):
    tenant_id, agent_id = tenant_and_agent
    r = client.post("/v1/runs", json=_payload(tenant_id, agent_id), headers=_headers("k1"))
    assert r.status_code == 202, r.text
    run = r.json()
    assert run["status"] == "queued"
    assert run["entity_id"] == "123"

    fetched = client.get(f"/v1/runs/{run['id']}").json()
    assert fetched["id"] == run["id"]


def test_same_idempotency_key_returns_original_run(client, tenant_and_agent):
    """Request B-same (double-click): caller gets the ORIGINAL run back, 200."""
    tenant_id, agent_id = tenant_and_agent
    first = client.post("/v1/runs", json=_payload(tenant_id, agent_id), headers=_headers("k2"))
    second = client.post("/v1/runs", json=_payload(tenant_id, agent_id), headers=_headers("k2"))
    assert first.status_code == 202
    assert second.status_code == 200
    assert second.json()["id"] == first.json()["id"]


def test_different_key_same_active_entity_gets_409(client, tenant_and_agent):
    """Request B-different: entity busy, even for a different caller/key."""
    tenant_id, agent_id = tenant_and_agent
    ok = client.post("/v1/runs", json=_payload(tenant_id, agent_id), headers=_headers("k3"))
    blocked = client.post("/v1/runs", json=_payload(tenant_id, agent_id), headers=_headers("k4"))
    assert ok.status_code == 202
    assert blocked.status_code == 409


def test_entity_slot_frees_after_terminal_state(client, tenant_and_agent):
    """History is unlimited: once a run reaches a terminal state, new runs are fine."""
    tenant_id, agent_id = tenant_and_agent
    engine = create_engine(client.app.state.settings.database_url)

    first = client.post("/v1/runs", json=_payload(tenant_id, agent_id), headers=_headers("k5")).json()
    with Session(engine) as s:
        from app.models import Run

        run = s.get(Run, uuid.UUID(first["id"]))
        run.status = "succeeded"  # type: ignore[assignment]
        s.commit()

    again = client.post("/v1/runs", json=_payload(tenant_id, agent_id), headers=_headers("k6"))
    assert again.status_code == 202


def test_runs_without_entity_are_never_locked(client, tenant_and_agent):
    """NULL entity columns are distinct in Postgres — ad-hoc runs don't collide."""
    tenant_id, agent_id = tenant_and_agent
    body = {"tenant_id": tenant_id, "agent_id": agent_id, "input": {}}
    a = client.post("/v1/runs", json=body, headers=_headers("k7"))
    b = client.post("/v1/runs", json=body, headers=_headers("k8"))
    assert a.status_code == 202 and b.status_code == 202


def test_replay_requires_terminal_source_and_links_parent(client, tenant_and_agent):
    tenant_id, agent_id = tenant_and_agent
    engine = create_engine(client.app.state.settings.database_url)

    source = client.post("/v1/runs", json=_payload(tenant_id, agent_id), headers=_headers("k9")).json()

    early = client.post(
        f"/v1/runs/{source['id']}/replay", json={}, headers=_headers("k10")
    )
    assert early.status_code == 409  # still queued/active

    with Session(engine) as s:
        from app.models import Run

        run = s.get(Run, uuid.UUID(source["id"]))
        run.status = "failed"  # type: ignore[assignment]
        s.commit()

    forked = client.post(f"/v1/runs/{source['id']}/replay", json={}, headers=_headers("k11"))
    assert forked.status_code == 202
    assert forked.json()["parent_run_id"] == source["id"]


def test_missing_idempotency_key_is_422(client, tenant_and_agent):
    tenant_id, agent_id = tenant_and_agent
    r = client.post("/v1/runs", json=_payload(tenant_id, agent_id))
    assert r.status_code == 422
