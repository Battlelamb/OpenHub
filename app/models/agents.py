"""
Agent-related Pydantic models
"""
from enum import Enum
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import Field, field_validator

from .base import BaseModel, TimestampMixin, IDMixin, MetadataMixin


class AgentStatus(str, Enum):
    """Agent status enumeration"""
    ONLINE = "online"
    OFFLINE = "offline"
    BUSY = "busy"
    IDLE = "idle"
    ERROR = "error"


class AgentCapability(BaseModel):
    """Agent capability model"""
    
    name: str = Field(
        description="Capability name",
        min_length=1,
        max_length=100
    )
    
    version: Optional[str] = Field(
        default=None,
        description="Capability version"
    )
    
    confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Confidence level (0.0 to 1.0)"
    )


class AgentCreate(BaseModel):
    """Model for creating a new agent"""
    
    agent_name: str = Field(
        description="Agent name",
        min_length=1,
        max_length=100
    )
    
    capabilities: List[str] = Field(
        description="List of agent capabilities",
        min_items=1,
        max_items=50
    )
    
    labels: Dict[str, str] = Field(
        default_factory=dict,
        description="Agent labels"
    )
    
    description: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Agent description"
    )
    
    @field_validator('capabilities')
    @classmethod
    def validate_capabilities(cls, v):
        """Validate capability names"""
        allowed_chars = set('abcdefghijklmnopqrstuvwxyz0123456789_-')
        
        for cap in v:
            if not cap:
                raise ValueError("Capability name cannot be empty")
            if not all(c.lower() in allowed_chars for c in cap):
                raise ValueError(f"Invalid capability name: {cap}")
            if len(cap) > 50:
                raise ValueError(f"Capability name too long: {cap}")
        
        return v
    
    @field_validator('agent_name')
    @classmethod
    def validate_agent_name(cls, v):
        """Validate agent name format"""
        if not v:
            raise ValueError("Agent name cannot be empty")
        
        # Allow alphanumeric, hyphens, underscores
        allowed_chars = set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-')
        if not all(c in allowed_chars for c in v):
            raise ValueError("Agent name contains invalid characters")
        
        return v


class AgentUpdate(BaseModel):
    """Model for updating an agent"""
    
    agent_name: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=100,
        description="Updated agent name"
    )
    
    capabilities: Optional[List[str]] = Field(
        default=None,
        min_items=1,
        max_items=50,
        description="Updated capabilities"
    )
    
    labels: Optional[Dict[str, str]] = Field(
        default=None,
        description="Updated labels"
    )
    
    description: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Updated description"
    )
    
    status: Optional[AgentStatus] = Field(
        default=None,
        description="Updated status"
    )


class AgentHeartbeat(BaseModel):
    """Model for agent heartbeat"""
    
    status: AgentStatus = Field(
        default=AgentStatus.ONLINE,
        description="Current agent status"
    )
    
    current_task: Optional[str] = Field(
        default=None,
        description="Current task ID being worked on"
    )
    
    message: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Optional status message"
    )
    
    metrics: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional performance metrics"
    )


class Agent(IDMixin, TimestampMixin, MetadataMixin):
    """Complete agent model"""
    
    agent_name: str = Field(
        description="Agent name"
    )
    
    capabilities: List[str] = Field(
        description="Agent capabilities"
    )
    
    status: AgentStatus = Field(
        default=AgentStatus.OFFLINE,
        description="Current agent status"
    )
    
    last_heartbeat: Optional[datetime] = Field(
        default=None,
        description="Last heartbeat timestamp"
    )
    
    current_task: Optional[str] = Field(
        default=None,
        description="Current task ID"
    )
    
    description: Optional[str] = Field(
        default=None,
        description="Agent description"
    )
    
    # Performance metrics
    tasks_completed: int = Field(
        default=0,
        ge=0,
        description="Total tasks completed"
    )
    
    tasks_failed: int = Field(
        default=0,
        ge=0,
        description="Total tasks failed"
    )
    
    average_task_duration: Optional[float] = Field(
        default=None,
        ge=0.0,
        description="Average task duration in seconds"
    )


class AgentRegistrationResponse(BaseModel):
    """Response for agent registration"""
    
    agent_id: str = Field(description="Generated agent ID")
    
    lease_ttl_sec: int = Field(description="Lease TTL in seconds")
    
    message: str = Field(description="Registration message")


class AgentListResponse(BaseModel):
    """Response for agent list"""
    
    agents: List[Agent] = Field(description="List of agents")
    
    total: int = Field(description="Total number of agents")


class AgentStatsResponse(BaseModel):
    """Response for agent statistics"""
    
    total_agents: int = Field(description="Total registered agents")
    
    online_agents: int = Field(description="Currently online agents")
    
    busy_agents: int = Field(description="Currently busy agents")
    
    idle_agents: int = Field(description="Currently idle agents")
    
    by_capability: Dict[str, int] = Field(
        description="Agent count by capability"
    )
    
    by_status: Dict[str, int] = Field(
        description="Agent count by status"
    )