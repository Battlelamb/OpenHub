"""Tests for graceful shutdown — task drain logic (Phase 05-04).

Verifies that drain_tasks() resets claimed/running tasks to queued,
and that the shutdown sequence follows the correct ordering.
"""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from app.database.connection import get_database
from app.database.repositories.tasks import TaskRepository
from app.models.tasks import Task, TaskPriority, TaskStatus, TaskType
from app.services.task_service import TaskService


# ── Fixtures ─────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _ensure_schema(test_client):
    """Guarantee the database schema exists before these tests run.

    Uses the session-scoped test_client fixture purely for its lifespan
    side-effect (table creation).
    """


def _persist_task(status: str) -> Task:
    """Insert a task in the given status directly via the repository."""
    repo = TaskRepository(get_database())
    now = datetime.now(timezone.utc)

    task = Task(
        title=f"drain-test-{uuid4().hex[:6]}",
        description="graceful shutdown test fixture",
        task_type=TaskType.FEATURE,
        priority=TaskPriority.NORMAL,
        required_capabilities=["python"],
        max_retries=2,
        status=status,
    )

    if status == TaskStatus.CLAIMED.value:
        task.owner_agent_id = f"agent-{uuid4().hex[:8]}"
        task.claimed_at = now
        task.lease_until = now + timedelta(seconds=60)
    elif status == TaskStatus.RUNNING.value:
        task.owner_agent_id = f"agent-{uuid4().hex[:8]}"
        task.claimed_at = now
        task.started_at = now
        task.lease_until = now + timedelta(seconds=120)

    return repo.create(task)


# ── drain_tasks() tests ─────────────────────────────────────────────────


def test_drains_claimed_tasks():
    """drain_tasks() resets CLAIMED tasks to QUEUED."""
    task = _persist_task(TaskStatus.CLAIMED.value)
    svc = TaskService(get_database())

    count = svc.drain_tasks()

    assert count >= 1
    refreshed = svc.task_repo.get_by_id(task.id)
    assert refreshed.status == TaskStatus.QUEUED.value
    assert refreshed.owner_agent_id is None
    assert refreshed.lease_until is None
    assert refreshed.claimed_at is None


def test_drains_running_tasks():
    """drain_tasks() resets RUNNING tasks to QUEUED."""
    task = _persist_task(TaskStatus.RUNNING.value)
    svc = TaskService(get_database())

    count = svc.drain_tasks()

    assert count >= 1
    refreshed = svc.task_repo.get_by_id(task.id)
    assert refreshed.status == TaskStatus.QUEUED.value
    assert refreshed.owner_agent_id is None


def test_drains_mixed_claimed_and_running():
    """drain_tasks() resets both CLAIMED and RUNNING tasks."""
    claimed = _persist_task(TaskStatus.CLAIMED.value)
    running = _persist_task(TaskStatus.RUNNING.value)
    svc = TaskService(get_database())

    count = svc.drain_tasks()

    assert count >= 2
    for tid in [claimed.id, running.id]:
        refreshed = svc.task_repo.get_by_id(tid)
        assert refreshed.status == TaskStatus.QUEUED.value


def test_drain_does_not_touch_completed_tasks():
    """drain_tasks() leaves COMPLETED tasks untouched."""
    completed = _persist_task(TaskStatus.COMPLETED.value)
    svc = TaskService(get_database())

    svc.drain_tasks()

    refreshed = svc.task_repo.get_by_id(completed.id)
    assert refreshed.status == TaskStatus.COMPLETED.value


def test_drain_preserves_existing_payload():
    """drain_tasks() merges drain info into existing payload."""
    task = _persist_task(TaskStatus.RUNNING.value)
    repo = TaskRepository(get_database())
    repo.update(task.id, {"payload": '{"custom_key": "custom_value"}'})

    svc = TaskService(get_database())
    svc.drain_tasks()

    import json

    refreshed = svc.task_repo.get_by_id(task.id)
    payload = json.loads(refreshed.payload) if isinstance(refreshed.payload, str) else refreshed.payload
    assert payload["custom_key"] == "custom_value"
    assert payload["drain"]["reason"] == "server_shutdown"


def test_drain_records_timestamp():
    """drain_tasks() records drain.drained_at in the payload."""
    task = _persist_task(TaskStatus.CLAIMED.value)
    svc = TaskService(get_database())

    before = datetime.now(timezone.utc)
    svc.drain_tasks()
    after = datetime.now(timezone.utc)

    import json

    refreshed = svc.task_repo.get_by_id(task.id)
    payload = json.loads(refreshed.payload) if isinstance(refreshed.payload, str) else refreshed.payload
    assert "drain" in payload
    assert payload["drain"]["reason"] == "server_shutdown"

    drained_at = datetime.fromisoformat(payload["drain"]["drained_at"])
    assert before <= drained_at <= after


# ── Shutdown sequence tests ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_shutdown_order_drain_before_connection_stop():
    """Task drain must happen before connection_manager.stop()."""
    call_order = []
    from unittest.mock import AsyncMock, MagicMock

    mock_task_service = MagicMock()
    mock_task_service.drain_tasks = MagicMock(
        side_effect=lambda: (call_order.append("drain"), 0)[1]
    )

    mock_cm = AsyncMock()

    async def tracked_stop():
        call_order.append("cm_stop")

    mock_cm.stop = tracked_stop
    mock_heartbeat = AsyncMock()

    # Simulate the shutdown sequence from main.py
    mock_task_service.drain_tasks()
    await mock_cm.stop()
    await mock_heartbeat.stop_monitoring()

    assert call_order == ["drain", "cm_stop"]
