"""
Unit tests for the task recovery audit trail (GSD slice 05-03-04).

When an admin recovers a stale task -- one an agent claimed or started but
never released, so its lease expired (see ``Task.is_stale``) --
``TaskService.recover_task`` records the action inside the task's ``payload``
under a ``recovery`` key. That block is the audit trail: it captures *who*
recovered the task (``recovered_by``), *why* (``reason``) and *when*
(``recovered_at``), so a stuck task that silently returns to the queue still
leaves a traceable record.

These tests pin down that audit contract against the real repository:
  * recovery writes ``recovery.recovered_by`` into the payload
  * recovery writes ``recovery.reason`` into the payload
  * recovery writes ``recovery.recovered_at`` (an ISO-8601 timestamp)
  * recovery with no reason still succeeds, recording ``reason`` as ``None``

This slice is tests-only: it verifies the existing implementation, it does
not change it.
"""
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from app.database.connection import get_database
from app.database.repositories.tasks import TaskRepository
from app.models.tasks import Task, TaskPriority, TaskStatus, TaskType
from app.services.task_service import TaskService


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _ensure_schema(test_client):
    """Guarantee the database schema exists before these tests run.

    The tests below exercise ``TaskService`` against the *real* repository, so
    the ``tasks`` table must already be created. Table creation happens in the
    FastAPI app's lifespan startup; entering the session-scoped ``test_client``
    runs that startup. We depend on the fixture purely for that side effect --
    none of these tests issue an HTTP request.
    """


def _persist_stale_task() -> Task:
    """Insert a RUNNING task whose lease expired an hour ago -> it is stale.

    Writes straight through the repository (bypassing ``TaskService`` so no
    auto-assignment runs) and carries only the fields staleness depends on: a
    RUNNING status plus an already-expired ``lease_until``. A unique title and
    owner keep every test's task independent of the others.
    """
    repo = TaskRepository(get_database())
    return repo.create(
        Task(
            title=f"recovery-audit-{uuid4().hex[:6]}",
            description="recovery audit trail test fixture",
            task_type=TaskType.FEATURE,
            priority=TaskPriority.NORMAL,
            required_capabilities=["python"],
            max_retries=2,
            status=TaskStatus.RUNNING,
            owner_agent_id=f"ghost-agent-{uuid4().hex[:8]}",
            lease_until=datetime.now(timezone.utc) - timedelta(hours=1),
        )
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_recovery_records_recovered_by_in_payload():
    """Recovery writes the admin's id to payload.recovery.recovered_by."""
    task = _persist_stale_task()

    recovered = TaskService(get_database()).recover_task(
        task.id,
        recovered_by="admin-audit-001",
        reason="agent crashed mid-run",
    )

    assert recovered is not None
    assert recovered.payload is not None
    assert recovered.payload["recovery"]["recovered_by"] == "admin-audit-001"


def test_recovery_records_reason_in_payload():
    """Recovery writes the operator's note to payload.recovery.reason."""
    task = _persist_stale_task()

    recovered = TaskService(get_database()).recover_task(
        task.id,
        recovered_by="admin-audit-001",
        reason="lease expired overnight, re-queuing",
    )

    assert recovered is not None
    assert recovered.payload is not None
    assert (
        recovered.payload["recovery"]["reason"]
        == "lease expired overnight, re-queuing"
    )


def test_recovery_records_recovered_at_in_payload():
    """Recovery writes an ISO-8601 timestamp to payload.recovery.recovered_at."""
    task = _persist_stale_task()

    before = datetime.now(timezone.utc)
    recovered = TaskService(get_database()).recover_task(
        task.id,
        recovered_by="admin-audit-001",
        reason="stuck task swept by operator",
    )
    after = datetime.now(timezone.utc)

    assert recovered is not None
    assert recovered.payload is not None

    recovered_at_raw = recovered.payload["recovery"]["recovered_at"]
    # Stored as an ISO-8601 string so the payload stays JSON-serializable.
    assert isinstance(recovered_at_raw, str)

    # It must parse back to a real time, and fall within the window that
    # brackets the recover_task() call -- proving it is the recovery moment.
    recovered_at = datetime.fromisoformat(recovered_at_raw)
    assert before <= recovered_at <= after


def test_recovery_without_reason_records_reason_as_none():
    """Recovery with no reason still succeeds; reason is recorded as None."""
    task = _persist_stale_task()

    # reason is omitted -> defaults to None (the endpoint allows a bodyless call).
    recovered = TaskService(get_database()).recover_task(
        task.id,
        recovered_by="admin-audit-001",
    )

    assert recovered is not None
    assert recovered.payload is not None

    recovery = recovered.payload["recovery"]
    # The reason key is always present, for a consistent audit-record shape...
    assert "reason" in recovery
    # ...but carries None when the operator gave no explanation.
    assert recovery["reason"] is None
    # The rest of the audit trail is still fully populated.
    assert recovery["recovered_by"] == "admin-audit-001"
    assert recovery["recovered_at"] is not None
