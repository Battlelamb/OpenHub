"""UI-10/11/13/14: dashboard read endpoints accept JWT (no X-API-Key, no X-Admin-Key)."""
from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def seeded_admin_agent(test_client: TestClient) -> str:
    """Seed the test-admin agent row for JWT auth routes."""
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
            "desc": "Plan 04-10 dashboard test admin agent",
            "caps": json.dumps([]),
            "labels": json.dumps({}),
            "now": now,
        },
    )
    return "test-admin"


def test_costs_summary_accepts_jwt_admin(
    test_client: TestClient, admin_headers: dict[str, str], seeded_admin_agent: str
) -> None:
    """/v1/costs/summary with JWT admin returns 200 (was previously 401 due to X-API-Key requirement)."""
    r = test_client.get("/v1/costs/summary", headers=admin_headers)
    assert r.status_code == 200, r.text
    body = r.json()
    assert "per_agent" in body
    assert isinstance(body["per_agent"], list)


def test_memory_keys_accepts_jwt_admin(
    test_client: TestClient, admin_headers: dict[str, str], seeded_admin_agent: str
) -> None:
    """/v1/memory/keys with JWT admin returns 200."""
    r = test_client.get("/v1/memory/keys", headers=admin_headers)
    assert r.status_code == 200, r.text
    body = r.json()
    assert "keys" in body
    assert isinstance(body["keys"], list)


def test_dlq_list_accepts_jwt_admin(
    test_client: TestClient, admin_headers: dict[str, str], seeded_admin_agent: str
) -> None:
    """/v1/dlq/ with JWT admin returns 200 (was previously 401 due to X-Admin-Key requirement)."""
    r = test_client.get("/v1/dlq/", headers=admin_headers)
    assert r.status_code == 200, r.text
    body = r.json()
    assert "dead_letters" in body
    assert isinstance(body["dead_letters"], list)


def test_dlq_list_still_accepts_x_admin_key(
    test_client: TestClient,
) -> None:
    """Legacy: X-Admin-Key still works (CLI scripts unaffected)."""
    from app.config import get_settings
    s = get_settings()
    ak = getattr(s, "acn_admin_key", None)
    if not ak:
        # Skip in environments without admin key configured
        pytest.skip("acn_admin_key not configured in settings")
    r = test_client.get("/v1/dlq/", headers={"X-Admin-Key": ak})
    assert r.status_code == 200, r.text
