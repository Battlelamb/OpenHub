"""ANP compatibility response shapes for public-safe JSON-LD."""

from __future__ import annotations

from typing import NotRequired, TypedDict


ANP_COLLECTION_CONTEXT: dict[str, str] = {
    "@vocab": "https://schema.org/",
    "ad": "https://agent-network-protocol.com/ad#",
}

ANP_AGENT_CONTEXT: dict[str, str] = {
    "@vocab": "https://schema.org/",
    "ad": "https://agent-network-protocol.com/ad#",
    "openhub": "https://hub.brunhilde.cloud/ns/openhub#",
}

EXPERIMENTAL_ANP_VERSION = "experimental-openhub-anp-v0"

ANPAgentDescriptionItem = TypedDict(
    "ANPAgentDescriptionItem",
    {
        "@type": str,
        "@id": str,
        "name": str,
    },
)

ANPInterface = TypedDict(
    "ANPInterface",
    {
        "@type": str,
        "protocol": str,
        "description": str,
    },
)

ANPSecurityDefinition = TypedDict(
    "ANPSecurityDefinition",
    {
        "scheme": str,
        "in": str,
        "name": str,
    },
)

ANPAgentDescription = TypedDict(
    "ANPAgentDescription",
    {
        "@context": dict[str, str],
        "@type": str,
        "@id": str,
        "name": str,
        "description": str,
        "version": str,
        "openhub:agentId": str,
        "openhub:status": str,
        "knowsAbout": list[str],
        "ad:interfaces": list[ANPInterface],
        "ad:securityDefinitions": dict[str, ANPSecurityDefinition],
        "ad:security": str,
        "did": NotRequired[str],
    },
)

ANPCollectionPage = TypedDict(
    "ANPCollectionPage",
    {
        "@context": dict[str, str],
        "@type": str,
        "url": str,
        "items": list[ANPAgentDescriptionItem],
        "next": NotRequired[str],
    },
)

DEFAULT_OPENHUB_INTERFACE: ANPInterface = {
    "@type": "ad:NaturalLanguageInterface",
    "protocol": "OpenHub",
    "description": "Use OpenHub ACN/API-key authenticated task routing for private operations.",
}

OPENHUB_SECURITY_DEFINITIONS: dict[str, ANPSecurityDefinition] = {
    "openhub_api_key": {
        "scheme": "openhub-api-key",
        "in": "header",
        "name": "X-API-Key",
    }
}
