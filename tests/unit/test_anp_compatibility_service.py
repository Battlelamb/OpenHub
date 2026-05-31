import json

from app.models.agents import Agent, AgentStatus
from app.services.anp_compatibility_service import (
    build_agent_description,
    build_discovery_page,
    is_anp_public,
)


def make_agent(**overrides) -> Agent:
    data = {
        "id": "agent-public-1",
        "agent_name": "brunhilde",
        "description": "Public coordination agent",
        "capabilities": ["code_edit", "testing"],
        "status": AgentStatus.ONLINE,
        "labels": {},
        "metadata": {},
    }
    data.update(overrides)
    return Agent(**data)


def test_public_flag_accepts_anp_public_label():
    agent = make_agent(labels={"anp_public": "true"})

    assert is_anp_public(agent) is True


def test_public_flag_accepts_metadata_boolean():
    assert is_anp_public(make_agent(metadata={"anp_public": True})) is True
    assert is_anp_public(make_agent(metadata={"public": True})) is True


def test_private_agent_is_not_public_by_default():
    agent = make_agent()

    assert is_anp_public(agent) is False


def test_agent_description_omits_sensitive_metadata():
    agent = make_agent(
        labels={"anp_public": "true", "secret_label": "must-not-leak"},
        metadata={
            "anp_public": True,
            "api_token": "oh_should_not_leak",
            "admin_key": "ak_should_not_leak",
            "workspace_path": "/home/brunhilde/OpenHub",
            "ip_address": "10.0.0.9",
            "bearer": "Bearer should-not-leak",
            "public_note": "metadata should not be returned wholesale",
        },
    )

    description = build_agent_description(agent, "https://hub.example/")
    payload = json.dumps(description, sort_keys=True)

    assert description["@type"] == "ad:AgentDescription"
    assert description["name"] == "brunhilde"
    assert "oh_should_not_leak" not in payload
    assert "ak_should_not_leak" not in payload
    assert "must-not-leak" not in payload
    assert "/home/brunhilde/OpenHub" not in payload
    assert "10.0.0.9" not in payload
    assert "Bearer should-not-leak" not in payload
    assert "metadata should not be returned wholesale" not in payload
    assert "workspace_path" not in payload
    assert "ip_address" not in payload
    assert "api_token" not in payload
    assert "admin_key" not in payload


def test_agent_description_includes_did_only_when_explicit():
    without_did = build_agent_description(
        make_agent(labels={"anp_public": "true"}),
        "https://hub.example",
    )
    with_did = build_agent_description(
        make_agent(labels={"anp_public": "true"}, metadata={"did_wba": "did:wba:hub.example:brunhilde"}),
        "https://hub.example",
    )

    assert "did" not in without_did
    assert with_did["did"] == "did:wba:hub.example:brunhilde"


def test_discovery_page_paginates_public_agents():
    agents = [
        make_agent(id="private", agent_name="private-agent"),
        make_agent(id="public-1", agent_name="alpha", labels={"anp_public": "true"}),
        make_agent(id="public-2", agent_name="beta", metadata={"public": True}),
        make_agent(id="public-3", agent_name="gamma", metadata={"anp_public": True}),
    ]

    first_page = build_discovery_page(
        agents,
        "https://hub.example/root/ignored",
        page=1,
        page_size=2,
    )
    second_page = build_discovery_page(
        agents,
        "https://hub.example/root/ignored",
        page=2,
        page_size=2,
    )

    assert first_page["@type"] == "CollectionPage"
    assert first_page["url"] == "https://hub.example/.well-known/agent-descriptions?page=1&page_size=2"
    assert [item["name"] for item in first_page["items"]] == ["alpha", "beta"]
    assert first_page["items"][0]["@id"] == "https://hub.example/v1/anp/agents/public-1/ad.json"
    assert first_page["next"] == "https://hub.example/.well-known/agent-descriptions?page=2&page_size=2"

    assert [item["name"] for item in second_page["items"]] == ["gamma"]
    assert "next" not in second_page
    assert "private-agent" not in json.dumps(first_page) + json.dumps(second_page)
