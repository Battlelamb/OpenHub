"""
ACN (Agent Collaboration Network) endpoints - Secure onboarding flow

Flow:
1. Admin creates invite key:     POST /v1/acn/admin/invite
2. New agent joins with invite:  POST /v1/acn/join
3. Agent gets permanent API key (oh_...) in response
4. All subsequent requests use:  X-API-Key: oh_...
"""
import secrets
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request, Header

from ..config import get_settings
from ..logging import get_logger
from ..database.connection import get_database, Database
from ..services.remote_agent_service import RemoteAgentService
from ..services.task_service import TaskService
from ..models.acn import ACNNode, ACNNodeCreate, RemoteAgentRegister
from ..models.agents import Agent
from ..models.tasks import TaskCreate, TaskType, TaskPriority, TaskStatus, TaskClaim, TaskComplete, TaskFail
from ..auth.api_keys import APIKeyManager, APIKeyType, APIKeyScope
from ..auth.dependencies import CurrentAdmin

logger = get_logger(__name__)
settings = get_settings()

router = APIRouter(prefix="/v1/acn", tags=["acn"])

# In-memory invite store (short-lived, single-use)
# Format: {invite_code: {created_at, created_by, expires_at, used: bool}}
_invite_store: Dict[str, Dict[str, Any]] = {}

# Master admin key - set via env AGENTHUB_ACN_ADMIN_KEY
# If not set, first request to /admin/invite creates it
_admin_key: Optional[str] = None


def _create_invite_record() -> str:
    """Create a single-use invite code and store it in memory."""
    invite_code = f"inv_{secrets.token_hex(16)}"
    _invite_store[invite_code] = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "expires_at": (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat(),
        "used": False,
    }
    return invite_code


def _invite_response(invite_code: str) -> Dict[str, str]:
    return {
        "invite_code": invite_code,
        "expires_in": "24 hours",
        "usage": "POST /v1/acn/join with this invite_code to register your agent"
    }


def get_remote_agent_service() -> RemoteAgentService:
    database = get_database()
    return RemoteAgentService(database)


def get_api_key_manager() -> APIKeyManager:
    database = get_database()
    return APIKeyManager(database)


def get_task_service() -> TaskService:
    database = get_database()
    return TaskService(database)


def _get_admin_key() -> str:
    """Get or generate the admin key"""
    global _admin_key
    if _admin_key is None:
        _admin_key = settings.acn_admin_key if hasattr(settings, 'acn_admin_key') and settings.acn_admin_key else None
    return _admin_key


def _require_admin_key(x_admin_key: str = Header(..., alias="X-Admin-Key")):
    """Require admin key for admin endpoints"""
    admin_key = _get_admin_key()
    if admin_key is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Admin key not configured. Set AGENTHUB_ACN_ADMIN_KEY env var."
        )
    if not secrets.compare_digest(x_admin_key, admin_key):
        logger.warning("acn_admin_auth_failed")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin key"
        )
    return True


def _require_api_key(
    x_api_key: str = Header(None, alias="X-API-Key"),
    database: Database = Depends(get_database),
) -> Dict[str, Any]:
    """Require valid API key for agent endpoints"""
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="X-API-Key header required"
        )
    manager = APIKeyManager(database)
    key_info = manager.validate_api_key(x_api_key)
    if not key_info:
        logger.warning("acn_api_key_invalid")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired API key"
        )
    return key_info


def _require_scope(required_scope: str):
    """Factory: require specific scope on API key"""
    def checker(
        x_api_key: str = Header(None, alias="X-API-Key"),
        database: Database = Depends(get_database),
    ) -> Dict[str, Any]:
        if not x_api_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="X-API-Key header required"
            )
        manager = APIKeyManager(database)
        key_info = manager.validate_api_key(x_api_key, required_scope=required_scope)
        if not key_info:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"API key missing required scope: {required_scope}"
            )
        return key_info
    return checker


# ========== ADMIN ENDPOINTS ==========

@router.post("/admin/setup")
async def setup_admin(request: Request) -> Dict[str, str]:
    """
    One-time setup: generates admin key.
    Only works if no admin key is set yet.
    Must be called from localhost.
    """
    global _admin_key

    # Only allow from localhost
    client_ip = request.client.host if request.client else "unknown"
    if client_ip not in ("127.0.0.1", "::1", "localhost"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Setup only allowed from localhost"
        )

    if _admin_key is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Admin key already configured"
        )

    _admin_key = f"ak_{secrets.token_hex(24)}"

    logger.info("acn_admin_key_generated", client_ip=client_ip)

    return {
        "admin_key": _admin_key,
        "message": "Save this key securely. It won't be shown again. Use it in X-Admin-Key header."
    }


@router.post("/admin/invite")
async def create_invite(
    request: Request,
    _: bool = Depends(_require_admin_key),
) -> Dict[str, str]:
    """
    Create a single-use invite code for a new agent.
    Requires X-Admin-Key header.
    Invite expires in 24 hours.
    """
    invite_code = _create_invite_record()

    logger.info("acn_invite_created",
               invite_prefix=invite_code[:8],
               client_ip=request.client.host if request.client else None)

    return _invite_response(invite_code)


@router.post("/dashboard/invite")
async def create_dashboard_invite(
    request: Request,
    current_admin: CurrentAdmin,
) -> Dict[str, str]:
    """
    Create a single-use invite code for dashboard admins.

    Uses the dashboard JWT session instead of exposing the ACN admin key to the
    browser. Invite expires in 24 hours.
    """
    invite_code = _create_invite_record()

    logger.info("acn_dashboard_invite_created",
               invite_prefix=invite_code[:8],
               admin_id=current_admin.agent_id,
               client_ip=request.client.host if request.client else None)

    return _invite_response(invite_code)


@router.get("/admin/invites")
async def list_invites(
    _: bool = Depends(_require_admin_key),
) -> Dict[str, Any]:
    """List all invite codes and their status"""
    invites = []
    for code, info in _invite_store.items():
        invites.append({
            "invite_prefix": code[:12] + "...",
            "created_at": info["created_at"],
            "expires_at": info["expires_at"],
            "used": info["used"],
        })
    return {"invites": invites, "total": len(invites)}


# ========== JOIN (Public with invite) ==========

@router.post("/join")
async def join_acn(
    agent_data: RemoteAgentRegister,
    invite_code: str = Header(..., alias="X-Invite-Code"),
    request: Request = None,
    service: RemoteAgentService = Depends(get_remote_agent_service),
    key_manager: APIKeyManager = Depends(get_api_key_manager),
) -> Dict[str, Any]:
    """
    Join the ACN with an invite code.
    Returns a permanent API key for all future requests.

    Headers:
        X-Invite-Code: inv_... (from admin)

    Body:
        agent_name, capabilities, node_name, description
    """
    # Validate invite
    invite = _invite_store.get(invite_code)
    if not invite:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid invite code"
        )
    if invite["used"]:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Invite code already used"
        )
    if datetime.fromisoformat(invite["expires_at"]) < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Invite code expired"
        )

    # Mark invite as used
    invite["used"] = True

    # Ensure node exists (auto-create if needed)
    try:
        node = service.node_repo.find_by_name(agent_data.node_name)
        if not node:
            service.register_node(ACNNodeCreate(
                node_name=agent_data.node_name,
                node_url=agent_data.callback_url or "http://localhost",
            ))
    except ValueError:
        pass  # Node already exists

    # Register the agent (with client IP)
    client_ip = request.client.host if request.client else None
    try:
        new_agent = service.register_remote_agent(agent_data, client_ip=client_ip)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))

    # Create permanent API key for this agent
    try:
        api_key_result = key_manager.create_api_key(
            name=f"acn-agent-{agent_data.agent_name}",
            key_type=APIKeyType.AGENT,
            scopes=[
                APIKeyScope.ACN_NODE_MANAGE.value,
                APIKeyScope.ACN_AGENT_REGISTER.value,
                APIKeyScope.ACN_AGENT_READ.value,
                APIKeyScope.ACN_TASK_SUBMIT.value,
                APIKeyScope.AGENT_HEARTBEAT.value,
                APIKeyScope.TASK_READ.value,
                APIKeyScope.TASK_UPDATE.value,
            ],
            description=f"ACN agent key for {agent_data.agent_name}",
            created_by="acn-join",
            metadata={
                "agent_id": new_agent.id,
                "agent_name": new_agent.agent_name,
                "node_id": service.node_repo.find_by_name(agent_data.node_name).id if service.node_repo.find_by_name(agent_data.node_name) else None,
                "node_name": agent_data.node_name,
                "allowed_capabilities": agent_data.capabilities or [],
                "mcp_profiles": agent_data.mcp_servers or [],
            },
        )
    except Exception as e:
        logger.error("acn_join_key_creation_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Agent registered but API key creation failed"
        )

    logger.info("acn_agent_joined",
               agent_id=new_agent.id,
               agent_name=new_agent.agent_name,
               client_ip=request.client.host if request.client else None)

    return {
        "agent_id": new_agent.id,
        "agent_name": new_agent.agent_name,
        "api_key": api_key_result["api_key"],
        "key_id": api_key_result["key_id"],
        "scopes": api_key_result["scopes"],
        "expires_at": api_key_result["expires_at"],
        "message": "Save your API key securely. Use it in X-API-Key header for all requests."
    }


# ========== AUTHENTICATED ENDPOINTS ==========

@router.post("/nodes", response_model=ACNNode)
async def register_node(
    node_data: ACNNodeCreate,
    request: Request,
    key_info: Dict = Depends(_require_scope(APIKeyScope.ACN_NODE_MANAGE.value)),
    service: RemoteAgentService = Depends(get_remote_agent_service),
) -> ACNNode:
    """Register a new ACN node. Requires API key with acn:node_manage scope."""
    try:
        return service.register_node(node_data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.get("/nodes", response_model=List[ACNNode])
async def list_nodes(
    key_info: Dict = Depends(_require_scope(APIKeyScope.ACN_AGENT_READ.value)),
    service: RemoteAgentService = Depends(get_remote_agent_service),
) -> List[ACNNode]:
    """List all ACN nodes. Requires API key."""
    return service.get_all_nodes()


@router.post("/nodes/{node_id}/heartbeat")
async def node_heartbeat(
    node_id: str,
    key_info: Dict = Depends(_require_scope(APIKeyScope.ACN_NODE_MANAGE.value)),
    service: RemoteAgentService = Depends(get_remote_agent_service),
) -> Dict[str, str]:
    """Send heartbeat for an ACN node. Requires API key."""
    node = service.get_node(node_id)
    if not node:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Node '{node_id}' not found")
    heartbeat_agent_id = (key_info.get("metadata") or {}).get("agent_id")
    service.heartbeat_node(node_id, agent_id=heartbeat_agent_id)
    _audit_acn_event("acn_node_heartbeat", node_id=node_id, agent_id=heartbeat_agent_id, key_id=key_info.get("key_id"))
    return {"status": "heartbeat_received", "node_id": node_id}


@router.post("/agents/register", response_model=Agent)
async def register_remote_agent(
    agent_data: RemoteAgentRegister,
    request: Request,
    key_info: Dict = Depends(_require_scope(APIKeyScope.ACN_AGENT_REGISTER.value)),
    service: RemoteAgentService = Depends(get_remote_agent_service),
) -> Agent:
    """Register a remote agent. Requires API key with acn:agent_register scope."""
    try:
        return service.register_remote_agent(agent_data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.get("/agents")
async def list_remote_agents(
    key_info: Dict = Depends(_require_scope(APIKeyScope.ACN_AGENT_READ.value)),
    service: RemoteAgentService = Depends(get_remote_agent_service),
) -> Dict[str, Any]:
    """List all remote agents. Requires API key."""
    agents = service.get_remote_agents()
    return {"remote_agents": agents, "total": len(agents)}


# ========== TASK ROUTING (auth required) ==========

from pydantic import BaseModel as PydanticBaseModel


class ACNTaskCreate(PydanticBaseModel):
    """Simple task creation model for ACN"""
    title: str
    description: str
    task_type: str = "feature"
    priority: int = 50
    required_capabilities: List[str] = ["code_edit"]
    payload: Optional[Dict[str, Any]] = None


def _redact_audit_payload(value: Any) -> Any:
    """Recursively redact secret-like fields before structured audit logging."""
    secret_markers = ("key", "token", "secret", "password", "credential", "bearer")
    if isinstance(value, dict):
        redacted = {}
        for key, item in value.items():
            if any(marker in str(key).lower() for marker in secret_markers):
                redacted[key] = "[REDACTED]"
            else:
                redacted[key] = _redact_audit_payload(item)
        return redacted
    if isinstance(value, list):
        return [_redact_audit_payload(item) for item in value]
    return value


def _audit_acn_event(event: str, **payload: Any) -> None:
    """Emit secret-safe ACN audit events via structured logs."""
    logger.info(event, **_redact_audit_payload(payload))


def _authenticated_agent_id(key_info: Dict[str, Any], provided_agent_id: Optional[str] = None) -> str:
    """Resolve task caller identity from API key metadata, with legacy query fallback."""
    metadata = key_info.get("metadata") or {}
    metadata_agent_id = metadata.get("agent_id")
    if metadata_agent_id:
        if provided_agent_id and provided_agent_id != metadata_agent_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="API key does not belong to requested agent")
        return metadata_agent_id
    if provided_agent_id:
        return provided_agent_id
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="API key metadata missing agent_id")


def _serialize_task(t) -> Dict[str, Any]:
    return {
        "task_id": t.id,
        "title": t.title,
        "description": t.description,
        "task_type": t.task_type if isinstance(t.task_type, str) else t.task_type.value,
        "priority": t.priority,
        "status": t.status if isinstance(t.status, str) else t.status.value,
        "assigned_to": t.owner_agent_id,
        "required_capabilities": t.required_capabilities,
        "payload": t.payload or {},
        "result_summary": t.result_summary,
        "output": t.output,
        "last_error": t.last_error,
        "created_at": t.created_at.isoformat() if t.created_at else None,
        "claimed_at": t.claimed_at.isoformat() if t.claimed_at else None,
        "started_at": t.started_at.isoformat() if t.started_at else None,
        "completed_at": t.completed_at.isoformat() if t.completed_at else None,
    }


@router.post("/tasks/create")
@router.post("/tasks")
async def create_task(
    body: ACNTaskCreate,
    key_info: Dict = Depends(_require_api_key),
    task_service: TaskService = Depends(get_task_service),
) -> Dict[str, Any]:
    """
    Create a task and auto-assign to best matching agent.
    Requires any valid API key. Send JSON body.
    """
    try:
        task_data = TaskCreate(
            title=body.title,
            description=body.description,
            task_type=TaskType(body.task_type) if body.task_type in [t.value for t in TaskType] else TaskType.FEATURE,
            priority=body.priority,
            required_capabilities=body.required_capabilities,
            payload=body.payload or {},
            labels={},
            max_retries=3,
        )
        new_task = task_service.create_task(task_data, created_by=key_info.get("name"))
        _audit_acn_event(
            "acn_task_created",
            task_id=new_task.id,
            created_by=key_info.get("name"),
            assigned_to=new_task.owner_agent_id,
            required_capabilities=body.required_capabilities,
        )

        return {
            "task_id": new_task.id,
            "title": new_task.title,
            "status": new_task.status if isinstance(new_task.status, str) else new_task.status.value,
            "assigned_to": new_task.owner_agent_id,
            "message": "Task created" + (f" and assigned to {new_task.owner_agent_id}" if new_task.owner_agent_id else " - waiting in queue"),
        }
    except Exception as e:
        logger.error("acn_task_creation_failed", error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/tasks/{task_id}/claim")
async def claim_task(
    task_id: str,
    agent_id: Optional[str] = None,
    key_info: Dict = Depends(_require_scope(APIKeyScope.ACN_TASK_SUBMIT.value)),
    task_service: TaskService = Depends(get_task_service),
) -> Dict[str, str]:
    """Claim a task for the authenticated agent. Requires API key."""
    resolved_agent_id = _authenticated_agent_id(key_info, agent_id)
    claim = TaskClaim(agent_id=resolved_agent_id)
    success = task_service.claim_task(task_id, claim)
    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to claim task")
    _audit_acn_event("acn_task_claimed", task_id=task_id, agent_id=resolved_agent_id, key_id=key_info.get("key_id"))
    return {"status": "claimed", "task_id": task_id, "agent_id": resolved_agent_id}


@router.post("/tasks/{task_id}/start")
async def start_task(
    task_id: str,
    agent_id: Optional[str] = None,
    key_info: Dict = Depends(_require_scope(APIKeyScope.ACN_TASK_SUBMIT.value)),
    task_service: TaskService = Depends(get_task_service),
) -> Dict[str, str]:
    """Start a claimed task. Requires API key."""
    resolved_agent_id = _authenticated_agent_id(key_info, agent_id)
    success = task_service.start_task(task_id, resolved_agent_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to start task")
    _audit_acn_event("acn_task_started", task_id=task_id, agent_id=resolved_agent_id, key_id=key_info.get("key_id"))
    return {"status": "started", "task_id": task_id, "agent_id": resolved_agent_id}


@router.post("/tasks/{task_id}/complete")
async def complete_task(
    task_id: str,
    agent_id: Optional[str] = None,
    result_summary: Optional[str] = None,
    output: Optional[Dict[str, Any]] = None,
    key_info: Dict = Depends(_require_scope(APIKeyScope.ACN_TASK_SUBMIT.value)),
    task_service: TaskService = Depends(get_task_service),
) -> Dict[str, str]:
    """Complete a task with results. Requires API key."""
    resolved_agent_id = _authenticated_agent_id(key_info, agent_id)
    completion = TaskComplete(
        result_summary=result_summary or "Task completed",
        output=output or {},
    )
    success = task_service.complete_task(task_id, resolved_agent_id, completion)
    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to complete task")
    _audit_acn_event("acn_task_completed", task_id=task_id, agent_id=resolved_agent_id, key_id=key_info.get("key_id"), output=output or {})
    return {"status": "completed", "task_id": task_id, "agent_id": resolved_agent_id}


@router.post("/tasks/{task_id}/fail")
async def fail_task(
    task_id: str,
    agent_id: Optional[str] = None,
    error_message: str = "Task failed",
    retryable: bool = True,
    key_info: Dict = Depends(_require_scope(APIKeyScope.ACN_TASK_SUBMIT.value)),
    task_service: TaskService = Depends(get_task_service),
) -> Dict[str, str]:
    """Report task failure. Requires API key."""
    resolved_agent_id = _authenticated_agent_id(key_info, agent_id)
    failure = TaskFail(error_message=error_message, retryable=retryable)
    success = task_service.fail_task(task_id, resolved_agent_id, failure)
    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to process task failure")
    _audit_acn_event("acn_task_failed", task_id=task_id, agent_id=resolved_agent_id, key_id=key_info.get("key_id"), retryable=retryable)
    return {"status": "failed", "task_id": task_id, "agent_id": resolved_agent_id}


@router.get("/tasks/available")
async def get_available_tasks(
    agent_id: Optional[str] = None,
    limit: int = 10,
    key_info: Dict = Depends(_require_api_key),
    task_service: TaskService = Depends(get_task_service),
) -> Dict[str, Any]:
    """Get tasks available for the authenticated agent based on capabilities."""
    resolved_agent_id = _authenticated_agent_id(key_info, agent_id)
    tasks = task_service.get_available_tasks(resolved_agent_id, limit)
    return {"tasks": [_serialize_task(t) for t in tasks], "total": len(tasks)}


@router.get("/tasks/poll")
async def poll_tasks(
    agent_id: Optional[str] = None,
    limit: int = 5,
    key_info: Dict = Depends(_require_api_key),
    task_service: TaskService = Depends(get_task_service),
) -> Dict[str, Any]:
    """Poll queued and already-owned tasks for the authenticated agent."""
    resolved_agent_id = _authenticated_agent_id(key_info, agent_id)
    available = task_service.get_available_tasks(resolved_agent_id, limit)
    owned = []
    for status_val in ["claimed", "running"]:
        for task in task_service.task_repo.find_by_status(status_val):
            if task.owner_agent_id == resolved_agent_id:
                owned.append(task)
    return {
        "agent_id": resolved_agent_id,
        "available": [_serialize_task(t) for t in available],
        "owned": [_serialize_task(t) for t in owned],
    }


@router.get("/tasks/mine")
async def get_my_tasks(
    agent_id: Optional[str] = None,
    key_info: Dict = Depends(_require_api_key),
    task_service: TaskService = Depends(get_task_service),
) -> Dict[str, Any]:
    """Get tasks assigned to the authenticated agent (claimed/running)."""
    resolved_agent_id = _authenticated_agent_id(key_info, agent_id)
    tasks = []
    for status_val in ["claimed", "running"]:
        found = task_service.task_repo.find_by_status(status_val)
        for t in found:
            if t.owner_agent_id == resolved_agent_id:
                tasks.append(_serialize_task(t))
    return {"agent_id": resolved_agent_id, "tasks": tasks, "total": len(tasks)}


@router.get("/tasks/{task_id}")
async def get_task(
    task_id: str,
    key_info: Dict = Depends(_require_api_key),
    task_service: TaskService = Depends(get_task_service),
) -> Dict[str, Any]:
    """Get task details. Requires API key."""
    task = task_service.get_task(task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return {
        "task_id": task.id,
        "title": task.title,
        "description": task.description,
        "task_type": task.task_type if isinstance(task.task_type, str) else task.task_type.value,
        "priority": task.priority,
        "status": task.status if isinstance(task.status, str) else task.status.value,
        "assigned_to": task.owner_agent_id,
        "required_capabilities": task.required_capabilities,
        "result_summary": task.result_summary,
        "output": task.output,
        "last_error": task.last_error,
        "created_at": task.created_at.isoformat() if task.created_at else None,
        "completed_at": task.completed_at.isoformat() if task.completed_at else None,
    }


# ========== SELF-SERVICE APPLICATION (no auth required) ==========

@router.post("/apply")
async def apply_to_acn(
    agent_data: RemoteAgentRegister,
    request: Request,
    database: Database = Depends(get_database),
) -> Dict[str, Any]:
    """
    Apply to join the ACN. No auth required.
    Admin will review and approve/reject via dashboard.

    Body: same as /join (agent_name, capabilities, model, platform, skills, etc.)
    """
    import json as _json
    from uuid import uuid4

    client_ip = request.client.host if request.client else None
    app_id = str(uuid4())

    # Check if agent name already taken
    service = RemoteAgentService(database)
    existing = service.agent_repo.find_by_name(agent_data.agent_name)
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Agent name '{agent_data.agent_name}' already registered")

    # Check if pending application exists for this name
    existing_app = database.fetch_one(
        "SELECT id FROM pending_applications WHERE agent_name = :name AND status = 'pending'",
        {"name": agent_data.agent_name}
    )
    if existing_app:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Application for '{agent_data.agent_name}' already pending")

    # Store application
    database.execute(
        """INSERT INTO pending_applications (id, agent_name, data, client_ip, status, source, created_at)
           VALUES (:id, :name, :data, :ip, 'pending', 'acn', :now)""",
        {
            "id": app_id,
            "name": agent_data.agent_name,
            "data": _json.dumps(agent_data.model_dump()),
            "ip": client_ip,
            "now": datetime.now(timezone.utc).isoformat(),
        }
    )

    logger.info("acn_application_received",
               app_id=app_id, agent_name=agent_data.agent_name, client_ip=client_ip)

    return {
        "application_id": app_id,
        "agent_name": agent_data.agent_name,
        "status": "pending",
        "message": "Application received. Waiting for admin approval. Check status at GET /v1/acn/apply/{application_id}/status"
    }


@router.get("/apply/{application_id}/status")
async def check_application_status(
    application_id: str,
    database: Database = Depends(get_database),
) -> Dict[str, Any]:
    """Check application status. No auth required - agent polls this after applying."""
    row = database.fetch_one(
        "SELECT * FROM pending_applications WHERE id = :id",
        {"id": application_id}
    )
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")

    app = dict(row) if isinstance(row, dict) else {k: row[i] for i, k in enumerate(["id", "agent_name", "data", "client_ip", "status", "api_key_value", "reviewed_by", "reviewed_at", "created_at"])}

    result = {
        "application_id": app["id"],
        "agent_name": app["agent_name"],
        "status": app["status"],
        "created_at": app["created_at"],
    }

    if app["status"] == "approved" and app.get("api_key_value"):
        result["api_key"] = app["api_key_value"]
        result["message"] = "Approved! Save this API key - it will only be shown ONCE."
        # Clear api_key_value from DB after delivery (one-time view)
        try:
            database.execute(
                "UPDATE pending_applications SET api_key_value = NULL WHERE id = :id",
                {"id": application_id}
            )
        except Exception:
            pass
    elif app["status"] == "approved":
        result["message"] = "Approved. API key was already delivered."
    elif app["status"] == "rejected":
        result["message"] = "Application rejected."
    else:
        result["message"] = "Pending admin review."

    return result


# ========== ADMIN: APPLICATION MANAGEMENT ==========

@router.get("/admin/applications")
async def list_applications(
    status_filter: Optional[str] = None,
    _: bool = Depends(_require_admin_key),
    database: Database = Depends(get_database),
) -> Dict[str, Any]:
    """List all applications. Requires X-Admin-Key."""
    import json as _json

    query = "SELECT * FROM pending_applications"
    params = {}
    if status_filter:
        query += " WHERE status = :status"
        params["status"] = status_filter
    query += " ORDER BY created_at DESC"

    rows = database.fetch_all(query, params if params else None)
    apps = []
    for row in rows:
        r = dict(row) if isinstance(row, dict) else row
        data = _json.loads(r["data"]) if isinstance(r.get("data"), str) else r.get("data", {})
        apps.append({
            "application_id": r["id"],
            "agent_name": r["agent_name"],
            "status": r["status"],
            "source": r.get("source") or "acn",
            "client_ip": r.get("client_ip"),
            "created_at": r.get("created_at"),
            "description": data.get("description"),
            "model": data.get("model"),
            "platform": data.get("platform"),
            "capabilities": data.get("capabilities", []),
            "skills_count": len(data.get("skills") or []),
            "mcp_servers_count": len(data.get("mcp_servers") or []),
        })

    return {"applications": apps, "total": len(apps)}


@router.post("/admin/applications/{application_id}/approve")
async def approve_application(
    application_id: str,
    _: bool = Depends(_require_admin_key),
    database: Database = Depends(get_database),
    service: RemoteAgentService = Depends(get_remote_agent_service),
    key_manager: APIKeyManager = Depends(get_api_key_manager),
) -> Dict[str, Any]:
    """Approve an application. Creates agent + API key. Requires X-Admin-Key."""
    import json as _json

    row = database.fetch_one(
        "SELECT * FROM pending_applications WHERE id = :id", {"id": application_id}
    )
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")

    app = dict(row) if isinstance(row, dict) else row
    if app["status"] != "pending":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Application already {app['status']}")

    data = _json.loads(app["data"]) if isinstance(app["data"], str) else app["data"]
    source = app.get("source") or "acn"

    if source == "direct":
        # Direct registration - create agent in agents table directly
        from uuid import uuid4

        agent_id = str(uuid4())
        now = datetime.now(timezone.utc).isoformat()
        agent_name = data.get("agent_name", app["agent_name"])

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
            "agent_name": agent_name,
            "description": data.get("description"),
            "capabilities": _json.dumps(data.get("capabilities") or []),
            "status": "online",
            "labels": _json.dumps(data.get("labels") or {}),
            "created_at": now,
            "updated_at": now,
            "last_heartbeat": now,
        })

        api_key_result = key_manager.create_api_key(
            name=f"agent-{agent_name}",
            key_type=APIKeyType.AGENT,
            scopes=[
                APIKeyScope.AGENT_HEARTBEAT.value,
                APIKeyScope.TASK_READ.value,
                APIKeyScope.TASK_UPDATE.value,
            ],
            description=f"Agent key for {agent_name}",
            metadata={
                "agent_id": agent_id,
                "agent_name": agent_name,
                "allowed_capabilities": data.get("capabilities") or [],
                "mcp_profiles": data.get("mcp_servers") or [],
            },
        )

        result_agent_id = agent_id
        result_agent_name = agent_name
    else:
        # ACN registration - use RemoteAgentService for node + agent creation
        agent_data = RemoteAgentRegister(**data)

        try:
            node = service.node_repo.find_by_name(agent_data.node_name)
            if not node:
                service.register_node(ACNNodeCreate(
                    node_name=agent_data.node_name,
                    node_url=agent_data.callback_url or "http://localhost",
                ))
        except ValueError:
            pass

        new_agent = service.register_remote_agent(agent_data, client_ip=app.get("client_ip"))

        api_key_result = key_manager.create_api_key(
            name=f"acn-agent-{agent_data.agent_name}",
            key_type=APIKeyType.AGENT,
            scopes=[
                APIKeyScope.ACN_NODE_MANAGE.value, APIKeyScope.ACN_AGENT_REGISTER.value,
                APIKeyScope.ACN_AGENT_READ.value, APIKeyScope.ACN_TASK_SUBMIT.value,
                APIKeyScope.AGENT_HEARTBEAT.value, APIKeyScope.TASK_READ.value, APIKeyScope.TASK_UPDATE.value,
            ],
            description=f"ACN agent key for {agent_data.agent_name}",
            metadata={
                "agent_id": new_agent.id,
                "agent_name": new_agent.agent_name,
                "node_id": service.node_repo.find_by_name(agent_data.node_name).id if service.node_repo.find_by_name(agent_data.node_name) else None,
                "node_name": agent_data.node_name,
                "allowed_capabilities": agent_data.capabilities or [],
                "mcp_profiles": agent_data.mcp_servers or [],
            },
        )

        result_agent_id = new_agent.id
        result_agent_name = new_agent.agent_name

    # Update application status
    database.execute(
        """UPDATE pending_applications SET status = 'approved', api_key_value = :key,
           reviewed_at = :now WHERE id = :id""",
        {"key": api_key_result["api_key"], "now": datetime.now(timezone.utc).isoformat(), "id": application_id}
    )

    logger.info("application_approved", app_id=application_id,
               agent_name=result_agent_name, source=source)

    return {
        "status": "approved",
        "agent_id": result_agent_id,
        "agent_name": result_agent_name,
        "api_key": api_key_result["api_key"],
    }


@router.get("/admin/full-status")
async def admin_full_status(
    _: bool = Depends(_require_admin_key),
    service: RemoteAgentService = Depends(get_remote_agent_service),
    task_service: TaskService = Depends(get_task_service),
) -> Dict[str, Any]:
    """Full status with sensitive info - admin only."""
    health = service.get_network_health()
    agents = service.get_remote_agents()

    agent_details = []
    for a in agents:
        agent_obj = service.agent_repo.get_by_id(a["agent_id"])
        meta = agent_obj.metadata if agent_obj and hasattr(agent_obj, 'metadata') else {}
        agent_details.append({
            "name": a["agent_name"], "status": a["status"],
            "capabilities": a["capabilities"],
            "model": meta.get("model"), "platform": meta.get("platform"),
            "version": meta.get("version"), "hostname": meta.get("hostname"),
            "os": meta.get("os_info"), "workspace": meta.get("workspace_path"),
            "channels": meta.get("channels", []),
            "skills_count": len(meta.get("skills") or []),
            "mcp_servers": meta.get("mcp_servers", []),
            "context_window": meta.get("context_window"),
            "ip": meta.get("ip_address"),
            "callback_url": a.get("callback_url"),
            "last_heartbeat": a.get("last_heartbeat"),
        })

    task_stats = {}
    for sv in ["queued", "claimed", "running", "completed", "failed"]:
        try:
            rows = task_service.task_repo.find_by_status(sv)
            task_stats[sv] = len(rows)
        except Exception:
            task_stats[sv] = 0

    return {
        "nodes": health["total_nodes"],
        "agents": {"total": len(agents), "list": agent_details},
        "tasks": task_stats,
    }


@router.get("/admin/tasks")
async def admin_list_tasks(
    _: bool = Depends(_require_admin_key),
    task_service: TaskService = Depends(get_task_service),
) -> Dict[str, Any]:
    """List all tasks with details - admin only."""
    all_tasks = task_service.task_repo.list_all()
    tasks = []
    for t in all_tasks:
        tasks.append({
            "task_id": t.id,
            "title": t.title,
            "description": t.description,
            "task_type": t.task_type if isinstance(t.task_type, str) else t.task_type.value,
            "priority": t.priority,
            "status": t.status if isinstance(t.status, str) else t.status.value,
            "assigned_to": t.owner_agent_id,
            "result_summary": t.result_summary,
            "created_at": t.created_at.isoformat() if t.created_at else None,
            "completed_at": t.completed_at.isoformat() if t.completed_at else None,
        })
    return {"tasks": tasks, "total": len(tasks)}


@router.post("/admin/tasks/create")
async def admin_create_task(
    body: ACNTaskCreate,
    _: bool = Depends(_require_admin_key),
    task_service: TaskService = Depends(get_task_service),
) -> Dict[str, Any]:
    """Create a task from admin dashboard."""
    task_data = TaskCreate(
        title=body.title,
        description=body.description,
        task_type=TaskType(body.task_type) if body.task_type in [t.value for t in TaskType] else TaskType.FEATURE,
        priority=body.priority,
        required_capabilities=body.required_capabilities,
        payload=body.payload or {},
        labels={},
        max_retries=3,
    )
    new_task = task_service.create_task(task_data, created_by="admin")
    return {
        "task_id": new_task.id,
        "title": new_task.title,
        "status": new_task.status if isinstance(new_task.status, str) else new_task.status.value,
        "assigned_to": new_task.owner_agent_id,
    }


@router.post("/admin/tasks/{task_id}/cancel")
async def admin_cancel_task(
    task_id: str,
    _: bool = Depends(_require_admin_key),
    task_service: TaskService = Depends(get_task_service),
) -> Dict[str, Any]:
    """Cancel a task. Requires X-Admin-Key."""
    success = task_service.cancel_task(task_id, reason="Cancelled by admin")
    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot cancel task")
    return {"status": "cancelled", "task_id": task_id}


@router.post("/admin/agents/{agent_id}/remove")
async def admin_remove_agent(
    agent_id: str,
    _: bool = Depends(_require_admin_key),
    service: RemoteAgentService = Depends(get_remote_agent_service),
    database: Database = Depends(get_database),
) -> Dict[str, Any]:
    """Remove an agent from the system. Requires X-Admin-Key."""
    agent = service.agent_repo.get_by_id(agent_id)
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")

    # Delete mapping, then agent
    database.execute("DELETE FROM remote_agent_mappings WHERE local_agent_id = :id", {"id": agent_id})
    service.agent_repo.delete(agent_id)

    logger.info("admin_agent_removed", agent_id=agent_id, agent_name=agent.agent_name)
    return {"status": "removed", "agent_id": agent_id, "agent_name": agent.agent_name}


@router.post("/admin/applications/{application_id}/reject")
async def reject_application(
    application_id: str,
    _: bool = Depends(_require_admin_key),
    database: Database = Depends(get_database),
) -> Dict[str, Any]:
    """Reject an application. Requires X-Admin-Key."""
    row = database.fetch_one(
        "SELECT * FROM pending_applications WHERE id = :id", {"id": application_id}
    )
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")

    app = dict(row) if isinstance(row, dict) else row
    if app["status"] != "pending":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Application already {app['status']}")

    database.execute(
        "UPDATE pending_applications SET status = 'rejected', reviewed_at = :now WHERE id = :id",
        {"now": datetime.now(timezone.utc).isoformat(), "id": application_id}
    )

    logger.info("acn_application_rejected", app_id=application_id, agent_name=app["agent_name"])

    return {"status": "rejected", "application_id": application_id, "agent_name": app["agent_name"]}


# ========== PUBLIC (no auth) ==========

@router.get("/health")
async def acn_health(
    service: RemoteAgentService = Depends(get_remote_agent_service),
) -> Dict[str, Any]:
    """ACN network health - public, no auth required."""
    return service.get_network_health()


@router.get("/status")
async def acn_status(
    service: RemoteAgentService = Depends(get_remote_agent_service),
    task_service: TaskService = Depends(get_task_service),
) -> Dict[str, Any]:
    """Public status - no sensitive info. Use /admin/full-status for details."""
    health = service.get_network_health()
    agents = service.get_remote_agents()

    return {
        "hub": "OpenHub",
        "version": "0.1.0",
        "nodes": health["total_nodes"],
        "total_agents": len(agents),
        "agents": [
            {
                "agent_id": a.get("agent_id"),
                "name": a["agent_name"],
                "status": a["status"],  # Backwards-compatible alias for agent_status.
                "agent_status": a.get("agent_status", a["status"]),
                "capabilities": a.get("capabilities") or [],
                "node_id": a.get("node_id"),
                "node_name": a.get("node_name"),
                "node_status": a.get("node_status"),
                "last_heartbeat": a.get("last_heartbeat"),
                "last_agent_heartbeat": a.get("last_agent_heartbeat", a.get("last_heartbeat")),
                "last_node_heartbeat": a.get("last_node_heartbeat"),
                "offline_reason": a.get("offline_reason"),
                "mcp_profiles": a.get("mcp_profiles") or [],
            }
            for a in agents
        ],
    }
