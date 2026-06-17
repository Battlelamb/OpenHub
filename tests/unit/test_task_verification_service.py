"""Phase 10-05 verification lifecycle service behavior."""
from __future__ import annotations

import json
from datetime import datetime
from uuid import uuid4

from app.database.connection import get_database
from app.database.repositories.task_evidence import TaskEvidenceRepository
from app.database.repositories.tasks import TaskRepository
from app.models.tasks import TaskEvidenceCreate, TaskEvidenceOutcome, TaskEvidenceType
from app.services.task_verification_service import TaskVerificationService


def _insert_task(task_id: str, *, status: str = "waiting_approval") -> None:
    db = get_database()
    db.execute(
        """
        INSERT INTO tasks (
            id, title, description, task_type, status, priority,
            required_capabilities, payload, labels, output, artifact_ids
        ) VALUES (
            :id, :title, :description, 'feature', :status, 50,
            :caps, '{}', '{}', '{}', '[]'
        )
        """,
        {
            "id": task_id,
            "title": f"verification-task-{task_id[:8]}",
            "description": "task verification service fixture",
            "status": status,
            "caps": json.dumps(["general"]),
        },
    )


def _add_quality_gate(
    task_id: str,
    *,
    title: str,
    outcome: TaskEvidenceOutcome,
    occurred_at: str,
) -> None:
    TaskEvidenceRepository(get_database()).create_for_task(
        task_id,
        TaskEvidenceCreate(
            evidence_type=TaskEvidenceType.QUALITY_GATE,
            title=title,
            summary=f"{title} summary",
            content={"command": "pytest -q", "exit_code": 0 if outcome == TaskEvidenceOutcome.PASSED else 1},
            outcome=outcome,
            source_agent_id="quality-bot",
            occurred_at=datetime.fromisoformat(occurred_at.replace("Z", "+00:00")),
        ),
    )


def test_waiting_approval_without_quality_gate_requires_verification(test_client) -> None:
    task_id = str(uuid4())
    _insert_task(task_id)

    state = TaskVerificationService(get_database()).get_verification_state(task_id)

    assert state is not None
    assert state.task_id == task_id
    assert state.task_status == "waiting_approval"
    assert state.lifecycle_state == "awaiting_quality_gate"
    assert state.ready_for_completion is False
    assert state.required_action == "submit_quality_gate_evidence"
    assert state.quality_gate_counts == {"passed": 0, "failed": 0, "skipped": 0, "unknown": 0}
    assert state.latest_quality_gate is None


def test_passed_quality_gate_marks_task_ready_without_auto_completing(test_client) -> None:
    task_id = str(uuid4())
    _insert_task(task_id)
    _add_quality_gate(
        task_id,
        title="Focused backend gate",
        outcome=TaskEvidenceOutcome.PASSED,
        occurred_at="2026-06-17T12:00:00Z",
    )

    state = TaskVerificationService(get_database()).get_verification_state(task_id)
    task = TaskRepository(get_database()).get_by_id(task_id)

    assert state is not None
    assert state.lifecycle_state == "quality_gate_passed"
    assert state.ready_for_completion is True
    assert state.required_action == "admin_review_or_complete"
    assert state.latest_quality_gate is not None
    assert state.latest_quality_gate["title"] == "Focused backend gate"
    assert state.latest_quality_gate["outcome"] == "passed"
    assert state.quality_gate_counts["passed"] == 1
    assert task is not None
    assert task.status == "waiting_approval"


def test_latest_failed_quality_gate_blocks_completion_even_after_prior_pass(test_client) -> None:
    task_id = str(uuid4())
    _insert_task(task_id)
    _add_quality_gate(
        task_id,
        title="Initial pass",
        outcome=TaskEvidenceOutcome.PASSED,
        occurred_at="2026-06-17T12:00:00Z",
    )
    _add_quality_gate(
        task_id,
        title="Regression gate failed",
        outcome=TaskEvidenceOutcome.FAILED,
        occurred_at="2026-06-17T12:05:00Z",
    )

    state = TaskVerificationService(get_database()).get_verification_state(task_id)

    assert state is not None
    assert state.lifecycle_state == "quality_gate_failed"
    assert state.ready_for_completion is False
    assert state.required_action == "fix_and_resubmit_quality_gate"
    assert state.latest_quality_gate is not None
    assert state.latest_quality_gate["title"] == "Regression gate failed"
    assert state.latest_quality_gate["outcome"] == "failed"
    assert state.quality_gate_counts["passed"] == 1
    assert state.quality_gate_counts["failed"] == 1
