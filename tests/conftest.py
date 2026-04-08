"""
Shared test fixtures for OpenHub test suite.
"""
import pytest
import os

# Set required env vars before app import so pydantic-settings validation passes.
# These will be set by Plan 01 (HARD-02) as real required fields.
# For now they prevent startup failures during testing.
os.environ.setdefault("AGENTHUB_ADMIN_USER", "test-admin")
os.environ.setdefault("AGENTHUB_ADMIN_PASSWORD", "test-password-secure")
os.environ.setdefault("AGENTHUB_SECRET_KEY", "test-secret-key-32-chars-minimum")
os.environ.setdefault("AGENTHUB_JWT_SECRET_KEY", "test-jwt-secret-key-32-chars-ok")
os.environ.setdefault("AGENTHUB_DB_PATH", ":memory:")

from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture(scope="session")
def test_client():
    """FastAPI TestClient for the full app. Session-scoped for speed."""
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client


@pytest.fixture(scope="session")
def admin_headers():
    """Headers for admin JWT auth - populated after login."""
    return {"Authorization": "Bearer test-admin-token-placeholder"}


@pytest.fixture(scope="session")
def agent_api_key():
    """A test API key value (raw, unhashed) for agent auth tests."""
    return "test-api-key-abcdef1234567890"
