"""
Authentication models for OpenHub
"""
from datetime import datetime
from typing import Optional, List
from pydantic import Field, field_validator

from ..models.base import BaseModel


class TokenData(BaseModel):
    """Token payload data"""
    
    sub: str = Field(description="Subject (agent_id)")
    exp: datetime = Field(description="Expiration time")
    iat: datetime = Field(description="Issued at time") 
    type: str = Field(description="Token type (access/refresh)")
    agent_name: Optional[str] = Field(default=None, description="Agent name")
    role: Optional[str] = Field(default=None, description="Agent role")
    permissions: List[str] = Field(default_factory=list, description="Agent permissions")


class AgentLogin(BaseModel):
    """Agent login request"""
    
    agent_name: str = Field(
        description="Agent name",
        min_length=1,
        max_length=100
    )
    
    api_key: Optional[str] = Field(
        default=None,
        description="API key for authentication"
    )
    
    capabilities: List[str] = Field(
        default_factory=list,
        description="Agent capabilities",
        max_items=50
    )
    
    @field_validator('agent_name')
    @classmethod
    def validate_agent_name(cls, v):
        """Validate agent name format"""
        if not v or not v.strip():
            raise ValueError("Agent name cannot be empty")
        
        # Allow alphanumeric, hyphens, underscores
        allowed_chars = set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-')
        if not all(c in allowed_chars for c in v):
            raise ValueError("Agent name contains invalid characters")
        
        return v.strip()


class AdminLogin(BaseModel):
    """Admin login request"""
    
    username: str = Field(
        description="Admin username",
        min_length=1,
        max_length=50
    )
    
    password: str = Field(
        description="Admin password",
        min_length=1,
        max_length=100
    )


class TokenResponse(BaseModel):
    """Token response for successful authentication"""
    
    access_token: str = Field(description="JWT access token")
    refresh_token: str = Field(description="JWT refresh token") 
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(description="Token expiration in seconds")
    agent_id: Optional[str] = Field(default=None, description="Agent ID")
    role: str = Field(description="User role")
    permissions: List[str] = Field(description="User permissions")


class TokenRefresh(BaseModel):
    """Token refresh request"""
    
    refresh_token: str = Field(description="Refresh token")


class TokenBlacklist(BaseModel):
    """Token blacklist entry"""
    
    token_id: str = Field(description="Token JTI (unique identifier)")
    agent_id: str = Field(description="Agent that owns the token")
    token_type: str = Field(description="Token type (access/refresh)")
    blacklisted_at: datetime = Field(description="When token was blacklisted")
    reason: Optional[str] = Field(default=None, description="Blacklist reason")


class APIKeyCreate(BaseModel):
    """API key creation request"""
    
    name: str = Field(
        description="API key name",
        min_length=1,
        max_length=100
    )
    
    description: Optional[str] = Field(
        default=None,
        max_length=500,
        description="API key description"
    )
    
    scopes: List[str] = Field(
        default_factory=list,
        description="API key scopes/permissions"
    )
    
    expires_at: Optional[datetime] = Field(
        default=None,
        description="API key expiration"
    )


class APIKeyResponse(BaseModel):
    """API key creation response"""
    
    key_id: str = Field(description="API key ID")
    api_key: str = Field(description="Generated API key (only shown once)")
    name: str = Field(description="API key name")
    scopes: List[str] = Field(description="API key scopes")
    created_at: datetime = Field(description="Creation timestamp")
    expires_at: Optional[datetime] = Field(description="Expiration timestamp")


class PermissionCheck(BaseModel):
    """Permission check request"""
    
    resource: str = Field(description="Resource name (e.g., 'tasks', 'agents')")
    action: str = Field(description="Action name (e.g., 'create', 'read', 'update')")
    context: Optional[dict] = Field(default=None, description="Additional context")


class AuthenticatedAgent(BaseModel):
    """Authenticated agent information"""
    
    agent_id: str = Field(description="Agent ID")
    agent_name: str = Field(description="Agent name")
    role: str = Field(description="Agent role")
    permissions: List[str] = Field(description="Agent permissions")
    is_active: bool = Field(description="Whether agent is active")
    last_seen: Optional[datetime] = Field(description="Last activity timestamp")


class SessionInfo(BaseModel):
    """Session information"""
    
    session_id: str = Field(description="Session ID")
    agent_id: str = Field(description="Associated agent ID")
    created_at: datetime = Field(description="Session creation time")
    last_activity: datetime = Field(description="Last activity time")
    ip_address: Optional[str] = Field(description="Client IP address")
    user_agent: Optional[str] = Field(description="Client user agent")
    is_active: bool = Field(description="Whether session is active")