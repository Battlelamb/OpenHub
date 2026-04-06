"""
ACN (Agent Collaboration Network) Pydantic models
"""
from enum import Enum
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import Field

from .base import BaseModel, TimestampMixin, IDMixin, MetadataMixin


class ACNNodeStatus(str, Enum):
    """ACN node status enumeration"""
    ONLINE = "online"
    OFFLINE = "offline"
    DEGRADED = "degraded"


class ACNNode(IDMixin, TimestampMixin, MetadataMixin):
    """Complete ACN node model"""

    node_name: str = Field(
        description="Node name"
    )

    node_url: str = Field(
        description="Node URL endpoint"
    )

    status: ACNNodeStatus = Field(
        default=ACNNodeStatus.OFFLINE,
        description="Current node status"
    )

    capabilities: List[str] = Field(
        default_factory=list,
        description="Node capabilities"
    )

    last_heartbeat: Optional[datetime] = Field(
        default=None,
        description="Last heartbeat timestamp"
    )


class ACNNodeCreate(BaseModel):
    """Model for creating a new ACN node"""

    node_name: str = Field(
        description="Node name",
        min_length=1,
        max_length=100
    )

    node_url: str = Field(
        description="Node URL endpoint",
        min_length=1,
        max_length=500
    )


class RemoteAgentRegister(BaseModel):
    """Model for registering a remote agent"""

    agent_name: str = Field(
        description="Agent name",
        min_length=1,
        max_length=100
    )

    capabilities: List[str] = Field(
        description="List of agent capabilities",
        min_length=1,
        max_length=50
    )

    node_name: str = Field(
        description="Name of the ACN node this agent belongs to",
        min_length=1,
        max_length=100
    )

    description: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Agent description"
    )

    callback_url: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Callback URL for task results"
    )


class RemoteAgentMapping(IDMixin, TimestampMixin):
    """Remote agent mapping model"""

    local_agent_id: str = Field(
        description="Local agent ID"
    )

    node_id: str = Field(
        description="ACN node ID"
    )

    remote_agent_name: str = Field(
        description="Remote agent name"
    )

    callback_url: Optional[str] = Field(
        default=None,
        description="Callback URL"
    )

    connection_metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Connection metadata"
    )


class TaskResultSubmission(BaseModel):
    """Model for submitting task results"""

    task_id: str = Field(
        description="Task ID"
    )

    status: str = Field(
        description="Task status - completed or failed"
    )

    result_summary: Optional[str] = Field(
        default=None,
        max_length=1000,
        description="Result summary"
    )

    output: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Task output data"
    )

    error_message: Optional[str] = Field(
        default=None,
        max_length=1000,
        description="Error message if failed"
    )
