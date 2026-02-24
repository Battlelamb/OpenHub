"""
Authentication and authorization endpoints
"""
from datetime import datetime, timedelta
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm

from ..config import get_settings
from ..logging import get_logger
from ..database.connection import get_database
from ..auth import (
    create_agent_tokens, 
    verify_token,
    hash_password,
    verify_password
)
from ..auth.models import (
    AgentLogin, 
    AdminLogin, 
    TokenResponse, 
    TokenRefresh,
    AuthenticatedAgent
)
from ..auth.dependencies import (
    get_current_agent, 
    get_current_admin,
    CurrentAgent,
    CurrentAdmin
)
from ..models.agents import AgentCreate

logger = get_logger(__name__)
settings = get_settings()

router = APIRouter(prefix="/v1/auth", tags=["authentication"])


@router.post("/agent/register", response_model=TokenResponse)
async def register_agent(
    agent_data: AgentCreate,
    request: Request
) -> TokenResponse:
    """
    Register a new agent and return authentication tokens
    
    This endpoint allows new agents to register themselves in the system.
    Returns JWT tokens for immediate authentication.
    """
    database = get_database()
    
    logger.info("agent_registration_attempt", 
               agent_name=agent_data.agent_name,
               capabilities=agent_data.capabilities,
               client_ip=request.client.host if request.client else None)
    
    try:
        # Check if agent name already exists
        existing_agent = database.fetch_one(
            "SELECT id FROM agents WHERE agent_name = :agent_name",
            {"agent_name": agent_data.agent_name}
        )
        
        if existing_agent:
            logger.warning("agent_registration_duplicate", 
                          agent_name=agent_data.agent_name)
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Agent name already exists"
            )
        
        # Create new agent in database
        from uuid import uuid4
        agent_id = str(uuid4())
        
        database.execute("""
            INSERT INTO agents (
                id, agent_name, description, capabilities, status, 
                labels, created_at, updated_at, last_heartbeat
            ) VALUES (
                :id, :agent_name, :description, :capabilities, :status,
                :labels, :created_at, :updated_at, :last_heartbeat
            )
        """, {
            "id": agent_id,
            "agent_name": agent_data.agent_name,
            "description": agent_data.description,
            "capabilities": str(agent_data.capabilities),  # JSON string
            "status": "online",
            "labels": str(agent_data.labels) if agent_data.labels else "{}",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "last_heartbeat": datetime.utcnow()
        })
        
        # Create authentication tokens
        tokens = create_agent_tokens(
            agent_id=agent_id,
            agent_name=agent_data.agent_name,
            role="agent"
        )
        
        logger.info("agent_registered_successfully", 
                   agent_id=agent_id,
                   agent_name=agent_data.agent_name)
        
        return TokenResponse(
            access_token=tokens["access_token"],
            refresh_token=tokens["refresh_token"],
            token_type=tokens["token_type"],
            expires_in=settings.jwt_access_token_expire_minutes * 60,
            agent_id=agent_id,
            role="agent",
            permissions=[
                "tasks:claim", "tasks:update_progress", "tasks:complete",
                "artifacts:upload", "artifacts:download_own",
                "events:create", "events:read_own",
                "communication:send_message", "communication:join_thread"
            ]
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("agent_registration_failed", 
                    agent_name=agent_data.agent_name,
                    error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Agent registration failed"
        )


@router.post("/agent/login", response_model=TokenResponse)
async def agent_login(
    login_data: AgentLogin,
    request: Request
) -> TokenResponse:
    """
    Authenticate existing agent and return tokens
    
    Agents can login using their agent_name. API key validation
    will be implemented in Phase 1.4.3.
    """
    database = get_database()
    
    logger.info("agent_login_attempt", 
               agent_name=login_data.agent_name,
               client_ip=request.client.host if request.client else None)
    
    try:
        # Get agent from database
        agent_row = database.fetch_one(
            "SELECT * FROM agents WHERE agent_name = :agent_name",
            {"agent_name": login_data.agent_name}
        )
        
        if not agent_row:
            logger.warning("agent_login_not_found", 
                          agent_name=login_data.agent_name)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid agent credentials"
            )
        
        agent = dict(agent_row)
        
        # Check if agent is not deactivated
        if agent["status"] == "error":
            logger.warning("deactivated_agent_login_attempt", 
                          agent_id=agent["id"],
                          agent_name=login_data.agent_name)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Agent account is deactivated"
            )
        
        # Update agent status and last heartbeat
        database.execute(
            """
            UPDATE agents 
            SET status = 'online', last_heartbeat = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = :agent_id
            """,
            {"agent_id": agent["id"]}
        )
        
        # Create authentication tokens
        tokens = create_agent_tokens(
            agent_id=agent["id"],
            agent_name=agent["agent_name"],
            role="agent"
        )
        
        logger.info("agent_login_successful", 
                   agent_id=agent["id"],
                   agent_name=agent["agent_name"])
        
        return TokenResponse(
            access_token=tokens["access_token"],
            refresh_token=tokens["refresh_token"],
            token_type=tokens["token_type"],
            expires_in=settings.jwt_access_token_expire_minutes * 60,
            agent_id=agent["id"],
            role="agent",
            permissions=[
                "tasks:claim", "tasks:update_progress", "tasks:complete",
                "artifacts:upload", "artifacts:download_own",
                "events:create", "events:read_own",
                "communication:send_message", "communication:join_thread"
            ]
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("agent_login_failed", 
                    agent_name=login_data.agent_name,
                    error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Agent login failed"
        )


@router.post("/admin/login", response_model=TokenResponse)
async def admin_login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    request: Request = None
) -> TokenResponse:
    """
    Admin login using username/password
    
    For demo purposes, this creates a default admin account.
    In production, admins should be pre-configured.
    """
    database = get_database()
    
    logger.info("admin_login_attempt", 
               username=form_data.username,
               client_ip=request.client.host if request.client else None)
    
    # For now, use a hardcoded admin account
    # TODO: Implement proper admin user management
    if form_data.username != "admin" or form_data.password != "admin123":
        logger.warning("admin_login_invalid_credentials", 
                      username=form_data.username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin credentials"
        )
    
    # Create admin tokens
    from uuid import uuid4
    admin_id = "admin-" + str(uuid4())
    
    tokens = create_agent_tokens(
        agent_id=admin_id,
        agent_name=form_data.username,
        role="admin"
    )
    
    logger.info("admin_login_successful", 
               admin_id=admin_id,
               username=form_data.username)
    
    return TokenResponse(
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
        token_type=tokens["token_type"],
        expires_in=settings.jwt_access_token_expire_minutes * 60,
        agent_id=admin_id,
        role="admin",
        permissions=["*"]  # Admin has all permissions
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_access_token(
    refresh_data: TokenRefresh,
    request: Request
) -> TokenResponse:
    """
    Refresh access token using refresh token
    """
    logger.info("token_refresh_attempt", 
               client_ip=request.client.host if request.client else None)
    
    try:
        # Verify refresh token
        payload = verify_token(refresh_data.refresh_token, expected_type="refresh")
        agent_id = payload["sub"]
        
        # Get agent information
        database = get_database()
        agent_row = database.fetch_one(
            "SELECT agent_name FROM agents WHERE id = :agent_id",
            {"agent_id": agent_id}
        )
        
        if not agent_row:
            logger.warning("token_refresh_agent_not_found", agent_id=agent_id)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Agent not found"
            )
        
        agent = dict(agent_row)
        
        # Determine role (admin tokens have different agent_id pattern)
        role = "admin" if agent_id.startswith("admin-") else "agent"
        
        # Create new tokens
        tokens = create_agent_tokens(
            agent_id=agent_id,
            agent_name=agent["agent_name"],
            role=role
        )
        
        logger.info("token_refresh_successful", agent_id=agent_id)
        
        return TokenResponse(
            access_token=tokens["access_token"],
            refresh_token=tokens["refresh_token"],
            token_type=tokens["token_type"],
            expires_in=settings.jwt_access_token_expire_minutes * 60,
            agent_id=agent_id,
            role=role,
            permissions=["*"] if role == "admin" else [
                "tasks:claim", "tasks:update_progress", "tasks:complete",
                "artifacts:upload", "artifacts:download_own",
                "events:create", "events:read_own",
                "communication:send_message", "communication:join_thread"
            ]
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("token_refresh_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token refresh failed"
        )


@router.post("/logout")
async def logout(
    current_agent: CurrentAgent,
    request: Request
) -> Dict[str, str]:
    """
    Logout current agent (blacklist token and update status)
    """
    logger.info("agent_logout", 
               agent_id=current_agent.agent_id,
               agent_name=current_agent.agent_name)
    
    try:
        # Get token from request
        from ..auth.dependencies import get_token_from_header
        token = await get_token_from_header(request)
        
        # Blacklist token in Redis
        try:
            from ..auth.redis_cache import get_redis_cache
            redis_cache = await get_redis_cache()
            await redis_cache.blacklist_token(
                token=token,
                reason="logout",
                blacklisted_by=current_agent.agent_id
            )
            logger.info("token_blacklisted_on_logout", agent_id=current_agent.agent_id)
        
        except Exception as e:
            logger.warning("token_blacklist_failed_on_logout", 
                          agent_id=current_agent.agent_id,
                          error=str(e))
        
        # Update agent status to offline
        database = get_database()
        database.execute(
            "UPDATE agents SET status = 'offline', updated_at = CURRENT_TIMESTAMP WHERE id = :agent_id",
            {"agent_id": current_agent.agent_id}
        )
        
        return {"message": "Logout successful"}
    
    except Exception as e:
        logger.error("logout_failed", 
                    agent_id=current_agent.agent_id,
                    error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout failed"
        )


@router.get("/me", response_model=AuthenticatedAgent)
async def get_current_user_info(current_agent: CurrentAgent) -> AuthenticatedAgent:
    """
    Get current authenticated agent information
    """
    logger.debug("user_info_requested", agent_id=current_agent.agent_id)
    return current_agent


@router.get("/verify")
async def verify_token_endpoint(current_agent: CurrentAgent) -> Dict[str, Any]:
    """
    Verify token validity (useful for other services)
    """
    return {
        "valid": True,
        "agent_id": current_agent.agent_id,
        "agent_name": current_agent.agent_name,
        "role": current_agent.role,
        "permissions": current_agent.permissions
    }