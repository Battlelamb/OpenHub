"""Auto-indexing helpers for write-path hooks (Plan 04).

This module exposes two things:

* ``schedule_embedding(background_tasks, entity_type, entity_id, text)`` - the
  fire-and-forget helper used by the 4 content-producing route handlers
  (memory, tasks, artifacts, messages). It short-circuits cleanly on local
  SQLite via ``is_vector_enabled`` so write paths stay free of background
  overhead until Turso is configured.

* ``_embed_and_store`` - the coroutine that the BackgroundTasks runner invokes.
  This coroutine MUST NEVER raise. FastAPI's BackgroundTasks swallow
  exceptions silently (Pitfall 6 in 03-RESEARCH.md), so any uncaught error
  would leave a row stuck in 'pending' forever with no operator signal. Every
  failure path here logs the error and calls ``mark_failed`` on the
  VectorSearchService so the retry worker (Plan 04 Task 2) can find it later.
"""
from typing import Optional

import structlog
from fastapi import BackgroundTasks

from ..database.connection import get_database
from ..database.vector_availability import is_vector_enabled
from ..services.embedding_service import get_embedding_service
from ..services.vector_search_service import ENTITY_CONFIG, VectorSearchService

logger = structlog.get_logger(__name__)

# Cheap defensive truncation. Mirrors the OpenAI backend cap so retry logic and
# auto-indexing always see the same upper bound on per-row text size.
_MAX_TEXT_CHARS = 30000


async def _embed_and_store(
    entity_type: str,
    entity_id: str,
    text: str,
    trace_id: str,
) -> None:
    """Embed ``text`` and persist the vector. Never raises.

    On any failure path, attempts to mark the row as ``failed`` so the retry
    worker can pick it up later. Even the mark_failed call is wrapped in a
    try/except so a transient DB hiccup cannot escape into the BackgroundTasks
    runner.
    """
    log = logger.bind(
        trace_id=trace_id, entity_type=entity_type, entity_id=entity_id
    )
    if not text or not text.strip():
        log.debug("embedding_skipped_empty_text")
        return

    db = get_database()
    svc = VectorSearchService(db)
    backend = get_embedding_service()
    if backend is None:
        log.warning("embedding_skipped_no_backend")
        try:
            svc.mark_failed(entity_type, entity_id, "no embedding backend configured")
        except Exception as inner:  # pragma: no cover - defensive
            log.error("embedding_mark_failed_errored", error=str(inner)[:500])
        return

    try:
        truncated = text[:_MAX_TEXT_CHARS]
        vectors = await backend.embed([truncated])
        if not vectors:
            svc.mark_failed(entity_type, entity_id, "backend returned empty result")
            return
        svc.write_embedding(entity_type, entity_id, vectors[0], backend.model_name)
        log.info("embedding_stored", dim=len(vectors[0]), model=backend.model_name)
    except Exception as e:
        log.error("embedding_failed", error=str(e)[:500])
        try:
            svc.mark_failed(entity_type, entity_id, str(e))
        except Exception as inner:  # pragma: no cover - defensive
            log.error("embedding_mark_failed_errored", error=str(inner)[:500])


def schedule_embedding(
    background_tasks: BackgroundTasks,
    entity_type: str,
    entity_id: str,
    text: Optional[str],
) -> None:
    """Schedule a background embedding job. Safe to call unconditionally.

    Short-circuits when:
      * vector search is disabled (``is_vector_enabled() is False``)
      * ``entity_type`` is not one of the four known indexable types
      * ``text`` is empty / None

    Any structlog ``trace_id`` bound on the current contextvars is propagated
    into the background task so the embedding log line can be correlated with
    the originating request.
    """
    if not is_vector_enabled():
        return
    if entity_type not in ENTITY_CONFIG:
        logger.warning("schedule_embedding_unknown_type", entity_type=entity_type)
        return
    if not text:
        return

    trace_id = ""
    try:
        trace_id = structlog.contextvars.get_contextvars().get("trace_id", "") or ""
    except Exception:
        pass

    background_tasks.add_task(
        _embed_and_store, entity_type, entity_id, text, trace_id
    )


__all__ = ["schedule_embedding", "_embed_and_store"]
