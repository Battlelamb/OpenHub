# 09-04 — `.well-known/agent-descriptions` Discovery Endpoint Evidence

Timestamp: 2026-05-31T12:26:07Z

## Objective

Expose the ANP-style public discovery collection with pagination and public/private filtering.

Endpoint:

```text
GET /.well-known/agent-descriptions?page=1&page_size=50
```

## Files changed

- `app/api/routes_anp.py`
- `tests/unit/test_anp_routes.py`

## Behavior shipped

- Returns `@type: CollectionPage`.
- Includes public agents only.
- Filters private agents before pagination.
- `page` is validated as `>= 1`.
- `page_size` is validated as `1..100`.
- `next` is emitted only when another public-agent page exists.
- Item `@id` values point to `/v1/anp/agents/{agent_id}/ad.json`.

## Verification

```text
.venv/bin/python -m pytest tests/unit/test_anp_compatibility_service.py tests/unit/test_anp_routes.py tests/unit/test_static_mount.py -q --tb=short
→ 19 passed
```

## Open question resolved

`AgentRepository.list_all()` is available through `BaseRepository`, so no raw SQL route code or new repository helper was needed.
