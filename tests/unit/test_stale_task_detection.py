"""
Unit tests for stale task detection logic (GSD slice 05-03-01).

A task is "stale" when an agent still holds it (status CLAIMED or RUNNING)
but its lease (`lease_until`) has already expired. That combination means
the agent most likely died or got stuck without releasing the work, so the
task is silently blocked and needs operator/recovery attention.

These tests pin down the detection contract:
  * Task.is_stale(now)            -- per-task predicate
  * TaskService.find_stale_tasks() -- finds every stale task
"""
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

from app.models.tasks import Task, TaskStatus, TaskType, TaskPriority
from app.services.task_service import TaskService


# A fixed reference "now" keeps the per-task tests deterministic regardless
# of the wall-clock time when the suite runs.
NOW = datetime(2026, 5, 20, 12, 0, 0, tzinfo=timezone.utc)
EXPIRED = NOW - timedelta(minutes=5)   # lease ended 5 minutes ago
ACTIVE = NOW + timedelta(minutes=5)    # lease still valid for 5 minutes


def _make_task(*, status: TaskStatus, lease_until) -> Task:
    """Build a minimal Task carrying only the fields staleness depends on."""
    return Task(
        title="demo task",
        description="demo description",
        task_type=TaskType.FEATURE,
        priority=TaskPriority.NORMAL,
        required_capabilities=["python"],
        max_retries=2,
        status=status,
        lease_until=lease_until,
    )


# ---------------------------------------------------------------------------
# Task.is_stale() -- per-task detection
# ---------------------------------------------------------------------------


def test_claimed_task_with_expired_lease_is_stale():
    """A CLAIMED task whose lease is in the past is stale."""
    task = _make_task(status=TaskStatus.CLAIMED, lease_until=EXPIRED)
    assert task.is_stale(now=NOW)


def test_running_task_with_expired_lease_is_stale():
    """A RUNNING task whose lease is in the past is stale."""
    task = _make_task(status=TaskStatus.RUNNING, lease_until=EXPIRED)
    assert task.is_stale(now=NOW)


def test_claimed_task_with_active_lease_is_not_stale():
    """An active (future) lease means the agent is still within its window."""
    task = _make_task(status=TaskStatus.CLAIMED, lease_until=ACTIVE)
    assert not task.is_stale(now=NOW)


def test_completed_task_with_expired_lease_is_not_stale():
    """A finished task is never stale, even though its lease is in the past."""
    task = _make_task(status=TaskStatus.COMPLETED, lease_until=EXPIRED)
    assert not task.is_stale(now=NOW)


def test_failed_task_with_expired_lease_is_not_stale():
    """A failed task is terminal -- an expired lease does not make it stale."""
    task = _make_task(status=TaskStatus.FAILED, lease_until=EXPIRED)
    assert not task.is_stale(now=NOW)


def test_claimed_task_with_no_lease_is_not_stale():
    """No lease set -> nothing has expired -> not stale."""
    task = _make_task(status=TaskStatus.CLAIMED, lease_until=None)
    assert not task.is_stale(now=NOW)


# ---------------------------------------------------------------------------
# TaskService.find_stale_tasks() -- bulk detection
# ---------------------------------------------------------------------------


def test_find_stale_tasks_returns_only_stale_active_tasks():
    """find_stale_tasks() returns CLAIMED/RUNNING tasks with expired leases only."""
    now = datetime.now(timezone.utc)
    expired = now - timedelta(hours=1)
    active = now + timedelta(hours=1)

    stale_claimed = _make_task(status=TaskStatus.CLAIMED, lease_until=expired)
    stale_running = _make_task(status=TaskStatus.RUNNING, lease_until=expired)
    fresh_running = _make_task(status=TaskStatus.RUNNING, lease_until=active)

    service = TaskService(MagicMock())
    fake_repo = MagicMock()
    fake_repo.find_by_status.side_effect = lambda status: {
        TaskStatus.CLAIMED.value: [stale_claimed],
        TaskStatus.RUNNING.value: [stale_running, fresh_running],
    }.get(status, [])
    service.task_repo = fake_repo

    stale = service.find_stale_tasks()

    assert {t.id for t in stale} == {stale_claimed.id, stale_running.id}
