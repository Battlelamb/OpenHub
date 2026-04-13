"""Background worker that re-processes failed or pending embeddings.

Started in app lifespan when vector search is enabled. Polls
``VectorSearchService.list_unindexed`` for each entity type every
``RETRY_INTERVAL_SECONDS`` (default 300 / 5 minutes per D-13) and re-embeds
any rows whose ``embedding_status`` is NULL or ``failed``.

The worker is a no-op on local SQLite: ``start_retry_worker`` short-circuits
on ``is_vector_enabled() is False`` so dev environments never pay the polling
cost.

The single inner iteration (``_run_once``) is exposed for unit tests so we can
verify per-entity behaviour without spinning up the full sleeper loop.
"""
from __future__ import annotations

import asyncio
from typing import Optional

import structlog

from ..database.connection import get_database
from ..database.vector_availability import is_vector_enabled
from ..services.embedding_service import get_embedding_service
from ..services.vector_search_service import ENTITY_CONFIG, VectorSearchService

logger = structlog.get_logger(__name__)

RETRY_INTERVAL_SECONDS = 300  # 5 minutes per D-13
BATCH_LIMIT = 50
_MAX_TEXT_CHARS = 30000

_worker_task: Optional[asyncio.Task] = None


async def _run_once() -> int:
    """Process one pass of all entity types. Returns rows successfully embedded."""
    if not is_vector_enabled():
        return 0
    backend = get_embedding_service()
    if backend is None:
        logger.debug("retry_worker_no_backend")
        return 0

    db = get_database()
    svc = VectorSearchService(db)
    processed = 0

    for entity_type in ENTITY_CONFIG.keys():
        try:
            rows = svc.list_unindexed(entity_type, limit=BATCH_LIMIT)
        except Exception as e:
            logger.error(
                "retry_worker_list_failed",
                entity_type=entity_type,
                error=str(e)[:500],
            )
            continue

        for row in rows or []:
            row_id = row.get("id") if isinstance(row, dict) else None
            try:
                text = (row.get("content") or "") if isinstance(row, dict) else ""
                text = text[:_MAX_TEXT_CHARS]
                if not text.strip():
                    try:
                        svc.mark_failed(entity_type, row_id, "empty content")
                    except Exception:  # pragma: no cover - defensive
                        pass
                    continue
                vectors = await backend.embed([text])
                if not vectors:
                    svc.mark_failed(entity_type, row_id, "backend returned empty result")
                    continue
                svc.write_embedding(
                    entity_type, row_id, vectors[0], backend.model_name
                )
                processed += 1
                logger.info(
                    "retry_worker_embedded",
                    entity_type=entity_type,
                    entity_id=row_id,
                )
            except Exception as e:
                logger.warning(
                    "retry_worker_item_failed",
                    entity_type=entity_type,
                    entity_id=row_id,
                    error=str(e)[:500],
                )
                try:
                    svc.mark_failed(entity_type, row_id, str(e))
                except Exception:  # pragma: no cover - defensive
                    pass
    return processed


async def _loop(interval: int = RETRY_INTERVAL_SECONDS) -> None:
    logger.info("embedding_retry_worker_started", interval=interval)
    try:
        while True:
            try:
                await _run_once()
            except Exception as e:
                logger.error("retry_worker_iteration_failed", error=str(e)[:500])
            await asyncio.sleep(interval)
    except asyncio.CancelledError:
        logger.info("embedding_retry_worker_stopped")
        raise


async def start_retry_worker(interval: int = RETRY_INTERVAL_SECONDS) -> None:
    """Start the retry worker as a background asyncio task. No-op if disabled."""
    global _worker_task
    if not is_vector_enabled():
        logger.info("embedding_retry_worker_skipped_vector_disabled")
        return
    if _worker_task is not None and not _worker_task.done():
        logger.warning("embedding_retry_worker_already_running")
        return
    _worker_task = asyncio.create_task(_loop(interval))


async def stop_retry_worker() -> None:
    """Cancel the worker task and clear the module-level handle."""
    global _worker_task
    if _worker_task is None:
        return
    _worker_task.cancel()
    try:
        await _worker_task
    except asyncio.CancelledError:
        pass
    except Exception as e:  # pragma: no cover - defensive
        logger.warning("embedding_retry_worker_stop_errored", error=str(e)[:500])
    _worker_task = None


__all__ = [
    "RETRY_INTERVAL_SECONDS",
    "BATCH_LIMIT",
    "start_retry_worker",
    "stop_retry_worker",
    "_run_once",
]
