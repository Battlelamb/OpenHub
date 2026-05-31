"""Repository for durable private/internal task evidence rows."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ...models.tasks import (
    TaskEvidence,
    TaskEvidenceCreate,
    TaskEvidenceOutcome,
    TaskEvidenceType,
)
from .base import BaseRepository


def _json_dict(raw: Any) -> Dict[str, Any]:
    if isinstance(raw, dict):
        return raw
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _json_list(raw: Any) -> List[str]:
    if isinstance(raw, list):
        return [str(item) for item in raw]
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return []
    if not isinstance(parsed, list):
        return []
    return [str(item) for item in parsed]


def _label_dict(raw: Any) -> Dict[str, str]:
    labels = _json_dict(raw)
    return {
        str(key): ("true" if value is True else "false" if value is False else str(value))
        for key, value in labels.items()
        if value is not None
    }


def _enum_value(value: Any) -> str:
    return value if isinstance(value, str) else value.value


def _when(value: Any) -> Any:
    return value or datetime.now(timezone.utc)


class TaskEvidenceRepository(BaseRepository[TaskEvidence]):
    """Database operations for task evidence."""

    def __init__(self, database):
        super().__init__(database, "task_evidence")

    def _row_to_model(self, row: Dict[str, Any]) -> TaskEvidence:
        """Convert a database row to a TaskEvidence model."""
        return TaskEvidence(
            id=row["id"],
            task_id=row["task_id"],
            evidence_type=TaskEvidenceType(row["evidence_type"]),
            title=row["title"],
            summary=row.get("summary"),
            content=_json_dict(row.get("content")),
            artifact_ids=_json_list(row.get("artifact_ids")),
            outcome=TaskEvidenceOutcome(row.get("outcome") or "unknown"),
            source_agent_id=row.get("source_agent_id"),
            labels=_label_dict(row.get("labels")),
            metadata=_json_dict(row.get("metadata")),
            occurred_at=_when(row.get("occurred_at")),
            created_at=_when(row.get("created_at")),
            updated_at=row.get("updated_at"),
        )

    def _model_to_dict(self, model: TaskEvidence) -> Dict[str, Any]:
        """Convert a TaskEvidence model to database columns."""
        evidence = model
        created_at = evidence.created_at or datetime.now(timezone.utc)
        updated_at = evidence.updated_at or created_at
        return {
            "id": evidence.id,
            "task_id": evidence.task_id,
            "evidence_type": _enum_value(evidence.evidence_type),
            "title": evidence.title,
            "summary": evidence.summary,
            "content": json.dumps(evidence.content),
            "artifact_ids": json.dumps(evidence.artifact_ids),
            "outcome": _enum_value(evidence.outcome),
            "source_agent_id": evidence.source_agent_id,
            "labels": json.dumps(evidence.labels),
            "metadata": json.dumps(evidence.metadata),
            "occurred_at": evidence.occurred_at,
            "created_at": created_at,
            "updated_at": updated_at,
        }

    def create_for_task(
        self,
        task_id: str,
        evidence_create: TaskEvidenceCreate,
    ) -> TaskEvidence:
        """Create one evidence row scoped to a task."""
        occurred_at = evidence_create.occurred_at or datetime.now(timezone.utc)
        evidence = TaskEvidence(
            task_id=task_id,
            evidence_type=evidence_create.evidence_type,
            title=evidence_create.title,
            summary=evidence_create.summary,
            content=evidence_create.content,
            artifact_ids=evidence_create.artifact_ids,
            outcome=evidence_create.outcome,
            source_agent_id=evidence_create.source_agent_id,
            labels=evidence_create.labels,
            metadata=evidence_create.metadata,
            occurred_at=occurred_at,
        )
        return self.create(evidence)

    def list_for_task(
        self,
        task_id: str,
        *,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> List[TaskEvidence]:
        """List task evidence oldest first for timeline consumption."""
        query = """
        SELECT * FROM task_evidence
        WHERE task_id = :task_id
        ORDER BY occurred_at ASC, created_at ASC, id ASC
        """
        params: Dict[str, Any] = {"task_id": task_id}
        if limit is not None:
            query += " LIMIT :limit OFFSET :offset"
            params["limit"] = limit
            params["offset"] = offset
        rows = self.database.fetch_all(query, params)
        return [self._row_to_model(dict(row)) for row in rows]
