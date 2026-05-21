"""Repository compatibility for legacy/demo rows.

Live dashboard list endpoints should not collapse when old seed rows contain
non-string JSON label values or deprecated task type values.
"""

import json

from app.database.repositories.agents import AgentRepository
from app.database.repositories.tasks import TaskRepository


def test_task_repository_coerces_legacy_labels_and_unknown_type():
    task = TaskRepository(database=None)._row_to_model(
        {
            "id": "legacy-task",
            "title": "Legacy planning task",
            "description": "seed row from an older dashboard demo",
            "task_type": "planning",
            "priority": 80,
            "status": "queued",
            "required_capabilities": json.dumps(["planning"]),
            "owner_agent_id": None,
            "labels": json.dumps({"seed": True, "phase": 7}),
            "payload": json.dumps({}),
            "output": json.dumps({}),
            "artifact_ids": json.dumps([]),
            "created_at": "2026-05-21T10:00:00Z",
            "updated_at": "2026-05-21T10:00:00Z",
        }
    )

    assert task.task_type == "feature"
    assert task.labels == {"seed": "true", "phase": "7"}


def test_agent_repository_coerces_legacy_label_values():
    agent = AgentRepository(database=None)._row_to_model(
        {
            "id": "legacy-agent",
            "agent_name": "Legacy Agent",
            "description": "seed row from an older dashboard demo",
            "capabilities": json.dumps(["planning"]),
            "status": "online",
            "labels": json.dumps({"demo": True, "tier": 1}),
            "metadata": json.dumps({}),
            "created_at": "2026-05-21T10:00:00Z",
            "updated_at": "2026-05-21T10:00:00Z",
            "last_heartbeat": "2026-05-21T10:00:00Z",
        }
    )

    assert agent.labels == {"demo": "true", "tier": "1"}
