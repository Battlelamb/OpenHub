"""Unified vector search API (experimental, VEC-05 / VEC-06 BETA).

This module owns the public surface of Phase 3:

  - POST   /v1/search                         Cross-entity semantic search
  - POST   /v1/search/reindex                 Admin-only re-embed (D-15)
  - DELETE /v1/search/{entity_type}/{id}      Admin-only embedding clear

BETA: opt-in vector search. Requires Turso configuration. See the README
"Vector Search (Beta)" section for setup. The router is tagged
"search [experimental]" (D-23) and the matching tag description in
``app/main.py`` advertises the beta opt-in contract via OpenAPI. Per D-08,
every handler returns 503 on local SQLite via the router-level
``Depends(require_vector)``.
"""
from typing import Any, Dict, List

import structlog
from fastapi import APIRouter, Depends, HTTPException, Path

from ..auth.dependencies import CurrentAdmin
from ..database.connection import get_database
from ..database.vector_availability import require_vector
from ..models.vector_search import (
    DeleteEmbeddingResponse,
    ENTITY_TYPES,
    ReindexByType,
    ReindexRequest,
    ReindexResponse,
    SearchHit,
    SearchRequest,
    SearchResponse,
)
from ..services.embedding_service import get_embedding_service
from ..services.vector_search_service import VectorSearchService

logger = structlog.get_logger(__name__)

router = APIRouter(
    prefix="/v1/search",
    tags=["search [experimental]"],
    dependencies=[Depends(require_vector)],
)


# ---------------------------------------------------------------------------
# Unified search
# ---------------------------------------------------------------------------


async def unified_search(req: SearchRequest) -> SearchResponse:
    """Embed the query, fan out to the requested entity types, merge & cap.

    This helper is also called by the per-entity shortcut routes
    (routes_memory.memory_search_shortcut etc.) with types forced to a single
    value, so all merge / cap / RFC 7807 logic lives here.
    """
    backend = get_embedding_service()
    if backend is None:
        raise HTTPException(
            status_code=503,
            detail=(
                "embedding-unavailable: No embedding backend is configured. "
                "Check AGENTHUB_EMBEDDING_PROVIDER and AGENTHUB_OPENAI_API_KEY."
            ),
        )

    types = list(req.types) if req.types else list(ENTITY_TYPES)
    invalid = [t for t in types if t not in ENTITY_TYPES]
    if invalid:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown entity types: {invalid}. Valid: {ENTITY_TYPES}",
        )

    query_vectors = await backend.embed([req.query])
    if not query_vectors:
        raise HTTPException(
            status_code=500,
            detail="Embedding backend returned empty result",
        )
    qvec = query_vectors[0]

    svc = VectorSearchService(get_database())
    all_hits: List[Dict[str, Any]] = []
    for t in types:
        try:
            hits = svc.search_entity(
                t, qvec, top_k=req.top_k, filters=req.filters or {}
            )
            all_hits.extend(hits)
        except Exception as e:
            logger.warning(
                "unified_search_entity_failed",
                entity_type=t,
                error=str(e)[:500],
            )

    all_hits.sort(key=lambda h: h.get("distance", float("inf")))
    capped = all_hits[: req.top_k]
    return SearchResponse(
        query=req.query,
        total=len(capped),
        hits=[SearchHit(**h) for h in capped],
    )


@router.post(
    "",
    response_model=SearchResponse,
    summary="Unified semantic search (experimental)",
)
async def post_search(req: SearchRequest) -> SearchResponse:
    return await unified_search(req)


# ---------------------------------------------------------------------------
# Reindex (admin-only, D-15)
# ---------------------------------------------------------------------------


@router.post(
    "/reindex",
    response_model=ReindexResponse,
    summary="Re-embed unindexed entities (admin-only, experimental)",
)
async def reindex_embeddings(
    req: ReindexRequest,
    admin: CurrentAdmin,
) -> ReindexResponse:
    """Re-embed rows whose embedding_status is NULL / 'failed' / 'pending'.

    Admin-only per D-15. Scope can be narrowed via `entity_type` and `since`.
    """
    if req.entity_type is not None and req.entity_type not in ENTITY_TYPES:
        raise HTTPException(
            status_code=400,
            detail=(
                f"invalid-entity-type: Unknown entity_type '{req.entity_type}'. "
                f"Valid: {ENTITY_TYPES}"
            ),
        )

    backend = get_embedding_service()
    if backend is None:
        raise HTTPException(
            status_code=503,
            detail="embedding-unavailable: No embedding backend is configured; cannot re-index.",
        )

    svc = VectorSearchService(get_database())
    types = [req.entity_type] if req.entity_type else list(ENTITY_TYPES)

    reindexed = 0
    failed = 0
    skipped = 0
    by_type: Dict[str, int] = {t: 0 for t in ENTITY_TYPES}

    for t in types:
        try:
            rows = svc.list_unindexed(entity_type=t, since=req.since)
        except TypeError:
            # Plan 02's list_unindexed only accepts (entity_type, limit). Fall
            # back gracefully so we still re-embed everything when no `since`
            # filter was requested.
            rows = svc.list_unindexed(t)

        if not rows:
            continue

        contents = [r.get("content") or "" for r in rows]
        try:
            vectors = await backend.embed(contents)
        except Exception as e:
            logger.error(
                "reindex_batch_embed_failed",
                entity_type=t,
                error=str(e)[:500],
            )
            failed += len(rows)
            continue

        for row, vec in zip(rows, vectors):
            try:
                svc.write_embedding(t, row["id"], vec, getattr(backend, "model_name", "unknown"))
                reindexed += 1
                by_type[t] = by_type.get(t, 0) + 1
            except Exception as e:
                logger.warning(
                    "reindex_write_failed",
                    entity_type=t,
                    id=row.get("id"),
                    error=str(e)[:500],
                )
                failed += 1

    logger.info(
        "reindex_complete",
        admin_id=getattr(admin, "agent_id", None),
        reindexed=reindexed,
        failed=failed,
        skipped=skipped,
    )
    return ReindexResponse(
        reindexed=reindexed,
        failed=failed,
        skipped=skipped,
        by_type=ReindexByType(**{k: by_type.get(k, 0) for k in ENTITY_TYPES}),
    )


# ---------------------------------------------------------------------------
# Delete embedding (admin-only)
# ---------------------------------------------------------------------------


@router.delete(
    "/{entity_type}/{entity_id}",
    response_model=DeleteEmbeddingResponse,
    summary="Clear embedding for a specific entity (admin-only, experimental)",
)
async def delete_embedding(
    admin: CurrentAdmin,
    entity_type: str = Path(...),
    entity_id: str = Path(...),
) -> DeleteEmbeddingResponse:
    """Set embedding=NULL and embedding_status='deleted' for a single row.

    The underlying entity row is NOT deleted - only its vector. Use the
    entity's own DELETE endpoint to remove the row itself.
    """
    if entity_type not in ENTITY_TYPES:
        raise HTTPException(
            status_code=400,
            detail=(
                f"invalid-entity-type: Unknown entity_type '{entity_type}'. "
                f"Valid: {ENTITY_TYPES}"
            ),
        )

    svc = VectorSearchService(get_database())
    try:
        updated = svc.clear_embedding(entity_type, entity_id)
    except Exception as e:
        logger.error(
            "delete_embedding_failed",
            entity_type=entity_type,
            id=entity_id,
            error=str(e)[:500],
        )
        raise HTTPException(
            status_code=503,
            detail="vector-store-unavailable: Could not clear embedding; Turso may be unreachable.",
        )

    if not updated:
        raise HTTPException(
            status_code=404,
            detail=f"entity-not-found: No {entity_type} row with id '{entity_id}'.",
        )

    logger.info(
        "embedding_cleared",
        admin_id=getattr(admin, "agent_id", None),
        entity_type=entity_type,
        id=entity_id,
    )
    return DeleteEmbeddingResponse(
        entity_type=entity_type,
        id=entity_id,
        status="deleted",
    )
