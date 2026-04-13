"""Integration tests for the Phase 03 vector search API (VEC-05 / Plan 05).

Covers:
  * Plan 01 carry-over: 503-on-local + explicit feature-flag-off via a tiny
    inline FastAPI app that mounts only require_vector. These were the only
    tests that could pass before the real /v1/search route existed.
  * Plan 05 Task 1: unified /v1/search contract, top_k bounds, query bounds,
    cross-entity merge, OpenAPI experimental tag.
  * Plan 05 Task 2: per-entity shortcut delegation forces single-type search.
  * Plan 05 Task 3: admin-only POST /v1/search/reindex + DELETE
    /v1/search/{entity_type}/{id} with admin gating, RFC 7807 errors, and the
    invariant that delete clears the embedding column without removing the row.

All tests run on local SQLite by monkeypatching is_vector_enabled to True and
injecting fake embedding/vector services - no Turso credentials required.
"""
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.database import vector_availability
from app.database.vector_availability import require_vector
from app.auth.jwt_auth import create_access_token


# ---------------------------------------------------------------------------
# Plan 01 carry-over: tiny inline app proves require_vector dependency works
# ---------------------------------------------------------------------------


def _build_test_app() -> FastAPI:
    """Mount a tiny app with one route guarded by require_vector()."""
    app = FastAPI()

    @app.get("/v1/search")
    def search(_=Depends(require_vector)):
        return {"hits": []}

    return app


class _FakeDb:
    def __init__(self, use_turso: bool):
        self._use_turso = use_turso


class _FakeSettings:
    def __init__(self, vector_search_enabled):
        self.vector_search_enabled = vector_search_enabled


def test_503_local(monkeypatch):
    """On local SQLite (no Turso), the search endpoint returns 503."""
    monkeypatch.setattr(
        vector_availability, "get_database", lambda: _FakeDb(use_turso=False)
    )
    monkeypatch.setattr(
        vector_availability,
        "get_settings",
        lambda: _FakeSettings(vector_search_enabled=None),
    )
    client = TestClient(_build_test_app(), raise_server_exceptions=False)
    response = client.get("/v1/search")
    assert response.status_code == 503
    body = response.json()
    inner = body.get("detail", body)
    assert "vector search requires Turso".lower() in str(inner).lower()


def test_flag_off(monkeypatch):
    """Explicit AGENTHUB_VECTOR_SEARCH_ENABLED=false disables even on Turso."""
    monkeypatch.setattr(
        vector_availability, "get_database", lambda: _FakeDb(use_turso=True)
    )
    monkeypatch.setattr(
        vector_availability,
        "get_settings",
        lambda: _FakeSettings(vector_search_enabled=False),
    )
    client = TestClient(_build_test_app(), raise_server_exceptions=False)
    response = client.get("/v1/search")
    assert response.status_code == 503


# ---------------------------------------------------------------------------
# Real app fixtures (used by Plan 05 Task 1 / 2 / 3 tests)
# ---------------------------------------------------------------------------


@pytest.fixture()
def real_client():
    """Standalone TestClient over the real app for vector search tests."""
    from app.main import app as real_app

    with TestClient(real_app, raise_server_exceptions=False) as client:
        yield client


@pytest.fixture()
def enable_vector(monkeypatch):
    """Force is_vector_enabled() to return True for require_vector's dep call.

    require_vector() is captured by FastAPI as the Depends callable at router
    creation time, so patching routes_search.require_vector itself is too late.
    Instead we patch the predicate it calls (is_vector_enabled in
    app.database.vector_availability), which is resolved at request time.
    """
    from app.database import vector_availability as va

    monkeypatch.setattr(va, "is_vector_enabled", lambda: True)
    return True


@pytest.fixture()
def mock_backend(monkeypatch):
    """Inject a fake embedding backend into routes_search.get_embedding_service."""
    from app.api import routes_search

    backend = MagicMock(name="fake_backend")
    backend.model_name = "mock"
    backend.dim=768
    backend.embed = AsyncMock(return_value=[[0.0] * 768])
    monkeypatch.setattr(routes_search, "get_embedding_service", lambda: backend)
    return backend


@pytest.fixture()
def mock_vector_service(monkeypatch):
    """Replace VectorSearchService with a MagicMock instance.

    The replacement is a callable returning a single shared MagicMock so tests
    can inspect call args after the route runs.
    """
    from app.api import routes_search

    svc = MagicMock(name="VectorSearchService")
    svc.search_entity = MagicMock(return_value=[])
    svc.list_unindexed = MagicMock(return_value=[])
    svc.write_embedding = MagicMock(return_value=None)
    svc.clear_embedding = MagicMock(return_value=True)
    monkeypatch.setattr(
        routes_search, "VectorSearchService", MagicMock(return_value=svc)
    )
    return svc


@pytest.fixture()
def admin_token():
    return create_access_token(
        subject="test-admin-search",
        claims={"role": "admin", "agent_name": "test-admin-search"},
    )


@pytest.fixture()
def viewer_token():
    return create_access_token(
        subject="test-viewer-search",
        claims={"role": "viewer", "agent_name": "test-viewer-search"},
    )


@pytest.fixture()
def seeded_admin_search_agents():
    """Seed the admin and viewer agent rows used by reindex/delete admin tests."""
    import json as _json
    from datetime import datetime, timezone

    from app.database.connection import get_database

    db = get_database()
    now = datetime.now(timezone.utc).isoformat()
    for agent_id, name in (
        ("test-admin-search", "test-admin-search"),
        ("test-viewer-search", "test-viewer-search"),
    ):
        existing = db.fetch_one(
            "SELECT id FROM agents WHERE id = :id", {"id": agent_id}
        )
        if existing:
            continue
        db.execute(
            """INSERT INTO agents (
                   id, agent_name, description, capabilities, status,
                   labels, created_at, updated_at, last_heartbeat
               ) VALUES (
                   :id, :name, :desc, :caps, 'online',
                   :labels, :now, :now, :now
               )""",
            {
                "id": agent_id,
                "name": name,
                "desc": "search admin test agent",
                "caps": _json.dumps([]),
                "labels": _json.dumps({}),
                "now": now,
            },
        )
    return True


# ---------------------------------------------------------------------------
# Task 1: Unified /v1/search contract
# ---------------------------------------------------------------------------


def test_top_k_cap(real_client, enable_vector, mock_backend, mock_vector_service):
    r = real_client.post(
        "/v1/search", json={"query": "x", "top_k": 51}
    )
    assert r.status_code == 422


def test_top_k_zero(real_client, enable_vector, mock_backend, mock_vector_service):
    r = real_client.post("/v1/search", json={"query": "x", "top_k": 0})
    assert r.status_code == 422


def test_top_k_default(
    real_client, enable_vector, mock_backend, mock_vector_service
):
    r = real_client.post("/v1/search", json={"query": "hello"})
    assert r.status_code == 200
    body = r.json()
    assert body["query"] == "hello"
    assert body["total"] == 0
    assert body["hits"] == []


def test_unified_defaults_to_all_types(
    real_client, enable_vector, mock_backend, mock_vector_service
):
    r = real_client.post("/v1/search", json={"query": "all types"})
    assert r.status_code == 200
    types_called = [
        call.args[0] for call in mock_vector_service.search_entity.call_args_list
    ]
    assert sorted(types_called) == ["artifact", "memory", "message", "task"]


def test_unified_respects_types(
    real_client, enable_vector, mock_backend, mock_vector_service
):
    r = real_client.post(
        "/v1/search",
        json={"query": "subset", "types": ["memory", "task"]},
    )
    assert r.status_code == 200
    types_called = [
        call.args[0] for call in mock_vector_service.search_entity.call_args_list
    ]
    assert sorted(types_called) == ["memory", "task"]


def test_unified_merges_and_caps(
    real_client, enable_vector, mock_backend, mock_vector_service
):
    def _hits(entity_type, qvec, top_k=10, filters=None):
        return [
            {
                "entity_type": entity_type,
                "id": f"{entity_type}-{i}",
                "content": f"{entity_type} content {i}",
                "distance": 0.5 + (i / 100.0),
            }
            for i in range(10)
        ]

    mock_vector_service.search_entity.side_effect = _hits
    r = real_client.post("/v1/search", json={"query": "merge", "top_k": 5})
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 5
    assert len(body["hits"]) == 5
    distances = [h["distance"] for h in body["hits"]]
    assert distances == sorted(distances)


def test_search_hit_shape(
    real_client, enable_vector, mock_backend, mock_vector_service
):
    mock_vector_service.search_entity.side_effect = lambda t, qv, top_k=10, filters=None: [
        {"entity_type": t, "id": f"{t}-1", "content": "c", "distance": 0.1}
    ]
    r = real_client.post(
        "/v1/search", json={"query": "shape", "types": ["memory"], "top_k": 1}
    )
    assert r.status_code == 200
    hit = r.json()["hits"][0]
    assert set(hit.keys()) == {"entity_type", "id", "content", "distance"}


def test_empty_query_rejected(
    real_client, enable_vector, mock_backend, mock_vector_service
):
    r = real_client.post("/v1/search", json={"query": ""})
    assert r.status_code == 422


def test_long_query_rejected(
    real_client, enable_vector, mock_backend, mock_vector_service
):
    r = real_client.post("/v1/search", json={"query": "x" * 5001})
    assert r.status_code == 422


def test_invalid_entity_type_in_unified(
    real_client, enable_vector, mock_backend, mock_vector_service
):
    r = real_client.post(
        "/v1/search", json={"query": "bad", "types": ["bogus"]}
    )
    assert r.status_code == 400
    body = r.json()
    assert "Unknown entity types" in str(body)


def test_openapi_beta_tag(real_client):
    r = real_client.get("/openapi.json")
    assert r.status_code == 200
    paths = r.json()["paths"]
    assert "/v1/search" in paths
    op = paths["/v1/search"]["post"]
    tags = op.get("tags", [])
    assert any("experimental" in t for t in tags)


# ---------------------------------------------------------------------------
# Task 2: Per-entity shortcut delegation
# ---------------------------------------------------------------------------


def _shortcut_assert(client, path, expected_type, mock_vector_service):
    mock_vector_service.search_entity.reset_mock()
    r = client.post(path, json={"query": "x"})
    assert r.status_code == 200, r.text
    types_called = [
        call.args[0] for call in mock_vector_service.search_entity.call_args_list
    ]
    assert types_called == [expected_type], (
        f"Shortcut {path} should only search [{expected_type}], got {types_called}"
    )


def test_memory_shortcut_delegates(
    real_client, enable_vector, mock_backend, mock_vector_service
):
    _shortcut_assert(real_client, "/v1/memory/search", "memory", mock_vector_service)


def test_task_shortcut_delegates(
    real_client, enable_vector, mock_backend, mock_vector_service
):
    _shortcut_assert(real_client, "/v1/tasks/search", "task", mock_vector_service)


def test_artifact_shortcut_delegates(
    real_client, enable_vector, mock_backend, mock_vector_service
):
    _shortcut_assert(
        real_client, "/v1/artifacts/search", "artifact", mock_vector_service
    )


def test_message_shortcut_delegates(
    real_client, enable_vector, mock_backend, mock_vector_service
):
    _shortcut_assert(
        real_client, "/v1/messages/search", "message", mock_vector_service
    )


def test_shortcut_ignores_types_in_body(
    real_client, enable_vector, mock_backend, mock_vector_service
):
    """Client-supplied types must be overridden by the shortcut's forced type."""
    mock_vector_service.search_entity.reset_mock()
    r = real_client.post(
        "/v1/memory/search", json={"query": "x", "types": ["task"]}
    )
    assert r.status_code == 200
    types_called = [
        call.args[0] for call in mock_vector_service.search_entity.call_args_list
    ]
    assert types_called == ["memory"]


def test_shortcut_openapi_paths_present(real_client):
    paths = real_client.get("/openapi.json").json()["paths"]
    expected = [
        "/v1/memory/search",
        "/v1/tasks/search",
        "/v1/artifacts/search",
        "/v1/messages/search",
    ]
    missing = [
        p
        for p in expected
        if p not in paths and p.replace("/search", "/vector-search") not in paths
    ]
    assert not missing, f"Missing shortcut routes: {missing}"


# ---------------------------------------------------------------------------
# Task 3: Reindex (admin-only)
# ---------------------------------------------------------------------------


def test_reindex_requires_admin_unauth(real_client, enable_vector, mock_backend):
    r = real_client.post("/v1/search/reindex", json={})
    assert r.status_code == 401


def test_reindex_requires_admin_viewer(
    real_client,
    enable_vector,
    mock_backend,
    mock_vector_service,
    viewer_token,
    seeded_admin_search_agents,
):
    r = real_client.post(
        "/v1/search/reindex",
        json={},
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert r.status_code == 403


def test_reindex_default_scope(
    real_client,
    enable_vector,
    mock_backend,
    mock_vector_service,
    admin_token,
    seeded_admin_search_agents,
):
    mock_vector_service.list_unindexed.return_value = [
        {"id": "row-1", "content": "first"},
        {"id": "row-2", "content": "second"},
    ]
    mock_backend.embed = AsyncMock(return_value=[[0.1] * 768, [0.2] * 768])
    r = real_client.post(
        "/v1/search/reindex",
        json={},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    # 4 entity types * 2 rows each
    assert body["reindexed"] == 8
    assert mock_vector_service.list_unindexed.call_count == 4


def test_reindex_entity_type_scope(
    real_client,
    enable_vector,
    mock_backend,
    mock_vector_service,
    admin_token,
    seeded_admin_search_agents,
):
    mock_vector_service.list_unindexed.return_value = [
        {"id": "m-1", "content": "memory row"}
    ]
    mock_backend.embed = AsyncMock(return_value=[[0.1] * 768])
    r = real_client.post(
        "/v1/search/reindex",
        json={"entity_type": "memory"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 200
    assert mock_vector_service.list_unindexed.call_count == 1
    call = mock_vector_service.list_unindexed.call_args
    assert call.kwargs.get("entity_type") == "memory" or (
        call.args and call.args[0] == "memory"
    )
    body = r.json()
    assert body["reindexed"] == 1
    assert body["by_type"]["memory"] == 1


def test_reindex_invalid_entity_type(
    real_client,
    enable_vector,
    mock_backend,
    mock_vector_service,
    admin_token,
    seeded_admin_search_agents,
):
    r = real_client.post(
        "/v1/search/reindex",
        json={"entity_type": "bogus"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 400
    assert "bogus" in str(r.json())


def test_reindex_invalid_since(
    real_client,
    enable_vector,
    mock_backend,
    mock_vector_service,
    admin_token,
    seeded_admin_search_agents,
):
    r = real_client.post(
        "/v1/search/reindex",
        json={"since": "not-a-date"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 422


def test_reindex_response_shape(
    real_client,
    enable_vector,
    mock_backend,
    mock_vector_service,
    admin_token,
    seeded_admin_search_agents,
):
    r = real_client.post(
        "/v1/search/reindex",
        json={},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 200
    body = r.json()
    assert set(body.keys()) == {"reindexed", "failed", "skipped", "by_type"}
    assert set(body["by_type"].keys()) == {"memory", "task", "artifact", "message"}


def test_reindex_embedding_backend_unavailable(
    real_client,
    enable_vector,
    mock_vector_service,
    admin_token,
    seeded_admin_search_agents,
    monkeypatch,
):
    from app.api import routes_search

    monkeypatch.setattr(routes_search, "get_embedding_service", lambda: None)
    r = real_client.post(
        "/v1/search/reindex",
        json={},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 503
    assert "embedding-unavailable" in str(r.json())


def test_reindex_per_row_failure_does_not_abort(
    real_client,
    enable_vector,
    mock_backend,
    mock_vector_service,
    admin_token,
    seeded_admin_search_agents,
):
    mock_vector_service.list_unindexed.side_effect = lambda *a, **k: (
        [{"id": "ok-1", "content": "good"}, {"id": "bad-1", "content": "bad"}]
        if (k.get("entity_type") == "memory" or (a and a[0] == "memory"))
        else []
    )
    mock_backend.embed = AsyncMock(return_value=[[0.1] * 768, [0.2] * 768])

    write_calls = {"n": 0}

    def _write(entity_type, entity_id, vec, model_name):
        write_calls["n"] += 1
        if entity_id == "bad-1":
            raise RuntimeError("write failed")

    mock_vector_service.write_embedding.side_effect = _write
    r = real_client.post(
        "/v1/search/reindex",
        json={"entity_type": "memory"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["reindexed"] == 1
    assert body["failed"] == 1


def test_reindex_writes_embedding(
    real_client,
    enable_vector,
    mock_backend,
    mock_vector_service,
    admin_token,
    seeded_admin_search_agents,
):
    mock_vector_service.list_unindexed.side_effect = lambda *a, **k: (
        [{"id": "row-1", "content": "hello"}]
        if (k.get("entity_type") == "task" or (a and a[0] == "task"))
        else []
    )
    mock_backend.embed = AsyncMock(return_value=[[0.42] * 768])
    r = real_client.post(
        "/v1/search/reindex",
        json={"entity_type": "task"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 200
    assert mock_vector_service.write_embedding.call_count == 1
    call = mock_vector_service.write_embedding.call_args
    # Args: (entity_type, entity_id, vector, model_name)
    assert call.args[0] == "task"
    assert call.args[1] == "row-1"
    assert call.args[2] == [0.42] * 768


# ---------------------------------------------------------------------------
# Task 3: Delete embedding (admin-only)
# ---------------------------------------------------------------------------


def test_delete_embedding_requires_admin(
    real_client,
    enable_vector,
    mock_vector_service,
    viewer_token,
    seeded_admin_search_agents,
):
    r = real_client.delete(
        "/v1/search/memory/some-id",
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert r.status_code == 403


def test_delete_embedding_invalid_entity_type(
    real_client,
    enable_vector,
    mock_vector_service,
    admin_token,
    seeded_admin_search_agents,
):
    r = real_client.delete(
        "/v1/search/bogus/abc",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 400


def test_delete_embedding_not_found(
    real_client,
    enable_vector,
    mock_vector_service,
    admin_token,
    seeded_admin_search_agents,
):
    mock_vector_service.clear_embedding.return_value = False
    r = real_client.delete(
        "/v1/search/memory/missing-id",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 404


def test_delete_embedding_success(
    real_client,
    enable_vector,
    mock_vector_service,
    admin_token,
    seeded_admin_search_agents,
):
    mock_vector_service.clear_embedding.return_value = True
    r = real_client.delete(
        "/v1/search/memory/keep-id",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body == {"entity_type": "memory", "id": "keep-id", "status": "deleted"}
    mock_vector_service.clear_embedding.assert_called_once_with("memory", "keep-id")


def test_delete_embedding_does_not_delete_row(
    real_client,
    enable_vector,
    mock_vector_service,
    admin_token,
    seeded_admin_search_agents,
):
    """The route must call clear_embedding (UPDATE), never DELETE FROM."""
    mock_vector_service.clear_embedding.return_value = True
    r = real_client.delete(
        "/v1/search/memory/keep-id",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 200
    # Asserting via the mock: clear_embedding (not delete_*) is the only call.
    assert mock_vector_service.clear_embedding.called
    assert not any(
        name.startswith("delete")
        for name in dir(mock_vector_service)
        if name in mock_vector_service._mock_children
        and getattr(mock_vector_service, name).called
    )


def test_delete_embedding_turso_unavailable(
    real_client,
    enable_vector,
    mock_vector_service,
    admin_token,
    seeded_admin_search_agents,
):
    mock_vector_service.clear_embedding.side_effect = RuntimeError("turso down")
    r = real_client.delete(
        "/v1/search/memory/keep-id",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 503


# ---------------------------------------------------------------------------
# Plan 06 (VEC-06): OpenAPI BETA tag description + startup warning
# ---------------------------------------------------------------------------


def test_openapi_tag_has_description(real_client):
    """The 'search [experimental]' tag must have a BETA description at app level."""
    r = real_client.get("/openapi.json")
    assert r.status_code == 200
    data = r.json()
    tags = data.get("tags", [])
    exp = [t for t in tags if "experimental" in t.get("name", "")]
    assert exp, f"No experimental tag found in OpenAPI tags: {[t.get('name') for t in tags]}"
    description = exp[0].get("description", "")
    assert "BETA" in description or "beta" in description or "opt-in" in description, (
        f"experimental tag description missing BETA/opt-in marker: {description!r}"
    )


def test_search_endpoint_marked_experimental_in_operation(real_client):
    """The /v1/search POST operation must carry an experimental tag."""
    r = real_client.get("/openapi.json")
    assert r.status_code == 200
    paths = r.json()["paths"]
    assert "/v1/search" in paths
    op = paths["/v1/search"]["post"]
    tags = op.get("tags", [])
    assert any("experimental" in t for t in tags), (
        f"/v1/search POST is missing experimental tag, got {tags}"
    )


def test_startup_logs_warning_on_local_sqlite(monkeypatch, capsys):
    """Lifespan startup must log a vector_search_disabled warning on local SQLite.

    OpenHub's structlog setup uses PrintLoggerFactory which writes to stdout,
    so we capture via capsys rather than caplog.
    """
    from app.database import vector_availability as va
    from app.main import app as real_app

    monkeypatch.setattr(va, "is_vector_enabled", lambda: False)
    with TestClient(real_app):
        pass

    captured = capsys.readouterr()
    combined = captured.out + captured.err
    assert "vector_search_disabled" in combined, (
        f"Expected vector_search_disabled in startup output, got: {combined[:500]}"
    )


def test_startup_no_warning_when_enabled(monkeypatch, capsys):
    """When vector is enabled, the vector_search_disabled warning must not fire."""
    from app.database import vector_availability as va
    from app.main import app as real_app

    monkeypatch.setattr(va, "is_vector_enabled", lambda: True)
    with TestClient(real_app):
        pass

    captured = capsys.readouterr()
    combined = captured.out + captured.err
    assert "vector_search_disabled" not in combined
