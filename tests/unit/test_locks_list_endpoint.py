"""UI-14 backend: GET /v1/locks/ returns active locks list."""
from __future__ import annotations

import json
from datetime import datetime, timezone, timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def seeded_admin_agent(test_client: TestClient) -> str:
    """
    Insert the test-admin agent row so JWT-auth routes that go through
    get_current_agent find the sub='test-admin' subject in the agents table.
    Idempotent across tests. Mirrors the pattern in tests/unit/test_task_trace_endpoint.py.
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
            "desc": "Plan 04-10 dashboard test admin agent",
            "caps": json.dumps([]),
            "labels": json.dumps({}),
            "now": now,
        },
    )
    return "test-admin"


def test_locks_list_returns_empty_when_no_active_locks(
    test_client: TestClient, admin_headers: dict[str, str], seeded_admin_agent: str
) -> None:
    """No rows in resource_locks (or all released) -> []."""
    from app.database.connection import get_database
    db = get_database()
    # Clean any pre-existing test rows
    db.execute("DELETE FROM resource_locks WHERE resource LIKE 'test-empty-%'")
    r = test_client.get("/v1/locks/", headers=admin_headers)
    assert r.status_code == 200, r.text
    body = r.json()
    assert isinstance(body, list)
    # Other tests may seed locks; we only assert our test rows do not appear
    test_rows = [x for x in body if str(x.get("resource_id")).startswith("test-empty-")]
    assert test_rows == []


def test_locks_list_returns_active_locks_with_correct_shape(
    test_client: TestClient, admin_headers: dict[str, str], seeded_admin_agent: str
) -> None:
    """Inserts 2 locks (1 active, 1 released). List returns only the active one with the UI shape."""
    from app.database.connection import get_database
    db = get_database()
    # Clean any pre-existing rows from prior local runs; this repo's test DB can persist.
    db.execute("DELETE FROM resource_locks WHERE resource LIKE 'test-active-%' OR resource LIKE 'test-released-%'")
    now = datetime.now(timezone.utc).isoformat()
    later = (datetime.now(timezone.utc) + timedelta(seconds=300)).isoformat()
    active_id = str(uuid4())
    released_id = str(uuid4())
    db.execute(
        "INSERT INTO resource_locks (id, resource, locked_by, ttl_seconds, expires_at, created_at) "
        "VALUES (:id, :res, :by, :ttl, :exp, :now)",
        {"id": active_id, "res": f"test-active-{active_id}", "by": "agent-x",
         "ttl": 300, "exp": later, "now": now},
    )
    db.execute(
        "INSERT INTO resource_locks (id, resource, locked_by, ttl_seconds, expires_at, created_at, released_at) "
        "VALUES (:id, :res, :by, :ttl, :exp, :now, :now)",
        {"id": released_id, "res": f"test-released-{released_id}", "by": "agent-y",
         "ttl": 300, "exp": later, "now": now},
    )
    r = test_client.get("/v1/locks/", headers=admin_headers)
    assert r.status_code == 200, r.text
    body = r.json()
    active_test = [x for x in body if str(x.get("resource_id")).startswith("test-active-")]
    released_test = [x for x in body if str(x.get("resource_id")).startswith("test-released-")]
    assert len(active_test) == 1, f"Expected 1 active row, got {active_test}"
    assert len(released_test) == 0, "Released locks must be filtered out"
    row = active_test[0]
    for key in ("resource_id", "agent_id", "acquired_at", "expires_at", "conflict"):
        assert key in row, f"missing {key} in {row}"
    assert row["agent_id"] == "agent-x"
    assert row["conflict"] is False  # not yet expired
