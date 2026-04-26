"""
Plan 04-10 Task 5: real backend round-trip for the seven dashboard list endpoints.

Each endpoint is hit with a JWT admin Bearer header (no msw, no X-API-Key, no X-Admin-Key)
to prove that the React dashboard's auth surface matches the backend's auth surface.
If this test passes, the gap from 04-UAT.md is closed at the integration level - not just
at the unit-test level where msw mocks could hide a 404/401.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module", autouse=True)
def seeded_admin_agent(test_client: TestClient) -> str:
    """
    Seed the test-admin agent row so JWT-auth routes that go through
    get_current_agent find the sub='test-admin' subject in the agents table.
    Module-scoped autouse so every test in this file gets the seeded agent.
    """
    from app.database.connection import get_database

    db = get_database()
    existing = db.fetch_one(
        "SELECT id FROM agents WHERE id = :id", {"id": "test-admin"}
    )
    if existing:
        return "test-admin"
    now = datetime.now(timezone.utc).isoformat()
    db.execute(
        """INSERT INTO agents (
               id, agent_name, description, capabilities, status,
               labels, created_at, updated_at, last_heartbeat
           ) VALUES (
               :id, :name, :desc, :caps, 'online',
               :labels, :now, :now, :now
           )""",
        {
            "id": "test-admin",
            "name": "test-admin",
            "desc": "Plan 04-10 dashboard live paths test admin agent",
            "caps": json.dumps([]),
            "labels": json.dumps({}),
            "now": now,
        },
    )
    return "test-admin"


def test_agents_discover_available_returns_200_with_jwt(
    test_client: TestClient, admin_headers: dict[str, str]
) -> None:
    r = test_client.get("/v1/agents/discover/available", headers=admin_headers)
    assert r.status_code == 200, r.text
    body = r.json()
    assert "agents" in body, f"expected 'agents' in response, got keys {list(body.keys())}"
    assert isinstance(body["agents"], list)


def test_tasks_search_returns_200_with_jwt(
    test_client: TestClient, admin_headers: dict[str, str]
) -> None:
    r = test_client.get(
        "/v1/tasks/search?page=1&limit=100", headers=admin_headers
    )
    assert r.status_code == 200, r.text
    body = r.json()
    for k in ("tasks", "total", "page", "limit"):
        assert k in body, f"missing {k} in {body}"
    assert isinstance(body["tasks"], list)


def test_costs_summary_returns_200_with_jwt(
    test_client: TestClient, admin_headers: dict[str, str]
) -> None:
    r = test_client.get("/v1/costs/summary", headers=admin_headers)
    assert r.status_code == 200, r.text
    body = r.json()
    assert "per_agent" in body
    assert isinstance(body["per_agent"], list)


def test_memory_keys_returns_200_with_jwt(
    test_client: TestClient, admin_headers: dict[str, str]
) -> None:
    r = test_client.get("/v1/memory/keys", headers=admin_headers)
    assert r.status_code == 200, r.text
    body = r.json()
    assert "keys" in body
    assert isinstance(body["keys"], list)


def test_locks_list_returns_200_with_jwt(
    test_client: TestClient, admin_headers: dict[str, str]
) -> None:
    r = test_client.get("/v1/locks/", headers=admin_headers)
    assert r.status_code == 200, r.text
    body = r.json()
    assert isinstance(body, list), f"expected list, got {type(body).__name__}"


def test_workflows_list_returns_200_with_jwt(
    test_client: TestClient, admin_headers: dict[str, str]
) -> None:
    r = test_client.get("/v1/workflows/", headers=admin_headers)
    assert r.status_code == 200, r.text
    body = r.json()
    assert isinstance(body, list), f"expected list, got {type(body).__name__}"


def test_dlq_list_returns_200_with_jwt(
    test_client: TestClient, admin_headers: dict[str, str]
) -> None:
    r = test_client.get("/v1/dlq/", headers=admin_headers)
    assert r.status_code == 200, r.text
    body = r.json()
    assert "dead_letters" in body
    assert isinstance(body["dead_letters"], list)
