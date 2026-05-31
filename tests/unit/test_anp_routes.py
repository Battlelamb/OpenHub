import json

import pytest
from fastapi.testclient import TestClient

from app.models.agents import Agent, AgentStatus


def make_agent(**overrides) -> Agent:
    data = {
        "id": "public-agent-1",
        "agent_name": "brunhilde",
        "description": "Public coordination agent",
        "capabilities": ["code_edit", "testing"],
        "status": AgentStatus.ONLINE,
        "labels": {},
        "metadata": {},
    }
    data.update(overrides)
    return Agent(**data)


class FakeAgentRepository:
    def __init__(self, agents: list[Agent]):
        self._agents = list(agents)

    def get_by_id(self, agent_id: str) -> Agent | None:
        return next((agent for agent in self._agents if agent.id == agent_id), None)

    def list_all(self, limit: int | None = None, offset: int = 0) -> list[Agent]:
        if limit is None:
            return self._agents[offset:]
        return self._agents[offset : offset + limit]


@pytest.fixture()
def anp_repository_override(test_client: TestClient):
    from app.api.routes_anp import get_agent_repository

    agents: list[Agent] = []

    def override_repository() -> FakeAgentRepository:
        return FakeAgentRepository(agents)

    test_client.app.dependency_overrides[get_agent_repository] = override_repository
    try:
        yield agents
    finally:
        test_client.app.dependency_overrides.pop(get_agent_repository, None)


def test_public_agent_description_returns_json_ld_fields(
    test_client: TestClient,
    anp_repository_override: list[Agent],
) -> None:
    anp_repository_override.append(
        make_agent(id="public-agent-1", labels={"anp_public": "true"})
    )

    response = test_client.get("/v1/anp/agents/public-agent-1/ad.json")

    assert response.status_code == 200
    payload = response.json()
    assert payload["@type"] == "ad:AgentDescription"
    assert payload["@id"].endswith("/v1/anp/agents/public-agent-1/ad.json")
    assert payload["name"] == "brunhilde"
    assert payload["knowsAbout"] == ["code_edit", "testing"]
    assert payload["ad:security"] == "openhub_api_key"


def test_private_agent_description_returns_404(
    test_client: TestClient,
    anp_repository_override: list[Agent],
) -> None:
    anp_repository_override.append(make_agent(id="private-agent-1"))

    response = test_client.get("/v1/anp/agents/private-agent-1/ad.json")

    assert response.status_code == 404


def test_missing_agent_description_returns_404(
    test_client: TestClient,
    anp_repository_override: list[Agent],
) -> None:
    response = test_client.get("/v1/anp/agents/missing-agent/ad.json")

    assert response.status_code == 404


def test_agent_description_response_does_not_leak_sensitive_values(
    test_client: TestClient,
    anp_repository_override: list[Agent],
) -> None:
    anp_repository_override.append(
        make_agent(
            id="sensitive-agent",
            labels={"anp_public": "true"},
            metadata={
                "did": "did:wba:hub.example:sensitive-agent",
                "api_key": "oh_should_not_leak",
                "admin_key": "ak_should_not_leak",
                "bearer": "Bearer should-not-leak",
                "workspace_path": "/home/brunhilde/OpenHub",
                "ip_address": "10.0.0.9",
            },
        )
    )

    response = test_client.get("/v1/anp/agents/sensitive-agent/ad.json")

    assert response.status_code == 200
    payload = json.dumps(response.json(), sort_keys=True)
    for forbidden in [
        "oh_should_not_leak",
        "ak_should_not_leak",
        "Bearer should-not-leak",
        "/home/brunhilde/OpenHub",
        "10.0.0.9",
        "admin_key",
        "workspace_path",
        "ip_address",
    ]:
        assert forbidden not in payload


def test_well_known_discovery_returns_collection_page(
    test_client: TestClient,
    anp_repository_override: list[Agent],
) -> None:
    anp_repository_override.extend(
        [
            make_agent(id="private-agent", agent_name="private"),
            make_agent(id="public-a", agent_name="alpha", labels={"anp_public": "true"}),
            make_agent(id="public-b", agent_name="beta", metadata={"public": True}),
        ]
    )

    response = test_client.get("/.well-known/agent-descriptions?page=1&page_size=10")

    assert response.status_code == 200
    payload = response.json()
    assert payload["@type"] == "CollectionPage"
    assert [item["name"] for item in payload["items"]] == ["alpha", "beta"]
    assert payload["items"][0]["@id"].endswith("/v1/anp/agents/public-a/ad.json")
    assert "private" not in json.dumps(payload)


def test_well_known_discovery_paginates_public_agents_only(
    test_client: TestClient,
    anp_repository_override: list[Agent],
) -> None:
    anp_repository_override.extend(
        [
            make_agent(id="private-agent", agent_name="private"),
            make_agent(id="public-a", agent_name="alpha", labels={"anp_public": "true"}),
            make_agent(id="public-b", agent_name="beta", metadata={"public": True}),
            make_agent(id="public-c", agent_name="gamma", metadata={"anp_public": True}),
        ]
    )

    first = test_client.get("/.well-known/agent-descriptions?page=1&page_size=2")
    second = test_client.get("/.well-known/agent-descriptions?page=2&page_size=2")

    assert first.status_code == 200
    assert second.status_code == 200
    assert [item["name"] for item in first.json()["items"]] == ["alpha", "beta"]
    assert first.json()["next"].endswith("/.well-known/agent-descriptions?page=2&page_size=2")
    assert [item["name"] for item in second.json()["items"]] == ["gamma"]
    assert "next" not in second.json()


def test_well_known_discovery_rejects_invalid_page_params(
    test_client: TestClient,
    anp_repository_override: list[Agent],
) -> None:
    response = test_client.get("/.well-known/agent-descriptions?page=0&page_size=0")

    assert response.status_code == 422
