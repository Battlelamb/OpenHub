"""
Task-related Pydantic models
"""
from enum import Enum, IntEnum
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import Field, field_validator

from .base import BaseModel, TimestampMixin, IDMixin


class TaskStatus(str, Enum):
    """Task status enumeration"""
    QUEUED = "queued"
    CLAIMED = "claimed"
    RUNNING = "running"
    WAITING_APPROVAL = "waiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    DEAD_LETTER = "dead_letter"
    CANCELLED = "cancelled"


class TaskPriority(IntEnum):
    """Task priority levels (lower number = higher priority)"""
    CRITICAL = 0
    HIGH = 25
    NORMAL = 50
    LOW = 75
    MINIMAL = 100


class TaskType(str, Enum):
    """Task type enumeration"""
    CODE_EDIT = "code_edit"
    CODE_REVIEW = "code_review"
    TESTING = "testing"
    DOCUMENTATION = "documentation"
    DEPLOYMENT = "deployment"
    ANALYSIS = "analysis"
    REFACTORING = "refactoring"
    BUG_FIX = "bug_fix"
    FEATURE = "feature"
    MAINTENANCE = "maintenance"
    RESEARCH = "research"
    AUTOMATION = "automation"


class TaskCreate(BaseModel):
    """Model for creating a new task"""
    
    title: str = Field(
        description="Task title",
        min_length=1,
        max_length=200
    )
    
    description: str = Field(
        description="Task description",
        min_length=1,
        max_length=5000
    )
    
    task_type: TaskType = Field(
        default=TaskType.FEATURE,
        description="Type of task"
    )
    
    required_capabilities: List[str] = Field(
        description="Required agent capabilities",
        min_items=1,
        max_items=20
    )
    
    priority: int = Field(
        default=TaskPriority.NORMAL,
        ge=0,
        le=100,
        description="Task priority (0-100, lower = higher priority)"
    )
    
    payload: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Task-specific data"
    )
    
    deadline_at: Optional[datetime] = Field(
        default=None,
        description="Task deadline"
    )
    
    max_retries: int = Field(
        default=2,
        ge=0,
        le=10,
        description="Maximum retry attempts"
    )
    
    idempotency_key: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Idempotency key for duplicate prevention"
    )
    
    labels: Dict[str, str] = Field(
        default_factory=dict,
        description="Task labels"
    )
    
    @field_validator('required_capabilities')
    @classmethod
    def validate_capabilities(cls, v):
        """Validate required capabilities"""
        for cap in v:
            if not cap or len(cap.strip()) == 0:
                raise ValueError("Empty capability not allowed")
            if len(cap) > 50:
                raise ValueError(f"Capability name too long: {cap}")
        return v


class TaskUpdate(BaseModel):
    """Model for updating a task"""
    
    title: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=200,
        description="Updated title"
    )
    
    description: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=5000,
        description="Updated description"
    )
    
    priority: Optional[int] = Field(
        default=None,
        ge=0,
        le=100,
        description="Updated priority"
    )
    
    deadline_at: Optional[datetime] = Field(
        default=None,
        description="Updated deadline"
    )
    
    labels: Optional[Dict[str, str]] = Field(
        default=None,
        description="Updated labels"
    )


class TaskClaim(BaseModel):
    """Model for claiming a task"""
    
    agent_id: str = Field(
        description="Agent ID claiming the task"
    )
    
    estimated_duration: Optional[int] = Field(
        default=None,
        ge=1,
        description="Estimated completion time in seconds"
    )


class TaskProgress(BaseModel):
    """Model for task progress updates"""
    
    progress_percent: int = Field(
        ge=0,
        le=100,
        description="Completion percentage"
    )
    
    note: Optional[str] = Field(
        default=None,
        max_length=1000,
        description="Progress note"
    )
    
    metrics: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Progress metrics"
    )


class TaskComplete(BaseModel):
    """Model for completing a task"""
    
    result_summary: str = Field(
        description="Summary of task completion",
        min_length=1,
        max_length=2000
    )
    
    output: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Task output data"
    )
    
    artifact_ids: List[str] = Field(
        default_factory=list,
        description="IDs of created artifacts"
    )
    
    metrics: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Completion metrics"
    )


class TaskFail(BaseModel):
    """Model for failing a task"""
    
    error_message: str = Field(
        description="Error description",
        min_length=1,
        max_length=2000
    )
    
    error_code: Optional[str] = Field(
        default=None,
        max_length=50,
        description="Error code"
    )
    
    retryable: bool = Field(
        default=True,
        description="Whether the task can be retried"
    )
    
    error_details: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Detailed error information"
    )


class TaskAttempt(IDMixin, TimestampMixin):
    """Model for task execution attempts"""
    
    task_id: str = Field(description="Associated task ID")
    
    agent_id: str = Field(description="Agent that made the attempt")
    
    attempt_number: int = Field(
        ge=1,
        description="Attempt number"
    )
    
    started_at: datetime = Field(description="Attempt start time")
    
    completed_at: Optional[datetime] = Field(
        default=None,
        description="Attempt completion time"
    )
    
    status: TaskStatus = Field(description="Attempt status")
    
    error_message: Optional[str] = Field(
        default=None,
        description="Error message if failed"
    )
    
    duration_seconds: Optional[float] = Field(
        default=None,
        ge=0.0,
        description="Attempt duration in seconds"
    )


class Task(IDMixin, TimestampMixin):
    """Complete task model"""
    
    title: str = Field(description="Task title")
    
    description: str = Field(description="Task description")
    
    task_type: TaskType = Field(description="Task type")
    
    status: TaskStatus = Field(
        default=TaskStatus.QUEUED,
        description="Current task status"
    )
    
    priority: int = Field(description="Task priority")
    
    required_capabilities: List[str] = Field(description="Required capabilities")
    
    # Assignment and execution
    owner_agent_id: Optional[str] = Field(
        default=None,
        description="Agent currently assigned to task"
    )
    
    claimed_at: Optional[datetime] = Field(
        default=None,
        description="When task was claimed"
    )
    
    started_at: Optional[datetime] = Field(
        default=None,
        description="When task execution started"
    )
    
    completed_at: Optional[datetime] = Field(
        default=None,
        description="When task was completed"
    )
    
    lease_until: Optional[datetime] = Field(
        default=None,
        description="Lease expiration time"
    )
    
    # Retry and failure handling
    retry_count: int = Field(
        default=0,
        ge=0,
        description="Current retry count"
    )
    
    max_retries: int = Field(description="Maximum retry attempts")
    
    last_error: Optional[str] = Field(
        default=None,
        description="Last error message"
    )
    
    # Deadline and metadata
    deadline_at: Optional[datetime] = Field(
        default=None,
        description="Task deadline"
    )
    
    idempotency_key: Optional[str] = Field(
        default=None,
        description="Idempotency key"
    )
    
    labels: Dict[str, str] = Field(
        default_factory=dict,
        description="Task labels"
    )
    
    payload: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Task-specific data"
    )
    
    # Results
    result_summary: Optional[str] = Field(
        default=None,
        description="Task completion summary"
    )
    
    output: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Task output data"
    )
    
    artifact_ids: List[str] = Field(
        default_factory=list,
        description="Associated artifact IDs"
    )
    
    # Performance metrics
    duration_seconds: Optional[float] = Field(
        default=None,
        ge=0.0,
        description="Total execution duration"
    )


class TaskListResponse(BaseModel):
    """Response for task list"""
    
    tasks: List[Task] = Field(description="List of tasks")
    
    total: int = Field(description="Total number of tasks")


class TaskStatsResponse(BaseModel):
    """Response for task statistics"""
    
    total_tasks: int = Field(description="Total tasks")
    
    by_status: Dict[str, int] = Field(description="Task count by status")
    
    by_type: Dict[str, int] = Field(description="Task count by type")
    
    by_priority: Dict[str, int] = Field(description="Task count by priority")
    
    average_completion_time: Optional[float] = Field(
        default=None,
        description="Average completion time in seconds"
    )
    
    success_rate: float = Field(
        ge=0.0,
        le=1.0,
        description="Task success rate"
    )