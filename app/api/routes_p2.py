"""
P2 Features: MCP/Tool Sharing, Agent Templates, Smart Retry, Rate Limiting, Dead Letter Queue
"""
import json as _json
import time
from datetime import datetime, timezone, timedelta
from uuid import uuid4
from typing import Dict, Any, Optional, List
from pydantic import BaseModel as PydanticBaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, Header, Query, Request, status

from ..logging import get_logger
from ..database.connection import get_database, Database
from ..auth.api_key_deps import ApiKeyAuth, resolve_agent_id

logger = get_logger(__name__)

tools_router = APIRouter(prefix="/v1/tools", tags=["mcp-tools"])
templates_router = APIRouter(prefix="/v1/templates", tags=["templates"])
dlq_router = APIRouter(prefix="/v1/dlq", tags=["dead-letter-queue"])

def _admin(x_admin_key: str = Header(..., alias="X-Admin-Key")):
    from ..config import get_settings
    s = get_settings()
    ak = getattr(s, 'acn_admin_key', None)
    if not ak or x_admin_key != ak:
        raise HTTPException(status_code=401, detail="Invalid admin key")
    return True


async def _dashboard_or_admin_key(
    request: Request,
    x_admin_key: Optional[str] = Header(None, alias="X-Admin-Key"),
) -> bool:
    """
    DLQ routes accept EITHER an X-Admin-Key (legacy CLI flow) OR a JWT admin
    Authorization header (dashboard flow). Either is sufficient. This is the
    minimum change that lets the React dashboard hit /v1/dlq/ without storing
    a permanent admin key in the browser.
    """
    # Try X-Admin-Key first (cheap)
    from ..config import get_settings
    s = get_settings()
    ak = getattr(s, 'acn_admin_key', None)
    if ak and x_admin_key and x_admin_key == ak:
        return True

    # Try JWT admin
    auth_header = request.headers.get("authorization") or request.headers.get("Authorization")
    if not auth_header or not auth_header.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="JWT admin or X-Admin-Key required")
    token = auth_header.split(" ", 1)[1]
    try:
        from ..auth.jwt_auth import verify_token
        payload = verify_token(token, expected_type="access")
        # CurrentAdmin requires role==admin in the token; mirror that check here
        if payload.get("role") != "admin":
            raise HTTPException(status_code=403, detail="Admin role required")
        return True
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid JWT")


# ========== P2.1: MCP/TOOL SHARING ==========

class ToolRegister(PydanticBaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str = ""
    tool_type: str = "mcp"  # mcp, api, function
    endpoint: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None


@tools_router.post("/register")
async def register_tool(
    body: ToolRegister,
    key_info: ApiKeyAuth,
    database: Database = Depends(get_database),
) -> Dict[str, Any]:
    """Register a tool/MCP server for sharing with other agents."""
    agent_id = resolve_agent_id(key_info, database)
    tool_id = str(uuid4())
    now = datetime.now(timezone.utc).isoformat()

    database.execute(
        """INSERT INTO shared_tools (id, name, description, tool_type, endpoint, config, tags, registered_by, created_at)
           VALUES (:id, :name, :desc, :type, :ep, :cfg, :tags, :by, :now)""",
        {
            "id": tool_id, "name": body.name, "desc": body.description,
            "type": body.tool_type, "ep": body.endpoint,
            "cfg": _json.dumps(body.config or {}),
            "tags": _json.dumps(body.tags or []),
            "by": agent_id, "now": now,
        }
    )
    return {"tool_id": tool_id, "name": body.name}


@tools_router.get("/discover")
async def discover_tools(
    key_info: ApiKeyAuth,
    tag: Optional[str] = None,
    tool_type: Optional[str] = None,
    database: Database = Depends(get_database),
) -> Dict[str, Any]:
    """Discover available tools shared by agents."""
    query = "SELECT * FROM shared_tools"
    params = {}
    conditions = []

    if tag:
        conditions.append("tags LIKE :tag")
        params["tag"] = f"%{tag}%"
    if tool_type:
        conditions.append("tool_type = :type")
        params["type"] = tool_type

    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY created_at DESC LIMIT 50"

    rows = database.fetch_all(query, params if params else None)
    tools = []
    for r in rows:
        r = dict(r) if isinstance(r, dict) else r
        # Get owner name
        owner = database.fetch_one("SELECT agent_name FROM agents WHERE id = :id", {"id": r.get("registered_by")})
        owner_name = (owner["agent_name"] if isinstance(owner, dict) else owner[0]) if owner else "unknown"

        tools.append({
            "tool_id": r["id"], "name": r["name"], "description": r.get("description"),
            "tool_type": r.get("tool_type"), "endpoint": r.get("endpoint"),
            "tags": _json.loads(r["tags"]) if isinstance(r.get("tags"), str) else [],
            "registered_by": owner_name,
        })

    return {"tools": tools, "total": len(tools)}


# ========== P2.2: AGENT TEMPLATES ==========

class AgentTemplate(PydanticBaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str = ""
    capabilities: List[str]
    skills: Optional[List[str]] = None
    mcp_servers: Optional[List[str]] = None
    model: Optional[str] = None
    platform: Optional[str] = None
    config: Optional[Dict[str, Any]] = None


@templates_router.post("/create")
async def create_template(
    body: AgentTemplate,
    key_info: ApiKeyAuth,
    database: Database = Depends(get_database),
) -> Dict[str, Any]:
    """Create an agent template for quick deployment."""
    tmpl_id = str(uuid4())
    now = datetime.now(timezone.utc).isoformat()
    agent_id = resolve_agent_id(key_info, database)

    database.execute(
        """INSERT INTO agent_templates (id, name, description, capabilities, skills, mcp_servers,
           model, platform, config, created_by, created_at)
           VALUES (:id, :name, :desc, :caps, :skills, :mcp, :model, :plat, :cfg, :by, :now)""",
        {
            "id": tmpl_id, "name": body.name, "desc": body.description,
            "caps": _json.dumps(body.capabilities),
            "skills": _json.dumps(body.skills or []),
            "mcp": _json.dumps(body.mcp_servers or []),
            "model": body.model, "plat": body.platform,
            "cfg": _json.dumps(body.config or {}),
            "by": agent_id, "now": now,
        }
    )
    return {"template_id": tmpl_id, "name": body.name}


@templates_router.get("/")
async def list_templates(
    key_info: ApiKeyAuth,
    database: Database = Depends(get_database),
) -> Dict[str, Any]:
    """List available agent templates."""
    rows = database.fetch_all("SELECT * FROM agent_templates ORDER BY created_at DESC LIMIT 50")
    templates = []
    for r in rows:
        r = dict(r) if isinstance(r, dict) else r
        templates.append({
            "template_id": r["id"], "name": r["name"],
            "description": r.get("description"),
            "capabilities": _json.loads(r["capabilities"]) if isinstance(r.get("capabilities"), str) else [],
            "model": r.get("model"), "platform": r.get("platform"),
        })
    return {"templates": templates, "total": len(templates)}


@templates_router.get("/{template_id}")
async def get_template(
    template_id: str,
    key_info: ApiKeyAuth,
    database: Database = Depends(get_database),
) -> Dict[str, Any]:
    """Get template details."""
    row = database.fetch_one("SELECT * FROM agent_templates WHERE id = :id", {"id": template_id})
    if not row:
        raise HTTPException(status_code=404, detail="Template not found")
    r = dict(row) if isinstance(row, dict) else row
    return {
        "template_id": r["id"], "name": r["name"], "description": r.get("description"),
        "capabilities": _json.loads(r["capabilities"]) if isinstance(r.get("capabilities"), str) else [],
        "skills": _json.loads(r["skills"]) if isinstance(r.get("skills"), str) else [],
        "mcp_servers": _json.loads(r["mcp_servers"]) if isinstance(r.get("mcp_servers"), str) else [],
        "model": r.get("model"), "platform": r.get("platform"),
        "config": _json.loads(r["config"]) if isinstance(r.get("config"), str) else {},
    }


# ========== P2.5: DEAD LETTER QUEUE ==========

@dlq_router.get("/")
async def list_dead_letters(
    _: bool = Depends(_dashboard_or_admin_key),
    database: Database = Depends(get_database),
) -> Dict[str, Any]:
    """List tasks in dead letter queue (failed all retries)."""
    rows = database.fetch_all(
        "SELECT * FROM tasks WHERE status = 'failed' AND retry_count >= max_retries ORDER BY created_at DESC LIMIT 50"
    )
    items = []
    for r in rows:
        # sqlite3.Row needs explicit dict() conversion before .get() works.
        # Original code had the conversion guard inverted; it skipped when r was a Row.
        r = dict(r) if not isinstance(r, dict) else r
        items.append({
            "task_id": r["id"], "title": r["title"],
            "task_type": r.get("task_type"), "priority": r.get("priority"),
            "retry_count": r.get("retry_count"), "max_retries": r.get("max_retries"),
            "last_error": r.get("last_error"),
            "assigned_to": r.get("owner_agent_id"),
            "created_at": r.get("created_at"),
        })
    return {"dead_letters": items, "total": len(items)}


@dlq_router.post("/{task_id}/retry")
async def retry_dead_letter(
    task_id: str,
    _: bool = Depends(_dashboard_or_admin_key),
    database: Database = Depends(get_database),
) -> Dict[str, Any]:
    """Retry a dead letter task (requeue it)."""
    now = datetime.now(timezone.utc).isoformat()
    database.execute(
        """UPDATE tasks SET status = 'queued', owner_agent_id = NULL, claimed_at = NULL,
           started_at = NULL, completed_at = NULL, lease_until = NULL,
           retry_count = 0, last_error = 'Requeued from DLQ', updated_at = :now
           WHERE id = :id AND status = 'failed'""",
        {"now": now, "id": task_id}
    )
    return {"status": "requeued", "task_id": task_id}


@dlq_router.post("/{task_id}/dismiss")
async def dismiss_dead_letter(
    task_id: str,
    _: bool = Depends(_dashboard_or_admin_key),
    database: Database = Depends(get_database),
) -> Dict[str, Any]:
    """Dismiss a dead letter (mark as dead_letter status)."""
    now = datetime.now(timezone.utc).isoformat()
    database.execute(
        "UPDATE tasks SET status = 'dead_letter', updated_at = :now WHERE id = :id",
        {"now": now, "id": task_id}
    )
    return {"status": "dismissed", "task_id": task_id}
