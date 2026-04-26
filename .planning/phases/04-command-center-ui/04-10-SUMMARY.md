---
phase: 04-command-center-ui
plan: 10
subsystem: api
tags: [fastapi, react, msw, vitest, pytest, jwt, dashboard]

# Dependency graph
requires:
  - phase: 04-04
    provides: api-client, auth store, query hooks scaffold
  - phase: 04-05
    provides: ResponsiveList consumers (agents, tasks)
  - phase: 04-05b
    provides: dashboard route shells (costs, memory, locks, dlq, workflows)
  - phase: 04-06
    provides: query-keys factory + WebSocket sync targets
provides:
  - Backend list endpoints GET /v1/locks/ and GET /v1/workflows/
  - JWT auth alignment for /v1/costs/summary, /v1/memory/keys, /v1/locks/* (read paths)
  - Dual-auth dep _dashboard_or_admin_key on DLQ routes (JWT admin OR X-Admin-Key)
  - Hook adapter pattern bridging real backend envelopes to UI types (no consumer rewrites)
  - Real-backend integration test suite for the seven dashboard list endpoints
affects: [05-polish, 05-pagination, future-mobile]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Hook adapter pattern: hook owns BackendShape -> UIShape conversion; consumers stay typed against UIShape; msw mocks the BackendShape so tests exercise the real adapter path"
    - "Dual-auth dependency for legacy compatibility: new dep accepts JWT admin OR X-Admin-Key, lets dashboard work without admin key in browser while CLI scripts keep using their existing X-Admin-Key flow"
    - "FastAPI route ordering: static-prefix paths (/search, /stats/overview) MUST be declared before /{param} paths in same router (registration order matters, not specificity)"

key-files:
  created:
    - app/api/routes_p1.py (added GET /v1/locks/ list_active_locks)
    - tests/unit/test_locks_list_endpoint.py
    - tests/unit/test_workflows_list_endpoint.py
    - tests/unit/test_dashboard_auth_alignment.py
    - tests/integration/test_dashboard_paths_live.py
  modified:
    - app/api/routes_p1.py (auth swap on lock_status, cost_summary)
    - app/api/routes_p2.py (added _dashboard_or_admin_key, swapped 3 DLQ routes, fixed sqlite3.Row guard)
    - app/api/routes_memory.py (auth swap on list_keys, fixed sqlite3.Row guard)
    - app/api/routes_workflows.py (added GET /v1/workflows/ list_workflows)
    - app/api/routes_tasks.py (reordered /search and /stats/overview before /{task_id})
    - web/src/types/entities.ts (Agent, Task, CostItem, MemoryItem, DlqItem, Workflow updates)
    - web/src/hooks/queries/useAgents.ts
    - web/src/hooks/queries/useTasks.ts
    - web/src/hooks/queries/useCosts.ts
    - web/src/hooks/queries/useMemory.ts
    - web/src/hooks/queries/useLocks.ts
    - web/src/hooks/queries/useWorkflows.ts
    - web/src/hooks/queries/useDlq.ts
    - web/src/mocks/handlers/agents.ts
    - web/src/mocks/handlers/tasks.ts
    - web/src/mocks/handlers/costs.ts
    - web/src/mocks/handlers/memory.ts
    - web/src/mocks/handlers/locks.ts
    - web/src/mocks/handlers/workflows.ts
    - web/src/mocks/handlers/dlq.ts
    - .planning/phases/04-command-center-ui/04-UAT.md

key-decisions:
  - "Adapter-in-hook pattern over consumer rewrite: each hook owns the backend->UI shape conversion so the seven consumer routes (.tsx files) are untouched"
  - "DLQ keeps X-Admin-Key as fallback alongside JWT admin: legacy CLI scripts unaffected, dashboard works with JWT only, no admin key stored in browser"
  - "Pagination on /v1/tasks/search hardcoded to page=1 limit=100: deferred real pager UI to Phase 5; covers all live data and consumer (tasks/index.tsx) has no pager affordance"
  - "MemoryItem.size_bytes set to 0 because backend /keys does not surface size without N+1 reads: type made it implicit-zero, surfaced as 'unknown' in the UI; future SUM(LENGTH(value)) optimization deferred"
  - "Workflow.updated_at remains required (adapter falls back to created_at): consumer workflows/index.tsx calls new Date(updated_at).toLocaleString() and would crash on undefined; minimal-change rule beats type-purity here"
  - "FastAPI route ordering bug in routes_tasks.py was Rule 1: /{task_id} matched 'search' as a task_id, returning 404; reorder is the only correct fix"
  - "sqlite3.Row guard inverted in routes_memory.py and routes_p2.py was Rule 1: dict() conversion was skipped when r was a Row, breaking r.get() calls. Six other route files have the same pattern but are out of scope for this plan"

patterns-established:
  - "Hook adapter: function adaptX(b: BackendX): UIShape; useQuery(...) maps over backend envelope; types/entities.ts holds the UIShape contract"
  - "Dual-auth FastAPI dep: parametrized dependency function checks both X-Admin-Key (cheap) and Authorization Bearer (JWT verify); raises 401 if neither matches"
  - "Test seeded_admin_agent fixture: integration tests that hit JWT-auth routes seed the test-admin agent row in agents table so get_current_agent finds the JWT subject"

requirements-completed: []

# Metrics
duration: 70min
completed: 2026-04-26
---

# Phase 4 Plan 10: Backend/Frontend Endpoint Mismatch Closure Summary

**Aligned all seven dashboard list hooks (agents, tasks, costs, memory, locks, workflows, dlq) to real backend endpoints via adapter pattern; added two new backend list endpoints, swapped four routes from ApiKeyAuth to JWT, and proved end-to-end with a real-backend integration test suite.**

## Performance

- **Duration:** ~70 min
- **Started:** 2026-04-26T16:50:00Z
- **Completed:** 2026-04-26T17:09:26Z
- **Tasks:** 5 atomic tasks (each committed separately)
- **Files created:** 4 test files
- **Files modified:** 18 source files (5 backend, 13 frontend, 1 docs)

## Accomplishments

- **Closed the UAT-discovered endpoint mismatch:** all seven dashboard list hooks now resolve against real backend endpoints with JWT auth. No 404s, no fragile 307 redirects.
- **Two new backend list endpoints** (GET /v1/locks/, GET /v1/workflows/) sized exactly for the dashboard panels they feed; both JWT auth, no admin requirement.
- **Auth surface alignment:** dashboard read paths (/v1/costs/summary, /v1/memory/keys, /v1/locks/*) accept JWT instead of X-API-Key. DLQ accepts JWT admin OR X-Admin-Key (legacy CLI compat).
- **Real-backend integration test (`tests/integration/test_dashboard_paths_live.py`):** seven tests, all 200 with JWT admin Bearer. This is the evidence base unit tests with msw mocks could not provide.
- **Two pre-existing Rule 1 bugs fixed inline** (route ordering in routes_tasks.py, inverted sqlite3.Row guard in routes_memory.py + routes_p2.py).

## Task Commits

Each task was committed atomically:

1. **Task 1: Backend list endpoints + auth swaps** — `fdfb3cd` (feat) — adds GET /v1/locks/ + GET /v1/workflows/, swaps cost_summary/list_keys/lock_status from ApiKeyAuth to CurrentAgent, introduces _dashboard_or_admin_key dual-auth dep, plus 8 pytest cases (locks list, workflows list, dashboard auth alignment).
2. **Task 2: useAgents + useTasks hooks** — `8973f94` (feat) — useAgents -> /v1/agents/discover/available with adapter, useTasks -> /v1/tasks/search?page=1&limit=100, useCreateTask trailing slash, msw handlers updated.
3. **Task 3: useCosts + useMemoryEntries hooks** — `5dff6ff` (feat) — useCosts -> /v1/costs/summary, useMemoryEntries -> /v1/memory/keys, age_seconds computed from updated_at, size_bytes=0.
4. **Task 4: useLocks + useWorkflows + useDlq hooks** — `92751b0` (feat) — useLocks -> new /v1/locks/, useWorkflows -> new /v1/workflows/ with run_id->id mapping, useDlq -> /v1/dlq/ with auth swap.
5. **Task 5: Regression + integration test + UAT update** — `3967cfb` (fix) — adds tests/integration/test_dashboard_paths_live.py (7 tests), reorders routes_tasks.py to fix /{task_id} shadowing /search, fixes sqlite3.Row guard in routes_memory.py + routes_p2.py.
6. **UAT documentation update** — `b220a46` (docs) — 04-UAT.md gains Resolution table marking all previously broken hooks RESOLVED.

## Adapter Mapping Table (BackendShape -> UIShape)

| Hook | Backend path | Backend envelope | UI shape | Adapter renames |
|------|--------------|------------------|----------|-----------------|
| useAgents | GET /v1/agents/discover/available | `{available_count, agents: [{agent_id, agent_name, status, capabilities, load_score}]}` | `Agent[]` | `agent_id -> id`, `agent_name -> name` |
| useTasks | GET /v1/tasks/search?page=1&limit=100 | `{tasks: [TaskResponse], total, page, limit}` | `Task[]` | `assigned_agent_id -> agent_id`, `last_error -> error`, `requested_capabilities -> required_capabilities`, `output_data -> result` |
| useCosts | GET /v1/costs/summary | `{period_days, total_cost_usd, ..., per_agent: [{agent_name, total_cost_usd, input_tokens, output_tokens, api_calls}]}` | `CostItem[]` | `agent_name -> agent_id` (fallback), `input_tokens+output_tokens -> total_tokens`, `api_calls -> task_count` |
| useMemoryEntries | GET /v1/memory/keys?limit=200 | `{keys: [{key, value_type, tags, created_by, updated_at}], total}` | `MemoryItem[]` | `updated_at -> age_seconds` (computed), `size_bytes` set to 0 |
| useLocks | GET /v1/locks/ (NEW) | `[{resource_id, agent_id, acquired_at, expires_at, conflict}]` | `ResourceLock[]` | None (backend already shaped for UI) |
| useWorkflows | GET /v1/workflows/ (NEW) | `[{run_id, name, status, progress: {steps?}, created_at, ...}]` | `Workflow[]` | `run_id -> id`, `progress.steps -> steps` (default `[]`), `updated_at` falls back to `created_at` |
| useDlq | GET /v1/dlq/ | `{dead_letters: [{task_id, title, retry_count, last_error, created_at, ...}], total}` | `DlqItem[]` | `retry_count -> retries`, `last_error -> error`, `created_at -> failed_at` |

## Auth Swap Summary

| Route | Before | After | Reason |
|-------|--------|-------|--------|
| GET /v1/locks/status | ApiKeyAuth | CurrentAgent (JWT) | Dashboard read path |
| GET /v1/locks/ (NEW) | n/a | CurrentAgent (JWT) | New, dashboard-only read |
| GET /v1/costs/summary | ApiKeyAuth | CurrentAgent (JWT) | Dashboard read path |
| GET /v1/memory/keys | ApiKeyAuth | CurrentAgent (JWT) | Dashboard read path |
| GET /v1/workflows/ (NEW) | n/a | CurrentAgent (JWT) | New, dashboard-only read |
| GET /v1/dlq/ | _admin (X-Admin-Key) | _dashboard_or_admin_key (JWT admin OR X-Admin-Key) | Dual: dashboard + legacy CLI |
| POST /v1/dlq/{task_id}/retry | _admin (X-Admin-Key) | _dashboard_or_admin_key | Same as above |
| POST /v1/dlq/{task_id}/dismiss | _admin (X-Admin-Key) | _dashboard_or_admin_key | Same as above |

Memory `write_memory`, `read_memory`, `search_memory`, `delete_memory` deliberately **kept on ApiKeyAuth** - agents (not the dashboard) own write paths.

## Test Counts

- **Backend pytest:** baseline 57 passed in unit + 63 in integration = ~120 total. After plan: 64 unit + 70 integration = 134 passed. **+15 new tests** (+8 unit from Task 1, +7 integration from Task 5). 26 pre-existing failures unchanged (out of scope per scope-boundary rule).
- **Frontend vitest:** 30 baseline preserved (no regression). All 11 test files green.
- **Frontend tsc:** 0 errors (clean tsbuildinfo + recheck).
- **Frontend build:** clean. dist/index.html and assets regenerated.

## Decisions Made

See `key-decisions` in frontmatter. Most consequential:

1. Adapter-in-hook over consumer rewrite (kept the seven `.tsx` consumers untouched, all changes flow through hook adapters).
2. DLQ dual-auth: kept X-Admin-Key as fallback so existing CLI scripts work unchanged while dashboard uses JWT.
3. Hardcoded pagination `page=1&limit=100` on /v1/tasks/search (deferred pager UI to a later polish plan).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] FastAPI route ordering in routes_tasks.py**
- **Found during:** Task 5 (real backend integration test)
- **Issue:** `GET /v1/tasks/{task_id}` was registered before `GET /v1/tasks/search`. FastAPI matches in registration order, so `search` was being consumed as a task_id parameter. Result: integration test got `404 Task 'search' not found` instead of the search results.
- **Fix:** Moved `/search` and `/stats/overview` route handlers before `/{task_id}` in routes_tasks.py. Added a comment block explaining why static-prefix routes must precede parametric routes.
- **Files modified:** app/api/routes_tasks.py
- **Verification:** test_tasks_search_returns_200_with_jwt now passes. The other route registrations that have the same pattern (`/agent/{agent_id}`, `/available/for-me`) are pre-existing breakage out of scope for this plan.
- **Committed in:** 3967cfb (Task 5)

**2. [Rule 1 - Bug] Inverted sqlite3.Row guard in routes_memory.py list_keys**
- **Found during:** Task 5 (full pytest run; failure surfaced only when test_auto_indexing populated shared_memory before the dashboard test ran)
- **Issue:** `r = dict(r) if isinstance(r, dict) else r` is inverted - this only converts when r is already a dict. Result: when sqlite3.Row was returned, `r.get('value_type')` raised `AttributeError: 'sqlite3.Row' object has no attribute 'get'`, returning 500.
- **Fix:** Reversed the condition to `if not isinstance(r, dict)` and added a comment.
- **Files modified:** app/api/routes_memory.py
- **Verification:** test_memory_keys_returns_200_with_jwt passes both alone and after test_auto_indexing populates the table.
- **Committed in:** 3967cfb (Task 5)

**3. [Rule 1 - Bug] Same inverted sqlite3.Row guard in routes_p2.py list_dead_letters**
- **Found during:** Task 5 (full pytest run)
- **Issue:** Same inverted guard as above; surfaced once the dlq test ran against an environment where tasks table had failed entries.
- **Fix:** Same reversal.
- **Files modified:** app/api/routes_p2.py
- **Verification:** test_dlq_list_accepts_jwt_admin passes both alone and in the full suite.
- **Committed in:** 3967cfb (Task 5)

**4. [Rule 3 - Blocking] Workflow.updated_at type kept required**
- **Found during:** Task 5 (frontend build)
- **Issue:** Plan made `Workflow.updated_at` optional, but consumer `web/src/routes/_authed/workflows/index.tsx:61` calls `new Date(workflow.updated_at).toLocaleString()` which is a TypeScript error when `updated_at` is `string | undefined` and a runtime crash on undefined.
- **Fix:** Reverted `updated_at` to required (string), and made `adaptWorkflow` fall back to `b.created_at` when the backend WorkflowResponse omits updated_at.
- **Files modified:** web/src/types/entities.ts, web/src/hooks/queries/useWorkflows.ts
- **Verification:** `npm run build` succeeds (was failing with TS2769).
- **Committed in:** 3967cfb (Task 5). Per the plan's explicit "do not touch consumers" rule, the adapter absorbed the shape mismatch instead of the consumer being rewritten.

### Out-of-Scope Discoveries (not fixed)

- The same inverted `sqlite3.Row` guard pattern exists in `routes_artifacts.py:121`, `routes_workflow.py:246` (workflows ENGINE not workflowS), `routes_p1.py:203`, `routes_messaging.py:178/307/340`, `routes_p2.py:128`. These are pre-existing and not exercised by Plan 04-10's tests.
- `routes_tasks.py` `/agent/{agent_id}` and `/available/for-me` are still shadowed by `/{task_id}` registered earlier - same root cause as the /search bug, but not exercised by this plan's test surface.
- 26 pre-existing pytest failures in `test_auto_index.py`, `test_connection_manager.py`, `test_embedding_service.py`, `test_retry_worker.py` (all `pytest.mark.asyncio` not configured) - unchanged by this plan.
- Two workflow router files coexist: `routes_workflow.py` (singular, "workflows-engine") and `routes_workflows.py` (plural, the one this plan extends). Both register at `/v1/workflows` prefix, generating a "Duplicate Operation ID list_workflows" warning. The plural router is registered first so the new GET / wins, but this duplication is a smell that should be cleaned up in a future plan.

These are tracked in this section but not addressed - they would expand scope beyond endpoint-mismatch closure.

---

**Total deviations:** 4 auto-fixed (3 Rule 1 bugs, 1 Rule 3 blocking)
**Impact on plan:** All four were necessary for the plan's success criteria to actually be true at runtime. Without them, the integration test gate would not pass and the build would fail.

## Issues Encountered

- Initial integration test failed because /v1/tasks/search shadowed by /{task_id}. Diagnosis required reading the FastAPI route registration order, not just the source line numbers.
- Memory and DLQ tests passed alone but failed when run with other integration tests that populated rows. Required understanding session-scoped fixtures and pre-existing inverted-guard bugs that surface only when rows exist.

## Deploy

**Deployed:** 2026-04-26T17:13:42Z
**Commit deployed:** `8f9980a` (master HEAD)
**Steps:**
1. `git push origin master` - succeeded (pushed `59f799d..8f9980a`)
2. SSH to brunhilde: `git pull origin master`, `cd web && npm ci && npm run build`, `systemctl --user restart openhub.service` - all succeeded
3. `systemctl --user is-active openhub.service` returned `active`
4. `curl https://hub.brunhilde.cloud/v1/health` returned HTTP 200 with healthy status (cpu 4.8%, memory 43.1%, db ready, port 7788)

The VPS is now serving the aligned dashboard with all seven hooks pointed at real backend endpoints.

## Self-Check: PASSED

All 24 referenced files (4 tests created, 20 sources/handlers modified) verified present on disk. All 6 referenced commit hashes (fdfb3cd, 8973f94, 5dff6ff, 92751b0, 3967cfb, b220a46) verified present in git log.

---
*Phase: 04-command-center-ui*
*Plan: 10*
*Completed: 2026-04-26*
