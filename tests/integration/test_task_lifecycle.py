"""
TEST-03: Integration tests for the task lifecycle via the HTTP API.

Covers create / claim / start / complete / fail flows through the real
FastAPI app and the real (tempfile) SQLite test database. No mocks.
"""
from uuid import uuid4

import pytest

from app.auth.jwt_auth import create_access_token
from app.database.connection import get_database
from app.models.agents import AgentCreate
from app.services.agent_service import AgentService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _register_agent_with_caps(capabilities: list[str]):
    """Register a fresh agent directly through the service layer.

    Returns the created ``Agent`` (has id, agent_name, status=online).
    """
    service = AgentService(get_database())
    return service.register_agent(
        AgentCreate(
            agent_name=f"task-lc-{uuid4().hex[:8]}",
            capabilities=capabilities,
            description="task lifecycle integration test fixture",
        )
    )


def _headers_for(agent) -> dict:
    """Build a Bearer header JWT whose ``sub`` matches a real DB agent row.

    ``get_current_agent`` in app/auth/dependencies.py looks up the token
    subject in the agents table, so the sub MUST be an existing agent id.
    """
    token = create_access_token(
        subject=agent.id,
        claims={"role": "agent", "agent_name": agent.agent_name},
    )
    return {"Authorization": f"Bearer {token}"}


def _ghost_cap() -> str:
    """A capability no other test fixture could ever register."""
    return f"ghost-{uuid4().hex}"


def _valid_task_payload(required_capabilities: list[str]) -> dict:
    return {
        "title": f"lifecycle-task-{uuid4().hex[:6]}",
        "description": "integration test task",
        "task_type": "feature",
        "required_capabilities": required_capabilities,
        "priority": 50,
        "max_retries": 2,
    }


@pytest.fixture
def claim_agent(test_client):
    """A freshly registered agent whose JWT is accepted by CurrentAgent."""
    agent = _register_agent_with_caps(["claimant"])
    return agent, _headers_for(agent)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_create_task(test_client, claim_agent):
    """POST /v1/tasks/ with a valid payload returns 200 with a task id."""
    _, headers = claim_agent

    resp = test_client.post(
        "/v1/tasks/",
        json=_valid_task_payload([_ghost_cap()]),
        headers=headers,
    )

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "id" in body and body["id"]
    assert body["status"] in ("queued", "claimed", "running")


def test_create_task_missing_fields(test_client, claim_agent):
    """Missing required fields yields 422 from Pydantic validation."""
    _, headers = claim_agent

    resp = test_client.post(
        "/v1/tasks/",
        json={"title": "only-title"},  # missing description, capabilities
        headers=headers,
    )

    assert resp.status_code == 422, resp.text


def test_claim_task(test_client, claim_agent):
    """Create a task that cannot auto-assign, then claim it via HTTP."""
    _, headers = claim_agent

    # Ghost capability ensures no agent auto-claims - task stays QUEUED.
    create = test_client.post(
        "/v1/tasks/",
        json=_valid_task_payload([_ghost_cap()]),
        headers=headers,
    )
    assert create.status_code == 200, create.text
    task_id = create.json()["id"]

    claim = test_client.post(
        f"/v1/tasks/{task_id}/claim",
        headers=headers,
    )
    assert claim.status_code == 200, claim.text
    assert claim.json()["status"] == "claimed"


def test_start_task(test_client, claim_agent):
    """Full create -> claim -> start transitions a task to running."""
    _, headers = claim_agent

    create = test_client.post(
        "/v1/tasks/",
        json=_valid_task_payload([_ghost_cap()]),
        headers=headers,
    )
    task_id = create.json()["id"]

    assert test_client.post(
        f"/v1/tasks/{task_id}/claim", headers=headers
    ).status_code == 200

    start = test_client.post(
        f"/v1/tasks/{task_id}/start", headers=headers
    )
    assert start.status_code == 200, start.text
    assert start.json()["status"] == "started"

    # Verify server-side persisted status is running.
    fetched = test_client.get(f"/v1/tasks/{task_id}", headers=headers)
    assert fetched.status_code == 200
    assert fetched.json()["status"] == "running"


def test_complete_task_full_lifecycle(test_client, claim_agent):
    """create -> claim -> start -> complete ends with status COMPLETED."""
    _, headers = claim_agent

    task_id = test_client.post(
        "/v1/tasks/",
        json=_valid_task_payload([_ghost_cap()]),
        headers=headers,
    ).json()["id"]

    assert test_client.post(
        f"/v1/tasks/{task_id}/claim", headers=headers
    ).status_code == 200
    assert test_client.post(
        f"/v1/tasks/{task_id}/start", headers=headers
    ).status_code == 200

    complete = test_client.post(
        f"/v1/tasks/{task_id}/complete",
        json={
            "result_summary": "all green",
            "output": {"lines_changed": 42},
            "artifact_ids": [],
        },
        headers=headers,
    )
    assert complete.status_code == 200, complete.text
    assert complete.json()["status"] == "completed"

    fetched = test_client.get(f"/v1/tasks/{task_id}", headers=headers)
    assert fetched.json()["status"] == "completed"


def test_fail_task_non_retryable(test_client, claim_agent):
    """Non-retryable failure after start transitions to FAILED."""
    _, headers = claim_agent

    task_id = test_client.post(
        "/v1/tasks/",
        # Force max_retries=0 so a non-retryable fail is terminal even
        # if the executor later flips retryable by accident.
        json={**_valid_task_payload([_ghost_cap()]), "max_retries": 0},
        headers=headers,
    ).json()["id"]

    assert test_client.post(
        f"/v1/tasks/{task_id}/claim", headers=headers
    ).status_code == 200
    assert test_client.post(
        f"/v1/tasks/{task_id}/start", headers=headers
    ).status_code == 200

    fail = test_client.post(
        f"/v1/tasks/{task_id}/fail",
        json={
            "error_message": "boom",
            "error_code": "E_BOOM",
            "retryable": False,
        },
        headers=headers,
    )
    assert fail.status_code == 200, fail.text
    assert fail.json()["status"] == "failed"

    fetched = test_client.get(f"/v1/tasks/{task_id}", headers=headers)
    assert fetched.json()["status"] == "failed"


def test_claim_already_claimed_task(test_client, claim_agent):
    """Re-claiming an already-claimed task is rejected by the API (400)."""
    _, headers = claim_agent

    task_id = test_client.post(
        "/v1/tasks/",
        json=_valid_task_payload([_ghost_cap()]),
        headers=headers,
    ).json()["id"]

    first = test_client.post(f"/v1/tasks/{task_id}/claim", headers=headers)
    assert first.status_code == 200, first.text

    # Same agent tries to claim again - task is no longer QUEUED, so
    # task_service.claim_task returns False and the route raises 400.
    second = test_client.post(f"/v1/tasks/{task_id}/claim", headers=headers)
    assert second.status_code == 400, second.text
