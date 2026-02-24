"""
RBAC models and data structures for OpenHub
"""
from enum import Enum
from typing import Dict, List, Any
from pydantic import Field

from ...models.base import BaseModel


class Subject(str, Enum):
    """Subjects that can perform actions (who)"""
    AGENT = "agent"
    ADMIN = "admin"  
    SERVICE = "service"
    READONLY = "readonly"
    WEBHOOK = "webhook"
    SYSTEM = "system"


class Resource(str, Enum):
    """Resources that can be accessed (what)"""
    TASK = "task"
    AGENT = "agent"
    ARTIFACT = "artifact"
    EVENT = "event"
    THREAD = "thread"
    MESSAGE = "message"
    APPROVAL = "approval"
    LOCK = "lock"
    SYSTEM = "system"
    WEBHOOK = "webhook"
    API_KEY = "api_key"


class Action(str, Enum):
    """Actions that can be performed (how)"""
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    CLAIM = "claim"
    COMPLETE = "complete"
    CANCEL = "cancel"
    ASSIGN = "assign"
    APPROVE = "approve"
    REJECT = "reject"
    UPLOAD = "upload"
    DOWNLOAD = "download"
    SEND = "send"
    RECEIVE = "receive"
    MONITOR = "monitor"
    CONFIGURE = "configure"
    BACKUP = "backup"


class PolicyRule(BaseModel):
    """Single RBAC policy rule"""
    
    subject: str = Field(description="Subject (role/user)")
    resource: str = Field(description="Resource being accessed")
    action: str = Field(description="Action being performed")
    effect: str = Field(default="allow", description="Effect (allow/deny)")
    conditions: Dict[str, Any] = Field(default_factory=dict, description="Additional conditions")


class RoleDefinition(BaseModel):
    """Role definition with permissions"""
    
    name: str = Field(description="Role name")
    description: str = Field(description="Role description")
    permissions: List[str] = Field(description="List of permissions")
    inherits_from: List[str] = Field(default_factory=list, description="Parent roles")
    is_system_role: bool = Field(default=False, description="Whether this is a system role")


class PermissionCheck(BaseModel):
    """Permission check request"""
    
    subject: str = Field(description="Subject identifier (agent_id, role, etc)")
    resource: str = Field(description="Resource being accessed") 
    action: str = Field(description="Action being performed")
    context: Dict[str, Any] = Field(default_factory=dict, description="Additional context")


class PermissionResult(BaseModel):
    """Permission check result"""
    
    allowed: bool = Field(description="Whether action is allowed")
    reason: str = Field(description="Reason for decision")
    matched_policies: List[str] = Field(description="Policies that matched")
    context: Dict[str, Any] = Field(default_factory=dict, description="Additional context")


class PolicyTemplate(BaseModel):
    """Template for creating policies"""
    
    name: str = Field(description="Template name")
    description: str = Field(description="Template description")
    subject_pattern: str = Field(description="Subject pattern")
    resource_pattern: str = Field(description="Resource pattern") 
    action_pattern: str = Field(description="Action pattern")
    effect: str = Field(default="allow", description="Effect")
    conditions: Dict[str, Any] = Field(default_factory=dict, description="Conditions")


# Predefined permission patterns
PERMISSION_PATTERNS = {
    # Task permissions
    "task:full": ["task:create", "task:read", "task:update", "task:delete", "task:claim", "task:complete"],
    "task:manage": ["task:create", "task:read", "task:update", "task:assign", "task:cancel"],
    "task:work": ["task:read", "task:claim", "task:update", "task:complete"],
    "task:view": ["task:read"],
    
    # Agent permissions  
    "agent:full": ["agent:create", "agent:read", "agent:update", "agent:delete"],
    "agent:manage": ["agent:read", "agent:update", "agent:assign"],
    "agent:register": ["agent:create", "agent:read"],
    "agent:view": ["agent:read"],
    
    # Artifact permissions
    "artifact:full": ["artifact:create", "artifact:read", "artifact:update", "artifact:delete", "artifact:upload", "artifact:download"],
    "artifact:manage": ["artifact:read", "artifact:upload", "artifact:download", "artifact:delete"],
    "artifact:work": ["artifact:read", "artifact:upload", "artifact:download"],
    "artifact:view": ["artifact:read", "artifact:download"],
    
    # System permissions
    "system:full": ["system:read", "system:configure", "system:monitor", "system:backup"],
    "system:admin": ["system:configure", "system:monitor", "system:backup"],
    "system:monitor": ["system:read", "system:monitor"],
    
    # Communication permissions
    "communication:full": ["thread:create", "thread:read", "thread:update", "message:send", "message:read"],
    "communication:participate": ["thread:read", "message:send", "message:read"],
    "communication:view": ["thread:read", "message:read"]
}


# Default role definitions
DEFAULT_ROLES = {
    "agent": RoleDefinition(
        name="agent",
        description="Standard AI agent with task execution capabilities",
        permissions=[
            "task:work",
            "artifact:work", 
            "communication:participate",
            "event:create",
            "agent:register"
        ],
        is_system_role=True
    ),
    
    "admin": RoleDefinition(
        name="admin",
        description="Administrator with full system access",
        permissions=[
            "task:full",
            "agent:full",
            "artifact:full",
            "system:full",
            "communication:full",
            "*"  # Wildcard for all permissions
        ],
        is_system_role=True
    ),
    
    "service": RoleDefinition(
        name="service",
        description="Service account for automated integrations",
        permissions=[
            "task:manage",
            "artifact:work",
            "system:monitor",
            "webhook:send",
            "webhook:receive"
        ],
        is_system_role=True
    ),
    
    "readonly": RoleDefinition(
        name="readonly",
        description="Read-only access for monitoring and reporting",
        permissions=[
            "task:view",
            "agent:view", 
            "artifact:view",
            "system:monitor",
            "communication:view"
        ],
        is_system_role=True
    ),
    
    "webhook": RoleDefinition(
        name="webhook",
        description="Webhook integration with limited task creation",
        permissions=[
            "task:create",
            "event:create",
            "webhook:receive"
        ],
        is_system_role=True
    )
}