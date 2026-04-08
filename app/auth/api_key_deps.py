"""
Shared API key authentication dependency for routes that use X-API-Key header.
Replaces the per-route _auth/_sender helpers in routes_p1, p2, artifacts, memory, websocket.
Per D-09: consolidate duplicate auth helpers into a single shared module.

Design note: Implemented as FastAPI Depends() rather than BaseHTTPMiddleware because
WebSocket routes and streaming endpoints require access to the authenticated key_info
dict in their handler - middleware cannot easily inject this into handler scope.
The ApiKeyAuth type alias means each route file has one import instead of duplicated logic.
"""
from typing import Dict, Optional, Annotated
from fastapi import Header, Depends, HTTPException, status

from ..database.connection import get_database, Database
from .api_keys import APIKeyManager


def require_api_key(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    database: Database = Depends(get_database)
) -> Dict:
    """
    Validate X-API-Key header against the api_keys table.
    Returns the key info dict on success. Raises 401 on failure.
    Replaces the per-route _auth() helper (was duplicated in 5 route files).
    """
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="X-API-Key header is required"
        )
    info = APIKeyManager(database).validate_api_key(x_api_key)
    if not info:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired API key"
        )
    return info


def resolve_agent_id(key_info: Dict, db: Database) -> str:
    """
    Resolve the local agent ID from API key info.
    For ACN bridge keys (name starts with 'acn-agent-'), looks up remote_agent_mappings.
    Replaces the per-route _sender() helper.
    """
    name = key_info.get("name", "")
    if name.startswith("acn-agent-"):
        row = db.fetch_one(
            "SELECT local_agent_id FROM remote_agent_mappings WHERE local_agent_id = :id",
            {"id": key_info.get("key_id")}
        )
        return row["local_agent_id"] if row else key_info.get("key_id", "unknown")
    return key_info.get("key_id", "unknown")


# Annotated type alias for use in route signatures
ApiKeyAuth = Annotated[Dict, Depends(require_api_key)]
