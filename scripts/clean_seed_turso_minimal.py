#!/usr/bin/env python3
"""Clean OpenHub Turso demo data and seed a tiny, intentional sample set.

Preserves api_keys to avoid breaking known-good tokens. Requires
/home/brunhilde/OpenHub/.env with AGENTHUB_TURSO_* credentials.
"""
from __future__ import annotations

import json
import pathlib
import re
import urllib.request
from datetime import datetime, timezone, timedelta

ROOT = pathlib.Path(__file__).resolve().parents[1]
ENV_PATH = ROOT / ".env"


def load_env() -> dict[str, str]:
    env: dict[str, str] = {}
    for line in ENV_PATH.read_text(errors="ignore").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        env[key.strip()] = value.strip().strip('"').strip("'")
    return env


env = load_env()
host = re.sub(r"^libsql://", "", env["AGENTHUB_TURSO_DATABASE_URL"]).split("?")[0]
endpoint = f"https://{host}/v2/pipeline"
token = env["AGENTHUB_TURSO_AUTH_TOKEN"]


def execute_many(sqls: list[str]) -> dict:
    body = json.dumps(
        {
            "requests": [
                {"type": "execute", "stmt": {"sql": sql}}
                for sql in sqls
            ]
            + [{"type": "close"}]
        }
    ).encode()
    req = urllib.request.Request(
        endpoint,
        data=body,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "Hermes-Agent",
        },
    )
    with urllib.request.urlopen(req, timeout=45) as response:
        return json.loads(response.read())


def query(sql: str) -> list[dict[str, object]]:
    result = execute_many([sql])["results"][0]["response"]["result"]
    cols = [col["name"] for col in result.get("cols", [])]
    rows: list[dict[str, object]] = []
    for row in result.get("rows", []):
        parsed: dict[str, object] = {}
        for idx, col in enumerate(cols):
            cell = row[idx]
            parsed[col] = cell.get("value") if isinstance(cell, dict) else cell
        rows.append(parsed)
    return rows


def lit(value: object) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, (int, float)):
        return str(value)
    return "'" + str(value).replace("'", "''") + "'"


def insert(table: str, values: dict[str, object]) -> str:
    columns = ", ".join(f'"{column}"' for column in values)
    literals = ", ".join(lit(value) for value in values.values())
    return f'INSERT INTO "{table}" ({columns}) VALUES ({literals})'


now = datetime.now(timezone.utc).replace(microsecond=0)
agent_id = "demo-agent-001"
clean_tables = [
    "trace_events",
    "task_attempts",
    "resource_locks",
    "messages",
    "threads",
    "artifacts",
    "cost_tracking",
    "events",
    "approvals",
    "shared_memory",
    "shared_tools",
    "workflows",
    "tasks",
    "remote_agent_mappings",
    "acn_nodes",
    "agents",
    "pending_applications",
    "agent_templates",
]

statements: list[str] = [f'DELETE FROM "{table}"' for table in clean_tables]
statements.append(
    insert(
        "agents",
        {
            "id": agent_id,
            "agent_name": "Demo Agent",
            "description": "Tek yalancı/demo agent: dashboard ve Kanban doğrulaması için minimal örnek.",
            "capabilities": json.dumps(["planning", "workflow", "verification"]),
            "status": "online",
            "labels": json.dumps({"demo": "true"}),
            "metadata": json.dumps({"seed": "minimal-clean"}),
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
            "last_heartbeat": now.isoformat(),
            "tasks_completed": 1,
            "tasks_failed": 0,
            "average_task_duration": 120.0,
            "current_task": None,
            "embedding_status": "pending",
        },
    )
)

tasks = [
    (
        "seed-task-001",
        "Phase 07 planını netleştir",
        "Verification Evidence fazı için küçük GSD slice listesini ve acceptance criteria bilgisini tamamla.",
        "analysis",
        80,
        "queued",
        ["planning", "verification"],
        None,
        None,
        None,
    ),
    (
        "seed-task-002",
        "Task evidence API taslağı",
        "POST/GET task evidence contract, storage modeli ve test kapsamını çıkar.",
        "feature",
        70,
        "queued",
        ["backend", "evidence"],
        None,
        None,
        None,
    ),
    (
        "seed-task-003",
        "Workflow canvas UX polish",
        "Task detail canvas altında bilgi paneli, stat kartları ve durum özeti görünür olsun.",
        "feature",
        60,
        "queued",
        ["frontend", "workflow"],
        None,
        None,
        None,
    ),
    (
        "seed-task-004",
        "Quality gate adapter stub",
        "Plankton/quality sidecar için advisory policy stub ve evidence mapping tasarla.",
        "feature",
        50,
        "queued",
        ["quality_gate", "adapter"],
        None,
        None,
        None,
    ),
    (
        "seed-task-005",
        "Demo agent smoke check",
        "Minimal demo agent ile heartbeat/status görünürlüğünü doğrula.",
        "maintenance",
        40,
        "completed",
        ["smoke", "agent"],
        agent_id,
        (now - timedelta(minutes=20)).isoformat(),
        120.0,
    ),
]
for task_id, title, description, task_type, priority, status, capabilities, owner, completed_at, duration in tasks:
    statements.append(
        insert(
            "tasks",
            {
                "id": task_id,
                "title": title,
                "description": description,
                "task_type": task_type,
                "priority": priority,
                "status": status,
                "required_capabilities": json.dumps(capabilities),
                "owner_agent_id": owner,
                "completed_at": completed_at,
                "retry_count": 0,
                "max_retries": 3,
                "labels": json.dumps({"seed": "true"}),
                "metadata": json.dumps({"seed": "minimal-clean"}),
                "payload": json.dumps({}),
                "output": json.dumps({}),
                "artifact_ids": json.dumps([]),
                "duration_seconds": duration,
                "created_by": "system-seed",
                "created_at": now.isoformat(),
                "updated_at": now.isoformat(),
                "embedding_status": "pending",
            },
        )
    )

steps = json.dumps(
    [
        {"id": "step-1", "name": "Plan", "status": "completed", "agent_id": agent_id},
        {"id": "step-2", "name": "Implement", "status": "pending", "agent_id": agent_id},
        {"id": "step-3", "name": "Verify", "status": "pending", "agent_id": agent_id},
    ]
)
statements.append(
    insert(
        "workflows",
        {
            "id": "seed-workflow-001",
            "name": "Phase 07 Verification Foundation",
            "description": "Minimal temiz demo workflow: plan → implement → verify.",
            "steps": steps,
            "status": "created",
            "current_step": 0,
            "results": json.dumps({}),
            "created_by": "system-seed",
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        },
    )
)

execute_many(statements)
for table in ["agents", "api_keys", "tasks", "workflows", "trace_events", "resource_locks"]:
    count = query(f'SELECT count(*) AS n FROM "{table}"')[0]["n"]
    print(f"{table}={count}")
print("seed_agent=demo-agent-001")
print("seed_tasks=seed-task-001..seed-task-005")
