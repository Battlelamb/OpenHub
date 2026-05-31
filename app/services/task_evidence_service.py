"""Service layer for private/internal task evidence API operations."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from ..database.connection import Database
from ..database.repositories.task_evidence import TaskEvidenceRepository
from ..database.repositories.tasks import TaskRepository
from ..models.tasks import TaskEvidence, TaskEvidenceCreate, TaskEvidenceResponse

_FORBIDDEN_KEY_FRAGMENTS = (
    "authorization",
    "api_key",
    "apikey",
    "credential",
    "password",
    "private_key",
    "secret",
    "token",
    "cookie",
)


def _is_forbidden_key(key: str) -> bool:
    normalized = key.lower().replace("-", "_")
    return any(fragment in normalized for fragment in _FORBIDDEN_KEY_FRAGMENTS)


def _sanitize_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            str(key): _sanitize_value(nested)
            for key, nested in value.items()
            if not _is_forbidden_key(str(key))
        }
    if isinstance(value, list):
        return [_sanitize_value(item) for item in value]
    return value


class TaskEvidenceService:
    """Business logic for creating and listing safe task evidence DTOs."""

    def __init__(self, database: Database):
        self.db = database
        self.task_repo = TaskRepository(database)
        self.evidence_repo = TaskEvidenceRepository(database)

    def create_evidence(
        self,
        task_id: str,
        evidence_create: TaskEvidenceCreate,
        *,
        source_agent_id: str,
    ) -> Optional[TaskEvidenceResponse]:
        """Create sanitized evidence for an existing task.

        The API surface is private/internal but still returns a safe DTO: caller-
        supplied source IDs are not trusted, metadata/labels are not echoed, and
        obvious secret-bearing content keys are stripped before persistence.
        """
        if not self.task_repo.get_by_id(task_id):
            return None

        safe_create = evidence_create.model_copy(
            update={
                "content": _sanitize_value(evidence_create.content),
                "source_agent_id": source_agent_id,
                "labels": {},
                "metadata": {},
            }
        )
        evidence = self.evidence_repo.create_for_task(task_id, safe_create)
        return self.to_response(evidence)

    def list_evidence(
        self,
        task_id: str,
        *,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> Optional[List[TaskEvidenceResponse]]:
        """List safe evidence DTOs for an existing task, oldest first."""
        if not self.task_repo.get_by_id(task_id):
            return None
        return [
            self.to_response(evidence)
            for evidence in self.evidence_repo.list_for_task(
                task_id,
                limit=limit,
                offset=offset,
            )
        ]

    @staticmethod
    def to_response(evidence: TaskEvidence) -> TaskEvidenceResponse:
        """Map a persisted evidence row to the API-safe response DTO."""
        return TaskEvidenceResponse(
            id=evidence.id,
            task_id=evidence.task_id,
            evidence_type=evidence.evidence_type,
            title=evidence.title,
            summary=evidence.summary,
            content=evidence.content,
            artifact_ids=evidence.artifact_ids,
            outcome=evidence.outcome,
            source_agent_id=evidence.source_agent_id,
            occurred_at=evidence.occurred_at,
            created_at=evidence.created_at,
            updated_at=evidence.updated_at,
        )
