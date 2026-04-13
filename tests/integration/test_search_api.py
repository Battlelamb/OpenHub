"""Stub from Wave 0 - implementations filled in by later plans.

Search API tests cover:
  * require_vector() raising RFC 7807 503 on local SQLite (Plan 01 - PASSES NOW)
  * explicit feature flag off behavior (Plan 01 - PASSES NOW)
  * top-k cap, shortcut delegation, OpenAPI beta tagging (Plan 05 / 06)
"""
import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.database import vector_availability
from app.database.vector_availability import require_vector


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
    # FastAPI wraps HTTPException.detail under "detail"; the inner dict is our
    # RFC 7807 problem.
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


@pytest.mark.xfail(reason="Plan 05 implements top-k cap")
def test_top_k_cap():
    assert False


@pytest.mark.xfail(reason="Plan 06 implements shortcut delegation")
def test_shortcut_delegation():
    assert False


@pytest.mark.xfail(reason="Plan 06 implements OpenAPI beta tag")
def test_openapi_beta_tag():
    assert False
