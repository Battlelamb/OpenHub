"""
Task management endpoints - clean and simple
"""
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query

from ..config import get_settings
from ..logging import get_logger
from ..database.connection import get_database
from ..services.task_service import TaskService
from ..models.tasks import (
    Task, TaskCreate, TaskUpdate, TaskClaim, TaskComplete, TaskFail,
    TaskProgress, TaskStatus, TaskPriority, TaskType, TaskResponse, TaskFilter
)
from ..auth.dependencies import CurrentAgent, CurrentAdmin

logger = get_logger(__name__)
settings = get_settings()

router = APIRouter(prefix="/v1/tasks", tags=["tasks"])


def get_task_service() -> TaskService:
    """Get task service instance"""
    database = get_database()
    return TaskService(database)


@router.post("/", response_model=TaskResponse)
async def create_task(
    task_data: TaskCreate,
    current_agent: CurrentAgent = None,
    task_service: TaskService = Depends(get_task_service)
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
    current_agent: CurrentAgent,
    task_service: TaskService = Depends(get_task_service)
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
    
    return {"status": "claimed", "message": "Task claimed successfully"}


@router.post("/{task_id}/start")
async def start_task(
    task_id: str,
    current_agent: CurrentAgent,
    task_service: TaskService = Depends(get_task_service)
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
    current_agent: CurrentAgent,
    task_service: TaskService = Depends(get_task_service)
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
    
    return {"status": "completed", "message": "Task completed successfully"}


@router.post("/{task_id}/fail")
async def fail_task(
    task_id: str,
    failure: TaskFail,
    current_agent: CurrentAgent,
    task_service: TaskService = Depends(get_task_service)
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
    sort_order: str = Query("desc", regex="^(asc|desc)$", description="Sort order"),
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


# Admin-only endpoints
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