"""
Stub tests for app import health.
These validate the test scaffold itself works - not app logic.
App logic tests are added by Wave 1+ plans.
"""
from fastapi.testclient import TestClient


def test_app_imports():
    """Confirm app/main.py imports without error given test env vars."""
    from app.main import app
    assert app is not None


def test_health_endpoint_reachable(test_client: TestClient):
    """Confirm the health endpoint responds - even if body format changes."""
    # Use simple health endpoint which doesn't require RequestIdDep
    response = test_client.get("/v1/health/simple")
    assert response.status_code == 200, (
        f"Expected 200 from /v1/health/simple, got {response.status_code}"
    )
