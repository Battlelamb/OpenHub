"""
Shared test fixtures for OpenHub test suite.
"""
import pytest
import os
import json
import tempfile

# Set required env vars before app import so pydantic-settings validation passes.
# These will be set by Plan 01 (HARD-02) as real required fields.
# For now they prevent startup failures during testing.
os.environ.setdefault("AGENTHUB_ADMIN_USER", "test-admin")
os.environ.setdefault("AGENTHUB_ADMIN_PASSWORD", "test-password-secure")
os.environ.setdefault("AGENTHUB_SECRET_KEY", "test-secret-key-32-chars-minimum")
os.environ.setdefault("AGENTHUB_JWT_SECRET_KEY", "test-jwt-secret-key-32-chars-ok")

# Use a real temp file for the DB so app.main.lifespan os.makedirs(dirname(db_path))
# does not fail on ":memory:" (dirname would be ""). The file itself is disposable.
_tmp_db_dir = tempfile.mkdtemp(prefix="openhub-test-db-")
os.environ.setdefault("AGENTHUB_DB_PATH", os.path.join(_tmp_db_dir, "test.db"))

# Allow all origins for testing
os.environ.setdefault("AGENTHUB_CORS_ORIGINS", json.dumps(["*"]))
os.environ.setdefault("AGENTHUB_CORS_METHODS", json.dumps(["*"]))
os.environ.setdefault("AGENTHUB_CORS_HEADERS", json.dumps(["*"]))

from fastapi.testclient import TestClient
from app.main import app
from app.auth.jwt_auth import create_access_token


@pytest.fixture(scope="session")
def test_client():
    """FastAPI TestClient for the full app. Session-scoped for speed."""
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client


@pytest.fixture(scope="session")
def admin_headers():
    """Headers for admin JWT auth - returns a real signed JWT access token."""
    token = create_access_token(
        subject="test-admin",
        claims={"role": "admin", "agent_name": "test-admin"}
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="session")
def auth_token():
    """Raw JWT access token for WebSocket and direct auth tests."""
    return create_access_token(
        subject="test-admin",
        claims={"role": "admin", "agent_name": "test-admin"}
    )


@pytest.fixture(scope="session")
def agent_headers():
    """Headers for agent-role JWT auth."""
    token = create_access_token(
        subject="test-agent-001",
        claims={"role": "agent", "agent_name": "test-agent"}
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="session")
def agent_api_key():
    """A test API key value (raw, unhashed) for agent auth tests."""
    return "test-api-key-abcdef1234567890"


# ---------------------------------------------------------------------------
# Phase 3 (Vector Database) test infrastructure
# ---------------------------------------------------------------------------


def pytest_configure(config):
    """Register custom markers used by Phase 3 vector tests."""
    config.addinivalue_line(
        "markers",
        "turso: requires live Turso DB for vector tests",
    )


def pytest_collection_modifyitems(config, items):
    """Auto-skip @pytest.mark.turso tests when Turso credentials are absent.

    Per VEC-06 / Approach A in 03-RESEARCH.md: vector tests that hit the real
    Turso backend must skip cleanly on local dev so the rest of the suite
    stays green without configuration.
    """
    has_turso = bool(
        os.environ.get("TURSO_DATABASE_URL")
        and os.environ.get("TURSO_AUTH_TOKEN")
    )
    if has_turso:
        return
    skip_marker = pytest.mark.skip(reason="Turso credentials not set")
    for item in items:
        if "turso" in item.keywords:
            item.add_marker(skip_marker)


class _MockEmbeddingBackend:
    """Deterministic in-process embedding backend for unit tests.

    Returns vectors of the configured dimension whose components encode the
    input index, which is enough to assert ordering/shape without booting a
    real model.
    """

    dim = 384
    model_name = "mock"

    async def embed(self, texts):
        return [[float(i)] * self.dim for i, _ in enumerate(texts)]


@pytest.fixture()
def mock_embedding_backend():
    """Function-scoped mock embedding backend for embedding-service tests."""
    return _MockEmbeddingBackend()
