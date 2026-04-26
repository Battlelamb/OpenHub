"""UI-06 backend: GET /v1/workflows/ returns the dashboard workflow list."""
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


def test_workflows_list_returns_array_with_jwt_auth(
    test_client: TestClient, admin_headers: dict[str, str], seeded_admin_agent: str
) -> None:
    """JWT admin can hit /v1/workflows/ and receives a JSON array (possibly empty)."""
    r = test_client.get("/v1/workflows/", headers=admin_headers)
    assert r.status_code == 200, r.text
    body = r.json()
    assert isinstance(body, list)
    # If any workflows are running, each has the WorkflowResponse shape
    for wf in body:
        for key in ("run_id", "name", "status", "created_at", "progress", "input_data"):
            assert key in wf, f"missing {key} in {wf}"


def test_workflows_list_unauthenticated_returns_parseable_response(
    test_client: TestClient,
) -> None:
    """No bearer token -> not 405/redirect; CurrentAgent=None means optional auth -> 200 acceptable."""
    r = test_client.get("/v1/workflows/")
    # Optional auth means 200 if no auth required. CurrentAgent = None means optional.
    # Backend behavior: routes_tasks.py search returns 200 without auth too.
    assert r.status_code in (200, 401, 422), f"Unexpected status {r.status_code}: {r.text}"
    assert r.headers.get("content-type", "").startswith("application/json")
