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
    """Model for registering a remote agent - all details collected at join time"""

    # Required
    agent_name: str = Field(description="Agent name", min_length=1, max_length=100)
    capabilities: List[str] = Field(description="Agent capabilities", min_length=1, max_length=50)
    node_name: str = Field(description="ACN node name", min_length=1, max_length=100)

    # Identity
    description: Optional[str] = Field(default=None, max_length=500)
    model: Optional[str] = Field(default=None, max_length=100, description="AI model (gpt-5.3-codex, claude-opus-4-6)")
    platform: Optional[str] = Field(default=None, max_length=100, description="Platform (openclaw, claude-code, qwen-code)")
    version: Optional[str] = Field(default=None, max_length=50, description="Agent version")

    # Location
    hostname: Optional[str] = Field(default=None, max_length=200)
    os_info: Optional[str] = Field(default=None, max_length=100, description="OS (debian-13, wsl2-ubuntu)")
    workspace_path: Optional[str] = Field(default=None, max_length=500)

    # Communication
    callback_url: Optional[str] = Field(default=None, max_length=500, description="Webhook callback URL")
    channels: Optional[List[str]] = Field(default=None, description="Communication channels (telegram, discord, terminal)")

    # Extended capabilities
    skills: Optional[List[str]] = Field(default=None, description="Installed skills")
    mcp_servers: Optional[List[str]] = Field(default=None, description="Connected MCP servers")
    languages: Optional[List[str]] = Field(default=None, description="Programming languages")
    context_window: Optional[int] = Field(default=None, description="Max context window size")


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
