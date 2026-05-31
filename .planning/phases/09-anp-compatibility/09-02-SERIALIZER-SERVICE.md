# 09-02 — ANP Serializer Service Evidence

Timestamp: 2026-05-31T12:26:07Z

## Objective

Convert OpenHub `Agent` objects into public-safe ANP-style JSON-LD without database or FastAPI route dependencies.

## Files added

- `app/models/anp.py`
- `app/services/anp_compatibility_service.py`
- `tests/unit/test_anp_compatibility_service.py`

## TDD evidence

RED:

```text
.venv/bin/python -m pytest tests/unit/test_anp_compatibility_service.py -q --tb=short
→ failed first because tests/module did not exist, then because `app.services.anp_compatibility_service` did not exist.
```

GREEN:

```text
.venv/bin/python -m pytest tests/unit/test_anp_compatibility_service.py -q --tb=short
→ 6 passed
```

Focused combined gate after route implementation:

```text
.venv/bin/python -m pytest tests/unit/test_anp_compatibility_service.py tests/unit/test_anp_routes.py tests/unit/test_static_mount.py -q --tb=short
→ 19 passed
```

## Behavior shipped

- `is_anp_public(agent)` returns true only for explicit opt-in flags:
  - `labels["anp_public"] == "true"`
  - `metadata["anp_public"] is True`
  - `metadata["public"] is True`
- `build_agent_description(agent, base_url)` emits a conservative JSON-LD document with:
  - public name/description/status/capabilities
  - stable OpenHub agent ID
  - static OpenHub interface/security scheme names only
  - optional `did` only when explicitly supplied as `metadata.did` or `metadata.did_wba`
- `build_discovery_page(agents, base_url, page, page_size)` filters private agents before pagination and emits `next` only when needed.

## Security notes

- Raw labels and metadata are never serialized wholesale.
- Credential-looking values in metadata are not copied into public responses.
- DID is not synthesized.
- The service is pure and deterministic; no database or runtime secret access.
