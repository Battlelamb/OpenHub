"""
FastAPI dependencies for authentication and authorization
"""
import jwt
from datetime import datetime
from typing import Optional, Annotated, List
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from ..config import get_settings
from ..logging import get_logger
from ..database.connection import get_database
from .jwt_auth import verify_token
from .models import TokenData, AuthenticatedAgent

logger = get_logger(__name__)
settings = get_settings()

# HTTP Bearer token security scheme
security = HTTPBearer(auto_error=False)


async def get_token_from_header(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> str:
    """Extract JWT token from Authorization header"""
    
    if not credentials:
        logger.warning("missing_authorization_header", 
                      path=request.url.path,
                      client_ip=request.client.host if request.client else None)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if credentials.scheme.lower() != "bearer":
        logger.warning("invalid_authorization_scheme", 
                      scheme=credentials.scheme,
                      path=request.url.path)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization scheme. Expected Bearer",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return credentials.credentials


async def verify_jwt_token(token: str = Depends(get_token_from_header)) -> TokenData:
    """Verify JWT token and extract payload"""
    
    try:
        # First verify JWT signature and expiration
        payload = verify_token(token, expected_type="access")
        token_data = TokenData(**payload)
        
        # Check if token is blacklisted in Redis
        try:
            from .redis_cache import get_redis_cache
            redis_cache = await get_redis_cache()
            
            if await redis_cache.is_token_blacklisted(token):
                logger.warning("blacklisted_token_used", 
                              agent_id=token_data.sub,
                              token_preview=token[:20] + "...")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token has been revoked",
                    headers={"WWW-Authenticate": "Bearer"},
                )
        
        except ImportError:
            # Redis not available, skip blacklist check
            logger.debug("redis_not_available_skipping_blacklist_check")
        except Exception as e:
            # Redis error, log but don't fail authentication
            logger.warning("blacklist_check_failed", error=str(e))
        
        logger.debug("token_verified", 
                    agent_id=token_data.sub,
                    agent_name=token_data.agent_name)
        
        return token_data
    
    except jwt.ExpiredSignatureError:
        logger.warning("expired_token_used", token_preview=token[:20] + "...")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    except jwt.InvalidTokenError as e:
        logger.warning("invalid_token_used", 
                      error=str(e),
                      token_preview=token[:20] + "...")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    except Exception as e:
        logger.error("token_verification_error", 
                    error=str(e),
                    token_preview=token[:20] + "...")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token verification failed"
        )


async def get_current_agent(
    token_data: TokenData = Depends(verify_jwt_token),
    request: Request = None
) -> AuthenticatedAgent:
    """Get current authenticated agent from database"""
    
    database = get_database()
    
    try:
        # Get agent from database
        agent_row = database.fetch_one(
            "SELECT * FROM agents WHERE id = :agent_id",
            {"agent_id": token_data.sub}
        )
        
        if not agent_row:
            logger.warning("agent_not_found_in_database", 
                          agent_id=token_data.sub,
                          agent_name=token_data.agent_name)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Agent not found or deactivated"
            )
        
        agent_dict = dict(agent_row)
        
        # Check if agent is active
        if agent_dict.get("status") in ["offline", "error"]:
            logger.warning("inactive_agent_access_attempt", 
                          agent_id=token_data.sub,
                          status=agent_dict.get("status"))
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Agent is not active"
            )
        
        # Update last heartbeat
        database.execute(
            "UPDATE agents SET last_heartbeat = CURRENT_TIMESTAMP WHERE id = :agent_id",
            {"agent_id": token_data.sub}
        )
        
        # Create authenticated agent object
        authenticated_agent = AuthenticatedAgent(
            agent_id=agent_dict["id"],
            agent_name=agent_dict["agent_name"],
            role=token_data.role or "agent",
            permissions=token_data.permissions,
            is_active=agent_dict.get("status") in ["online", "idle", "busy"],
            last_seen=datetime.utcnow()
        )
        
        logger.debug("agent_authenticated", 
                    agent_id=authenticated_agent.agent_id,
                    agent_name=authenticated_agent.agent_name)
        
        return authenticated_agent
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("agent_authentication_error", 
                    agent_id=token_data.sub,
                    error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication failed"
        )


async def get_current_admin(
    current_agent: AuthenticatedAgent = Depends(get_current_agent)
) -> AuthenticatedAgent:
    """Ensure current user has admin role"""
    
    if current_agent.role != "admin":
        logger.warning("non_admin_access_attempt", 
                      agent_id=current_agent.agent_id,
                      role=current_agent.role)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    return current_agent


def require_permissions(*required_permissions: str):
    """Dependency factory for permission-based access control"""
    
    async def permission_checker(
        current_agent: AuthenticatedAgent = Depends(get_current_agent)
    ) -> AuthenticatedAgent:
        """Check if agent has required permissions"""
        
        # Admin role has all permissions
        if current_agent.role == "admin" or "*" in current_agent.permissions:
            return current_agent
        
        # Check specific permissions
        missing_permissions = []
        for permission in required_permissions:
            if permission not in current_agent.permissions:
                missing_permissions.append(permission)
        
        if missing_permissions:
            logger.warning("insufficient_permissions", 
                          agent_id=current_agent.agent_id,
                          required=list(required_permissions),
                          missing=missing_permissions,
                          has=current_agent.permissions)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required: {', '.join(required_permissions)}"
            )
        
        logger.debug("permission_check_passed", 
                    agent_id=current_agent.agent_id,
                    permissions=list(required_permissions))
        
        return current_agent
    
    return permission_checker


def require_role(required_role: str):
    """Dependency factory for role-based access control"""
    
    async def role_checker(
        current_agent: AuthenticatedAgent = Depends(get_current_agent)
    ) -> AuthenticatedAgent:
        """Check if agent has required role"""
        
        if current_agent.role != required_role:
            logger.warning("insufficient_role", 
                          agent_id=current_agent.agent_id,
                          required_role=required_role,
                          actual_role=current_agent.role)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{required_role}' required"
            )
        
        return current_agent
    
    return role_checker


async def get_optional_current_agent(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[AuthenticatedAgent]:
    """Get current agent if token provided, otherwise None (for optional auth)"""
    
    if not credentials:
        return None
    
    try:
        token_data = await verify_jwt_token(credentials.credentials)
        return await get_current_agent(token_data, request)
    except HTTPException:
        # Invalid token provided - return None instead of raising
        return None
    except Exception:
        return None


# Type aliases for dependency injection
CurrentAgent = Annotated[AuthenticatedAgent, Depends(get_current_agent)]
CurrentAdmin = Annotated[AuthenticatedAgent, Depends(get_current_admin)]
OptionalAgent = Annotated[Optional[AuthenticatedAgent], Depends(get_optional_current_agent)]


# Common permission combinations
RequireTaskAccess = Depends(require_permissions("tasks:read", "tasks:claim"))
RequireTaskManagement = Depends(require_permissions("tasks:create", "tasks:cancel", "tasks:reassign"))
RequireAgentManagement = Depends(require_permissions("agents:register", "agents:deactivate"))
RequireSystemAccess = Depends(require_permissions("system:monitor", "system:configure"))


class PermissionChecker:
    """Utility class for checking permissions in business logic"""
    
    @staticmethod
    def has_permission(agent: AuthenticatedAgent, permission: str) -> bool:
        """Check if agent has specific permission"""
        return (
            agent.role == "admin" or 
            "*" in agent.permissions or 
            permission in agent.permissions
        )
    
    @staticmethod
    def has_any_permission(agent: AuthenticatedAgent, permissions: List[str]) -> bool:
        """Check if agent has any of the specified permissions"""
        return any(
            PermissionChecker.has_permission(agent, perm) 
            for perm in permissions
        )
    
    @staticmethod
    def has_all_permissions(agent: AuthenticatedAgent, permissions: List[str]) -> bool:
        """Check if agent has all specified permissions"""
        return all(
            PermissionChecker.has_permission(agent, perm) 
            for perm in permissions
        )
    
    @staticmethod
    def require_permission_or_raise(agent: AuthenticatedAgent, permission: str) -> None:
        """Raise HTTPException if agent doesn't have permission"""
        if not PermissionChecker.has_permission(agent, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission '{permission}' required"
            )