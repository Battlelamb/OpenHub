"""
Authentication and authorization system for OpenHub
"""
from .jwt_auth import (
    JWTManager, create_access_token, verify_token,
    create_agent_tokens, hash_password, verify_password
)
from .dependencies import get_current_agent, get_current_admin, require_permissions
from .models import TokenData, AgentLogin, TokenResponse
# permissions module does not exist - PermissionChecker lives in dependencies.py
# from .permissions import Permission, Role, PermissionChecker

__all__ = [
    "JWTManager",
    "create_access_token",
    "verify_token",
    "get_current_agent",
    "get_current_admin",
    "require_permissions",
    "TokenData",
    "AgentLogin",
    "TokenResponse",
]