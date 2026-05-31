"""Task evidence model validation for Phase 10-01."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.models.tasks import (
    TaskEvidenceCreate,
    TaskEvidenceOutcome,
    TaskEvidenceType,
)


def test_task_evidence_create_accepts_supported_types_and_structured_payload() -> None:
    evidence = TaskEvidenceCreate(
        evidence_type=TaskEvidenceType.QUALITY_GATE,
        title="Quality gate passed",
        summary="lint and tests passed",
        content={"commands": [{"cmd": "pytest", "exit_code": 0, "redacted": True}]},
        artifact_ids=["artifact-1"],
        outcome=TaskEvidenceOutcome.PASSED,
        labels={"phase": "10-01"},
        metadata={"runner": "local"},
    )

    assert evidence.evidence_type == "quality_gate"
    assert evidence.outcome == "passed"
    assert evidence.content["commands"][0]["redacted"] is True
    assert evidence.artifact_ids == ["artifact-1"]
    assert evidence.labels == {"phase": "10-01"}


def test_task_evidence_create_rejects_unknown_evidence_type() -> None:
    with pytest.raises(ValidationError):
        TaskEvidenceCreate(
            evidence_type="screenshot",  # type: ignore[arg-type]
            title="Unsupported evidence",
            content={},
        )


def test_task_evidence_create_forbids_extra_fields() -> None:
    with pytest.raises(ValidationError):
        TaskEvidenceCreate(
            evidence_type=TaskEvidenceType.LOG,
            title="Log sample",
            content={},
            private_raw_field="must-not-be-accepted",  # type: ignore[call-arg]
        )
