"""Regression tests for admin dashboard JWT sessions.

Admin UI sessions use synthetic ``admin-<uuid>`` JWT subjects. They must not
require a matching row in the agents table; otherwise the dashboard logs in,
then protected reads fail and the UI bounces back toward /login.
"""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.auth.jwt_auth import create_agent_tokens


def _synthetic_admin_tokens() -> dict[str, str]:
    return create_agent_tokens(
        agent_id="admin-regression-test",
        agent_name="test-admin",
        role="admin",
    )


def test_admin_login_token_can_read_me_without_agent_row(test_client: TestClient) -> None:
    tokens = _synthetic_admin_tokens()
    response = test_client.get(
        "/v1/auth/me",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["role"] == "admin"
    assert body["agent_id"].startswith("admin-")
    assert body["is_active"] is True


def test_admin_refresh_token_does_not_require_agent_row(test_client: TestClient) -> None:
    tokens = _synthetic_admin_tokens()
    response = test_client.post(
        "/v1/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["role"] == "admin"
    assert body["access_token"]
    assert body["refresh_token"]
