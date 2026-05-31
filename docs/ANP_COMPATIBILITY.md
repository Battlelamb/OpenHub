# ANP Compatibility

Status: implemented experimental spike, Phase 09
Updated: 2026-05-31

OpenHub exposes a small, read-only Agent Network Protocol (ANP) compatibility surface so external tools can discover public-safe OpenHub agents without weakening OpenHub's own trust model.

This document is the source of truth for the Phase 09 ANP compatibility spike.

## Implementation status

Implemented endpoints:

- `GET /.well-known/agent-descriptions?page=1&page_size=50`
- `GET /v1/anp/agents/{agent_id}/ad.json`

Implemented modules:

- `app/models/anp.py`
- `app/services/anp_compatibility_service.py`
- `app/api/routes_anp.py`

Verification coverage:

- Serializer/public-private/filtering tests: `tests/unit/test_anp_compatibility_service.py`
- Public route/discovery/pagination/no-leak tests: `tests/unit/test_anp_routes.py`

## Scope

Implement only the public discovery and public agent-description layer:

- `GET /.well-known/agent-descriptions`
- `GET /v1/anp/agents/{agent_id}/ad.json`

These endpoints serialize explicitly public OpenHub agent records into ANP-style JSON-LD. They do not create tasks, join agents, issue credentials, verify identities, or replace existing OpenHub routes.

## Non-goals

Phase 09 does not implement:

- `did:wba` key generation or verification
- end-to-end encrypted ANP messaging
- passive registration with external ANP search services
- meta-protocol negotiation
- payment protocols
- replacement of ACN invite flow, per-agent API keys, admin keys, task routing, evidence bundles, or human review gates
- dashboard UX beyond documentation or a future tiny link if needed
- any release tag, package publish, Docker registry publish, or external protocol dependency

## OpenHub trust model remains authoritative

ANP compatibility is a public interoperability veneer. OpenHub continues to use:

- `inv_...` short-lived invite codes for onboarding
- `oh_...` per-agent keys for agent operations
- `ak_...` admin keys for server-side administration only
- OpenHub task routing, evidence, and review gates for real work
- existing API/JWT/admin dependencies for private operations

A public ANP document may advertise that OpenHub authenticated APIs exist, but it must never expose actual credentials, raw private metadata, or enough machine detail to identify private runtime state.

## Public/private discovery policy

Default: private.

An agent is public-discoverable only if one of these explicit opt-in flags exists:

| Source | Public when |
|---|---|
| `agent.labels` | `labels["anp_public"] == "true"` |
| `agent.metadata` | `metadata["anp_public"] is true` |
| `agent.metadata` | `metadata["public"] is true` |

Everything else is excluded from both discovery and direct public ANP agent-description endpoints.

A private or missing agent must return `404` from `GET /v1/anp/agents/{agent_id}/ad.json` so callers cannot distinguish private IDs from unknown IDs.

## Sensitive data denylist

Public ANP responses must never return raw `labels` or raw `metadata` wholesale.

Drop any field whose key contains, case-insensitive:

- `key`
- `token`
- `secret`
- `password`
- `credential`
- `auth`
- `bearer`
- `cookie`
- `session`

Also drop these machine/runtime details even if they do not match the substring list:

- `ip_address`
- `hostname`
- `workspace_path`
- `os_info`
- local callback URLs unless a future field explicitly marks them public-safe
- local file paths
- process IDs
- raw environment names or values
- bridge command lines

Security tests must search serialized public responses for credential-looking values and these denied field names.

## Endpoint contract

### `GET /.well-known/agent-descriptions`

Purpose: ANP-style active discovery endpoint.

Query params:

| Param | Type | Default | Limits |
|---|---:|---:|---|
| `page` | integer | `1` | minimum `1` |
| `page_size` | integer | `50` | minimum `1`, maximum `100` |

Response shape:

```json
{
  "@context": {
    "@vocab": "https://schema.org/",
    "ad": "https://agent-network-protocol.com/ad#"
  },
  "@type": "CollectionPage",
  "url": "https://hub.example/.well-known/agent-descriptions?page=1&page_size=50",
  "items": [
    {
      "@type": "ad:AgentDescription",
      "name": "public-agent",
      "@id": "https://hub.example/v1/anp/agents/agent_123/ad.json"
    }
  ],
  "next": "https://hub.example/.well-known/agent-descriptions?page=2&page_size=50"
}
```

Rules:

- `items` contains public agents only.
- `next` is omitted when no next page exists.
- Each item `@id` points to the per-agent document endpoint.
- The endpoint is public and unauthenticated, so it must be aggressively redacted by design.

### `GET /v1/anp/agents/{agent_id}/ad.json`

Purpose: ANP-style Agent Description Protocol document for one public OpenHub agent.

Response shape:

```json
{
  "@context": {
    "@vocab": "https://schema.org/",
    "ad": "https://agent-network-protocol.com/ad#",
    "openhub": "https://hub.brunhilde.cloud/ns/openhub#"
  },
  "@type": "ad:AgentDescription",
  "@id": "https://hub.example/v1/anp/agents/agent_123/ad.json",
  "name": "public-agent",
  "description": "Public description for discovery.",
  "version": "experimental-openhub-anp-v0",
  "openhub:agentId": "agent_123",
  "openhub:status": "online",
  "knowsAbout": ["code_edit", "testing"],
  "ad:interfaces": [
    {
      "@type": "ad:NaturalLanguageInterface",
      "protocol": "OpenHub",
      "description": "Use OpenHub ACN/API-key authenticated task routing for private operations."
    }
  ],
  "ad:securityDefinitions": {
    "openhub_api_key": {
      "scheme": "openhub-api-key",
      "in": "header",
      "name": "X-API-Key"
    }
  },
  "ad:security": "openhub_api_key"
}
```

Rules:

- Include `did` only when `agent.metadata["did"]` or `agent.metadata["did_wba"]` is explicitly present.
- Do not synthesize or imply a DID.
- Do not include private API URLs unless they are already public OpenHub routes and require authentication for mutation/private operations.
- Do not include callback URLs by default.

## Field mapping

| OpenHub source | ANP output | Notes |
|---|---|---|
| request base URL | `@id`, `url`, item IDs | Prefer request-derived public URL for now; consider `AGENTHUB_PUBLIC_BASE_URL` only if proxy headers prove insufficient. |
| `Agent.id` | `openhub:agentId`, URL path | Stable identifier; safe because only public agents are emitted. |
| `Agent.agent_name` | `name` | Required public display name. |
| `Agent.description` or safe public metadata description | `description` | Use a generic fallback if empty. |
| `Agent.status` | `openhub:status` | Informational only; not proof of liveness. |
| `Agent.capabilities` | `knowsAbout` | Public capability labels only. |
| `Agent.metadata.did` | `did` | Optional; pass through only when explicit. |
| `Agent.metadata.did_wba` | `did` | Optional fallback if `did` absent. |
| public interface hints | `ad:interfaces` | Static OpenHub natural-language/API description in first slice. |
| OpenHub auth model | `ad:securityDefinitions`, `ad:security` | Advertise scheme names only; never expose key values. |
| raw metadata/labels | omitted | Never return wholesale. |

## Interface advertisement policy

Phase 09 starts with a conservative interface list:

- `ad:NaturalLanguageInterface` describing that OpenHub is an authenticated coordination hub.
- Optional future `ad:OpenRPCInterface` only if OpenHub publishes a public-safe OpenRPC schema.
- Optional future `ad:MCPInterface` only if MCP endpoints are explicitly public-safe and documented.

Do not imply that public ANP callers can submit tasks without OpenHub authentication.

## Base URL policy

Initial implementation may derive URLs from `request.base_url`.

If Cloudflare/proxy behavior produces wrong public URLs, add a later setting such as `AGENTHUB_PUBLIC_BASE_URL` and tests for proxy/public URL generation. Do not add the setting before it is needed.

## Tests required by this design

Serializer tests:

- public flag from `labels["anp_public"] == "true"`
- public flag from metadata booleans
- private by default
- sensitive metadata omitted
- DID included only when explicit
- discovery pagination

Route tests:

- public agent document returns `200`
- private agent document returns `404`
- missing agent document returns `404`
- discovery returns `CollectionPage`
- discovery includes only public agents
- pagination emits/omits `next` correctly
- serialized response does not contain denied field names or credential-looking values

## Implementation notes

- Keep mapping logic in a pure service module, not inside route functions.
- Keep routes thin.
- Prefer existing `AgentRepository` access patterns.
- If repository list helpers are insufficient, add a narrow helper with focused tests rather than raw SQL in routes.
- Do not touch runtime secrets or `.env` for this feature.
- Do not add an ANP package dependency unless a later implementation requires schema validation that cannot be reasonably expressed locally.

## Future work after this spike

Possible later slices, if Phase 09 proves useful:

- `did:wba` identity bridge for agents that already have DID material.
- Public OpenRPC or MCP interface descriptor once OpenHub has a stable public-safe schema.
- Passive registration with ANP search services.
- Dashboard control for public-discovery opt-in.
- Rate limiting or cache headers for public discovery if traffic requires it.

## Reference sources

- Upstream repo inspected: `agent-network-protocol/AgentNetworkProtocol`
- ADP reference: `07-anp-agent-description-protocol-specification.md`
- ADSP reference: `08-ANP-Agent-Discovery-Protocol-Specification.md`
- Example inspected: `examples/adp/hotel/examples/ad.json`
- Local research note: `/home/brunhilde/Documents/Obsidian Vault/Agent Network Protocol (ANP).md`

License caution: the upstream repository license file was observed as Apache-2.0, while some upstream README/spec footers mention MIT. OpenHub should implement its own minimal compatibility surface and avoid copying upstream spec prose wholesale.
