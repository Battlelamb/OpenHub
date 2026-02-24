"""
FastAPI dependency injection for Agent Hub
"""
from fastapi import HTTPException, Header, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional, Annotated
import time
import uuid

from .config import get_settings
from .logging import get_logger

logger = get_logger(__name__)
security = HTTPBearer(auto_error=False)


async def get_request_id(request: Request) -> str:
    """Generate or extract request ID for tracing"""
    request_id = request.headers.get("x-request-id")
    if not request_id:
        request_id = str(uuid.uuid4())
    return request_id


async def get_api_key(
    x_agenthub_key: Annotated[Optional[str], Header()] = None,
    authorization: Optional[HTTPAuthorizationCredentials] = security
) -> Optional[str]:
    """Extract API key from headers"""
    # Try custom header first
    if x_agenthub_key:
        return x_agenthub_key
    
    # Try authorization header
    if authorization:
        return authorization.credentials
    
    return None


async def verify_api_key(api_key: Optional[str] = get_api_key) -> str:
    """Verify API key and return agent role"""
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # TODO: Implement actual API key validation against database
    # For now, accept any non-empty key
    if len(api_key) < 8:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key format",
        )
    
    # TODO: Return actual role from database lookup
    return "agent"  # Default role for now


async def require_admin_role(role: str = verify_api_key) -> None:
    """Require admin role for endpoint access"""
    if role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )


async def require_agent_role(role: str = verify_api_key) -> None:
    """Require agent role for endpoint access"""
    if role not in ["agent", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Agent privileges required"
        )


class RequestTimer:
    """Context manager for timing requests"""
    
    def __init__(self, request_id: str):
        self.request_id = request_id
        self.start_time = 0.0
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = (time.time() - self.start_time) * 1000  # Convert to milliseconds
        logger.info(
            "request_completed",
            request_id=self.request_id,
            duration_ms=round(duration, 2),
            success=exc_type is None
        )


async def get_settings_dependency():
    """Dependency to inject settings"""
    return get_settings()


# Common dependency aliases
ApiKeyDep = Annotated[str, verify_api_key]
RequestIdDep = Annotated[str, get_request_id]
AdminRoleDep = Annotated[None, require_admin_role]
AgentRoleDep = Annotated[None, require_agent_role]