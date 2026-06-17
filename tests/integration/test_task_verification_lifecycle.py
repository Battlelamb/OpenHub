"""Phase 10-05 verification lifecycle HTTP contract."""
from __future__ import annotations

from uuid import uuid4

from app.auth.jwt_auth import create_access_token
from app.database.connection import get_database
from app.models.agents import AgentCreate
from app.services.agent_service import AgentService


def _register_agent_with_caps(capabilities: list[str]):
    service = AgentService(get_database())
    return service.register_agent(
        AgentCreate(
            agent_name=f"verification-lc-{uuid4().hex[:8]}",
            capabilities=capabilities,
            description="verification lifecycle integration test fixture",
        )
    )


def _headers_for(agent) -> dict[str, str]:
    token = create_access_token(
        subject=agent.id,
        claims={"role": "agent", "agent_name": agent.agent_name},
    )
    return {"Authorization": f"Bearer {token}"}


def _ghost_cap() -> str:
    return f"vg-{uuid4().hex[:16]}"


def _create_claimed_started_task(test_client, headers: dict[str, str]) -> str:
    task_id = test_client.post(
        "/v1/tasks/",
        headers=headers,
        json={
            "title": f"verification-lifecycle-{uuid4().hex[:6]}",
            "description": "task should await verification after agent completion claim",
            "task_type": "feature",
            "required_capabilities": [_ghost_cap()],
            "priority": 50,
        },
    ).json()["id"]
    assert test_client.post(f"/v1/tasks/{task_id}/claim", headers=headers).status_code == 200
    assert test_client.post(f"/v1/tasks/{task_id}/start", headers=headers).status_code == 200
    return task_id


def test_agent_completion_claim_waits_for_quality_gate(test_client, admin_headers: dict[str, str]) -> None:
    agent = _register_agent_with_caps(["verification"])
    headers = _headers_for(agent)
    task_id = _create_claimed_started_task(test_client, headers)

    complete = test_client.post(
        f"/v1/tasks/{task_id}/complete",
        headers=headers,
        json={
            "result_summary": "agent claims implementation is done",
            "output": {"summary": "all local steps claimed green"},
            "artifact_ids": ["artifact-verification-claim"],
        },
    )

    assert complete.status_code == 200, complete.text
    assert complete.json()["status"] == "waiting_approval"
    assert "verification" in complete.json()["message"].lower()

    fetched = test_client.get(f"/v1/tasks/{task_id}", headers=headers)
    assert fetched.status_code == 200, fetched.text
    assert fetched.json()["status"] == "waiting_approval"
    assert fetched.json()["completed_at"] is None

    pending_state = test_client.get(f"/v1/tasks/{task_id}/verification", headers=admin_headers)
    assert pending_state.status_code == 200, pending_state.text
    assert pending_state.json()["lifecycle_state"] == "awaiting_quality_gate"
    assert pending_state.json()["ready_for_completion"] is False

    gate = test_client.post(
        f"/v1/tasks/{task_id}/evidence",
        headers=admin_headers,
        json={
            "evidence_type": "quality_gate",
            "title": "Full verification gate",
            "summary": "Backend/service verification passed.",
            "content": {"command": "pytest", "exit_code": 0},
            "outcome": "passed",
            "occurred_at": "2026-06-17T12:30:00Z",
        },
    )
    assert gate.status_code == 201, gate.text

    verified_state = test_client.get(f"/v1/tasks/{task_id}/verification", headers=admin_headers)
    assert verified_state.status_code == 200, verified_state.text
    body = verified_state.json()
    assert body["task_status"] == "waiting_approval"
    assert body["lifecycle_state"] == "quality_gate_passed"
    assert body["ready_for_completion"] is True
    assert body["latest_quality_gate"]["title"] == "Full verification gate"
    assert body["latest_quality_gate"]["outcome"] == "passed"

    # Quality-gate evidence makes the task ready for admin/human closeout; it must
    # never auto-transition the canonical task status to completed.
    still_waiting = test_client.get(f"/v1/tasks/{task_id}", headers=admin_headers)
    assert still_waiting.status_code == 200, still_waiting.text
    assert still_waiting.json()["status"] == "waiting_approval"
