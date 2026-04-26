"""
P1 Features: Human-in-the-loop, Resource Locking, Tracing, Cost Tracking
"""
import json as _json
from datetime import datetime, timezone, timedelta
from uuid import uuid4
from typing import Dict, Any, Optional, List
from pydantic import BaseModel as PydanticBaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, Query

from ..logging import get_logger
from ..database.connection import get_database, Database
from ..auth.api_key_deps import ApiKeyAuth, resolve_agent_id
from ..auth.dependencies import CurrentAgent

logger = get_logger(__name__)

lock_router = APIRouter(prefix="/v1/locks", tags=["locks"])
trace_router = APIRouter(prefix="/v1/traces", tags=["tracing"])
cost_router = APIRouter(prefix="/v1/costs", tags=["costs"])


# ========== RESOURCE LOCKING ==========

class LockAcquire(PydanticBaseModel):
    resource: str = Field(min_length=1, max_length=500, description="Resource to lock (file path, repo, etc)")
    ttl_seconds: int = Field(default=300, ge=10, le=3600, description="Lock TTL")
    reason: Optional[str] = None


@lock_router.post("/acquire")
async def acquire_lock(
    body: LockAcquire,
    key_info: ApiKeyAuth,
    database: Database = Depends(get_database),
) -> Dict[str, Any]:
    """Acquire a lock on a resource. Returns conflict if already locked."""
    agent_id = resolve_agent_id(key_info, database)
    now = datetime.now(timezone.utc)

    # Check existing lock
    existing = database.fetch_one(
        "SELECT * FROM resource_locks WHERE resource = :res AND released_at IS NULL",
        {"res": body.resource}
    )
    if existing:
        ex = dict(existing) if isinstance(existing, dict) else existing
        # Check if expired
        exp = ex.get("expires_at")
        if exp:
            try:
                exp_dt = datetime.fromisoformat(str(exp).replace("Z", "").replace("+00:00", ""))
                if now > exp_dt:
                    # Expired - release it
                    database.execute(
                        "UPDATE resource_locks SET released_at = :now WHERE id = :id",
                        {"now": now.isoformat(), "id": ex["id"]}
                    )
                else:
                    raise HTTPException(status_code=409, detail=f"Resource locked by agent {ex.get('locked_by')}")
            except (ValueError, TypeError):
                raise HTTPException(status_code=409, detail="Resource is locked")
        else:
            raise HTTPException(status_code=409, detail="Resource is locked")

    lock_id = str(uuid4())
    expires_at = (now + timedelta(seconds=body.ttl_seconds)).isoformat()

    database.execute(
        """INSERT INTO resource_locks (id, resource, locked_by, reason, ttl_seconds, expires_at, created_at)
           VALUES (:id, :res, :by, :reason, :ttl, :exp, :now)""",
        {"id": lock_id, "res": body.resource, "by": agent_id, "reason": body.reason,
         "ttl": body.ttl_seconds, "exp": expires_at, "now": now.isoformat()}
    )

    return {"lock_id": lock_id, "resource": body.resource, "expires_at": expires_at}


@lock_router.post("/release")
async def release_lock(
    resource: str,
    key_info: ApiKeyAuth,
    database: Database = Depends(get_database),
) -> Dict[str, str]:
    """Release a lock on a resource."""
    now = datetime.now(timezone.utc).isoformat()
    database.execute(
        "UPDATE resource_locks SET released_at = :now WHERE resource = :res AND released_at IS NULL",
        {"now": now, "res": resource}
    )
    return {"status": "released", "resource": resource}


@lock_router.get("/status")
async def lock_status(
    resource: str,
    current_agent: CurrentAgent = None,
    database: Database = Depends(get_database),
) -> Dict[str, Any]:
    """Check if a resource is locked."""
    row = database.fetch_one(
        "SELECT * FROM resource_locks WHERE resource = :res AND released_at IS NULL ORDER BY created_at DESC LIMIT 1",
        {"res": resource}
    )
    if not row:
        return {"resource": resource, "locked": False}

    r = dict(row) if isinstance(row, dict) else row
    return {"resource": resource, "locked": True, "locked_by": r.get("locked_by"), "expires_at": r.get("expires_at")}


@lock_router.get("/")
async def list_active_locks(
    current_agent: CurrentAgent = None,
    database: Database = Depends(get_database),
) -> List[Dict[str, Any]]:
    """
    List currently held resource locks (active = not released yet).
    Used by the Phase 4 dashboard locks panel (UI-14). JWT auth.

    Returns ResourceLock[] matching web/src/types/entities.ts:
    [{resource_id, agent_id, acquired_at, expires_at, conflict}]
    """
    rows = database.fetch_all(
        "SELECT id, resource, locked_by, created_at, expires_at "
        "FROM resource_locks WHERE released_at IS NULL "
        "ORDER BY created_at DESC LIMIT 100"
    )
    locks: List[Dict[str, Any]] = []
    now = datetime.now(timezone.utc)
    for r in rows:
        r = dict(r) if not isinstance(r, dict) else r
        # An expired-but-not-released lock is a "conflict" (stale lock detection)
        conflict = False
        exp = r.get("expires_at")
        if exp:
            try:
                exp_dt = datetime.fromisoformat(str(exp).replace("Z", "").replace("+00:00", ""))
                if now.replace(tzinfo=None) > exp_dt.replace(tzinfo=None):
                    conflict = True
            except (ValueError, TypeError):
                conflict = False
        locks.append({
            "resource_id": r.get("resource") or "",
            "agent_id": r.get("locked_by") or "",
            "acquired_at": r.get("created_at") or "",
            "expires_at": r.get("expires_at") or "",
            "conflict": conflict,
        })
    return locks


# ========== TRACING ==========

class TraceEvent(PydanticBaseModel):
    trace_id: Optional[str] = None  # auto-generated if not provided
    event_type: str = "info"  # info, error, metric, span_start, span_end
    name: str = Field(min_length=1, max_length=200)
    data: Optional[Dict[str, Any]] = None
    task_id: Optional[str] = None
    duration_ms: Optional[float] = None


@trace_router.post("/event")
async def log_trace_event(
    body: TraceEvent,
    key_info: ApiKeyAuth,
    database: Database = Depends(get_database),
) -> Dict[str, Any]:
    """Log a trace event."""
    agent_id = resolve_agent_id(key_info, database)
    trace_id = body.trace_id or str(uuid4())
    event_id = str(uuid4())
    now = datetime.now(timezone.utc).isoformat()

    database.execute(
        """INSERT INTO trace_events (id, trace_id, agent_id, event_type, name, data, task_id, duration_ms, created_at)
           VALUES (:id, :tid, :aid, :type, :name, :data, :task_id, :dur, :now)""",
        {
            "id": event_id, "tid": trace_id, "aid": agent_id,
            "type": body.event_type, "name": body.name,
            "data": _json.dumps(body.data or {}), "task_id": body.task_id,
            "dur": body.duration_ms, "now": now,
        }
    )

    return {"event_id": event_id, "trace_id": trace_id}


@trace_router.get("/{trace_id}")
async def get_trace(
    trace_id: str,
    key_info: ApiKeyAuth,
    database: Database = Depends(get_database),
) -> Dict[str, Any]:
    """Get all events for a trace."""
    rows = database.fetch_all(
        "SELECT * FROM trace_events WHERE trace_id = :tid ORDER BY created_at ASC",
        {"tid": trace_id}
    )
    events = []
    for r in rows:
        r = dict(r) if isinstance(r, dict) else r
        events.append({
            "event_id": r["id"], "event_type": r["event_type"],
            "name": r["name"], "agent_id": r.get("agent_id"),
            "duration_ms": r.get("duration_ms"),
            "data": _json.loads(r["data"]) if isinstance(r.get("data"), str) else r.get("data", {}),
            "created_at": r.get("created_at"),
        })
    return {"trace_id": trace_id, "events": events, "total": len(events)}


# ========== COST TRACKING ==========

class CostEntry(PydanticBaseModel):
    task_id: Optional[str] = None
    model: str = Field(min_length=1, max_length=100)
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    cost_usd: Optional[float] = None  # auto-calculated if not provided


# Rough cost per 1M tokens
_MODEL_COSTS = {
    "claude-opus-4-6": {"input": 15.0, "output": 75.0},
    "gpt-5.3-codex": {"input": 10.0, "output": 40.0},
    "qwen3.5-plus": {"input": 0.0, "output": 0.0},  # free tier
}


@cost_router.post("/log")
async def log_cost(
    body: CostEntry,
    key_info: ApiKeyAuth,
    database: Database = Depends(get_database),
) -> Dict[str, Any]:
    """Log token usage and cost for an agent."""
    agent_id = resolve_agent_id(key_info, database)
    cost_id = str(uuid4())
    now = datetime.now(timezone.utc).isoformat()

    # Auto-calculate cost if not provided
    cost = body.cost_usd
    if cost is None:
        rates = _MODEL_COSTS.get(body.model, {"input": 5.0, "output": 15.0})
        cost = (body.input_tokens * rates["input"] + body.output_tokens * rates["output"]) / 1_000_000

    database.execute(
        """INSERT INTO cost_tracking (id, agent_id, task_id, model, input_tokens, output_tokens, cost_usd, created_at)
           VALUES (:id, :aid, :tid, :model, :inp, :out, :cost, :now)""",
        {
            "id": cost_id, "aid": agent_id, "tid": body.task_id,
            "model": body.model, "inp": body.input_tokens,
            "out": body.output_tokens, "cost": cost, "now": now,
        }
    )

    return {"cost_id": cost_id, "cost_usd": round(cost, 6), "model": body.model}


@cost_router.get("/summary")
async def cost_summary(
    days: int = Query(7, ge=1, le=90),
    current_agent: CurrentAgent = None,
    database: Database = Depends(get_database),
) -> Dict[str, Any]:
    """Get cost summary for last N days."""
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

    # Total
    total = database.fetch_one(
        "SELECT SUM(cost_usd) as total, SUM(input_tokens) as inp, SUM(output_tokens) as out FROM cost_tracking WHERE created_at > :since",
        {"since": since}
    )
    t = dict(total) if total and isinstance(total, dict) else {}

    # Per agent
    agents = database.fetch_all(
        """SELECT agent_id, SUM(cost_usd) as total, SUM(input_tokens) as inp, SUM(output_tokens) as out, COUNT(*) as calls
           FROM cost_tracking WHERE created_at > :since GROUP BY agent_id""",
        {"since": since}
    )

    per_agent = []
    for a in agents:
        a = dict(a) if isinstance(a, dict) else a
        # Get agent name
        ag = database.fetch_one("SELECT agent_name FROM agents WHERE id = :id", {"id": a["agent_id"]})
        name = (ag["agent_name"] if isinstance(ag, dict) else ag[0]) if ag else "unknown"
        per_agent.append({
            "agent_name": name, "total_cost_usd": round(a.get("total") or 0, 4),
            "input_tokens": a.get("inp") or 0, "output_tokens": a.get("out") or 0,
            "api_calls": a.get("calls") or 0,
        })

    return {
        "period_days": days,
        "total_cost_usd": round(t.get("total") or 0, 4),
        "total_input_tokens": t.get("inp") or 0,
        "total_output_tokens": t.get("out") or 0,
        "per_agent": per_agent,
    }
