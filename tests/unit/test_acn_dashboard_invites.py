"""Dashboard-admin ACN invite tests."""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.auth.jwt_auth import create_agent_tokens


def _admin_headers() -> dict[str, str]:
    tokens = create_agent_tokens(
        agent_id="admin-dashboard-invite-test",
        agent_name="test-admin",
        role="admin",
    )
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def test_dashboard_admin_can_create_acn_invite_with_jwt(test_client: TestClient) -> None:
    response = test_client.post(
        "/v1/acn/dashboard/invite",
        headers=_admin_headers(),
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["invite_code"].startswith("inv_")
    assert body["expires_in"] == "24 hours"
    assert body["usage"] == "POST /v1/acn/join with this invite_code to register your agent"


def test_dashboard_invite_creation_requires_admin_jwt(test_client: TestClient) -> None:
    response = test_client.post("/v1/acn/dashboard/invite")

    assert response.status_code == 401
