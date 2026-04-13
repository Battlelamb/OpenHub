"""Integration tests for VectorSearchService against a real Turso database.

Marked turso so they skip on local dev without credentials. The session-scoped
turso_db fixture is re-used by tests/integration/test_vector_storage.py.

Tests cover:
    - write_embedding roundtrip (status flips to 'ok', model recorded)
    - search_entity returns nearest neighbor first (cosine distance ordering)
    - search_entity filters out rows with embedding_status != 'ok'
    - mark_failed sets status='failed' and records the error
    - search_entity respects top_k limit
"""
import os

import pytest

from app.database.connection import close_database, get_database
from app.services.vector_search_service import VectorSearchService


pytestmark = pytest.mark.turso


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def turso_db():
    """Session-scoped Turso DB handle.

    Reads TURSO_DATABASE_URL / TURSO_AUTH_TOKEN from the environment via
    Settings (already wired into app.database.connection.Database). Tests are
    auto-skipped when these are absent (see tests/conftest.py).
    """
    if not (os.environ.get("TURSO_DATABASE_URL") and os.environ.get("TURSO_AUTH_TOKEN")):
        pytest.skip("Turso credentials not set")

    # Mirror env -> AGENTHUB_ prefix so Settings picks it up.
    os.environ.setdefault("AGENTHUB_TURSO_DATABASE_URL", os.environ["TURSO_DATABASE_URL"])
    os.environ.setdefault("AGENTHUB_TURSO_AUTH_TOKEN", os.environ["TURSO_AUTH_TOKEN"])

    # Reset cached singletons so the new env vars are honoured.
    close_database()
    import app.config as _config
    _config.settings = _config.Settings()

    db = get_database()
    if not getattr(db, "_use_turso", False):
        pytest.skip("Database did not activate Turso mode")
    yield db
    close_database()


@pytest.fixture()
def clean_memory_rows(turso_db):
    """Delete all __vector_test_ shared_memory rows before and after each test."""
    def _cleanup():
        try:
            turso_db.execute(
                "DELETE FROM shared_memory WHERE id LIKE '__vector_test_%'",
            )
        except Exception:
            pass

    _cleanup()
    yield
    _cleanup()


def _make_vec(index: int, dim: int = 384) -> list:
    """Build a deterministic unit vector with a single 1.0 at position `index`."""
    v = [0.0] * dim
    v[index % dim] = 1.0
    return v


def _insert_memory(db, row_id: str, value: str = "test content") -> None:
    db.execute(
        "INSERT INTO shared_memory (id, key, value, created_at) "
        "VALUES (:id, :k, :v, CURRENT_TIMESTAMP)",
        {"id": row_id, "k": row_id, "v": value},
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_write_embedding_roundtrip(turso_db, clean_memory_rows):
    svc = VectorSearchService(turso_db)
    row_id = "__vector_test_roundtrip"
    _insert_memory(turso_db, row_id, "roundtrip content")

    svc.write_embedding("memory", row_id, _make_vec(0), "test-model")

    row = turso_db.fetch_one(
        "SELECT embedding_status, embedding_model FROM shared_memory WHERE id = :id",
        {"id": row_id},
    )
    assert row is not None
    assert row["embedding_status"] == "ok"
    assert row["embedding_model"] == "test-model"


def test_search_entity_returns_nearest(turso_db, clean_memory_rows):
    svc = VectorSearchService(turso_db)
    rows = [
        ("__vector_test_a", _make_vec(0), "row a"),
        ("__vector_test_b", _make_vec(1), "row b"),
        ("__vector_test_c", _make_vec(2), "row c"),
    ]
    for rid, vec, content in rows:
        _insert_memory(turso_db, rid, content)
        svc.write_embedding("memory", rid, vec, "test-model")

    # Query close to row b (axis 1)
    results = svc.search_entity("memory", _make_vec(1), top_k=3)
    assert len(results) >= 1
    assert results[0]["id"] == "__vector_test_b"
    # Results sorted by distance ascending
    distances = [r["distance"] for r in results]
    assert distances == sorted(distances)


def test_search_entity_filters_by_status(turso_db, clean_memory_rows):
    svc = VectorSearchService(turso_db)

    _insert_memory(turso_db, "__vector_test_ok", "ok row")
    svc.write_embedding("memory", "__vector_test_ok", _make_vec(5), "test-model")

    _insert_memory(turso_db, "__vector_test_pending", "pending row")
    svc.write_embedding("memory", "__vector_test_pending", _make_vec(5), "test-model")
    svc.mark_pending("memory", "__vector_test_pending")

    results = svc.search_entity("memory", _make_vec(5), top_k=10)
    ids = [r["id"] for r in results]
    assert "__vector_test_ok" in ids
    assert "__vector_test_pending" not in ids


def test_mark_failed_sets_status(turso_db, clean_memory_rows):
    svc = VectorSearchService(turso_db)
    _insert_memory(turso_db, "__vector_test_failed", "to fail")
    svc.mark_failed("memory", "__vector_test_failed", "boom: provider down")

    row = turso_db.fetch_one(
        "SELECT embedding_status, embedding_error FROM shared_memory WHERE id = :id",
        {"id": "__vector_test_failed"},
    )
    assert row is not None
    assert row["embedding_status"] == "failed"
    assert row["embedding_error"] is not None
    assert "boom" in row["embedding_error"]


def test_search_entity_respects_top_k(turso_db, clean_memory_rows):
    svc = VectorSearchService(turso_db)
    for i in range(5):
        rid = f"__vector_test_k{i}"
        _insert_memory(turso_db, rid, f"row {i}")
        svc.write_embedding("memory", rid, _make_vec(i), "test-model")

    results = svc.search_entity("memory", _make_vec(0), top_k=2)
    assert len(results) == 2


def test_end_to_end_search(turso_db, clean_memory_rows, monkeypatch):
    """Plan 05 / VEC-05: POST /v1/search end-to-end against a real Turso DB.

    Seeds 3 memory rows with orthogonal vectors, monkeypatches the embedding
    backend so the query vector points at row b, then asserts the public API
    returns row b first and distances are sorted ascending. Uses a mock
    backend so the real sentence-transformers download is not required.
    """
    from unittest.mock import AsyncMock, MagicMock

    from fastapi.testclient import TestClient

    from app.api import routes_search
    from app.database import vector_availability as va
    from app.main import app as real_app

    svc = VectorSearchService(turso_db)
    rows = [
        ("__vector_test_e2e_a", _make_vec(0), "row alpha"),
        ("__vector_test_e2e_b", _make_vec(1), "row bravo"),
        ("__vector_test_e2e_c", _make_vec(2), "row charlie"),
    ]
    for rid, vec, content in rows:
        _insert_memory(turso_db, rid, content)
        svc.write_embedding("memory", rid, vec, "test-model")

    fake_backend = MagicMock(name="fake_backend")
    fake_backend.dim = 384
    fake_backend.model_name = "mock"
    # Return the same vector as row b so cosine distance to b is ~0.
    fake_backend.embed = AsyncMock(return_value=[_make_vec(1)])

    monkeypatch.setattr(routes_search, "get_embedding_service", lambda: fake_backend)
    monkeypatch.setattr(va, "is_vector_enabled", lambda: True)

    with TestClient(real_app, raise_server_exceptions=False) as client:
        response = client.post(
            "/v1/search",
            json={"query": "find bravo", "types": ["memory"], "top_k": 3},
        )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["total"] >= 1
    hits = body["hits"]
    assert hits[0]["id"] == "__vector_test_e2e_b"
    distances = [h["distance"] for h in hits]
    assert distances == sorted(distances)
