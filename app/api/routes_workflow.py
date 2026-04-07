"""
Workflow Engine - multi-step agent task orchestration (DAG)

Workflow = ordered list of steps, each step creates a task for an agent.
Steps run sequentially. Each step's output feeds into the next step's input.

Example workflow:
{
  "name": "Code Review Pipeline",
  "steps": [
    {"title": "Write code", "task_type": "code_edit", "capabilities": ["code_edit"], "description": "Implement feature X"},
    {"title": "Review code", "task_type": "code_review", "capabilities": ["code_review"], "description": "Review the implementation"},
    {"title": "Write tests", "task_type": "testing", "capabilities": ["testing"], "description": "Add unit tests"}
  ]
}
"""
import json as _json
from datetime import datetime, timezone
from uuid import uuid4
from typing import Dict, Any, Optional, List
from pydantic import BaseModel as PydanticBaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, status, Header

from ..logging import get_logger
from ..database.connection import get_database, Database
from ..services.task_service import TaskService
from ..models.tasks import TaskCreate, TaskType
from ..auth.api_keys import APIKeyManager

logger = get_logger(__name__)

router = APIRouter(prefix="/v1/workflows", tags=["workflows-engine"])


def _require_api_key(x_api_key: str = Header(None, alias="X-API-Key"), database: Database = Depends(get_database)) -> Dict:
    if not x_api_key:
        raise HTTPException(status_code=401, detail="X-API-Key required")
    info = APIKeyManager(database).validate_api_key(x_api_key)
    if not info:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return info


class WorkflowStep(PydanticBaseModel):
    title: str
    description: str = ""
    task_type: str = "feature"
    capabilities: List[str] = ["code_edit"]


class WorkflowCreate(PydanticBaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: Optional[str] = None
    steps: List[WorkflowStep] = Field(min_length=1, max_length=20)


@router.post("/create")
async def create_workflow(
    body: WorkflowCreate,
    key_info: Dict = Depends(_require_api_key),
    database: Database = Depends(get_database),
) -> Dict[str, Any]:
    """Create a new workflow (does not start it)."""
    wf_id = str(uuid4())
    now = datetime.now(timezone.utc).isoformat()

    steps_data = [s.model_dump() for s in body.steps]

    database.execute(
        """INSERT INTO workflows (id, name, description, steps, status, current_step, results, created_by, created_at, updated_at)
           VALUES (:id, :name, :desc, :steps, 'created', 0, :results, :by, :now, :now)""",
        {
            "id": wf_id, "name": body.name, "desc": body.description,
            "steps": _json.dumps(steps_data), "results": "{}",
            "by": key_info.get("name"), "now": now,
        }
    )

    return {"workflow_id": wf_id, "name": body.name, "steps": len(body.steps), "status": "created"}


@router.post("/{workflow_id}/run")
async def run_workflow(
    workflow_id: str,
    key_info: Dict = Depends(_require_api_key),
    database: Database = Depends(get_database),
    task_service: TaskService = Depends(lambda: TaskService(get_database())),
) -> Dict[str, Any]:
    """Start running a workflow - executes the first step."""
    row = database.fetch_one("SELECT * FROM workflows WHERE id = :id", {"id": workflow_id})
    if not row:
        raise HTTPException(status_code=404, detail="Workflow not found")

    wf = dict(row) if isinstance(row, dict) else row
    if wf["status"] not in ("created", "paused"):
        raise HTTPException(status_code=400, detail=f"Workflow is {wf['status']}, cannot run")

    steps = _json.loads(wf["steps"]) if isinstance(wf["steps"], str) else wf["steps"]
    current = wf.get("current_step", 0) or 0

    if current >= len(steps):
        return {"status": "completed", "message": "All steps done"}

    # Create task for current step
    step = steps[current]
    task_type = step.get("task_type", "feature")

    task_data = TaskCreate(
        title=f"[WF:{wf['name']}] Step {current+1}: {step['title']}",
        description=step.get("description", ""),
        task_type=TaskType(task_type) if task_type in [t.value for t in TaskType] else TaskType.FEATURE,
        priority=25,
        required_capabilities=step.get("capabilities", ["code_edit"]),
        payload={"workflow_id": workflow_id, "step_index": current},
        labels={"workflow": wf["name"]},
        max_retries=2,
    )

    new_task = task_service.create_task(task_data, created_by=f"workflow:{workflow_id}")

    # Update workflow status
    now = datetime.now(timezone.utc).isoformat()
    database.execute(
        "UPDATE workflows SET status = 'running', current_step = :step, updated_at = :now WHERE id = :id",
        {"step": current, "now": now, "id": workflow_id}
    )

    logger.info("workflow_step_started", workflow_id=workflow_id, step=current, task_id=new_task.id)

    return {
        "status": "running",
        "workflow_id": workflow_id,
        "current_step": current + 1,
        "total_steps": len(steps),
        "step_title": step["title"],
        "task_id": new_task.id,
        "assigned_to": new_task.owner_agent_id,
    }


@router.post("/{workflow_id}/advance")
async def advance_workflow(
    workflow_id: str,
    step_result: Optional[str] = None,
    key_info: Dict = Depends(_require_api_key),
    database: Database = Depends(get_database),
    task_service: TaskService = Depends(lambda: TaskService(get_database())),
) -> Dict[str, Any]:
    """Advance workflow to the next step (call after current step's task completes)."""
    row = database.fetch_one("SELECT * FROM workflows WHERE id = :id", {"id": workflow_id})
    if not row:
        raise HTTPException(status_code=404, detail="Workflow not found")

    wf = dict(row) if isinstance(row, dict) else row
    steps = _json.loads(wf["steps"]) if isinstance(wf["steps"], str) else wf["steps"]
    current = (wf.get("current_step", 0) or 0)
    results = _json.loads(wf["results"]) if isinstance(wf.get("results"), str) else wf.get("results", {})

    # Save result of current step
    if step_result:
        results[f"step_{current}"] = step_result

    next_step = current + 1

    if next_step >= len(steps):
        # Workflow complete
        now = datetime.now(timezone.utc).isoformat()
        database.execute(
            "UPDATE workflows SET status = 'completed', current_step = :step, results = :res, updated_at = :now WHERE id = :id",
            {"step": next_step, "res": _json.dumps(results), "now": now, "id": workflow_id}
        )
        return {"status": "completed", "workflow_id": workflow_id, "results": results}

    # Create task for next step
    step = steps[next_step]
    task_type = step.get("task_type", "feature")

    task_data = TaskCreate(
        title=f"[WF:{wf['name']}] Step {next_step+1}: {step['title']}",
        description=step.get("description", "") + (f"\n\nPrevious step result: {step_result}" if step_result else ""),
        task_type=TaskType(task_type) if task_type in [t.value for t in TaskType] else TaskType.FEATURE,
        priority=25,
        required_capabilities=step.get("capabilities", ["code_edit"]),
        payload={"workflow_id": workflow_id, "step_index": next_step, "previous_result": step_result},
        labels={"workflow": wf["name"]},
        max_retries=2,
    )

    new_task = task_service.create_task(task_data, created_by=f"workflow:{workflow_id}")

    now = datetime.now(timezone.utc).isoformat()
    database.execute(
        "UPDATE workflows SET current_step = :step, results = :res, updated_at = :now WHERE id = :id",
        {"step": next_step, "res": _json.dumps(results), "now": now, "id": workflow_id}
    )

    return {
        "status": "running",
        "workflow_id": workflow_id,
        "current_step": next_step + 1,
        "total_steps": len(steps),
        "step_title": step["title"],
        "task_id": new_task.id,
        "assigned_to": new_task.owner_agent_id,
    }


@router.get("/{workflow_id}")
async def get_workflow(
    workflow_id: str,
    key_info: Dict = Depends(_require_api_key),
    database: Database = Depends(get_database),
) -> Dict[str, Any]:
    """Get workflow status and details."""
    row = database.fetch_one("SELECT * FROM workflows WHERE id = :id", {"id": workflow_id})
    if not row:
        raise HTTPException(status_code=404, detail="Workflow not found")

    wf = dict(row) if isinstance(row, dict) else row
    steps = _json.loads(wf["steps"]) if isinstance(wf["steps"], str) else wf["steps"]
    results = _json.loads(wf["results"]) if isinstance(wf.get("results"), str) else wf.get("results", {})

    return {
        "workflow_id": wf["id"],
        "name": wf["name"],
        "description": wf.get("description"),
        "status": wf["status"],
        "current_step": (wf.get("current_step", 0) or 0) + 1,
        "total_steps": len(steps),
        "steps": steps,
        "results": results,
        "created_at": wf.get("created_at"),
    }


@router.get("/")
async def list_workflows(
    key_info: Dict = Depends(_require_api_key),
    database: Database = Depends(get_database),
) -> Dict[str, Any]:
    """List all workflows."""
    rows = database.fetch_all("SELECT * FROM workflows ORDER BY created_at DESC LIMIT 50")

    workflows = []
    for r in rows:
        r = dict(r) if isinstance(r, dict) else r
        steps = _json.loads(r["steps"]) if isinstance(r.get("steps"), str) else r.get("steps", [])
        workflows.append({
            "workflow_id": r["id"],
            "name": r["name"],
            "status": r["status"],
            "current_step": (r.get("current_step", 0) or 0) + 1,
            "total_steps": len(steps),
            "created_at": r.get("created_at"),
        })

    return {"workflows": workflows, "total": len(workflows)}
