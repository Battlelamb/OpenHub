"""
Artifact / File sharing between agents
Files stored as base64 in Turso (small files) or metadata-only (large files via external storage)
"""
import json as _json
import base64
from datetime import datetime, timezone
from uuid import uuid4
from typing import Dict, Any, Optional
from pydantic import BaseModel as PydanticBaseModel, Field
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from ..logging import get_logger
from ..database.connection import get_database, Database
from ..auth.api_key_deps import ApiKeyAuth, resolve_agent_id
from ..database.vector_availability import require_vector
from ..models.vector_search import SearchRequest, SearchResponse
from ..services.embedding_hooks import schedule_embedding

logger = get_logger(__name__)
router = APIRouter(prefix="/v1/artifacts", tags=["artifacts"])


class ArtifactUpload(PydanticBaseModel):
    filename: str = Field(min_length=1, max_length=255)
    content_type: str = "text/plain"  # text/plain, application/json, image/png, etc
    content: str = Field(min_length=1, max_length=500000, description="Base64 encoded content or plain text")
    encoding: str = "text"  # text or base64
    task_id: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[list] = None


@router.post("/upload")
async def upload_artifact(
    body: ArtifactUpload,
    key_info: ApiKeyAuth,
    background_tasks: BackgroundTasks,
    database: Database = Depends(get_database),
) -> Dict[str, Any]:
    """Upload an artifact (file). Max 500KB for inline storage."""
    agent_id = resolve_agent_id(key_info, database)
    art_id = str(uuid4())
    now = datetime.now(timezone.utc).isoformat()

    size = len(body.content)

    database.execute(
        """INSERT INTO artifacts (id, filename, content_type, content, encoding, size_bytes,
           task_id, description, tags, uploaded_by, created_at)
           VALUES (:id, :fn, :ct, :content, :enc, :size, :tid, :desc, :tags, :by, :now)""",
        {
            "id": art_id, "fn": body.filename, "ct": body.content_type,
            "content": body.content, "enc": body.encoding, "size": size,
            "tid": body.task_id, "desc": body.description,
            "tags": _json.dumps(body.tags or []), "by": agent_id, "now": now,
        }
    )

    logger.info("artifact_uploaded", id=art_id, filename=body.filename, size=size)

    # Auto-index artifact content (VEC-04). For base64 artifacts, decode best-effort
    # so the embedded text reflects the source bytes; non-decodable blobs become
    # an empty string and the schedule helper will short-circuit.
    indexable: Optional[str] = body.content
    if body.encoding == "base64":
        try:
            indexable = base64.b64decode(body.content).decode("utf-8", errors="replace")
        except Exception:
            indexable = None
    schedule_embedding(background_tasks, "artifact", art_id, indexable)

    return {"artifact_id": art_id, "filename": body.filename, "size_bytes": size}


@router.get("/{artifact_id}")
async def get_artifact(
    artifact_id: str,
    key_info: ApiKeyAuth,
    database: Database = Depends(get_database),
) -> Dict[str, Any]:
    """Download an artifact."""
    row = database.fetch_one("SELECT * FROM artifacts WHERE id = :id", {"id": artifact_id})
    if not row:
        raise HTTPException(status_code=404, detail="Artifact not found")

    r = dict(row) if isinstance(row, dict) else row
    return {
        "artifact_id": r["id"],
        "filename": r["filename"],
        "content_type": r["content_type"],
        "content": r["content"],
        "encoding": r["encoding"],
        "size_bytes": r["size_bytes"],
        "task_id": r.get("task_id"),
        "description": r.get("description"),
        "uploaded_by": r.get("uploaded_by"),
        "created_at": r.get("created_at"),
    }


@router.get("/")
async def list_artifacts(
    task_id: Optional[str] = None,
    limit: int = 20,
    key_info: ApiKeyAuth = None,
    database: Database = Depends(get_database),
) -> Dict[str, Any]:
    """List artifacts (metadata only, no content)."""
    query = "SELECT id, filename, content_type, encoding, size_bytes, task_id, description, tags, uploaded_by, created_at FROM artifacts"
    params = {}
    if task_id:
        query += " WHERE task_id = :tid"
        params["tid"] = task_id
    query += " ORDER BY created_at DESC LIMIT :limit"
    params["limit"] = limit

    rows = database.fetch_all(query, params)
    items = []
    for r in rows:
        r = dict(r) if isinstance(r, dict) else r
        items.append({
            "artifact_id": r["id"], "filename": r["filename"],
            "content_type": r["content_type"], "size_bytes": r["size_bytes"],
            "task_id": r.get("task_id"), "description": r.get("description"),
            "created_at": r.get("created_at"),
        })

    return {"artifacts": items, "total": len(items)}


@router.delete("/{artifact_id}")
async def delete_artifact(
    artifact_id: str,
    key_info: ApiKeyAuth,
    database: Database = Depends(get_database),
) -> Dict[str, str]:
    database.execute("DELETE FROM artifacts WHERE id = :id", {"id": artifact_id})
    return {"status": "deleted", "artifact_id": artifact_id}


@router.post(
    "/search",
    response_model=SearchResponse,
    dependencies=[Depends(require_vector)],
    tags=["artifacts [experimental]"],
    summary="Semantic search over artifacts (experimental, Phase 03 / VEC-05)",
)
async def artifact_search_shortcut(req: SearchRequest) -> SearchResponse:
    """Vector search shortcut. Forces types=['artifact'] regardless of body."""
    from .routes_search import unified_search  # local import avoids cycle
    forced = req.model_copy(update={"types": ["artifact"]})
    return await unified_search(forced)
