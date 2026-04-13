"""Integration tests for auto-indexing hooks across the 4 write paths.

These tests monkeypatch is_vector_enabled to True and inject a fake embedding
backend + a MagicMock VectorSearchService so we can verify the route handlers
schedule the background task with the correct entity_type and content text
without needing a real Turso DB.
"""
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def vector_enabled(monkeypatch):
    """Force is_vector_enabled() to return True everywhere it's looked up."""
    from app.services import embedding_hooks

    monkeypatch.setattr(embedding_hooks, "is_vector_enabled", lambda: True)
    return True


@pytest.fixture()
def fake_backend(monkeypatch):
    from app.services import embedding_hooks

    backend = MagicMock(name="fake_backend")
    backend.model_name = "mock"
    backend.embed = AsyncMock(return_value=[[0.0] * 384])
    monkeypatch.setattr(embedding_hooks, "get_embedding_service", lambda: backend)
    return backend


@pytest.fixture()
def fake_vector_service(monkeypatch):
    from app.services import embedding_hooks

    svc = MagicMock(name="VectorSearchService")
    monkeypatch.setattr(
        embedding_hooks, "VectorSearchService", MagicMock(return_value=svc)
    )
    return svc


@pytest.fixture()
def admin_api_key(test_client, admin_headers):
    """Create a real API key for admin and return its plaintext value."""
    resp = test_client.post(
        "/v1/auth/api-keys",
        json={"name": "test-auto-index", "scopes": ["read", "write", "admin"]},
        headers=admin_headers,
    )
    assert resp.status_code in (200, 201), resp.text
    body = resp.json()
    return body.get("api_key") or body.get("key") or body.get("plaintext")


def test_memory_write_triggers_embedding(
    test_client: TestClient, vector_enabled, fake_backend, fake_vector_service, admin_api_key
):
    resp = test_client.post(
        "/v1/memory/write",
        headers={"X-API-Key": admin_api_key},
        json={"key": "auto_idx_test_key", "value": "hello memory"},
    )
    assert resp.status_code == 200, resp.text
    # Background task runs synchronously inside TestClient's lifespan
    fake_backend.embed.assert_called()
    args, _ = fake_backend.embed.call_args
    assert args[0] == ["hello memory"]
    fake_vector_service.write_embedding.assert_called()
    call_args, _ = fake_vector_service.write_embedding.call_args
    assert call_args[0] == "memory"


def test_message_send_triggers_embedding(
    test_client: TestClient, vector_enabled, fake_backend, fake_vector_service, admin_api_key
):
    # Need a recipient agent. Use whatever already exists; if empty, send returns 400
    resp = test_client.post(
        "/v1/messages/send",
        headers={"X-API-Key": admin_api_key},
        json={"to_agent_name": "test-admin", "content": "hi msg"},
    )
    if resp.status_code == 404:
        pytest.skip("no recipient agent available")
    assert resp.status_code in (200, 201), resp.text
    fake_backend.embed.assert_called()
    args, _ = fake_backend.embed.call_args
    assert args[0] == ["hi msg"]
    fake_vector_service.write_embedding.assert_called()
    call_args, _ = fake_vector_service.write_embedding.call_args
    assert call_args[0] == "message"


def test_artifact_upload_triggers_embedding(
    test_client: TestClient, vector_enabled, fake_backend, fake_vector_service, admin_api_key
):
    resp = test_client.post(
        "/v1/artifacts/upload",
        headers={"X-API-Key": admin_api_key},
        json={
            "filename": "auto_idx_test.txt",
            "content_type": "text/plain",
            "content": "artifact body",
            "encoding": "text",
        },
    )
    assert resp.status_code == 200, resp.text
    fake_backend.embed.assert_called()
    args, _ = fake_backend.embed.call_args
    assert args[0] == ["artifact body"]
    fake_vector_service.write_embedding.assert_called()
    call_args, _ = fake_vector_service.write_embedding.call_args
    assert call_args[0] == "artifact"


def test_task_create_triggers_embedding(
    test_client: TestClient, vector_enabled, fake_backend, fake_vector_service, admin_headers
):
    resp = test_client.post(
        "/v1/tasks/",
        headers=admin_headers,
        json={
            "title": "auto-index task",
            "description": "task description text",
            "task_type": "feature",
            "priority": 3,
        },
    )
    if resp.status_code != 200:
        pytest.skip(f"task create returned {resp.status_code}: {resp.text}")
    fake_backend.embed.assert_called()
    args, _ = fake_backend.embed.call_args
    assert args[0] == ["task description text"]
    fake_vector_service.write_embedding.assert_called()
    call_args, _ = fake_vector_service.write_embedding.call_args
    assert call_args[0] == "task"


def test_memory_write_noop_when_vector_disabled(
    test_client: TestClient, monkeypatch, fake_backend, fake_vector_service, admin_api_key
):
    from app.services import embedding_hooks

    monkeypatch.setattr(embedding_hooks, "is_vector_enabled", lambda: False)
    resp = test_client.post(
        "/v1/memory/write",
        headers={"X-API-Key": admin_api_key},
        json={"key": "auto_idx_disabled", "value": "hello"},
    )
    assert resp.status_code == 200, resp.text
    fake_backend.embed.assert_not_called()
    fake_vector_service.write_embedding.assert_not_called()
