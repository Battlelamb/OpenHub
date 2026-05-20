"""
Unit tests for the stale task listing endpoint (GSD slice 05-03-03).

``GET /v1/tasks/stale`` lists every task currently stuck with an expired
lease -- one an agent claimed or started but never released (see
``Task.is_stale``). It is read-only discovery (no auth required) and returns
a compact row per task: id, title, status, owner_agent_id, lease_until and
``stale_seconds`` (how long the task has been stale).

These tests pin down the *endpoint* contract. They override the task service
with a controllable fake repository, so the real ``find_stale_tasks()``
staleness filter still runs but the input set is deterministic -- no shared
database state, no test-ordering flakiness.
"""
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest

from app.api.routes_tasks import get_task_service
from app.main import app
from app.models.tasks import Task, TaskPriority, TaskStatus, TaskType
from app.services.task_service import TaskService


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


def _make_task(
    *,
    status: TaskStatus,
    lease_until,
    title: str = "stale-listing demo",
    owner: str = "agent-x",
) -> Task:
    """Build a Task carrying only the fields the stale-listing endpoint reports."""
    return Task(
        title=title,
        description="stale listing endpoint test fixture",
        task_type=TaskType.FEATURE,
        priority=TaskPriority.NORMAL,
        required_capabilities=["python"],
        max_retries=2,
        status=status,
        owner_agent_id=owner,
        lease_until=lease_until,
    )


@pytest.fixture()
def stale_tasks_repo():
    """Override ``get_task_service`` with a service backed by a fake repository.

    Yields a setter: call it with the CLAIMED / RUNNING tasks the fake
    repository should expose. The endpoint then runs the *real*
    ``TaskService.find_stale_tasks()`` filter over exactly those tasks, so
    each test controls staleness precisely without touching the database.
    """
    service = TaskService(MagicMock())
    fake_repo = MagicMock()
    service.task_repo = fake_repo

    def _set(*, claimed=(), running=()) -> None:
        fake_repo.find_by_status.side_effect = lambda status: {
            TaskStatus.CLAIMED.value: list(claimed),
            TaskStatus.RUNNING.value: list(running),
        }.get(status, [])

    _set()  # default: nothing claimed or running
    app.dependency_overrides[get_task_service] = lambda: service
    yield _set
    app.dependency_overrides.pop(get_task_service, None)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_stale_listing_returns_empty_list_when_no_stale_tasks(
    test_client, stale_tasks_repo
):
    """With no CLAIMED/RUNNING tasks at all, the endpoint returns []."""
    stale_tasks_repo()  # nothing claimed or running

    resp = test_client.get("/v1/tasks/stale")

    assert resp.status_code == 200, resp.text
    assert resp.json() == []


def test_stale_listing_returns_stale_task_with_expected_fields(
    test_client, stale_tasks_repo
):
    """A stale task is returned with all six reported fields populated."""
    expired = datetime.now(timezone.utc) - timedelta(hours=1)
    task = _make_task(
        status=TaskStatus.CLAIMED,
        lease_until=expired,
        title="ghost-claimed-task",
        owner="agent-ghost-1",
    )
    stale_tasks_repo(claimed=[task])

    resp = test_client.get("/v1/tasks/stale")

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert len(body) == 1

    row = body[0]
    assert row["id"] == task.id
    assert row["title"] == "ghost-claimed-task"
    assert row["status"] == TaskStatus.CLAIMED.value
    assert row["owner_agent_id"] == "agent-ghost-1"
    assert row["lease_until"] is not None
    # The lease expired ~1h ago, so the task has been stale ~3600 seconds.
    assert 3600 <= row["stale_seconds"] < 3660


def test_stale_listing_excludes_non_stale_tasks(test_client, stale_tasks_repo):
    """A RUNNING task with a still-valid lease is not stale and must be absent,
    even when a genuinely stale task is present alongside it."""
    now = datetime.now(timezone.utc)
    stale = _make_task(
        status=TaskStatus.RUNNING,
        lease_until=now - timedelta(hours=1),
        title="stale-running",
    )
    fresh = _make_task(
        status=TaskStatus.RUNNING,
        lease_until=now + timedelta(hours=1),
        title="fresh-running",
    )
    stale_tasks_repo(running=[stale, fresh])

    resp = test_client.get("/v1/tasks/stale")

    assert resp.status_code == 200, resp.text
    returned_ids = {row["id"] for row in resp.json()}
    assert stale.id in returned_ids
    assert fresh.id not in returned_ids
