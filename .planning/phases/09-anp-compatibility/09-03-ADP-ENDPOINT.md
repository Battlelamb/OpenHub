# 09-03 — Public Per-Agent ANP Agent Description Endpoint Evidence

Timestamp: 2026-05-31T12:26:07Z

## Objective

Expose a public read-only endpoint for ANP-style Agent Description documents while returning `404` for private or missing agents.

Endpoint:

```text
GET /v1/anp/agents/{agent_id}/ad.json
```

## Files changed

- `app/api/routes_anp.py`
- `app/main.py`
- `tests/unit/test_anp_routes.py`

## TDD evidence

RED:

```text
.venv/bin/python -m pytest tests/unit/test_anp_routes.py -q --tb=short
→ failed because `app.api.routes_anp` did not exist.
```

GREEN:

```text
.venv/bin/python -m pytest tests/unit/test_anp_compatibility_service.py tests/unit/test_anp_routes.py tests/unit/test_static_mount.py -q --tb=short
→ 19 passed
```

## Behavior shipped

- Public opted-in agent returns `200` with JSON-LD fields.
- Private agent returns `404`.
- Missing agent returns `404`.
- The route delegates mapping/redaction to the pure serializer service.
- The route uses an overridable repository dependency (`get_agent_repository`) for isolated tests.

## Security evidence

Route tests serialize the response and assert it does not include credential-looking values or denied runtime details such as:

- `oh_...`-style values
- `ak_...`-style values
- bearer-token strings
- workspace paths
- IP addresses
- admin key field names

The endpoint only advertises the OpenHub API-key scheme name (`openhub_api_key`) and header name (`X-API-Key`); it never returns key values.
