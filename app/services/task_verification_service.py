"""Task verification lifecycle service for Phase 10-05."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from ..database.connection import Database
from ..database.repositories.task_evidence import TaskEvidenceRepository
from ..database.repositories.tasks import TaskRepository
from ..models.tasks import (
    Task,
    TaskEvidence,
    TaskEvidenceOutcome,
    TaskEvidenceType,
    TaskStatus,
    TaskVerificationState,
)

_QUALITY_GATE_OUTCOMES = ("passed", "failed", "skipped", "unknown")


def _enum_value(value: Any) -> str:
    return value.value if hasattr(value, "value") else str(value)


def _iso(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


class TaskVerificationService:
    """Derive verification state from task status and quality_gate evidence.

    Agent `/complete` calls can record a completion claim, but they are not the
    final canonical closeout. A task awaiting approval becomes ready for human or
    admin completion only after the latest `quality_gate` evidence has passed.
    """

    def __init__(self, database: Database):
        self.db = database
        self.task_repo = TaskRepository(database)
        self.evidence_repo = TaskEvidenceRepository(database)

    def get_verification_state(self, task_id: str) -> Optional[TaskVerificationState]:
        task = self.task_repo.get_by_id(task_id)
        if not task:
            return None

        quality_gates = [
            evidence
            for evidence in self.evidence_repo.list_for_task(task_id)
            if _enum_value(evidence.evidence_type) == TaskEvidenceType.QUALITY_GATE.value
        ]
        counts = {outcome: 0 for outcome in _QUALITY_GATE_OUTCOMES}
        for evidence in quality_gates:
            outcome = _enum_value(evidence.outcome)
            if outcome not in counts:
                outcome = TaskEvidenceOutcome.UNKNOWN.value
            counts[outcome] += 1

        latest = quality_gates[-1] if quality_gates else None
        lifecycle_state, ready_for_completion, required_action = self._derive_state(task, latest)

        return TaskVerificationState(
            task_id=task.id,
            task_status=task.status,
            lifecycle_state=lifecycle_state,
            ready_for_completion=ready_for_completion,
            required_action=required_action,
            quality_gate_counts=counts,
            latest_quality_gate=self._quality_gate_summary(latest) if latest else None,
        )

    def _derive_state(
        self,
        task: Task,
        latest_quality_gate: Optional[TaskEvidence],
    ) -> tuple[str, bool, str]:
        status = _enum_value(task.status)

        if status == TaskStatus.COMPLETED.value:
            return "completed", False, "none"
        if status in {
            TaskStatus.FAILED.value,
            TaskStatus.CANCELLED.value,
            TaskStatus.DEAD_LETTER.value,
        }:
            return "terminal", False, "none"
        if status in {TaskStatus.QUEUED.value, TaskStatus.CLAIMED.value}:
            return "not_started", False, "start_or_continue_work"
        if status == TaskStatus.RUNNING.value:
            return "in_progress", False, "agent_complete_claim"

        if status == TaskStatus.WAITING_APPROVAL.value:
            if latest_quality_gate is None:
                return "awaiting_quality_gate", False, "submit_quality_gate_evidence"
            outcome = _enum_value(latest_quality_gate.outcome)
            if outcome == TaskEvidenceOutcome.PASSED.value:
                return "quality_gate_passed", True, "admin_review_or_complete"
            if outcome == TaskEvidenceOutcome.FAILED.value:
                return "quality_gate_failed", False, "fix_and_resubmit_quality_gate"
            if outcome == TaskEvidenceOutcome.SKIPPED.value:
                return "quality_gate_skipped", False, "run_required_quality_gate"
            return "awaiting_quality_gate", False, "submit_quality_gate_evidence"

        return "unknown", False, "inspect_task"

    @staticmethod
    def _quality_gate_summary(evidence: TaskEvidence) -> dict[str, Any]:
        return {
            "id": evidence.id,
            "title": evidence.title,
            "summary": evidence.summary,
            "outcome": _enum_value(evidence.outcome),
            "source_agent_id": evidence.source_agent_id,
            "occurred_at": _iso(evidence.occurred_at),
            "created_at": _iso(evidence.created_at),
        }
