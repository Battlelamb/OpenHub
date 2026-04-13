"""Unit tests for the embedding retry worker (Plan 04 Task 2)."""
import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.fixture()
def patched_db(monkeypatch):
    from app.services import embedding_retry_worker

    fake_db = MagicMock(name="fake_db")
    monkeypatch.setattr(embedding_retry_worker, "get_database", lambda: fake_db)
    return fake_db


@pytest.fixture()
def patched_service(monkeypatch):
    from app.services import embedding_retry_worker

    svc = MagicMock(name="VectorSearchService")
    svc.list_unindexed = MagicMock(return_value=[])
    svc.write_embedding = MagicMock()
    svc.mark_failed = MagicMock()
    monkeypatch.setattr(
        embedding_retry_worker, "VectorSearchService", MagicMock(return_value=svc)
    )
    return svc


@pytest.mark.asyncio
async def test_worker_skips_when_vector_disabled(monkeypatch):
    from app.services import embedding_retry_worker

    monkeypatch.setattr(embedding_retry_worker, "is_vector_enabled", lambda: False)
    embedding_retry_worker._worker_task = None
    await embedding_retry_worker.start_retry_worker()
    assert embedding_retry_worker._worker_task is None


@pytest.mark.asyncio
async def test_run_once_returns_zero_when_vector_disabled(monkeypatch):
    from app.services import embedding_retry_worker

    monkeypatch.setattr(embedding_retry_worker, "is_vector_enabled", lambda: False)
    result = await embedding_retry_worker._run_once()
    assert result == 0


@pytest.mark.asyncio
async def test_run_once_returns_zero_when_no_backend(monkeypatch, patched_db, patched_service):
    from app.services import embedding_retry_worker

    monkeypatch.setattr(embedding_retry_worker, "is_vector_enabled", lambda: True)
    monkeypatch.setattr(embedding_retry_worker, "get_embedding_service", lambda: None)
    result = await embedding_retry_worker._run_once()
    assert result == 0


@pytest.mark.asyncio
async def test_run_once_processes_rows(monkeypatch, patched_db, patched_service):
    from app.services import embedding_retry_worker

    monkeypatch.setattr(embedding_retry_worker, "is_vector_enabled", lambda: True)
    backend = MagicMock()
    backend.model_name = "mock"
    backend.embed = AsyncMock(return_value=[[0.1] * 384])
    monkeypatch.setattr(embedding_retry_worker, "get_embedding_service", lambda: backend)

    # Return rows for "memory" only, empty for the others
    def list_unindexed(entity_type, limit=50):
        if entity_type == "memory":
            return [{"id": "1", "content": "hi"}, {"id": "2", "content": "hey"}]
        return []

    patched_service.list_unindexed.side_effect = list_unindexed
    result = await embedding_retry_worker._run_once()
    assert result == 2
    assert patched_service.write_embedding.call_count == 2


@pytest.mark.asyncio
async def test_run_once_iterates_all_entity_types(monkeypatch, patched_db, patched_service):
    from app.services import embedding_retry_worker

    monkeypatch.setattr(embedding_retry_worker, "is_vector_enabled", lambda: True)
    backend = MagicMock()
    backend.model_name = "mock"
    backend.embed = AsyncMock(return_value=[[0.0] * 384])
    monkeypatch.setattr(embedding_retry_worker, "get_embedding_service", lambda: backend)

    patched_service.list_unindexed.side_effect = lambda et, limit=50: [
        {"id": f"{et}-1", "content": "x"}
    ]
    result = await embedding_retry_worker._run_once()
    assert result == 4
    assert patched_service.write_embedding.call_count == 4
    types_processed = {
        c.args[0] for c in patched_service.write_embedding.call_args_list
    }
    assert types_processed == {"memory", "task", "artifact", "message"}


@pytest.mark.asyncio
async def test_run_once_handles_item_failure(monkeypatch, patched_db, patched_service):
    from app.services import embedding_retry_worker

    monkeypatch.setattr(embedding_retry_worker, "is_vector_enabled", lambda: True)
    call_count = {"n": 0}

    async def flaky_embed(texts):
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise RuntimeError("boom")
        return [[0.0] * 384]

    backend = MagicMock()
    backend.model_name = "mock"
    backend.embed = flaky_embed
    monkeypatch.setattr(embedding_retry_worker, "get_embedding_service", lambda: backend)

    def list_unindexed(et, limit=50):
        if et == "memory":
            return [{"id": "1", "content": "first"}, {"id": "2", "content": "second"}]
        return []

    patched_service.list_unindexed.side_effect = list_unindexed
    result = await embedding_retry_worker._run_once()
    assert result == 1  # second succeeded
    patched_service.mark_failed.assert_called()


@pytest.mark.asyncio
async def test_run_once_skips_empty_content(monkeypatch, patched_db, patched_service):
    from app.services import embedding_retry_worker

    monkeypatch.setattr(embedding_retry_worker, "is_vector_enabled", lambda: True)
    backend = MagicMock()
    backend.model_name = "mock"
    backend.embed = AsyncMock(return_value=[[0.0] * 384])
    monkeypatch.setattr(embedding_retry_worker, "get_embedding_service", lambda: backend)
    patched_service.list_unindexed.side_effect = lambda et, limit=50: (
        [{"id": "1", "content": "  "}] if et == "memory" else []
    )
    result = await embedding_retry_worker._run_once()
    assert result == 0
    patched_service.mark_failed.assert_called()


@pytest.mark.asyncio
async def test_stop_cancels_running_task(monkeypatch, patched_db, patched_service):
    from app.services import embedding_retry_worker

    monkeypatch.setattr(embedding_retry_worker, "is_vector_enabled", lambda: True)
    backend = MagicMock()
    backend.model_name = "mock"
    backend.embed = AsyncMock(return_value=[[0.0] * 384])
    monkeypatch.setattr(embedding_retry_worker, "get_embedding_service", lambda: backend)
    patched_service.list_unindexed.return_value = []

    embedding_retry_worker._worker_task = None
    await embedding_retry_worker.start_retry_worker(interval=10)
    assert embedding_retry_worker._worker_task is not None
    # Yield once so the loop body runs
    await asyncio.sleep(0)
    await embedding_retry_worker.stop_retry_worker()
    assert embedding_retry_worker._worker_task is None
