---
phase: 03-vector-database
plan: 05
subsystem: vector-search-api
tags: [vector, search, reindex, delete, admin, fastapi, rfc7807, tdd]
requires:
  - app.services.vector_search_service.VectorSearchService (Plan 02)
  - app.services.embedding_service.get_embedding_service (Plan 03)
  - app.database.vector_availability.require_vector (Plan 01)
  - app.auth.dependencies.CurrentAdmin (Phase 1)
provides:
  - POST   /v1/search                          (unified semantic search)
  - POST   /v1/search/reindex                  (admin-only re-embed, D-15)
  - DELETE /v1/search/{entity_type}/{entity_id} (admin-only embedding clear)
  - POST   /v1/memory/search                   (shortcut, types=['memory'])
  - POST   /v1/tasks/search                    (shortcut, types=['task'])
  - POST   /v1/artifacts/search                (shortcut, types=['artifact'])
  - POST   /v1/messages/search                 (shortcut, types=['message'])
  - app.models.vector_search.SearchRequest / SearchHit / SearchResponse
  - app.models.vector_search.ReindexRequest / ReindexResponse / ReindexByType
  - app.models.vector_search.DeleteEmbeddingResponse
  - app.api.routes_search.unified_search (shared helper for shortcuts)
  - app.services.vector_search_service.VectorSearchService.clear_embedding
  - list_unindexed gains optional since: datetime filter
affects:
  - app/main.py (routes_search.router registered after artifacts)
  - app/api/routes_memory.py (POST /v1/memory/search; existing GET /search untouched)
  - app/api/routes_tasks.py  (POST /v1/tasks/search;  existing GET /search untouched)
  - app/api/routes_artifacts.py (POST /v1/artifacts/search)
  - app/api/routes_messaging.py (POST /v1/messages/search)
tech_stack:
  added: []
  removed: []
  patterns:
    - router-level Depends(require_vector) so every handler 503s on local SQLite
    - cross-entity merge by sort key=distance ASC, slice [: top_k]
    - shortcut routes call unified_search with model_copy(update={"types": [...]})
    - admin gate via CurrentAdmin = Annotated[..., Depends(get_current_admin)]
    - HTTPException(detail=str) instead of dict because middleware re-wraps detail
      into ProblemDetail.detail: str (dict raised ValidationError pre-fix)
    - clear_embedding is UPDATE-only - never DELETE FROM the entity table
key_files:
  created:
    - app/api/routes_search.py
    - app/models/vector_search.py
    - .planning/phases/03-vector-database/03-05-SUMMARY.md
  modified:
    - app/main.py
    - app/api/routes_memory.py
    - app/api/routes_tasks.py
    - app/api/routes_artifacts.py
    - app/api/routes_messaging.py
    - app/services/vector_search_service.py
    - tests/integration/test_search_api.py
    - tests/integration/test_vector_search.py
decisions:
  - "HTTPException detail must be a string, not a dict. OpenHub's middleware (app/middleware.py http_exception_handler_custom) re-wraps exc.detail into ProblemDetail(detail=...) where detail is typed str. Passing a dict raises pydantic ValidationError and the original 503/400/404 turns into a 500. Fix: encode the problem code into a 'code: message' string (e.g. 'embedding-unavailable: ...'). The trace_id and instance fields are still added by middleware."
  - "Shortcut routes use POST /search even on memory and tasks where a GET /search (LIKE-based) already exists - FastAPI dispatches by method, so the two coexist. No rename to /vector-search needed."
  - "Messaging shortcut lives at /v1/messages/search (router prefix is /v1/messages, not /v1/messaging as the plan example suggested). The plan acceptance criterion accepted either form."
  - "The shortcut handlers do model_copy(update={'types': [single]}) so client-supplied 'types' in the body are silently overridden. This was a deliberate D-19/D-20 rule and is covered by test_shortcut_ignores_types_in_body."
  - "list_unindexed already existed from Plan 02 with signature (entity_type, limit). Added an optional since: Optional[datetime] kwarg. The reindex handler tries the new signature first and falls back via except TypeError so a partial backport stays safe."
  - "write_embedding existed from Plan 02 with the 4-arg signature (entity_type, entity_id, vector, model_name). The reindex handler passes backend.model_name as the model arg so re-embedded rows record the actual provider, not a hardcoded string."
  - "clear_embedding does an existence check (SELECT id) before issuing UPDATE so the route can return a clean 404. This is one extra round-trip per delete but the alternative (UPDATE...RETURNING) is not portable across SQLite/Turso."
  - "Reindex worker reuses the existing 30000-char content cap from embedding_hooks via the EmbeddingService backend itself (OpenAI backend truncates internally; LocalSentenceTransformerBackend handles arbitrary length). No additional truncation in the reindex loop."
  - "enable_vector test fixture patches app.database.vector_availability.is_vector_enabled rather than routes_search.require_vector because FastAPI captures the Depends callable at router creation time. Patching the predicate is the only seam that survives Depends caching."
metrics:
  duration: 9m
  completed: 2026-04-13T07:10:26Z
  tasks: 3
  files_created: 2
  files_modified: 8
  commits: 3
---

# Phase 03 Plan 05: Vector Search API Summary

VEC-05 fully delivered: unified POST /v1/search with cross-entity merge, four per-entity shortcuts, admin-only POST /v1/search/reindex (D-15), and admin-only DELETE /v1/search/{entity_type}/{entity_id} - all gated by require_vector for the local-SQLite 503 path and tagged "[experimental]" in OpenAPI per D-23.

## What Was Done

### Task 1 - Unified /v1/search endpoint + Pydantic models + main.py registration

- **app/models/vector_search.py** (new): seven Pydantic v2 models with `extra="forbid"`:
  - `SearchRequest`: `query` (1..5000 chars), `types: Optional[List[str]]`, `filters`, `top_k` (1..50)
  - `SearchHit`: entity_type, id, content, distance
  - `SearchResponse`: query, total, hits
  - `ReindexRequest`: optional `entity_type` and `since: datetime`
  - `ReindexByType` / `ReindexResponse` / `DeleteEmbeddingResponse`
  - `ENTITY_TYPES = ["memory", "task", "artifact", "message"]` is the single source of truth - mirrors `app.services.vector_search_service.ENTITY_CONFIG.keys()`.

- **app/api/routes_search.py** (new):
  - `router = APIRouter(prefix="/v1/search", tags=["search [experimental]"], dependencies=[Depends(require_vector)])` - the router-level dependency means every handler returns 503 RFC 7807 on local SQLite without per-handler boilerplate.
  - `unified_search(req)` is the public helper exported for shortcut routes. It:
    1. Resolves the embedding backend via `get_embedding_service()`; 503 if None.
    2. Validates / defaults `req.types` against `ENTITY_TYPES`; 400 on unknown types.
    3. Embeds the query (single call, single vector).
    4. Iterates types, calls `VectorSearchService.search_entity(t, qvec, top_k, filters)`. Per-type failures are logged and swallowed so one bad entity table cannot break the whole search.
    5. Sorts the merged hit list by `distance ASC` and slices `[: top_k]`.
    6. Wraps each dict in `SearchHit(**h)` and returns `SearchResponse`.
  - `POST /v1/search` (`post_search`) is a one-line wrapper around `unified_search`.

- **app/main.py**: added `from .api.routes_search import router as search_router; app.include_router(search_router)` immediately after the artifacts router. The Plan 04 retry-worker startup wiring (`start_retry_worker` / `stop_retry_worker` in lifespan) is preserved verbatim.

- **tests/integration/test_search_api.py**: replaced the Plan 01 stubs with 35 real tests. The two original `test_503_local` and `test_flag_off` tests still mount their tiny inline FastAPI app to prove `require_vector` works in isolation; the rest of the file uses the real `app.main.app` via a function-scoped TestClient and these fixtures:
  - `enable_vector`: monkeypatches `app.database.vector_availability.is_vector_enabled -> True`. (Patching `routes_search.require_vector` does NOT work because FastAPI captured the `Depends(require_vector)` callable at router creation time - the only working seam is the predicate that `require_vector` calls at request time.)
  - `mock_backend`: injects a `MagicMock` backend with `embed = AsyncMock(...)` into `routes_search.get_embedding_service`.
  - `mock_vector_service`: monkeypatches `routes_search.VectorSearchService` to a callable returning a single shared `MagicMock` so tests can introspect `search_entity.call_args_list`.
  - `admin_token` / `viewer_token` / `seeded_admin_search_agents`: mint signed JWTs with role=admin/viewer and seed the matching agent rows so `get_current_agent` finds them.
  - 11 unified search tests: top_k cap (51 -> 422), top_k zero (-> 422), top_k default 10, defaults to 4 entity types, respects explicit types, merges 40 hits and caps to 5 with ascending distance, hit shape, empty query (-> 422), 5001-char query (-> 422), invalid entity_type (-> 400), OpenAPI experimental tag.

### Task 2 - Per-entity /search shortcuts + Turso end-to-end test

- **Per-entity shortcut routes** (4 files, identical pattern):
  - `app/api/routes_memory.py::memory_search_shortcut` -> POST /v1/memory/search
  - `app/api/routes_tasks.py::task_search_shortcut` -> POST /v1/tasks/search
  - `app/api/routes_artifacts.py::artifact_search_shortcut` -> POST /v1/artifacts/search
  - `app/api/routes_messaging.py::message_search_shortcut` -> POST /v1/messages/search

  Each handler:
  1. Imports `unified_search` lazily inside the function body to avoid an import cycle with routes_search.
  2. Calls `req.model_copy(update={"types": [SINGLE]})` so client-supplied `types` are overridden.
  3. Returns `await unified_search(forced)`.

  All four are decorated with `dependencies=[Depends(require_vector)]` and `tags=["{entity} [experimental]"]` so OpenAPI flags them as experimental and they 503 on local without Turso.

- **URL layout note**: memory and tasks already had **GET** `/search` (LIKE-based, kept for backward compat). FastAPI dispatches by HTTP method, so POST `/search` coexists with GET `/search` cleanly - no `/vector-search` rename was needed. The plan's acceptance criterion explicitly allowed either form.

- **Messaging prefix**: the messaging router prefix is `/v1/messages`, not `/v1/messaging` as the plan's example suggested. The plan acceptance criterion accepted both. The actual deployed path is `/v1/messages/search`.

- **Tests in test_search_api.py**:
  - 4 `test_*_shortcut_delegates` tests (one per entity) assert that `mock_vector_service.search_entity` was called exactly once with the expected entity type.
  - `test_shortcut_ignores_types_in_body` posts `{"query": "x", "types": ["task"]}` to `/v1/memory/search` and asserts the call still hit `memory`.
  - `test_shortcut_openapi_paths_present` verifies all 4 shortcut paths show up in `GET /openapi.json`.

- **tests/integration/test_vector_search.py::test_end_to_end_search** (new, `@pytest.mark.turso`):
  - Seeds 3 shared_memory rows (`__vector_test_e2e_a/b/c`) with orthogonal 384-dim vectors.
  - Monkeypatches `routes_search.get_embedding_service` to return a `MagicMock` whose `embed()` returns the same vector as row B.
  - Posts to the real `/v1/search` via a TestClient over `app.main.app`.
  - Asserts the first hit is row B and distances are ascending.
  - **Did NOT run green in this execution - skipped because no Turso credentials are configured in the local WSL env.** Plan 02 / Plan 04 / Plan 05 should all be re-run together against a real Turso DB before tagging Phase 3 complete.

### Task 3 - Admin reindex + delete endpoints

- **app/api/routes_search.py extensions**:
  - `POST /reindex` -> `reindex_embeddings(req: ReindexRequest, admin: CurrentAdmin)`:
    1. Validates `req.entity_type` (if set) against `ENTITY_TYPES`; 400 on unknown.
    2. Resolves embedding backend; 503 if None ("embedding-unavailable").
    3. Iterates the requested entity types (default = all 4) and calls `VectorSearchService.list_unindexed(entity_type=t, since=req.since)`. Has a `TypeError` fallback to the old 2-arg form `list_unindexed(t)` for forward-compat.
    4. Embeds each batch's contents via `backend.embed(contents)`. If the batch fails, increments `failed += len(rows)` and continues to the next type (a per-type failure does not abort the whole reindex).
    5. For each row, calls `svc.write_embedding(t, row["id"], vec, backend.model_name)` and increments `reindexed` / `by_type[t]`. Per-row write failures bump `failed` and continue.
    6. Returns `ReindexResponse(reindexed, failed, skipped, by_type=ReindexByType(...))`.
    Logs `reindex_complete` with the admin's `agent_id`.
  - `DELETE /{entity_type}/{entity_id}` -> `delete_embedding(admin, entity_type, entity_id)`:
    1. Validates entity_type (-> 400 if invalid).
    2. Calls `svc.clear_embedding(entity_type, entity_id)`. Any exception becomes 503 ("vector-store-unavailable") with structured logging.
    3. If the helper returned False (row not found), 404 ("entity-not-found").
    4. On success, returns `DeleteEmbeddingResponse(entity_type, id, status="deleted")` and logs `embedding_cleared`.

- **app/services/vector_search_service.py**:
  - `clear_embedding(entity_type, entity_id) -> bool`: SELECTs the id first for a clean existence check, then issues `UPDATE {table} SET embedding=NULL, embedding_status='deleted', embedding_error=NULL WHERE {id_col}=:id`. **Never** issues `DELETE FROM` against the entity table - this is the load-bearing invariant for VEC-05.
  - `list_unindexed` gains an optional `since: Optional[datetime]` kwarg. When set, the WHERE clause becomes `(<existing>) AND COALESCE(updated_at, created_at) >= :since` so D-15's bulk-backfill scope works portably across the 4 entity tables (some have updated_at, some only have created_at). The default behavior (since=None) is unchanged so the Plan 04 retry worker keeps calling `list_unindexed(entity_type, limit=...)` without modification.

- **18 new tests in test_search_api.py**:
  - **Reindex (10 tests)**: unauth (-> 401), viewer (-> 403), default scope (4 entity types * 2 rows = 8 reindexed), entity_type scope (1 list_unindexed call, 1 reindexed, by_type.memory == 1), invalid entity_type (-> 400), invalid since (-> 422), response shape (4 keys + 4 by_type keys), embedding backend None (-> 503 "embedding-unavailable"), per-row failure (1 reindexed + 1 failed), write_embedding called with correct args.
  - **Delete (6 tests)**: viewer (-> 403), invalid entity_type (-> 400), not-found via clear_embedding=False (-> 404), success (200 with deleted body, clear_embedding called with exact args), does-not-delete-row invariant (asserts `clear_embedding` was called and no `delete_*` mock children were touched), turso unavailable via clear_embedding raising (-> 503).

## Verification

```bash
.venv/bin/python -m pytest tests/integration/test_search_api.py -v --tb=short --no-cov -m "not turso"
# 35 passed in 2.30s

.venv/bin/python -m pytest tests/ --no-cov -m "not turso"
# 127 passed, 1 skipped, 9 deselected, 133 warnings in 3.68s
# (Plan 04 baseline was 94 passed; +33 from Plan 05 = 127)

AGENTHUB_ADMIN_USER=x AGENTHUB_ADMIN_PASSWORD=y .venv/bin/python -c \
  "from app.main import app; print('app boots ok'); paths=[p for p in app.openapi()['paths'] if 'search' in p]; print(paths)"
# app boots ok
# ['/v1/tasks/search', '/v1/messages/search', '/v1/memory/search',
#  '/v1/artifacts/search', '/v1/search', '/v1/search/reindex',
#  '/v1/search/{entity_type}/{entity_id}']

# Acceptance grep checks (all PASS):
grep -q "class SearchRequest"             app/models/vector_search.py             # OK
grep -q "class SearchHit"                 app/models/vector_search.py             # OK
grep -q "le=50"                           app/models/vector_search.py             # OK
grep -q "ge=1"                            app/models/vector_search.py             # OK
grep -q "min_length=1"                    app/models/vector_search.py             # OK
grep -q "max_length=5000"                 app/models/vector_search.py             # OK
grep -q "APIRouter"                       app/api/routes_search.py                # OK
grep -q 'prefix="/v1/search"'             app/api/routes_search.py                # OK
grep -q "Depends(require_vector)"         app/api/routes_search.py                # OK
grep -q 'search \[experimental\]'         app/api/routes_search.py                # OK
grep -q "async def unified_search"        app/api/routes_search.py                # OK
grep -q "all_hits.sort"                   app/api/routes_search.py                # OK
grep -q "include_router(search_router)"   app/main.py                              # OK
grep -q "class ReindexRequest"            app/models/vector_search.py             # OK
grep -q "class ReindexResponse"           app/models/vector_search.py             # OK
grep -q "class DeleteEmbeddingResponse"   app/models/vector_search.py             # OK
grep -q "@router.delete"                  app/api/routes_search.py                # OK
grep -q "CurrentAdmin"                    app/api/routes_search.py                # OK
grep -q "def reindex_embeddings"          app/api/routes_search.py                # OK
grep -q "def delete_embedding"            app/api/routes_search.py                # OK
grep -q "def clear_embedding"             app/services/vector_search_service.py   # OK
grep -q "embedding_status = 'deleted'"    app/services/vector_search_service.py   # OK
# clear_embedding contains no DELETE FROM:                                        # OK
```

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] HTTPException(detail=dict) trips OpenHub middleware**
- **Found during:** Task 1 GREEN verification (6 tests failed with status 500 instead of expected 400/404/503)
- **Issue:** OpenHub's `app/middleware.py::http_exception_handler_custom` re-wraps `exc.detail` into `ProblemDetail(detail=...)` where `ProblemDetail.detail` is typed `str` in `app/models/errors.py`. Passing a dict (the standard FastAPI pattern for RFC 7807) raises pydantic `ValidationError("Input should be a valid string")` and the custom handler crashes, which the general exception handler catches and reports as 500.
- **Fix:** Switched all `raise HTTPException(detail={...})` calls in routes_search.py to `raise HTTPException(detail="problem-code: human message")` strings. The middleware still adds `instance` and `trace_id` and emits the right RFC 7807 envelope; only the per-route problem code is encoded into the detail string instead of structured fields. Affected raises: embedding-unavailable, invalid-entity-type, vector-store-unavailable, entity-not-found.
- **Files modified:** app/api/routes_search.py
- **Commit:** 9ad1c1e (folded into Task 1)

**2. [Rule 3 - Blocking] FastAPI Depends caching defeats route-level monkeypatching**
- **Found during:** Task 1 GREEN (test_top_k_default returned 503 instead of 200)
- **Issue:** Initial `enable_vector` fixture monkeypatched `routes_search.require_vector` to a no-op. FastAPI captured the `Depends(require_vector)` callable as part of the router definition at `routes_search.py` import time, so reassigning the module attribute at test time has no effect.
- **Fix:** Patch `app.database.vector_availability.is_vector_enabled -> True` instead. `require_vector` calls that predicate at request time, so the seam is live.
- **Files modified:** tests/integration/test_search_api.py
- **Commit:** 9ad1c1e (folded into Task 1)

## URL Layout (final)

| Method | Path                                       | Auth   | Notes                                              |
|--------|--------------------------------------------|--------|----------------------------------------------------|
| POST   | /v1/search                                 | none   | unified, types defaults to all 4                   |
| POST   | /v1/search/reindex                         | admin  | D-15 bulk backfill                                 |
| DELETE | /v1/search/{entity_type}/{entity_id}       | admin  | clears embedding column only                       |
| POST   | /v1/memory/search                          | none   | shortcut, types forced to ['memory']               |
| POST   | /v1/tasks/search                           | none   | shortcut, types forced to ['task']                 |
| POST   | /v1/artifacts/search                       | none   | shortcut, types forced to ['artifact']             |
| POST   | /v1/messages/search                        | none   | shortcut, types forced to ['message']              |

The pre-existing `GET /v1/memory/search` and `GET /v1/tasks/search` (LIKE-based, non-vector) were left in place. POST and GET on the same path are different operations - no conflict.

## Outcome of the Turso End-to-End Test

**Status: NOT RUN against a real Turso DB.** The local WSL environment has no `TURSO_DATABASE_URL` / `TURSO_AUTH_TOKEN`, so `tests/integration/test_vector_search.py::test_end_to_end_search` was auto-skipped via the conftest hook. Before Phase 3 is declared complete, this test (along with all 8 other turso-marked tests from Plans 02 and 05) must run green against the dev Turso DB:

```bash
export TURSO_DATABASE_URL=...
export TURSO_AUTH_TOKEN=...
.venv/bin/alembic upgrade head
.venv/bin/python scripts/smoke_turso_vector.py     # must exit 0
.venv/bin/python -m pytest -m turso tests/integration/ -v
# expected: 9 passed (1 storage + 5 search + 1 e2e + 2 from Plan 04 if any)
```

If `test_end_to_end_search` fails specifically:
- It points at the cross-entity merge or the JSON serialization layer, not at the vector_top_k query (Plan 02's smoke script and storage tests would catch that first).
- Most likely cause: `SearchHit` serialization error or `clear_embedding` interfering with seeded rows from earlier tests in the same session. Add `clean_memory_rows` to the test or change the fixture scope.

## Reindex Request/Response Shape (final, decided here per 03-CONTEXT.md)

**Request:**
```json
{
  "entity_type": "memory",          // optional, one of ENTITY_TYPES, default=all
  "since": "2026-04-01T00:00:00Z"   // optional ISO8601, default=null
}
```

**Response:**
```json
{
  "reindexed": 17,
  "failed": 2,
  "skipped": 0,
  "by_type": {
    "memory": 8,
    "task":   5,
    "artifact": 4,
    "message": 0
  }
}
```

`skipped` is reserved for a future plan that wants to count rows whose content is empty / null without consuming an embedding budget. For Plan 05 it always returns 0 - the empty-content-marks-failed behavior from Plan 04's retry worker is NOT replicated here because the admin reindex is treated as an explicit user action, not a polling loop.

## Existing list_unindexed / write_embedding from Plan 02

- `list_unindexed(entity_type, limit=100)` - **already shipped in Plan 02**. Plan 05 added an optional `since: datetime` kwarg in a fully-backwards-compatible way. The reindex handler tries `list_unindexed(entity_type=t, since=req.since)` first and falls back to `list_unindexed(t)` via `except TypeError` so the route survives even if a downstream branch reverts the signature.
- `write_embedding(entity_type, entity_id, vector, model_name)` - **already shipped in Plan 02**. Plan 05 reuses it as-is. The reindex handler passes `backend.model_name` (e.g. `"sentence-transformers/all-MiniLM-L6-v2"` or `"text-embedding-3-small"`) so re-embedded rows record the actual provider that produced them.
- `clear_embedding(entity_type, entity_id) -> bool` - **new in Plan 05**. UPDATE-only, never DELETE FROM, with an existence check for the 404 path.

## Admin token test fixture

The `admin_token` and `viewer_token` fixtures are local to `tests/integration/test_search_api.py` (function-scoped). They use `create_access_token` from `app.auth.jwt_auth` with subjects `test-admin-search` and `test-viewer-search`, and the `seeded_admin_search_agents` fixture inserts matching rows into the `agents` table so `get_current_agent` resolves them. These fixtures were NOT promoted to `tests/conftest.py` because:
1. The session-scoped `admin_headers` fixture in conftest already exists and uses subject `test-admin` for non-admin-gated endpoints.
2. The Plan 05 admin tests need a *different* subject (so they can also test the viewer 403 path with `test-viewer-search`) and seed two distinct agent rows.
3. Promoting them to conftest would require coordinating with the existing agent fixtures from Plan 04's `test_auto_indexing.py`, which is out of scope for this plan.

If a future plan needs admin/viewer tokens for its own integration tests, the cleanest path is to copy the local fixtures, not to promote.

## Known Stubs

None. All endpoints are wired end-to-end through real handlers; the only behavior that isn't exercised on local SQLite is the actual DiskANN search (Plan 02's 8 turso-marked tests cover that, and Plan 05 adds 1 more turso-marked end-to-end test).

## Known Gotchas For Downstream Plans

- **HTTPException detail must be a string.** OpenHub's middleware re-wraps it into `ProblemDetail.detail: str`. Future routes that want structured RFC 7807 fields beyond the title/status auto-mapping should either patch the middleware (out of scope) or encode the problem code into the string detail (`"problem-code: message"` pattern).
- **enable_vector test pattern.** Any future test that needs to bypass `require_vector` must monkeypatch `app.database.vector_availability.is_vector_enabled`, NOT `app.api.routes_*.require_vector`. FastAPI Depends caches the callable at router creation.
- **Cross-entity merge keeps the per-type top_k**: `unified_search` requests `top_k` results PER entity type and then merges + caps. With 4 types and top_k=10 that's potentially 40 round-trips of vector_top_k under the hood. If Phase 4 introduces query-cost budgets, this is the place to add a per-type cap < top_k.
- **Reindex backend = current backend, not original**: re-embedded rows record `backend.model_name` at reindex time, not the original model that wrote the row. If a future plan needs to enforce model consistency (e.g., reject mixing 384-dim local with 1536-dim openai vectors in the same table), it must add a check before `write_embedding`.
- **Delete is admin-only, full DELETE of the entity row is NOT here.** This route only clears the embedding column. The actual entity DELETE endpoints (`DELETE /v1/memory/{key}`, etc.) do not currently zero out their embedding; on Turso the row vanishes anyway, but a future plan that introduces an external vector store will need explicit cleanup hooks in those routes.
- **`since` parameter uses `COALESCE(updated_at, created_at)`**. Tables that don't have either column will fail at SQL parse time. Currently all 4 ENTITY_CONFIG tables have `created_at`; only memory and tasks have `updated_at`. If Phase 4 adds a new entity type without a created_at column, `list_unindexed` will need adjustment.

## Self-Check: PASSED

- app/models/vector_search.py: FOUND
- app/api/routes_search.py: FOUND
- app/api/routes_memory.py (memory_search_shortcut): FOUND
- app/api/routes_tasks.py (task_search_shortcut): FOUND
- app/api/routes_artifacts.py (artifact_search_shortcut): FOUND
- app/api/routes_messaging.py (message_search_shortcut): FOUND
- app/services/vector_search_service.py (clear_embedding): FOUND
- app/services/vector_search_service.py (list_unindexed since kwarg): FOUND
- app/main.py (include_router(search_router)): FOUND
- tests/integration/test_search_api.py (35 tests, 0 xfail stubs): FOUND
- tests/integration/test_vector_search.py::test_end_to_end_search: FOUND (turso-marked)
- Commit 9ad1c1e (Task 1: unified search + models + main.py + tests): FOUND
- Commit a3dbbfc (Task 2: per-entity shortcuts + Turso e2e test): FOUND
- Commit 84f0e43 (Task 3: clear_embedding + list_unindexed since): FOUND
- Plan 04 retry worker lifespan wiring in app/main.py: PRESERVED (start_retry_worker / stop_retry_worker calls intact)
- Full non-turso suite: 127 passed, 1 skipped (pre-existing bcrypt skip), 9 deselected (turso)
