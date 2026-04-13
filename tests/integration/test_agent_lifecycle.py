"""
TEST-04: Integration tests for agent registration, heartbeat, and listing
via the real HTTP API. No mocks - real (tempfile) SQLite backend.
"""
from uuid import uuid4

import pytest

from app.auth.jwt_auth import create_access_token


def _unique_agent_name(prefix: str = "lc-agent") -> str:
    return f"{prefix}-{uuid4().hex[:8]}"


def _register_payload(name: str, caps: list[str] | None = None) -> dict:
    return {
        "agent_name": name,
        "capabilities": caps or ["python"],
        "description": "agent lifecycle integration test",
        "labels": {"env": "test"},
    }


def _headers_for(agent_id: str, agent_name: str) -> dict:
    token = create_access_token(
        subject=agent_id,
        claims={"role": "agent", "agent_name": agent_name},
    )
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_register_agent(test_client):
    """POST /v1/agents/register with a valid body returns the full agent row."""
    payload = _register_payload(_unique_agent_name())

    resp = test_client.post("/v1/agents/register", json=payload)

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["agent_name"] == payload["agent_name"]
    assert body["capabilities"] == payload["capabilities"]
    assert body["status"] == "online"
    assert body["id"]  # uuid issued by the service


def test_register_duplicate_name_conflict(test_client):
    """Registering the same agent_name twice returns 409."""
    name = _unique_agent_name("dupe")
    first = test_client.post("/v1/agents/register", json=_register_payload(name))
    assert first.status_code == 200, first.text

    second = test_client.post("/v1/agents/register", json=_register_payload(name))
    assert second.status_code == 409, second.text
    assert "already exists" in second.text.lower()


def test_agent_heartbeat_keeps_agent_online(test_client):
    """Register -> heartbeat -> agent still shows as online in /online list."""
    reg = test_client.post(
        "/v1/agents/register", json=_register_payload(_unique_agent_name("hb"))
    )
    assert reg.status_code == 200, reg.text
    agent = reg.json()
    headers = _headers_for(agent["id"], agent["agent_name"])

    beat = test_client.post("/v1/agents/heartbeat", headers=headers)
    assert beat.status_code == 200, beat.text
    assert beat.json()["status"] == "heartbeat_received"

    # Confirm the agent is still in the online list after the heartbeat.
    online = test_client.get("/v1/agents/online", headers=headers)
    assert online.status_code == 200, online.text
    ids = [a["id"] for a in online.json()]
    assert agent["id"] in ids


def test_agent_list_contains_registered_agents(test_client):
    """Multiple registrations are all visible through /v1/agents/online."""
    first = test_client.post(
        "/v1/agents/register", json=_register_payload(_unique_agent_name("list-a"))
    ).json()
    second = test_client.post(
        "/v1/agents/register", json=_register_payload(_unique_agent_name("list-b"))
    ).json()

    headers = _headers_for(first["id"], first["agent_name"])
    online = test_client.get("/v1/agents/online", headers=headers)
    assert online.status_code == 200

    ids = {a["id"] for a in online.json()}
    assert first["id"] in ids
    assert second["id"] in ids


def test_registered_agent_status_is_online(test_client):
    """After registration the agent's status in the online list is 'online'."""
    reg = test_client.post(
        "/v1/agents/register", json=_register_payload(_unique_agent_name("status"))
    )
    assert reg.status_code == 200
    agent = reg.json()
    assert agent["status"] == "online"

    headers = _headers_for(agent["id"], agent["agent_name"])
    online = test_client.get("/v1/agents/online", headers=headers)
    assert online.status_code == 200
    rows = {a["id"]: a for a in online.json()}
    assert agent["id"] in rows
    assert rows[agent["id"]]["status"] == "online"
