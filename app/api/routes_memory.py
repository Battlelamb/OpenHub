"""
Shared Memory / Context Store - agent'lar arasi bilgi paylasimi
"""
import json as _json
from datetime import datetime, timezone, timedelta
from uuid import uuid4
from typing import Dict, Any, Optional, List
from pydantic import BaseModel as PydanticBaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, status, Query

from ..logging import get_logger
from ..database.connection import get_database, Database
from ..auth.api_key_deps import ApiKeyAuth, resolve_agent_id

logger = get_logger(__name__)

router = APIRouter(prefix="/v1/memory", tags=["memory"])


class MemoryWrite(PydanticBaseModel):
    key: str = Field(min_length=1, max_length=200)
    value: str = Field(min_length=1, max_length=50000)
    value_type: str = "text"  # text, json, code, url
    tags: Optional[List[str]] = None
    access_level: str = "public"  # public, private, team
    ttl_seconds: Optional[int] = None  # None = permanent


@router.post("/write")
async def write_memory(
    body: MemoryWrite,
    key_info: ApiKeyAuth,
    database: Database = Depends(get_database),
) -> Dict[str, Any]:
    """Write to shared memory. Overwrites if key exists."""
    agent_id = resolve_agent_id(key_info, database)

    expires_at = None
    if body.ttl_seconds:
        expires_at = (datetime.now(timezone.utc) + timedelta(seconds=body.ttl_seconds)).isoformat()

    # Upsert - check if key exists
    existing = database.fetch_one("SELECT id FROM shared_memory WHERE key = :key", {"key": body.key})

    now = datetime.now(timezone.utc).isoformat()

    if existing:
        eid = existing["id"] if isinstance(existing, dict) else existing[0]
        database.execute(
            """UPDATE shared_memory SET value = :val, value_type = :vtype, tags = :tags,
               access_level = :access, ttl_seconds = :ttl, expires_at = :exp, updated_at = :now
               WHERE id = :id""",
            {
                "val": body.value, "vtype": body.value_type,
                "tags": _json.dumps(body.tags or []),
                "access": body.access_level, "ttl": body.ttl_seconds,
                "exp": expires_at, "now": now, "id": eid,
            }
        )
        return {"status": "updated", "key": body.key}
    else:
        mem_id = str(uuid4())
        database.execute(
            """INSERT INTO shared_memory (id, key, value, value_type, tags, created_by, access_level, ttl_seconds, expires_at, created_at, updated_at)
               VALUES (:id, :key, :val, :vtype, :tags, :by, :access, :ttl, :exp, :now, :now)""",
            {
                "id": mem_id, "key": body.key, "val": body.value,
                "vtype": body.value_type, "tags": _json.dumps(body.tags or []),
                "by": agent_id, "access": body.access_level,
                "ttl": body.ttl_seconds, "exp": expires_at, "now": now,
            }
        )
        return {"status": "created", "key": body.key, "id": mem_id}


@router.get("/read")
async def read_memory(
    key: str,
    key_info: ApiKeyAuth,
    database: Database = Depends(get_database),
) -> Dict[str, Any]:
    """Read from shared memory by key."""
    row = database.fetch_one("SELECT * FROM shared_memory WHERE key = :key", {"key": key})
    if not row:
        raise HTTPException(status_code=404, detail=f"Key '{key}' not found")

    r = dict(row) if isinstance(row, dict) else row

    # Check TTL
    if r.get("expires_at"):
        exp = datetime.fromisoformat(str(r["expires_at"]).replace("Z", "+00:00").replace("+00:00", ""))
        if datetime.utcnow() > exp:
            database.execute("DELETE FROM shared_memory WHERE key = :key", {"key": key})
            raise HTTPException(status_code=404, detail=f"Key '{key}' expired")

    return {
        "key": r["key"],
        "value": r["value"],
        "value_type": r.get("value_type", "text"),
        "tags": _json.loads(r["tags"]) if isinstance(r.get("tags"), str) else r.get("tags", []),
        "created_by": r.get("created_by"),
        "created_at": r.get("created_at"),
        "updated_at": r.get("updated_at"),
    }


@router.get("/search")
async def search_memory(
    q: Optional[str] = None,
    tag: Optional[str] = None,
    key_info: ApiKeyAuth = None,
    limit: int = Query(20, ge=1, le=100),
    database: Database = Depends(get_database),
) -> Dict[str, Any]:
    """Search shared memory by text or tag."""
    query = "SELECT * FROM shared_memory WHERE 1=1"
    params = {}

    if q:
        query += " AND (key LIKE :q OR value LIKE :q)"
        params["q"] = f"%{q}%"

    if tag:
        query += " AND tags LIKE :tag"
        params["tag"] = f"%{tag}%"

    query += " ORDER BY updated_at DESC LIMIT :limit"
    params["limit"] = limit

    rows = database.fetch_all(query, params)

    results = []
    for r in rows:
        r = dict(r) if isinstance(r, dict) else r
        results.append({
            "key": r["key"],
            "value": r["value"][:200] + ("..." if len(str(r["value"])) > 200 else ""),
            "value_type": r.get("value_type"),
            "tags": _json.loads(r["tags"]) if isinstance(r.get("tags"), str) else [],
            "updated_at": r.get("updated_at"),
        })

    return {"results": results, "total": len(results)}


@router.delete("/delete")
async def delete_memory(
    key: str,
    key_info: ApiKeyAuth,
    database: Database = Depends(get_database),
) -> Dict[str, str]:
    """Delete a key from shared memory."""
    database.execute("DELETE FROM shared_memory WHERE key = :key", {"key": key})
    return {"status": "deleted", "key": key}


@router.get("/keys")
async def list_keys(
    limit: int = Query(50, ge=1, le=200),
    key_info: ApiKeyAuth = None,
    database: Database = Depends(get_database),
) -> Dict[str, Any]:
    """List all keys in shared memory."""
    rows = database.fetch_all(
        "SELECT key, value_type, tags, created_by, updated_at FROM shared_memory ORDER BY updated_at DESC LIMIT :limit",
        {"limit": limit}
    )
    keys = []
    for r in rows:
        r = dict(r) if isinstance(r, dict) else r
        keys.append({
            "key": r["key"],
            "value_type": r.get("value_type"),
            "tags": _json.loads(r["tags"]) if isinstance(r.get("tags"), str) else [],
            "created_by": r.get("created_by"),
            "updated_at": r.get("updated_at"),
        })
    return {"keys": keys, "total": len(keys)}
