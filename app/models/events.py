"""
Event-related Pydantic models for system events and notifications
"""
from enum import Enum
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import Field, field_validator

from .base import BaseModel, TimestampMixin, IDMixin


class EventType(str, Enum):
    """Event type enumeration"""
    AGENT_REGISTERED = "agent_registered"
    AGENT_DISCONNECTED = "agent_disconnected"
    AGENT_STATUS_CHANGED = "agent_status_changed"
    TASK_CREATED = "task_created"
    TASK_CLAIMED = "task_claimed"
    TASK_STARTED = "task_started"
    TASK_PROGRESS_UPDATED = "task_progress_updated"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    TASK_CANCELLED = "task_cancelled"
    TASK_RETRY = "task_retry"
    ARTIFACT_CREATED = "artifact_created"
    ARTIFACT_ACCESSED = "artifact_accessed"
    SYSTEM_ERROR = "system_error"
    SYSTEM_WARNING = "system_warning"
    COORDINATION_CONFLICT = "coordination_conflict"
    CAPABILITY_UPDATED = "capability_updated"


class EventSeverity(str, Enum):
    """Event severity levels"""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class EventCreate(BaseModel):
    """Model for creating a new event"""
    
    event_type: EventType = Field(
        description="Type of event"
    )
    
    severity: EventSeverity = Field(
        default=EventSeverity.INFO,
        description="Event severity level"
    )
    
    title: str = Field(
        description="Event title",
        min_length=1,
        max_length=200
    )
    
    description: Optional[str] = Field(
        default=None,
        max_length=1000,
        description="Event description"
    )
    
    source_agent_id: Optional[str] = Field(
        default=None,
        description="Agent that triggered the event"
    )
    
    related_task_id: Optional[str] = Field(
        default=None,
        description="Related task ID"
    )
    
    related_artifact_id: Optional[str] = Field(
        default=None,
        description="Related artifact ID"
    )
    
    data: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional event data"
    )
    
    labels: Dict[str, str] = Field(
        default_factory=dict,
        description="Event labels"
    )


class EventFilter(BaseModel):
    """Model for filtering events"""
    
    event_types: Optional[List[EventType]] = Field(
        default=None,
        description="Filter by event types"
    )
    
    severities: Optional[List[EventSeverity]] = Field(
        default=None,
        description="Filter by severity levels"
    )
    
    source_agent_id: Optional[str] = Field(
        default=None,
        description="Filter by source agent"
    )
    
    related_task_id: Optional[str] = Field(
        default=None,
        description="Filter by related task"
    )
    
    from_timestamp: Optional[datetime] = Field(
        default=None,
        description="Filter events from this timestamp"
    )
    
    to_timestamp: Optional[datetime] = Field(
        default=None,
        description="Filter events until this timestamp"
    )
    
    labels: Optional[Dict[str, str]] = Field(
        default=None,
        description="Filter by labels"
    )


class Event(IDMixin, TimestampMixin):
    """Complete event model"""
    
    event_type: EventType = Field(description="Event type")
    
    severity: EventSeverity = Field(description="Event severity")
    
    title: str = Field(description="Event title")
    
    description: Optional[str] = Field(
        default=None,
        description="Event description"
    )
    
    source_agent_id: Optional[str] = Field(
        default=None,
        description="Source agent ID"
    )
    
    related_task_id: Optional[str] = Field(
        default=None,
        description="Related task ID"
    )
    
    related_artifact_id: Optional[str] = Field(
        default=None,
        description="Related artifact ID"
    )
    
    data: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Event data"
    )
    
    labels: Dict[str, str] = Field(
        default_factory=dict,
        description="Event labels"
    )
    
    acknowledged: bool = Field(
        default=False,
        description="Whether event has been acknowledged"
    )
    
    acknowledged_by: Optional[str] = Field(
        default=None,
        description="Agent that acknowledged the event"
    )
    
    acknowledged_at: Optional[datetime] = Field(
        default=None,
        description="Acknowledgment timestamp"
    )


class EventListResponse(BaseModel):
    """Response for event list"""
    
    events: List[Event] = Field(description="List of events")
    
    total: int = Field(description="Total number of events")


class EventStatsResponse(BaseModel):
    """Response for event statistics"""
    
    total_events: int = Field(description="Total events")
    
    by_type: Dict[str, int] = Field(description="Event count by type")
    
    by_severity: Dict[str, int] = Field(description="Event count by severity")
    
    by_agent: Dict[str, int] = Field(description="Event count by source agent")
    
    recent_errors: int = Field(
        description="Error events in last 24 hours"
    )
    
    unacknowledged_count: int = Field(
        description="Unacknowledged events"
    )