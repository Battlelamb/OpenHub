"""Unit tests for the auto-indexing hook helper (Plan 04).

Covers schedule_embedding short-circuiting on local SQLite and the
_embed_and_store coroutine's never-raises contract (Pitfall 6).
"""
from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.fixture()
def patched_db(monkeypatch):
    """Patch get_database in the embedding_hooks module to return a MagicMock."""
    from app.services import embedding_hooks

    fake_db = MagicMock(name="fake_db")
    monkeypatch.setattr(embedding_hooks, "get_database", lambda: fake_db)
    return fake_db


@pytest.fixture()
def patched_service(monkeypatch):
    """Patch VectorSearchService used by embedding_hooks to a MagicMock instance."""
    from app.services import embedding_hooks

    svc = MagicMock(name="VectorSearchService")
    svc_factory = MagicMock(return_value=svc)
    monkeypatch.setattr(embedding_hooks, "VectorSearchService", svc_factory)
    return svc


def test_schedule_embedding_noop_when_disabled(monkeypatch):
    from app.services import embedding_hooks

    monkeypatch.setattr(embedding_hooks, "is_vector_enabled", lambda: False)
    bg = MagicMock()
    embedding_hooks.schedule_embedding(bg, "memory", "id-1", "hello")
    bg.add_task.assert_not_called()


def test_schedule_embedding_adds_task(monkeypatch):
    from app.services import embedding_hooks

    monkeypatch.setattr(embedding_hooks, "is_vector_enabled", lambda: True)
    bg = MagicMock()
    embedding_hooks.schedule_embedding(bg, "memory", "id-1", "hello")
    assert bg.add_task.call_count == 1
    args, _ = bg.add_task.call_args
    assert args[0] is embedding_hooks._embed_and_store
    assert args[1] == "memory"
    assert args[2] == "id-1"
    assert args[3] == "hello"


def test_schedule_embedding_skips_unknown_entity_type(monkeypatch):
    from app.services import embedding_hooks

    monkeypatch.setattr(embedding_hooks, "is_vector_enabled", lambda: True)
    bg = MagicMock()
    embedding_hooks.schedule_embedding(bg, "bogus", "id-1", "hello")
    bg.add_task.assert_not_called()


def test_schedule_embedding_skips_empty_text(monkeypatch):
    from app.services import embedding_hooks

    monkeypatch.setattr(embedding_hooks, "is_vector_enabled", lambda: True)
    bg = MagicMock()
    embedding_hooks.schedule_embedding(bg, "memory", "id-1", "")
    embedding_hooks.schedule_embedding(bg, "memory", "id-1", None)
    bg.add_task.assert_not_called()


@pytest.mark.asyncio
async def test_embed_and_store_handles_none_backend(monkeypatch, patched_db, patched_service):
    from app.services import embedding_hooks

    monkeypatch.setattr(embedding_hooks, "get_embedding_service", lambda: None)
    # Must not raise
    await embedding_hooks._embed_and_store("memory", "id-1", "hello", "trace-1")
    patched_service.mark_failed.assert_called_once()
    args, _ = patched_service.mark_failed.call_args
    assert args[0] == "memory"
    assert args[1] == "id-1"
    assert "no embedding backend" in args[2].lower()


@pytest.mark.asyncio
async def test_embed_and_store_handles_backend_exception(monkeypatch, patched_db, patched_service):
    from app.services import embedding_hooks

    backend = MagicMock()
    backend.model_name = "mock"
    backend.embed = AsyncMock(side_effect=RuntimeError("boom"))
    monkeypatch.setattr(embedding_hooks, "get_embedding_service", lambda: backend)
    await embedding_hooks._embed_and_store("memory", "id-1", "hello", "trace-1")
    patched_service.mark_failed.assert_called_once()
    args, _ = patched_service.mark_failed.call_args
    assert args[2] == "boom"


@pytest.mark.asyncio
async def test_embed_and_store_writes_embedding_on_success(monkeypatch, patched_db, patched_service):
    from app.services import embedding_hooks

    backend = MagicMock()
    backend.model_name = "mock"
    backend.embed = AsyncMock(return_value=[[0.1] * 768])
    monkeypatch.setattr(embedding_hooks, "get_embedding_service", lambda: backend)
    await embedding_hooks._embed_and_store("memory", "id-1", "hello", "trace-1")
    patched_service.write_embedding.assert_called_once()
    args, _ = patched_service.write_embedding.call_args
    assert args[0] == "memory"
    assert args[1] == "id-1"
    assert len(args[2]) == 768
    assert args[3] == "mock"
    patched_service.mark_failed.assert_not_called()


@pytest.mark.asyncio
async def test_embed_and_store_truncates_long_text(monkeypatch, patched_db, patched_service):
    from app.services import embedding_hooks

    backend = MagicMock()
    backend.model_name = "mock"
    backend.embed = AsyncMock(return_value=[[0.0] * 768])
    monkeypatch.setattr(embedding_hooks, "get_embedding_service", lambda: backend)
    long_text = "x" * 60000
    await embedding_hooks._embed_and_store("memory", "id-1", long_text, "trace-1")
    args, _ = backend.embed.call_args
    assert len(args[0][0]) == 30000


@pytest.mark.asyncio
async def test_embed_and_store_skips_empty_text(monkeypatch, patched_db, patched_service):
    from app.services import embedding_hooks

    backend = MagicMock()
    backend.model_name = "mock"
    backend.embed = AsyncMock(return_value=[])
    monkeypatch.setattr(embedding_hooks, "get_embedding_service", lambda: backend)
    await embedding_hooks._embed_and_store("memory", "id-1", "   ", "trace-1")
    backend.embed.assert_not_called()
    patched_service.mark_failed.assert_not_called()


@pytest.mark.asyncio
async def test_embed_and_store_marks_failed_on_empty_result(monkeypatch, patched_db, patched_service):
    from app.services import embedding_hooks

    backend = MagicMock()
    backend.model_name = "mock"
    backend.embed = AsyncMock(return_value=[])
    monkeypatch.setattr(embedding_hooks, "get_embedding_service", lambda: backend)
    await embedding_hooks._embed_and_store("memory", "id-1", "hello", "trace-1")
    patched_service.mark_failed.assert_called_once()
