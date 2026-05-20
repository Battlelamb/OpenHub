"""
Integration tests for the task recovery endpoint (GSD slice 05-03-02).

POST /v1/tasks/{task_id}/recover lets an admin reset a *stale* task -- one an
agent claimed or started but never released, so its lease expired (see
``Task.is_stale``) -- back to QUEUED. A healthy agent can then re-claim it.

These tests pin down the endpoint contract:
  * admin recovers a stale task  -> 200, task is reset to "queued"
  * recovering a non-stale task  -> 400 (resetting live/finished work is unsafe)
  * a non-admin caller           -> 403 (recovery is an admin-only action)
"""
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from app.auth.jwt_auth import create_access_token
from app.database.connection import get_database
from app.database.repositories.tasks import TaskRepository
from app.models.agents import AgentCreate
from app.models.tasks import Task, TaskPriority, TaskStatus, TaskType
from app.services.agent_service import AgentService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _persist_task(*, status: TaskStatus, lease_until: datetime) -> Task:
    """Insert a task straight through the repository.

    Carries only the fields staleness depends on (status + lease_until) plus
    an owner, so the row looks like real claimed/running work. Bypasses
    TaskService so no auto-assignment runs and the state stays exactly as set.
    """
    repo = TaskRepository(get_database())
    return repo.create(
        Task(
            title=f"recover-test-{uuid4().hex[:6]}",
            description="task recovery integration test fixture",
            task_type=TaskType.FEATURE,
            priority=TaskPriority.NORMAL,
            required_capabilities=["python"],
            max_retries=2,
            status=status,
            owner_agent_id=f"ghost-agent-{uuid4().hex[:8]}",
            lease_until=lease_until,
        )
    )


def _expired_lease() -> datetime:
    """A lease deadline an hour in the past -> a claimed/running task is stale."""
    return datetime.now(timezone.utc) - timedelta(hours=1)


def _active_lease() -> datetime:
    """A lease deadline an hour in the future -> the task is NOT stale."""
    return datetime.now(timezone.utc) + timedelta(hours=1)


def _non_admin_headers() -> dict:
    """Register a real agent and return agent-role Bearer headers for it.

    ``get_current_agent`` resolves non-admin token subjects against the agents
    table, so the subject must be a real row. A registered agent therefore
    authenticates successfully -- which is exactly what makes the admin check
    return 403 (forbidden) rather than 401 (unauthenticated).
    """
    agent = AgentService(get_database()).register_agent(
        AgentCreate(
            agent_name=f"recover-nonadmin-{uuid4().hex[:8]}",
            capabilities=["python"],
            description="non-admin caller for the recovery 403 test",
        )
    )
    token = create_access_token(
        subject=agent.id,
        claims={"role": "agent", "agent_name": agent.agent_name},
    )
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_admin_recovers_stale_task_back_to_queued(test_client, admin_headers):
    """A stale RUNNING task (expired lease) is reset to QUEUED on recovery."""
    task = _persist_task(status=TaskStatus.RUNNING, lease_until=_expired_lease())

    resp = test_client.post(
        f"/v1/tasks/{task.id}/recover",
        json={"reason": "agent crashed mid-run"},
        headers=admin_headers,
    )

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "queued"
    assert body["assigned_agent_id"] is None

    # The three slice-mandated fields are cleared at the persistence layer.
    # lease_until is not part of the API response, so assert it on the row.
    persisted = TaskRepository(get_database()).get_by_id(task.id)
    assert persisted is not None
    assert persisted.status == TaskStatus.QUEUED.value
    assert persisted.owner_agent_id is None
    assert persisted.lease_until is None


def test_recovering_non_stale_task_returns_400(test_client, admin_headers):
    """A RUNNING task with a still-valid lease is not stale -> 400, untouched."""
    task = _persist_task(status=TaskStatus.RUNNING, lease_until=_active_lease())

    resp = test_client.post(
        f"/v1/tasks/{task.id}/recover",
        json={"reason": "this should be rejected"},
        headers=admin_headers,
    )

    assert resp.status_code == 400, resp.text

    # A live task must be left exactly as it was.
    persisted = TaskRepository(get_database()).get_by_id(task.id)
    assert persisted is not None
    assert persisted.status == TaskStatus.RUNNING.value
    assert persisted.owner_agent_id == task.owner_agent_id


def test_non_admin_cannot_recover_task(test_client):
    """An authenticated agent-role caller is forbidden from recovery -> 403."""
    task = _persist_task(status=TaskStatus.RUNNING, lease_until=_expired_lease())

    resp = test_client.post(
        f"/v1/tasks/{task.id}/recover",
        json={"reason": "agents may not recover tasks"},
        headers=_non_admin_headers(),
    )

    assert resp.status_code == 403, resp.text
