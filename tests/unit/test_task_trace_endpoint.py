"""UI-12: GET /v1/tasks/{task_id}/trace returns spans for a task."""
from __future__ import annotations

import json
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def seeded_admin_agent(test_client: TestClient) -> str:
    """
    Insert the test-admin agent row so JWT-auth routes that go through
    get_current_agent find the sub='test-admin' subject in the agents table.
    Idempotent across tests. Mirrors the pattern in tests/integration/test_auto_indexing.py.
    """
    from datetime import datetime, timezone

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
            "desc": "UI-12 trace endpoint test agent",
            "caps": json.dumps([]),
            "labels": json.dumps({}),
            "now": now,
        },
    )
    return "test-admin"


def test_task_trace_returns_empty_list_when_no_spans(
    test_client: TestClient, admin_headers: dict[str, str], seeded_admin_agent: str
) -> None:
    """
    When a task has no trace_events rows, the endpoint returns an empty list
    (not 404). UI consumes [] and renders the TraceTimeline empty state.
    """
    task_id = str(uuid4())

    r = test_client.get(f"/v1/tasks/{task_id}/trace", headers=admin_headers)

    assert r.status_code == 200, r.text
    assert r.json() == []


def test_task_trace_returns_shaped_spans_when_rows_exist(
    test_client: TestClient,
    admin_headers: dict[str, str],
    seeded_admin_agent: str,
) -> None:
    """
    Inserts two trace_events rows for a task and verifies the endpoint returns
    them shaped as TraceSpan objects (id, name, category, duration_ms, level,
    started_at, completed_at). Categories derive from data.category; event_type='error'
    overrides to 'error' category.
    """
    from app.database.connection import get_database

    db = get_database()
    task_id = str(uuid4())
    span1_id = str(uuid4())
    span2_id = str(uuid4())
    trace_id = str(uuid4())

    # Insert a tool-category span
    db.execute(
        "INSERT INTO trace_events (id, trace_id, agent_id, event_type, name, data, task_id, duration_ms, created_at) "
        "VALUES (:id, :tid, :aid, :et, :n, :d, :task, :dur, :now)",
        {
            "id": span1_id,
            "tid": trace_id,
            "aid": "agent-test",
            "et": "span_end",
            "n": "read_file",
            "d": json.dumps({"category": "tool", "level": 0}),
            "task": task_id,
            "dur": 42.0,
            "now": "2026-04-19T10:00:00Z",
        },
    )
    # Insert an error-category span (event_type=error overrides)
    db.execute(
        "INSERT INTO trace_events (id, trace_id, agent_id, event_type, name, data, task_id, duration_ms, created_at) "
        "VALUES (:id, :tid, :aid, :et, :n, :d, :task, :dur, :now)",
        {
            "id": span2_id,
            "tid": trace_id,
            "aid": "agent-test",
            "et": "error",
            "n": "disk_full",
            "d": json.dumps({"level": 1}),
            "task": task_id,
            "dur": 1.5,
            "now": "2026-04-19T10:00:01Z",
        },
    )

    r = test_client.get(f"/v1/tasks/{task_id}/trace", headers=admin_headers)

    assert r.status_code == 200, r.text
    body = r.json()
    assert isinstance(body, list)
    assert len(body) == 2

    # Ordered by created_at ASC
    assert body[0]["id"] == span1_id
    assert body[0]["name"] == "read_file"
    assert body[0]["category"] == "tool"
    assert body[0]["duration_ms"] == 42.0
    assert body[0]["level"] == 0

    assert body[1]["id"] == span2_id
    assert body[1]["category"] == "error"
    assert body[1]["level"] == 1

    # Required TraceSpan keys all present
    for span in body:
        for key in ("id", "name", "category", "duration_ms", "level", "started_at"):
            assert key in span, f"missing {key} in {span}"
