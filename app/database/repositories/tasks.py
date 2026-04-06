"""
Task repository for database operations - raw sqlite3 (matching BaseRepository pattern)
"""
import json
from typing import List, Optional, Dict, Any
from datetime import datetime

from ...logging import get_logger
from .base import BaseRepository
from ...models.tasks import Task, TaskStatus, TaskPriority, TaskType

logger = get_logger(__name__)


class TaskRepository(BaseRepository[Task]):
    """Task database operations using raw sqlite3"""

    def __init__(self, database):
        super().__init__(database, "tasks")

    def _row_to_model(self, row: Dict[str, Any]) -> Task:
        """Convert database row to Task model"""
        return Task(
            id=row["id"],
            title=row["title"],
            description=row.get("description"),
            task_type=row.get("task_type", "feature"),
            priority=row.get("priority", 50),
            status=row.get("status", "queued"),
            required_capabilities=json.loads(row.get("required_capabilities", "[]")),
            owner_agent_id=row.get("owner_agent_id"),
            claimed_at=row.get("claimed_at"),
            started_at=row.get("started_at"),
            completed_at=row.get("completed_at"),
            lease_until=row.get("lease_until"),
            retry_count=row.get("retry_count", 0),
            max_retries=row.get("max_retries", 3),
            last_error=row.get("last_error"),
            deadline_at=row.get("deadline_at"),
            idempotency_key=row.get("idempotency_key"),
            labels=json.loads(row.get("labels", "{}")),
            metadata=json.loads(row.get("metadata", "{}")),
            payload=json.loads(row.get("payload", "{}")),
            result_summary=row.get("result_summary"),
            output=json.loads(row.get("output", "{}")),
            artifact_ids=json.loads(row.get("artifact_ids", "[]")),
            duration_seconds=row.get("duration_seconds"),
            created_at=row.get("created_at"),
            updated_at=row.get("updated_at"),
        )

    def _model_to_dict(self, task: Task) -> Dict[str, Any]:
        """Convert Task model to database dict"""
        return {
            "id": task.id,
            "title": task.title,
            "description": task.description,
            "task_type": task.task_type if isinstance(task.task_type, str) else task.task_type.value,
            "priority": task.priority if isinstance(task.priority, int) else int(task.priority),
            "status": task.status if isinstance(task.status, str) else task.status.value,
            "required_capabilities": json.dumps(task.required_capabilities),
            "owner_agent_id": task.owner_agent_id,
            "claimed_at": task.claimed_at,
            "started_at": task.started_at,
            "completed_at": task.completed_at,
            "lease_until": task.lease_until,
            "retry_count": task.retry_count,
            "max_retries": task.max_retries,
            "last_error": task.last_error,
            "deadline_at": task.deadline_at,
            "idempotency_key": task.idempotency_key,
            "labels": json.dumps(task.labels),
            "metadata": json.dumps(task.metadata if hasattr(task, 'metadata') else {}),
            "payload": json.dumps(task.payload),
            "result_summary": task.result_summary,
            "output": json.dumps(task.output),
            "artifact_ids": json.dumps(task.artifact_ids),
            "duration_seconds": task.duration_seconds,
            "created_at": task.created_at,
            "updated_at": task.updated_at,
        }

    def find_by_status(self, status: str) -> List[Task]:
        """Find tasks by status"""
        return self.find_by({"status": status})

    def find_by_agent(self, agent_id: str, status_filter: Optional[List[str]] = None) -> List[Task]:
        """Find tasks assigned to specific agent"""
        conditions = {"owner_agent_id": agent_id}
        tasks = self.find_by(conditions)
        if status_filter:
            tasks = [t for t in tasks if (t.status if isinstance(t.status, str) else t.status.value) in status_filter]
        return tasks

    def find_available_for_agent(self, agent_capabilities: List[str], limit: int = 10) -> List[Task]:
        """Find queued tasks sorted by priority"""
        rows = self.database.fetch_all(
            "SELECT * FROM tasks WHERE status = :status ORDER BY priority ASC, created_at DESC LIMIT :limit",
            {"status": "queued", "limit": limit}
        )
        return [self._row_to_model(dict(r)) for r in rows]

    def search_tasks(self, search_query=None, status_filter=None, priority_filter=None,
                     type_filter=None, agent_filter=None, created_after=None, created_before=None,
                     page=1, limit=20, sort_by="created_at", sort_order="desc") -> Dict[str, Any]:
        """Search tasks with filtering"""
        query = "SELECT * FROM tasks WHERE 1=1"
        count_query = "SELECT COUNT(*) as cnt FROM tasks WHERE 1=1"
        params = {}

        if search_query:
            query += " AND (title LIKE :search OR description LIKE :search)"
            count_query += " AND (title LIKE :search OR description LIKE :search)"
            params["search"] = f"%{search_query}%"
        if status_filter:
            placeholders = ",".join(f":s{i}" for i in range(len(status_filter)))
            query += f" AND status IN ({placeholders})"
            count_query += f" AND status IN ({placeholders})"
            for i, s in enumerate(status_filter):
                params[f"s{i}"] = s
        if agent_filter:
            query += " AND owner_agent_id = :agent"
            count_query += " AND owner_agent_id = :agent"
            params["agent"] = agent_filter

        # Count
        count_row = self.database.fetch_one(count_query, params)
        total = count_row["cnt"] if count_row else 0

        # Sort and paginate
        allowed_sorts = {"created_at", "priority", "status", "title", "updated_at"}
        if sort_by not in allowed_sorts:
            sort_by = "created_at"
        direction = "DESC" if sort_order.lower() == "desc" else "ASC"
        query += f" ORDER BY {sort_by} {direction}"
        query += " LIMIT :limit OFFSET :offset"
        params["limit"] = limit
        params["offset"] = (page - 1) * limit

        rows = self.database.fetch_all(query, params)
        tasks = [self._row_to_model(dict(r)) for r in rows]

        return {
            "tasks": tasks,
            "total": total,
            "page": page,
            "limit": limit,
            "total_pages": (total + limit - 1) // limit if total > 0 else 0,
        }

    def cleanup_expired_leases(self) -> int:
        """Clean up tasks with expired leases"""
        cursor = self.database.execute(
            """UPDATE tasks SET status = 'queued', owner_agent_id = NULL,
               claimed_at = NULL, lease_until = NULL,
               last_error = 'Lease expired - returned to queue'
               WHERE status = 'claimed' AND lease_until < CURRENT_TIMESTAMP"""
        )
        count = cursor.rowcount
        if count > 0:
            logger.info("expired_leases_cleaned_up", count=count)
        return count

    def get_task_statistics(self) -> Dict[str, Any]:
        """Get task statistics"""
        total_row = self.database.fetch_one("SELECT COUNT(*) as cnt FROM tasks")
        total = total_row["cnt"] if total_row else 0

        status_counts = {}
        for s in TaskStatus:
            row = self.database.fetch_one(
                "SELECT COUNT(*) as cnt FROM tasks WHERE status = :s", {"s": s.value}
            )
            status_counts[s.value] = row["cnt"] if row else 0

        return {
            "total_tasks": total,
            "by_status": status_counts,
        }
