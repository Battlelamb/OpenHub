"""Pure ANP compatibility serializers for OpenHub agents.

This module deliberately contains no FastAPI or database access. Routes can call
these helpers after loading Agent objects through existing repositories.
"""

from __future__ import annotations

from urllib.parse import urlsplit

from app.models.agents import Agent
from app.models.anp import (
    ANP_AGENT_CONTEXT,
    ANP_COLLECTION_CONTEXT,
    DEFAULT_OPENHUB_INTERFACE,
    EXPERIMENTAL_ANP_VERSION,
    OPENHUB_SECURITY_DEFINITIONS,
    ANPAgentDescription,
    ANPAgentDescriptionItem,
    ANPCollectionPage,
)


def is_anp_public(agent: Agent) -> bool:
    """Return whether an agent explicitly opts in to public ANP discovery."""

    labels = agent.labels or {}
    metadata = agent.metadata or {}
    return (
        labels.get("anp_public") == "true"
        or metadata.get("anp_public") is True
        or metadata.get("public") is True
    )


def build_agent_description(agent: Agent, base_url: str) -> ANPAgentDescription:
    """Build a public-safe ANP Agent Description document for one agent."""

    origin = _origin_from_base_url(base_url)
    agent_url = _agent_description_url(origin, agent.id)
    status = agent.status.value if hasattr(agent.status, "value") else str(agent.status)
    description: ANPAgentDescription = {
        "@context": dict(ANP_AGENT_CONTEXT),
        "@type": "ad:AgentDescription",
        "@id": agent_url,
        "name": agent.agent_name,
        "description": agent.description or "Public OpenHub agent description.",
        "version": EXPERIMENTAL_ANP_VERSION,
        "openhub:agentId": agent.id,
        "openhub:status": status,
        "knowsAbout": list(agent.capabilities or []),
        "ad:interfaces": [DEFAULT_OPENHUB_INTERFACE.copy()],
        "ad:securityDefinitions": {
            name: definition.copy()
            for name, definition in OPENHUB_SECURITY_DEFINITIONS.items()
        },
        "ad:security": "openhub_api_key",
    }

    did = _explicit_did(agent)
    if did:
        description["did"] = did

    return description


def build_discovery_page(
    agents: list[Agent],
    base_url: str,
    page: int,
    page_size: int,
) -> ANPCollectionPage:
    """Build a paginated ANP discovery CollectionPage for public agents."""

    if page < 1:
        raise ValueError("page must be >= 1")
    if page_size < 1:
        raise ValueError("page_size must be >= 1")

    origin = _origin_from_base_url(base_url)
    public_agents = [agent for agent in agents if is_anp_public(agent)]
    start = (page - 1) * page_size
    end = start + page_size
    page_agents = public_agents[start:end]

    collection: ANPCollectionPage = {
        "@context": dict(ANP_COLLECTION_CONTEXT),
        "@type": "CollectionPage",
        "url": _discovery_url(origin, page, page_size),
        "items": [_discovery_item(origin, agent) for agent in page_agents],
    }

    if end < len(public_agents):
        collection["next"] = _discovery_url(origin, page + 1, page_size)

    return collection


def _discovery_item(origin: str, agent: Agent) -> ANPAgentDescriptionItem:
    return {
        "@type": "ad:AgentDescription",
        "name": agent.agent_name,
        "@id": _agent_description_url(origin, agent.id),
    }


def _explicit_did(agent: Agent) -> str | None:
    metadata = agent.metadata or {}
    did = metadata.get("did") or metadata.get("did_wba")
    if isinstance(did, str) and did:
        return did
    return None


def _origin_from_base_url(base_url: str) -> str:
    parsed = urlsplit(base_url)
    if parsed.scheme and parsed.netloc:
        return f"{parsed.scheme}://{parsed.netloc}"
    return base_url.rstrip("/")


def _agent_description_url(origin: str, agent_id: str) -> str:
    return f"{origin}/v1/anp/agents/{agent_id}/ad.json"


def _discovery_url(origin: str, page: int, page_size: int) -> str:
    return f"{origin}/.well-known/agent-descriptions?page={page}&page_size={page_size}"
