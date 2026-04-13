"""Pydantic models for the vector search API (Phase 03 / VEC-05).

These models live under app/models/ rather than inline in routes_search.py so
that the per-entity shortcut routes (memory/tasks/artifacts/messages) can
import the same SearchRequest/SearchResponse types without creating a circular
dependency back into routes_search.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

# Single source of truth for valid entity_type strings. Mirrors
# app.services.vector_search_service.ENTITY_CONFIG keys.
ENTITY_TYPES: List[str] = ["memory", "task", "artifact", "message"]


class SearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str = Field(min_length=1, max_length=5000)
    types: Optional[List[str]] = Field(
        default=None,
        description="Entity types to search; default = all 4 ENTITY_TYPES",
    )
    filters: Optional[Dict[str, Any]] = Field(default_factory=dict)
    top_k: int = Field(default=10, ge=1, le=50)


class SearchHit(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entity_type: str
    id: str
    content: str
    distance: float


class SearchResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str
    total: int
    hits: List[SearchHit]


# ---------------------------------------------------------------------------
# Reindex / Delete admin endpoint models (D-15, VEC-05)
# ---------------------------------------------------------------------------


class ReindexRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entity_type: Optional[str] = Field(
        default=None,
        description="Restrict to one of ENTITY_TYPES; default = all",
    )
    since: Optional[datetime] = Field(
        default=None,
        description="Only re-embed rows updated on/after this ISO 8601 timestamp",
    )


class ReindexByType(BaseModel):
    model_config = ConfigDict(extra="forbid")

    memory: int = 0
    task: int = 0
    artifact: int = 0
    message: int = 0


class ReindexResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reindexed: int
    failed: int
    skipped: int
    by_type: ReindexByType


class DeleteEmbeddingResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entity_type: str
    id: str
    status: str  # always "deleted" on success
