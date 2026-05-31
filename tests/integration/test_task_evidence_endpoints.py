"""Integration tests for Phase 10 task evidence API endpoints."""
from __future__ import annotations

import json
from datetime import datetime, timezone

from fastapi.testclient import TestClient


def _create_task(test_client: TestClient, admin_headers: dict[str, str], title: str = "Evidence task") -> str:
    response = test_client.post(
        "/v1/tasks/",
        headers=admin_headers,
        json={
            "title": title,
            "description": "Task used by task evidence endpoint tests.",
            "required_capabilities": [f"phase10-evidence-{title}"],
            "priority": 50,
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["id"]


def _seed_agent(agent_id: str = "test-agent-001") -> None:
    from app.database.connection import get_database

    db = get_database()
    existing = db.fetch_one("SELECT id FROM agents WHERE id = :id", {"id": agent_id})
    if existing:
        return
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
            "id": agent_id,
            "name": "test-agent",
            "desc": "Phase 10 evidence endpoint test agent",
            "caps": json.dumps(["testing"]),
            "labels": json.dumps({}),
            "now": now,
        },
    )


def test_admin_can_create_evidence_with_safe_response(
    test_client: TestClient, admin_headers: dict[str, str]
) -> None:
    task_id = _create_task(test_client, admin_headers, "safe evidence response")

    response = test_client.post(
        f"/v1/tasks/{task_id}/evidence",
        headers=admin_headers,
        json={
            "evidence_type": "test",
            "title": "Focused pytest gate",
            "summary": "Evidence endpoint focused tests passed.",
            "content": {
                "command": "pytest tests/integration/test_task_evidence_endpoints.py",
                "safe_detail": "5 passed",
                "api_token": "should-not-echo",
                "authorization": "Bearer should-not-echo",
            },
            "artifact_ids": ["artifact-123"],
            "outcome": "passed",
            "source_agent_id": "spoofed-agent",
            "labels": {"internal": "true"},
            "metadata": {"raw_log_path": "/home/brunhilde/OpenHub/.env"},
        },
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["task_id"] == task_id
    assert body["evidence_type"] == "test"
    assert body["title"] == "Focused pytest gate"
    assert body["outcome"] == "passed"
    assert body["artifact_ids"] == ["artifact-123"]
    assert body["source_agent_id"] == "test-admin"
    assert body["content"]["safe_detail"] == "5 passed"
    assert "api_token" not in body["content"]
    assert "authorization" not in body["content"]
    assert "labels" not in body
    assert "metadata" not in body


def test_agent_can_create_evidence_for_existing_task(
    test_client: TestClient,
    admin_headers: dict[str, str],
    agent_headers: dict[str, str],
) -> None:
    _seed_agent("test-agent-001")
    task_id = _create_task(test_client, admin_headers, "agent evidence")

    response = test_client.post(
        f"/v1/tasks/{task_id}/evidence",
        headers=agent_headers,
        json={
            "evidence_type": "log",
            "title": "Agent progress note",
            "summary": "Agent emitted sanitized progress evidence.",
            "content": {"line": "working"},
            "outcome": "unknown",
        },
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["source_agent_id"] == "test-agent-001"
    assert body["content"] == {"line": "working"}


def test_list_evidence_returns_oldest_first(
    test_client: TestClient, admin_headers: dict[str, str]
) -> None:
    task_id = _create_task(test_client, admin_headers, "evidence ordering")
    for title, occurred_at in [
        ("Later gate", "2026-05-31T12:02:00Z"),
        ("Earlier gate", "2026-05-31T12:01:00Z"),
    ]:
        response = test_client.post(
            f"/v1/tasks/{task_id}/evidence",
            headers=admin_headers,
            json={
                "evidence_type": "quality_gate",
                "title": title,
                "summary": title,
                "content": {"status": "ok"},
                "outcome": "passed",
                "occurred_at": occurred_at,
            },
        )
        assert response.status_code == 201, response.text

    response = test_client.get(f"/v1/tasks/{task_id}/evidence", headers=admin_headers)

    assert response.status_code == 200, response.text
    body = response.json()
    assert [item["title"] for item in body] == ["Earlier gate", "Later gate"]


def test_evidence_endpoints_return_404_for_unknown_task(
    test_client: TestClient, admin_headers: dict[str, str]
) -> None:
    post_response = test_client.post(
        "/v1/tasks/missing-task/evidence",
        headers=admin_headers,
        json={
            "evidence_type": "test",
            "title": "Missing task evidence",
            "summary": "Should not be stored.",
            "content": {},
        },
    )
    get_response = test_client.get("/v1/tasks/missing-task/evidence", headers=admin_headers)

    assert post_response.status_code == 404, post_response.text
    assert get_response.status_code == 404, get_response.text
    assert "not found" in post_response.text.lower()
    assert "not found" in get_response.text.lower()


def test_evidence_endpoints_require_authentication(
    test_client: TestClient, admin_headers: dict[str, str]
) -> None:
    task_id = _create_task(test_client, admin_headers, "evidence auth")

    post_response = test_client.post(
        f"/v1/tasks/{task_id}/evidence",
        json={
            "evidence_type": "test",
            "title": "Unauthenticated evidence",
            "summary": "Should be rejected.",
            "content": {},
        },
    )
    get_response = test_client.get(f"/v1/tasks/{task_id}/evidence")

    assert post_response.status_code == 401, post_response.text
    assert get_response.status_code == 401, get_response.text
