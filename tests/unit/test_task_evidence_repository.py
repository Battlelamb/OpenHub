"""Task evidence repository behavior for Phase 10-01."""
from __future__ import annotations

import json
from uuid import uuid4

from app.database.connection import get_database
from app.database.repositories.task_evidence import TaskEvidenceRepository
from app.models.tasks import TaskEvidenceCreate, TaskEvidenceOutcome, TaskEvidenceType


def _insert_task(task_id: str) -> None:
    db = get_database()
    db.execute(
        """
        INSERT INTO tasks (
            id, title, description, task_type, status, priority,
            required_capabilities, payload, labels, output, artifact_ids
        ) VALUES (
            :id, :title, :description, 'feature', 'queued', 50,
            :caps, '{}', '{}', '{}', '[]'
        )
        """,
        {
            "id": task_id,
            "title": f"evidence-task-{task_id[:8]}",
            "description": "task evidence repository fixture",
            "caps": json.dumps(["general"]),
        },
    )


def test_task_evidence_repository_round_trips_json_fields(test_client) -> None:
    task_id = str(uuid4())
    _insert_task(task_id)
    repo = TaskEvidenceRepository(get_database())

    created = repo.create_for_task(
        task_id,
        TaskEvidenceCreate(
            evidence_type=TaskEvidenceType.COMMAND,
            title="Focused backend tests",
            summary="task evidence tests passed",
            content={"command": "pytest tests/unit/test_task_evidence_repository.py", "exit_code": 0},
            artifact_ids=["artifact-a", "artifact-b"],
            outcome=TaskEvidenceOutcome.PASSED,
            source_agent_id="test-admin",
            labels={"slice": "10-01"},
            metadata={"redacted": True, "truncated": False},
        ),
    )

    assert created.id
    assert created.task_id == task_id
    assert created.evidence_type == "command"
    assert created.outcome == "passed"
    assert created.content["exit_code"] == 0
    assert created.artifact_ids == ["artifact-a", "artifact-b"]
    assert created.labels == {"slice": "10-01"}
    assert created.metadata == {"redacted": True, "truncated": False}


def test_task_evidence_repository_lists_task_evidence_oldest_first(test_client) -> None:
    task_id = str(uuid4())
    _insert_task(task_id)
    repo = TaskEvidenceRepository(get_database())

    first = repo.create_for_task(
        task_id,
        TaskEvidenceCreate(evidence_type=TaskEvidenceType.LOG, title="First log", content={}),
    )
    second = repo.create_for_task(
        task_id,
        TaskEvidenceCreate(evidence_type=TaskEvidenceType.REVIEW, title="Review note", content={}),
    )

    rows = repo.list_for_task(task_id)

    assert [row.id for row in rows] == [first.id, second.id]
    assert [row.evidence_type for row in rows] == ["log", "review"]
