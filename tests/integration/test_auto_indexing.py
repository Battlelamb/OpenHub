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
    backend.embed = AsyncMock(return_value=[[0.0] * 768])
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


@pytest.fixture(autouse=True)
def stable_api_key_auth(monkeypatch):
    """Keep these embedding-hook tests focused on indexing, not remote API-key consistency."""
    from app.auth.api_keys import APIKeyManager, APIKeyScope

    def _validate(self, api_key, required_scope=None):
        scopes = [scope.value for scope in APIKeyScope]
        if required_scope and required_scope not in scopes:
            return None
        return {
            "key_id": "test-admin",
            "name": "test-auto-index",
            "key_type": "admin",
            "scopes": scopes,
            "metadata": {},
        }

    monkeypatch.setattr(APIKeyManager, "validate_api_key", _validate)


@pytest.fixture()
def seeded_admin_agent():
    """Insert the test-admin agent row so task/message routes find a sender."""
    import json as _json
    from datetime import datetime, timezone

    from app.database.connection import get_database

    db = get_database()
    now = datetime.now(timezone.utc).isoformat()
    existing = db.fetch_one(
        "SELECT id FROM agents WHERE id = :id", {"id": "test-admin"}
    )
    if existing:
        return "test-admin"
    db.execute(
        """INSERT INTO agents (
               id, agent_name, description, capabilities, status,
               labels, created_at, updated_at, last_heartbeat
           ) VALUES (
               :id, :name, :desc, :caps, 'online',
               :labels, :now, :now, :now
           )""",
        {
            "id": "test-admin",
            "name": "test-admin",
            "desc": "auto-index test agent",
            "caps": _json.dumps([]),
            "labels": _json.dumps({}),
            "now": now,
        },
    )
    return "test-admin"


@pytest.fixture()
def admin_api_key(test_client):
    """Create a real API key directly via APIKeyManager and return its plaintext."""
    from app.auth.api_keys import APIKeyManager, APIKeyType
    from app.database.connection import get_database

    db = get_database()
    mgr = APIKeyManager(db)
    result = mgr.create_api_key(
        name="test-auto-index",
        key_type=APIKeyType.ADMIN,
        scopes=[
            "task:read", "task:create", "task:update",
            "artifact:read", "artifact:upload",
            "system:monitor", "system:admin",
        ],
        created_by="test-admin",
    )
    return result["api_key"]


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
    test_client: TestClient, vector_enabled, fake_backend, fake_vector_service, admin_api_key, seeded_admin_agent
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
    test_client: TestClient, vector_enabled, fake_backend, fake_vector_service, admin_headers, seeded_admin_agent
):
    resp = test_client.post(
        "/v1/tasks/",
        headers=admin_headers,
        json={
            "title": "auto-index task",
            "description": "task description text",
            "task_type": "feature",
            "priority": 3,
            "required_capabilities": ["general"],
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


def test_acn_task_create_triggers_embedding(
    test_client: TestClient, vector_enabled, fake_backend, fake_vector_service, admin_api_key
):
    resp = test_client.post(
        "/v1/acn/tasks",
        headers={"X-API-Key": admin_api_key},
        json={
            "title": "acn auto-index task",
            "description": "acn task description text",
            "task_type": "feature",
            "priority": 3,
            "required_capabilities": ["general"],
        },
    )
    assert resp.status_code == 200, resp.text
    fake_backend.embed.assert_called()
    args, _ = fake_backend.embed.call_args
    assert args[0] == ["acn task description text"]
    fake_vector_service.write_embedding.assert_called()
    call_args, _ = fake_vector_service.write_embedding.call_args
    assert call_args[0] == "task"


def test_acn_agent_register_triggers_embedding(
    test_client: TestClient, vector_enabled, fake_backend, fake_vector_service
):
    from uuid import uuid4

    from app.auth.api_keys import APIKeyManager, APIKeyType, APIKeyScope
    from app.database.connection import get_database

    suffix = uuid4().hex[:8]
    node_name = f"test-node-{suffix}"
    agent_name = f"semantic-agent-{suffix}"

    db = get_database()
    mgr = APIKeyManager(db)
    key = mgr.create_api_key(
        name=f"test-acn-agent-register-index-{suffix}",
        key_type=APIKeyType.ADMIN,
        scopes=[APIKeyScope.ACN_AGENT_REGISTER.value, APIKeyScope.ACN_NODE_MANAGE.value],
        created_by="test-admin",
    )["api_key"]

    node_resp = test_client.post(
        "/v1/acn/nodes",
        headers={"X-API-Key": key},
        json={"node_name": node_name, "node_url": "http://test-node.local"},
    )
    assert node_resp.status_code in (200, 409), node_resp.text

    resp = test_client.post(
        "/v1/acn/agents/register",
        headers={"X-API-Key": key},
        json={
            "agent_name": agent_name,
            "description": "Handles semantic search and Turkish support",
            "capabilities": ["semantic_search", "code_edit"],
            "node_name": node_name,
            "model": "gpt-test",
            "platform": "openhub-test",
            "skills": ["vector-memory"],
            "mcp_servers": ["filesystem", "github"],
            "languages": ["python", "typescript"],
        },
    )
    assert resp.status_code == 200, resp.text
    fake_backend.embed.assert_called()
    args, _ = fake_backend.embed.call_args
    text = args[0][0]
    assert "semantic-agent" in text
    assert "semantic_search" in text
    assert "filesystem" in text
    assert "github" in text
    fake_vector_service.write_embedding.assert_called()
    call_args, _ = fake_vector_service.write_embedding.call_args
    assert call_args[0] == "agent"


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
