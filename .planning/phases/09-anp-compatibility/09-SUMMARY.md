# Phase 09 Summary — ANP Compatibility Spike

Status: complete
Updated: 2026-05-31T12:26:07Z

## Goal

Expose a bounded public-safe ANP compatibility surface for OpenHub agents while keeping OpenHub ACN identity, invites, scoped keys, task routing, evidence bundles, and human review gates authoritative.

## Shipped

- `GET /.well-known/agent-descriptions`
  - ANP-style `CollectionPage`
  - public agents only
  - pagination through `page` and `page_size`
  - `next` omitted when no additional page exists
- `GET /v1/anp/agents/{agent_id}/ad.json`
  - ANP-style Agent Description document
  - `404` for private or missing agents
  - DID included only when explicitly supplied in agent metadata
- Pure serializer layer:
  - `is_anp_public(agent)`
  - `build_agent_description(agent, base_url)`
  - `build_discovery_page(agents, base_url, page, page_size)`
- Documentation:
  - `docs/ANP_COMPATIBILITY.md`
  - README API overview and experimental ANP section
- GSD evidence:
  - `09-01-ANP-MAPPING-DESIGN.md`
  - `09-02-SERIALIZER-SERVICE.md`
  - `09-03-ADP-ENDPOINT.md`
  - `09-04-WELL-KNOWN-DISCOVERY.md`
  - `09-05-VERIFICATION.md`

## Security posture

- Default private.
- No raw labels or metadata in public responses.
- No key/token/secret/bearer/admin values in public responses.
- No IPs, local paths, workspace paths, hostnames, process details, env values, or bridge command lines in public responses.
- ANP is only an interoperability/discovery layer; it does not grant task execution or private OpenHub operations.

## Tests

Focused gate:

```text
.venv/bin/python -m pytest tests/unit/test_anp_compatibility_service.py tests/unit/test_anp_routes.py tests/unit/test_static_mount.py -q --tb=short
→ 19 passed
```

Full closeout gate is recorded in `09-05-VERIFICATION.md`.

```text
.venv/bin/python -m pytest tests/unit/test_anp_compatibility_service.py tests/unit/test_anp_routes.py tests/unit/test_static_mount.py -q --tb=short
→ 19 passed

.venv/bin/python -m pytest tests/ -q --tb=short --disable-warnings
→ passed; Turso-dependent vector tests skipped when credentials are not set

cd web && npm run test -- --run
→ 19 files passed; 49 tests passed

cd web && npx playwright test --reporter=list
→ 10 passed
```

## Release decision

Live smoke after deploy:

```text
https://hub.brunhilde.cloud/v1/health/simple → HTTP 200, status=ok
https://hub.brunhilde.cloud/.well-known/agent-descriptions?page=1&page_size=2 → HTTP 200, CollectionPage, items=0
https://hub.brunhilde.cloud/v1/acn/status → HTTP 200
```

No release, tag, package publish, Docker registry publish, or GitHub release was created. Those actions still require explicit operator approval for version and target.
