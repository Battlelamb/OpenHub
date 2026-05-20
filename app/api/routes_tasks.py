"""
Task management endpoints - clean and simple
"""
import json as _json
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, BackgroundTasks, Body, Depends, HTTPException, Request, status, Query

from ..config import get_settings
from ..logging import get_logger
from ..database.connection import get_database
from ..services.task_service import TaskService
from ..services.embedding_hooks import schedule_embedding
from ..models.tasks import (
    Task, TaskCreate, TaskUpdate, TaskClaim, TaskComplete, TaskFail, TaskRecover,
    TaskProgress, TaskStatus, TaskPriority, TaskType, TaskResponse, TaskFilter
)
from ..auth.dependencies import CurrentAgent, CurrentAdmin, get_current_admin
from ..database.vector_availability import require_vector
from ..models.vector_search import SearchRequest, SearchResponse

logger = get_logger(__name__)
settings = get_settings()

router = APIRouter(prefix="/v1/tasks", tags=["tasks"])


def get_task_service() -> TaskService:
    """Get task service instance"""
    database = get_database()
    return TaskService(database)


async def _broadcast_task_status(
    request: Request,
    task_id: str,
    new_status: str,
    previous_status: Optional[str],
    agent_id: Optional[str],
) -> None:
    """
    Broadcast task_status_changed (WS-05) to UI clients.

    Guarded with getattr so tests without a wired ConnectionManager still pass.
    Never raises - failures are logged only.
    """
    connection_manager = getattr(request.app.state, "connection_manager", None)
    if connection_manager is None:
        return
    try:
        await connection_manager.broadcast_to_ui(
            "task_status_changed",
            {
                "task_id": task_id,
                "status": new_status,
                "previous_status": previous_status,
                "agent_id": agent_id,
            },
            True,
        )
    except Exception as e:
        logger.warning(
            "ws_broadcast_failed",
            event="task_status_changed",
            task_id=task_id,
            error=str(e),
        )


@router.post("/", response_model=TaskResponse)
async def create_task(
    task_data: TaskCreate,
    request: Request,
    background_tasks: BackgroundTasks,
    current_agent: CurrentAgent = None,
    task_service: TaskService = Depends(get_task_service),
) -> TaskResponse:
    """
    Create a new task with automatic agent matching
    """
    logger.info("task_creation_request",
               title=task_data.title,
               task_type=task_data.task_type,
               by_agent=current_agent.agent_id if current_agent else "system")

    try:
        # Create task
        new_task = task_service.create_task(
            task_data,
            created_by=current_agent.agent_id if current_agent else None
        )

        # Broadcast task_status_changed (WS-05) - newly queued
        await _broadcast_task_status(
            request,
            task_id=new_task.id,
            new_status=new_task.status.value if hasattr(new_task.status, "value") else str(new_task.status),
            previous_status=None,
            agent_id=new_task.owner_agent_id,
        )

        # Auto-index task description for vector search (VEC-04).
        schedule_embedding(
            background_tasks, "task", new_task.id, new_task.description
        )

        # Convert to response model
        return _task_to_response(new_task)
    
    except Exception as e:
        logger.error("task_creation_failed", 
                    title=task_data.title,
                    error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Task creation failed"
        )


# NOTE: Static-prefix routes (/search, /stats/overview, /agent/..., /available/...) MUST
# be declared BEFORE the /{task_id} parametric route. FastAPI matches in registration
# order; if /{task_id} comes first, "search" gets consumed as a task_id and returns 404.
# Plan 04-10 reordered these out of the broken position they had in 04-04.
@router.get("/search", response_model=Dict[str, Any])
async def search_tasks(
    search_query: Optional[str] = Query(None, description="Search in title/description"),
    status: Optional[List[TaskStatus]] = Query(None, description="Filter by status"),
    task_type: Optional[List[TaskType]] = Query(None, description="Filter by type"),
    priority: Optional[List[TaskPriority]] = Query(None, description="Filter by priority"),
    assigned_agent_id: Optional[str] = Query(None, description="Filter by assigned agent"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    sort_by: str = Query("created_at", description="Sort field"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$", description="Sort order"),
    current_agent: CurrentAgent = None,
    task_service: TaskService = Depends(get_task_service)
) -> Dict[str, Any]:
    """
    Search and filter tasks with pagination
    """
    # Use task repository for search (would implement search method)
    task_repo = task_service.task_repo

    try:
        # Convert enums to values
        status_values = [s.value for s in status] if status else None
        type_values = [t.value for t in task_type] if task_type else None
        priority_values = [p.value for p in priority] if priority else None

        search_result = task_repo.search_tasks(
            search_query=search_query,
            status_filter=status_values,
            type_filter=type_values,
            priority_filter=priority_values,
            agent_filter=assigned_agent_id,
            page=page,
            limit=limit,
            sort_by=sort_by,
            sort_order=sort_order
        )

        # Convert tasks to response format
        search_result["tasks"] = [_task_to_response(task) for task in search_result["tasks"]]

        return search_result

    except Exception as e:
        logger.error("task_search_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Task search failed"
        )


@router.get("/stats/overview", response_model=Dict[str, Any])
async def get_task_statistics(
    current_agent: CurrentAgent = None,
    task_service: TaskService = Depends(get_task_service)
) -> Dict[str, Any]:
    """
    Get comprehensive task statistics
    """
    try:
        stats = task_service.task_repo.get_task_statistics()

        logger.debug("task_statistics_requested",
                    by_agent=current_agent.agent_id if current_agent else "system")

        return stats

    except Exception as e:
        logger.error("task_statistics_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve task statistics"
        )


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: str,
    current_agent: CurrentAgent = None,
    task_service: TaskService = Depends(get_task_service)
) -> TaskResponse:
    """
    Get task by ID
    """
    task = task_service.get_task(task_id)

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task '{task_id}' not found"
        )

    return _task_to_response(task)


def _trace_row_to_span(r: Dict[str, Any]) -> Dict[str, Any]:
    """
    Map a trace_events row to the UI TraceSpan shape (see
    web/src/components/common/TraceTimeline.tsx and web/src/types/entities.ts).

    Agents that log via POST /v1/traces/event may include category/level/completed_at
    in data. When they do, those values flow through. When they don't, we fall back
    to neutral defaults so the timeline degrades gracefully instead of crashing.
    """
    event_type = r.get("event_type") or "info"
    data = r.get("data") or {}
    if isinstance(data, str):
        try:
            data = _json.loads(data)
        except Exception:
            data = {}

    if event_type == "error":
        category = "error"
    else:
        raw = data.get("category", "internal") if isinstance(data, dict) else "internal"
        category = raw if raw in ("llm", "tool", "db", "http", "internal", "error") else "internal"

    level_raw = data.get("level", 0) if isinstance(data, dict) else 0
    level = int(level_raw) if isinstance(level_raw, (int, float)) else 0

    completed_at = data.get("completed_at") if isinstance(data, dict) else None

    return {
        "id": r["id"],
        "name": r.get("name") or "",
        "category": category,
        "duration_ms": float(r.get("duration_ms") or 0),
        "level": level,
        "started_at": r.get("created_at") or "",
        "completed_at": completed_at,
    }


@router.get("/{task_id}/trace", response_model=List[Dict[str, Any]])
async def get_task_trace(
    task_id: str,
    current_agent: CurrentAgent = None,
) -> List[Dict[str, Any]]:
    """
    Return the distributed trace for a task as an array of TraceSpan objects
    (UI-12). Reads from the trace_events table filtered by task_id, ordered by
    creation time so nested spans appear in causal order. Returns [] when the
    task has no spans yet - the UI shows the empty state without needing a
    separate 404 handler.
    """
    database = get_database()
    rows = database.fetch_all(
        "SELECT id, trace_id, agent_id, event_type, name, data, task_id, duration_ms, created_at "
        "FROM trace_events WHERE task_id = :tid ORDER BY created_at ASC",
        {"tid": task_id},
    )
    spans = []
    for r in rows:
        r_dict = dict(r) if not isinstance(r, dict) else r
        spans.append(_trace_row_to_span(r_dict))
    return spans


@router.put("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: str,
    updates: TaskUpdate,
    current_agent: CurrentAgent = None,
    task_service: TaskService = Depends(get_task_service)
) -> TaskResponse:
    """
    Update task details
    """
    logger.info("task_update_request", 
               task_id=task_id,
               by_agent=current_agent.agent_id if current_agent else "system")
    
    updated_task = task_service.update_task(task_id, updates)
    
    if not updated_task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task '{task_id}' not found"
        )
    
    return _task_to_response(updated_task)


@router.post("/{task_id}/claim")
async def claim_task(
    task_id: str,
    request: Request,
    current_agent: CurrentAgent,
    task_service: TaskService = Depends(get_task_service),
) -> Dict[str, str]:
    """
    Claim a task for execution
    """
    logger.info("task_claim_request",
               task_id=task_id,
               agent_id=current_agent.agent_id)

    claim_data = TaskClaim(agent_id=current_agent.agent_id)
    success = task_service.claim_task(task_id, claim_data)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to claim task - may not be available or agent not eligible"
        )

    await _broadcast_task_status(
        request,
        task_id=task_id,
        new_status=TaskStatus.CLAIMED.value,
        previous_status=TaskStatus.QUEUED.value,
        agent_id=current_agent.agent_id,
    )

    return {"status": "claimed", "message": "Task claimed successfully"}


@router.post("/{task_id}/start")
async def start_task(
    task_id: str,
    request: Request,
    current_agent: CurrentAgent,
    task_service: TaskService = Depends(get_task_service),
) -> Dict[str, str]:
    """
    Start task execution
    """
    logger.info("task_start_request",
               task_id=task_id,
               agent_id=current_agent.agent_id)

    success = task_service.start_task(task_id, current_agent.agent_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to start task - not claimed by this agent or invalid status"
        )

    await _broadcast_task_status(
        request,
        task_id=task_id,
        new_status=TaskStatus.RUNNING.value,
        previous_status=TaskStatus.CLAIMED.value,
        agent_id=current_agent.agent_id,
    )

    return {"status": "started", "message": "Task started successfully"}


@router.post("/{task_id}/progress")
async def update_progress(
    task_id: str,
    progress: TaskProgress,
    current_agent: CurrentAgent,
    task_service: TaskService = Depends(get_task_service)
) -> Dict[str, str]:
    """
    Update task progress
    """
    success = task_service.update_progress(task_id, current_agent.agent_id, progress)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to update progress - task not owned by agent or invalid status"
        )
    
    return {"status": "progress_updated", "progress": f"{progress.progress_percent}%"}


@router.post("/{task_id}/complete")
async def complete_task(
    task_id: str,
    completion: TaskComplete,
    request: Request,
    current_agent: CurrentAgent,
    task_service: TaskService = Depends(get_task_service),
) -> Dict[str, str]:
    """
    Complete a task
    """
    logger.info("task_completion_request",
               task_id=task_id,
               agent_id=current_agent.agent_id)

    success = task_service.complete_task(task_id, current_agent.agent_id, completion)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to complete task - not owned by agent or invalid status"
        )

    await _broadcast_task_status(
        request,
        task_id=task_id,
        new_status=TaskStatus.COMPLETED.value,
        previous_status=TaskStatus.RUNNING.value,
        agent_id=current_agent.agent_id,
    )

    return {"status": "completed", "message": "Task completed successfully"}


@router.post("/{task_id}/fail")
async def fail_task(
    task_id: str,
    failure: TaskFail,
    request: Request,
    current_agent: CurrentAgent,
    task_service: TaskService = Depends(get_task_service),
) -> Dict[str, str]:
    """
    Fail a task with optional retry
    """
    logger.info("task_failure_request",
               task_id=task_id,
               agent_id=current_agent.agent_id,
               retryable=failure.retryable)

    success = task_service.fail_task(task_id, current_agent.agent_id, failure)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to process task failure"
        )

    # If retryable, task goes back to QUEUED; otherwise FAILED
    broadcast_status = TaskStatus.QUEUED.value if failure.retryable else TaskStatus.FAILED.value
    await _broadcast_task_status(
        request,
        task_id=task_id,
        new_status=broadcast_status,
        previous_status=TaskStatus.RUNNING.value,
        agent_id=current_agent.agent_id,
    )

    status_message = "queued for retry" if failure.retryable else "permanently failed"
    return {"status": "failed", "message": f"Task {status_message}"}


@router.post("/{task_id}/cancel")
async def cancel_task(
    task_id: str,
    reason: Optional[str] = Query(None, description="Cancellation reason"),
    current_agent: CurrentAgent = None,
    task_service: TaskService = Depends(get_task_service)
) -> Dict[str, str]:
    """
    Cancel a task
    """
    logger.info("task_cancellation_request", 
               task_id=task_id,
               by_agent=current_agent.agent_id if current_agent else "system",
               reason=reason)
    
    success = task_service.cancel_task(task_id, reason)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to cancel task - may already be finished"
        )
    
    return {"status": "cancelled", "message": "Task cancelled successfully"}


@router.get("/agent/{agent_id}", response_model=List[TaskResponse])
async def get_agent_tasks(
    agent_id: str,
    status_filter: Optional[List[TaskStatus]] = Query(None, description="Filter by task status"),
    current_agent: CurrentAgent = None,
    task_service: TaskService = Depends(get_task_service)
) -> List[TaskResponse]:
    """
    Get tasks assigned to specific agent
    """
    tasks = task_service.get_agent_tasks(agent_id, status_filter)
    
    return [_task_to_response(task) for task in tasks]


@router.get("/available/for-me", response_model=List[TaskResponse])
async def get_available_tasks(
    limit: int = Query(10, ge=1, le=50, description="Number of tasks to return"),
    current_agent: CurrentAgent = None,
    task_service: TaskService = Depends(get_task_service)
) -> List[TaskResponse]:
    """
    Get tasks available for claiming by current agent
    """
    if not current_agent:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Agent authentication required"
        )
    
    available_tasks = task_service.get_available_tasks(current_agent.agent_id, limit)
    
    return [_task_to_response(task) for task in available_tasks]


# Admin-only endpoints
@router.post("/{task_id}/recover", response_model=TaskResponse)
async def recover_task(
    task_id: str,
    recovery: TaskRecover,
    current_admin = Depends(get_current_admin),
    task_service: TaskService = Depends(get_task_service),
) -> TaskResponse:
    """
    Recover a stale task by resetting it to QUEUED (admin only).

    A stale task is one an agent claimed or started but never released --
    its lease has expired (see Task.is_stale). Recovery returns the work to
    the queue so a healthy agent can re-claim it.

    Responses:
      * 200 - task recovered, returns the updated task
      * 400 - task is not stale (recovering live/finished work is unsafe)
      * 404 - no task with that ID
    """
    reason = recovery.reason

    logger.info(
        "task_recovery_request",
        task_id=task_id,
        admin_id=current_admin.agent_id,
        reason=reason,
    )

    try:
        recovered = task_service.recover_task(
            task_id,
            recovered_by=current_admin.agent_id,
            reason=reason,
        )
    except ValueError as e:
        # Task exists but is not stale - a business-rule violation.
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    if recovered is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task '{task_id}' not found",
        )

    return _task_to_response(recovered)


@router.delete("/{task_id}")
async def delete_task(
    task_id: str,
    current_admin: CurrentAdmin,
    task_service: TaskService = Depends(get_task_service)
) -> Dict[str, str]:
    """
    Delete a task (admin only)
    """
    logger.info("task_deletion_request", 
               task_id=task_id,
               admin_id=current_admin.agent_id)
    
    # Get task first to check if exists
    task = task_service.get_task(task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task '{task_id}' not found"
        )
    
    # Delete task using repository
    success = task_service.task_repo.delete(task_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete task"
        )
    
    logger.info("task_deleted_by_admin", 
               task_id=task_id,
               admin_id=current_admin.agent_id)
    
    return {"status": "deleted", "message": "Task deleted successfully"}


@router.post("/admin/cleanup/expired-leases")
async def cleanup_expired_leases(
    current_admin: CurrentAdmin,
    task_service: TaskService = Depends(get_task_service)
) -> Dict[str, Any]:
    """
    Cleanup tasks with expired leases (admin only)
    """
    try:
        cleaned_count = task_service.task_repo.cleanup_expired_leases()
        
        logger.info("expired_leases_cleanup_requested", 
                   admin_id=current_admin.agent_id,
                   cleaned_count=cleaned_count)
        
        return {
            "status": "completed",
            "cleaned_tasks": cleaned_count,
            "message": f"Cleaned up {cleaned_count} expired task leases"
        }
    
    except Exception as e:
        logger.error("expired_leases_cleanup_failed", 
                    admin_id=current_admin.agent_id,
                    error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Cleanup operation failed"
        )


def _task_to_response(task: Task) -> TaskResponse:
    """Convert Task model to TaskResponse"""
    try:
        return TaskResponse(
            id=task.id,
            title=task.title,
            description=task.description,
            task_type=TaskType(task.task_type),
            priority=TaskPriority(task.priority) if hasattr(TaskPriority, str(task.priority)) else task.priority,
            status=TaskStatus(task.status),
            
            # Assignment info
            assigned_agent_id=task.owner_agent_id,
            requested_capabilities=task.required_capabilities,
            
            # Task data
            input_data=task.payload,
            output_data=task.output,
            error_data={"last_error": task.last_error} if task.last_error else None,
            
            # Workflow info (future Hatchet)
            workflow_id=None,
            workflow_run_id=None,
            
            # Metadata
            created_by=getattr(task, 'created_by', None),
            tags=list(task.labels.keys()) if task.labels else None,
            metadata=task.metadata if hasattr(task, 'metadata') else None,
            
            # Timing
            created_at=task.created_at,
            updated_at=task.updated_at,
            assigned_at=task.claimed_at,
            started_at=task.started_at,
            completed_at=task.completed_at,
            deadline=task.deadline_at,
            
            # Retry info
            retry_count=task.retry_count,
            max_retries=task.max_retries,
            last_error=task.last_error,
            
            # Agent info
            assigned_agent_name=None,  # Would need join with agent table
            assigned_agent_status=None
        )
    except Exception as e:
        logger.error("task_to_response_conversion_failed", 
                    task_id=task.id,
                    error=str(e))
        # Return minimal response on conversion error
        return TaskResponse(
            id=task.id,
            title=task.title,
            description=task.description or "",
            task_type=TaskType.FEATURE,
            priority=TaskPriority.NORMAL,
            status=TaskStatus(task.status),
            assigned_agent_id=task.owner_agent_id,
            requested_capabilities=task.required_capabilities or [],
            input_data=task.payload,
            output_data=task.output,
            error_data=None,
            workflow_id=None,
            workflow_run_id=None,
            created_by=None,
            tags=None,
            metadata=None,
            created_at=task.created_at,
            updated_at=task.updated_at,
            assigned_at=task.claimed_at,
            started_at=task.started_at,
            completed_at=task.completed_at,
            deadline=task.deadline_at,
            retry_count=task.retry_count,
            max_retries=task.max_retries,
            last_error=task.last_error
        )


@router.post(
    "/search",
    response_model=SearchResponse,
    dependencies=[Depends(require_vector)],
    tags=["tasks [experimental]"],
    summary="Semantic search over tasks (experimental, Phase 03 / VEC-05)",
)
async def task_search_shortcut(req: SearchRequest) -> SearchResponse:
    """Vector search shortcut. Forces types=['task'] regardless of body."""
    from .routes_search import unified_search  # local import avoids cycle
    forced = req.model_copy(update={"types": ["task"]})
    return await unified_search(forced)