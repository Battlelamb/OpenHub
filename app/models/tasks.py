"""
Task-related Pydantic models
"""
from enum import Enum, IntEnum
from datetime import datetime, timezone
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


class TaskEvidenceType(str, Enum):
    """Supported durable task evidence categories."""

    TEST = "test"
    LOG = "log"
    DIFF = "diff"
    ARTIFACT = "artifact"
    PR = "pr"
    REVIEW = "review"
    COMMAND = "command"
    QUALITY_GATE = "quality_gate"


class TaskEvidenceOutcome(str, Enum):
    """Optional outcome attached to task evidence."""

    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    RUNNING = "running"
    UNKNOWN = "unknown"


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
        min_length=1,
        max_length=20
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


class TaskRecover(BaseModel):
    """Model for recovering a stale task back to the queue.

    The recovery endpoint accepts this body optionally; when supplied,
    ``reason`` is recorded for the recovery audit trail.
    """

    reason: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Why the task is being recovered (for the audit trail)"
    )


class TaskEvidenceCreate(BaseModel):
    """Model for creating private/internal task evidence."""

    evidence_type: TaskEvidenceType = Field(description="Evidence category")

    title: str = Field(
        description="Short evidence title",
        min_length=1,
        max_length=200,
    )

    summary: Optional[str] = Field(
        default=None,
        max_length=2000,
        description="Human-readable evidence summary",
    )

    content: Dict[str, Any] = Field(
        default_factory=dict,
        description="Structured, sanitized evidence payload",
    )

    artifact_ids: List[str] = Field(
        default_factory=list,
        max_length=50,
        description="Related artifact IDs",
    )

    outcome: TaskEvidenceOutcome = Field(
        default=TaskEvidenceOutcome.UNKNOWN,
        description="Evidence result state",
    )

    source_agent_id: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Agent that emitted the evidence",
    )

    labels: Dict[str, str] = Field(
        default_factory=dict,
        description="Internal evidence labels",
    )

    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Internal evidence metadata",
    )

    occurred_at: Optional[datetime] = Field(
        default=None,
        description="When the evidenced event occurred",
    )


class TaskEvidence(IDMixin, TimestampMixin):
    """Persisted private/internal evidence row for a task."""

    task_id: str = Field(description="Associated task ID")
    evidence_type: TaskEvidenceType = Field(description="Evidence category")
    title: str = Field(description="Short evidence title")
    summary: Optional[str] = Field(default=None, description="Evidence summary")
    content: Dict[str, Any] = Field(default_factory=dict, description="Structured payload")
    artifact_ids: List[str] = Field(default_factory=list, description="Related artifacts")
    outcome: TaskEvidenceOutcome = Field(
        default=TaskEvidenceOutcome.UNKNOWN,
        description="Evidence result state",
    )
    source_agent_id: Optional[str] = Field(default=None, description="Emitting agent")
    labels: Dict[str, str] = Field(default_factory=dict, description="Internal labels")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Internal metadata")
    occurred_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When the evidenced event occurred",
    )


class TaskEvidenceResponse(IDMixin, TimestampMixin):
    """API-safe task evidence DTO that omits internal labels/metadata."""

    task_id: str = Field(description="Associated task ID")
    evidence_type: TaskEvidenceType = Field(description="Evidence category")
    title: str = Field(description="Short evidence title")
    summary: Optional[str] = Field(default=None, description="Evidence summary")
    content: Dict[str, Any] = Field(default_factory=dict, description="Sanitized payload")
    artifact_ids: List[str] = Field(default_factory=list, description="Related artifacts")
    outcome: TaskEvidenceOutcome = Field(
        default=TaskEvidenceOutcome.UNKNOWN,
        description="Evidence result state",
    )
    source_agent_id: Optional[str] = Field(default=None, description="Emitting principal")
    occurred_at: datetime = Field(description="When the evidenced event occurred")


class TaskVerificationState(BaseModel):
    """Verification lifecycle DTO for a task's quality-gate state.

    This does not mutate task status. It summarizes whether an agent completion
    claim has enough quality-gate evidence for an admin/human to close the task.
    """

    task_id: str = Field(description="Task ID")
    task_status: TaskStatus = Field(description="Canonical task status")
    lifecycle_state: str = Field(
        description="Derived verification state: not_started, in_progress, awaiting_quality_gate, quality_gate_passed, quality_gate_failed, skipped, completed, or terminal"
    )
    ready_for_completion: bool = Field(
        description="True when the latest quality_gate evidence passed and the task awaits approval"
    )
    required_action: str = Field(description="Next operator/system action")
    quality_gate_counts: Dict[str, int] = Field(
        default_factory=lambda: {"passed": 0, "failed": 0, "skipped": 0, "unknown": 0},
        description="Counts of quality_gate evidence by outcome",
    )
    latest_quality_gate: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Latest quality_gate evidence summary, if present",
    )


class TaskTimelineItem(BaseModel):
    """Safe internal task timeline item merging trace and evidence sources."""

    id: str = Field(description="Source row ID")
    task_id: str = Field(description="Associated task ID")
    source: str = Field(description="Timeline source: evidence or trace")
    item_type: str = Field(description="Evidence type or trace event type")
    title: str = Field(description="Operator-facing event title")
    occurred_at: datetime = Field(description="When the event occurred")
    actor_id: Optional[str] = Field(default=None, description="Agent/principal that emitted the event")
    summary: Optional[str] = Field(default=None, description="Short human-readable summary")
    content: Dict[str, Any] = Field(default_factory=dict, description="Sanitized structured payload")
    artifact_ids: List[str] = Field(default_factory=list, description="Related artifacts")
    outcome: Optional[str] = Field(default=None, description="Evidence outcome, when applicable")
    trace_id: Optional[str] = Field(default=None, description="Trace ID, when source is trace")
    duration_ms: Optional[float] = Field(default=None, description="Trace duration, when available")
    category: Optional[str] = Field(default=None, description="Trace category, when available")
    level: Optional[int] = Field(default=None, description="Trace nesting level, when available")
    created_at: Optional[datetime] = Field(default=None, description="Source row creation timestamp")
    updated_at: Optional[datetime] = Field(default=None, description="Source row update timestamp")


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

    def is_stale(self, now: Optional[datetime] = None) -> bool:
        """Return True if this task is stuck with an expired lease.

        A task is "stale" when an agent still holds it (status CLAIMED or
        RUNNING) but its ``lease_until`` deadline has already passed -- a
        strong signal the agent died or hung without releasing the work.
        Terminal and unclaimed tasks (COMPLETED, FAILED, QUEUED, ...) are
        never stale, even if an old lease timestamp sits in the past.

        This is a pure detection predicate: it never mutates the task.

        Args:
            now: Reference time to compare the lease against. Defaults to
                the current UTC time; tests inject a fixed value so the
                result is deterministic.

        Returns:
            True if the task is stale, False otherwise.
        """
        # 1. Only CLAIMED or RUNNING tasks can be stale.
        status_str = self.status if isinstance(self.status, str) else self.status.value
        if status_str not in ("claimed", "running"):
            return False

        # 2. No lease deadline -> not stale.
        if self.lease_until is None:
            return False

        # 3. Default now to current UTC.
        if now is None:
            now = datetime.now(timezone.utc)

        # 4. Normalise both sides to timezone-aware UTC.
        lease = self.lease_until
        if lease.tzinfo is None:
            lease = lease.replace(tzinfo=timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        # 5. Stale if lease deadline is before now.
        return lease < now


class TaskResponse(BaseModel):
    """API response model for a single task"""

    id: str = Field(description="Task ID")
    title: str = Field(description="Task title")
    description: Optional[str] = Field(default=None, description="Task description")
    task_type: TaskType = Field(description="Task type")
    priority: Any = Field(description="Task priority")
    status: TaskStatus = Field(description="Current status")

    # Assignment
    assigned_agent_id: Optional[str] = Field(default=None, description="Assigned agent ID")
    requested_capabilities: Optional[List[str]] = Field(default=None, description="Required capabilities")

    # Data
    input_data: Optional[Dict[str, Any]] = Field(default=None, description="Input payload")
    output_data: Optional[Dict[str, Any]] = Field(default=None, description="Output data")
    error_data: Optional[Dict[str, Any]] = Field(default=None, description="Error details")

    # Workflow
    workflow_id: Optional[str] = Field(default=None, description="Workflow ID")
    workflow_run_id: Optional[str] = Field(default=None, description="Workflow run ID")

    # Metadata
    created_by: Optional[str] = Field(default=None, description="Creator ID")
    tags: Optional[List[str]] = Field(default=None, description="Tags")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Extra metadata")

    # Timing
    created_at: Optional[datetime] = Field(default=None, description="Created at")
    updated_at: Optional[datetime] = Field(default=None, description="Updated at")
    assigned_at: Optional[datetime] = Field(default=None, description="Assigned at")
    started_at: Optional[datetime] = Field(default=None, description="Started at")
    completed_at: Optional[datetime] = Field(default=None, description="Completed at")
    deadline: Optional[datetime] = Field(default=None, description="Deadline")

    # Retry
    retry_count: int = Field(default=0, description="Retry count")
    max_retries: int = Field(default=0, description="Max retries")
    last_error: Optional[str] = Field(default=None, description="Last error message")

    # Agent info
    assigned_agent_name: Optional[str] = Field(default=None, description="Agent name")
    assigned_agent_status: Optional[str] = Field(default=None, description="Agent status")


class StaleTaskResponse(BaseModel):
    """Compact API row for a stale task in the ``GET /v1/tasks/stale`` listing.

    A *stale* task is one an agent claimed or started but never released --
    its lease (``lease_until``) has expired (see ``Task.is_stale``), so the
    work is silently stuck. This shape is intentionally small: just enough for
    an operator to spot the stuck task and see how long it has been stuck.
    """

    id: str = Field(description="Task ID")
    title: str = Field(description="Task title")
    status: TaskStatus = Field(description="Current status (claimed or running)")
    owner_agent_id: Optional[str] = Field(
        default=None, description="Agent holding the expired lease"
    )
    lease_until: Optional[datetime] = Field(
        default=None, description="When the task's lease expired"
    )
    stale_seconds: float = Field(
        description="How long the task has been stale, in seconds "
        "(elapsed time since lease_until expired)"
    )


class TaskFilter(BaseModel):
    """Filter criteria for task queries"""

    status: Optional[TaskStatus] = None
    task_type: Optional[TaskType] = None
    priority: Optional[TaskPriority] = None
    assigned_agent_id: Optional[str] = None
    tags: Optional[List[str]] = None


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