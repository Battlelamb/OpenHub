---
phase: 04-command-center-ui
plan: 04
subsystem: ui
tags: [react, tanstack-query, websocket, zustand, i18next, msw, typescript]

# Dependency graph
requires:
  - phase: 04-command-center-ui/04-01
    provides: Vite/React bootstrap, msw handlers.ts, cn.test.ts sanity
  - phase: 04-command-center-ui/04-02
    provides: AppShell, Topbar, ReconnectingBanner, uiStore.setWsStatus, i18n common/nav namespaces
  - phase: 04-command-center-ui/04-03
    provides: authStore, api<T> wrapper, router-ref
  - phase: 02-websocket-test-suite
    provides: "D-01 event envelope, D-03 first-frame JWT auth, D-05 hybrid sync, D-06 rehydrate on reconnect"
provides:
  - Centralized TanStack Query key factory (qk) for all resources
  - Typed entity shapes (Agent, Task, Workflow, DlqItem, CostItem, MemoryItem, ResourceLock, HealthResponse)
  - Query hooks for agents, tasks (with mutations), workflows, health (10s poll), dlq (with retry mutation), costs, memory, locks
  - useWebSocketSync hook with first-frame JWT auth, hybrid merge/invalidate dispatch, exponential backoff with jitter
  - Per-feature i18n namespace modules (EN + TR) for 9 feature areas
  - Per-feature msw handler modules aggregated by handlers.ts for 9 feature areas
  - AppShell mounts the WS hook; Topbar health dot wired to useHealth
affects: [04-05, 04-05b, 04-06, 04-07, 04-08]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Query key factory (qk): centralized, typed, composable keys consumed by both queries and WS dispatch"
    - "Hybrid WS sync (D-05): setQueryData for critical events, invalidateQueries for non-critical"
    - "First-frame JWT auth (D-03): token sent as first WebSocket frame payload; never in URL"
    - "Rehydrate on reconnect (D-06): queryClient.invalidateQueries() on server `connected` welcome frame"
    - "Exponential backoff with jitter: min(30s, 1s * 2^attempt) * (0.5 + random*0.5)"
    - "Per-feature i18n modules: one EN file + one TR sibling (`{area}.ts` + `{area}.tr.ts`) so Wave 4 plans own their namespace without touching i18n/index.ts"
    - "Per-feature msw handler modules: handlers.ts spreads per-area arrays so Wave 4 plans only touch handlers/{area}.ts"

key-files:
  created:
    - web/src/lib/query-keys.ts
    - web/src/types/entities.ts
    - web/src/hooks/queries/useAgents.ts
    - web/src/hooks/queries/useTasks.ts
    - web/src/hooks/queries/useWorkflows.ts
    - web/src/hooks/queries/useHealth.ts
    - web/src/hooks/queries/useDlq.ts
    - web/src/hooks/queries/useCosts.ts
    - web/src/hooks/queries/useMemory.ts
    - web/src/hooks/queries/useLocks.ts
    - web/src/hooks/useWebSocketSync.ts
    - web/src/hooks/useWebSocketSync.test.ts
    - web/src/hooks/useHealth.test.ts
    - web/src/i18n/namespaces/agents.ts
    - web/src/i18n/namespaces/agents.tr.ts
    - web/src/i18n/namespaces/tasks.ts
    - web/src/i18n/namespaces/tasks.tr.ts
    - web/src/i18n/namespaces/workflows.ts
    - web/src/i18n/namespaces/workflows.tr.ts
    - web/src/i18n/namespaces/dlq.ts
    - web/src/i18n/namespaces/dlq.tr.ts
    - web/src/i18n/namespaces/costs.ts
    - web/src/i18n/namespaces/costs.tr.ts
    - web/src/i18n/namespaces/memory.ts
    - web/src/i18n/namespaces/memory.tr.ts
    - web/src/i18n/namespaces/locks.ts
    - web/src/i18n/namespaces/locks.tr.ts
    - web/src/i18n/namespaces/health.ts
    - web/src/i18n/namespaces/health.tr.ts
    - web/src/i18n/namespaces/settings.ts
    - web/src/i18n/namespaces/settings.tr.ts
    - web/src/mocks/handlers/agents.ts
    - web/src/mocks/handlers/tasks.ts
    - web/src/mocks/handlers/workflows.ts
    - web/src/mocks/handlers/dlq.ts
    - web/src/mocks/handlers/costs.ts
    - web/src/mocks/handlers/memory.ts
    - web/src/mocks/handlers/locks.ts
    - web/src/mocks/handlers/health.ts
    - web/src/mocks/handlers/settings.ts
  modified:
    - web/src/components/layout/AppShell.tsx
    - web/src/components/layout/Topbar.tsx
    - web/src/i18n/index.ts
    - web/src/mocks/handlers.ts

key-decisions:
  - "WS URL construction is factored into exported buildWsUrl() so tests can assert it never contains ?token= (Phase 2 D-03 compliance by construction, not convention)."
  - "handleEvent is extracted from the hook body and takes queryClient as a param, so dispatch logic is pure and unit-testable without mounting the hook."
  - "i18n shipped with real EN+TR strings per feature rather than empty stubs, so Wave 4 feature plans inherit a baseline instead of writing copy from scratch."
  - "Per-feature i18n split into two sibling files ({area}.ts + {area}.tr.ts) each default-exporting a flat object, rather than one module exporting {en, tr}. Simpler per-locale ownership; still collision-free for Wave 4."
  - "mocks/handlers.ts aggregator imports per-area files directly and exports a flat spread; no separate handlers/index.ts barrel was added (one less indirection)."
  - "Plan's atomic-per-task commit rule was not followed; backfilled SUMMARY.md documents the squashed delivery."

patterns-established:
  - "All TanStack Query keys flow through the qk factory; no raw arrays in queryKey positions."
  - "WS event handlers use qk.*() functions so the query-key contract is shared between fetchers and the WS sync layer - a key rename is a single-file change."
  - "Feature-plan ownership boundary: Wave 4 plans edit only their own i18n/namespaces/{area}[.tr].ts and mocks/handlers/{area}.ts. Aggregators (i18n/index.ts, mocks/handlers.ts) are frozen."

requirements-completed: ["UI-08", "UI-16"]

# Metrics
duration: unknown (backfill)
completed: 2026-04-13
---

# Phase 4 - Plan 04 Summary: Data Layer (TanStack Query + WebSocket Sync)

**Centralized qk factory, typed entity shapes, nine query hooks, and a single useWebSocketSync hook with D-03 first-frame JWT auth and D-05 hybrid merge/invalidate - all wired into AppShell/Topbar.**

## Performance

- **Duration:** unknown (backfill)
- **Completed:** 2026-04-13
- **Commit timestamp:** 2026-04-13T17:35:07+03:00
- **Tasks:** 4 (all delivered in one squashed commit)
- **Files created:** 40
- **Files modified:** 4

## Accomplishments

- `qk` query-key factory with typed keys for agents, tasks (all/list/detail/trace), workflows, health, dlq, costs, memory, locks
- TanStack Query hooks for every backend resource, including mutations (useCreateTask, useCancelTask, useRetryDlq) and polled health (useHealth, 10s interval)
- `useWebSocketSync` hook implementing Phase 2 D-03 (first-frame JWT), D-05 (hybrid setQueryData / invalidateQueries dispatch), and D-06 (queryClient.invalidateQueries() on `connected` welcome) with exponential-backoff-with-jitter reconnect
- Typed entity shapes shared across the app in `web/src/types/entities.ts`
- Wave 4 extension-point scaffolds: per-feature i18n namespace modules (EN + TR) and per-feature msw handler modules for 9 areas
- AppShell mounts `useWebSocketSync()` once; Topbar health dot reads `useHealth().data?.status === 'ok'`

## WS Event Dispatch Table

| Event | Action | Rationale |
|-------|--------|-----------|
| `connected` | setWsStatus('connected'); attempt=0; queryClient.invalidateQueries() | D-06 full rehydrate on (re)connect |
| `agent_status_changed` | setQueryData(qk.agents.all, ...); setQueryData(qk.agents.detail(id), ...) | D-05 critical: optimistic merge |
| `task_status_changed` | setQueryData(qk.tasks.all, ...); setQueryData(qk.tasks.detail(id), ...) | D-05 critical: optimistic merge |
| `task_progress` | setQueryData(qk.tasks.detail(id), ...) | D-05 critical: optimistic merge |
| `workflow_step_changed` | invalidateQueries({ queryKey: qk.workflows.detail(id) }) | Refetch the workflow detail |
| `heartbeat` | invalidateQueries({ queryKey: qk.agents.all, refetchType: 'none' }) | D-05 non-critical: mark stale, don't refetch |
| `metadata_changed` | invalidateQueries({ queryKey: [entity] }) | Generic fallback |
| `token_expiring` | toast.warning | User-facing session warning |
| `error` | toast.error | Server-forwarded error |
| on `close` | setWsStatus('reconnecting'); schedule reconnect with jittered backoff | max delay 30s |

## Phase 2 D-03 Compliance Proof

- `web/src/hooks/useWebSocketSync.ts` exports `buildWsUrl()` which returns `${proto}//${host}/v1/ws/ui` - no query-string token
- On `ws.onopen` the hook sends `ws.send(JSON.stringify({ type: 'auth', token }))` as the first frame
- Test assertion in `useWebSocketSync.test.ts`: `expect(url).not.toContain('?token')` and `expect(url).not.toContain('token=')`
- Second test: `expect(JSON.parse(ws.sent[0])).toEqual({ type: 'auth', token: 'my-jwt' })`

## Task Commits

All four planned tasks were delivered in a single retrospective commit. The plan's atomic-per-task commit rule was not followed.

1. **Single squashed commit:** `9885ed5` - "Phase 4 Wave 3: Data layer with TanStack Query hooks and WebSocket sync"

_Note: All tasks squashed into a single retrospective commit; SUMMARY.md backfilled afterward._

## Files Created/Modified

### Created
- `web/src/lib/query-keys.ts` - `qk` factory for all query keys
- `web/src/types/entities.ts` - Agent, Task, Workflow, WorkflowStep, DlqItem, CostItem, MemoryItem, ResourceLock, HealthResponse
- `web/src/hooks/queries/useAgents.ts` - useAgents(), useAgent(id)
- `web/src/hooks/queries/useTasks.ts` - useTasks(filters), useTask(id), useCreateTask, useCancelTask
- `web/src/hooks/queries/useWorkflows.ts` - useWorkflows(), useWorkflow(id)
- `web/src/hooks/queries/useHealth.ts` - useHealth() with 10s refetchInterval
- `web/src/hooks/queries/useDlq.ts` - useDlq(), useRetryDlq
- `web/src/hooks/queries/useCosts.ts` - useCosts()
- `web/src/hooks/queries/useMemory.ts` - useMemoryEntries()
- `web/src/hooks/queries/useLocks.ts` - useLocks()
- `web/src/hooks/useWebSocketSync.ts` - WS lifecycle with hybrid merge/invalidate, first-frame auth, backoff+jitter reconnect
- `web/src/hooks/useWebSocketSync.test.ts` - 3 tests: URL safety, first-frame auth payload, cache mutation on event
- `web/src/hooks/useHealth.test.ts` - msw-backed fetch test
- `web/src/i18n/namespaces/{agents,tasks,workflows,dlq,costs,memory,locks,health,settings}.ts` - English namespaces (real strings)
- `web/src/i18n/namespaces/{agents,tasks,workflows,dlq,costs,memory,locks,health,settings}.tr.ts` - Turkish sibling files (real strings)
- `web/src/mocks/handlers/{agents,tasks,workflows,dlq,costs,memory,locks,health,settings}.ts` - per-feature handler arrays

### Modified
- `web/src/components/layout/AppShell.tsx` - `useWebSocketSync()` call added
- `web/src/components/layout/Topbar.tsx` - `useHealth()` replaces the placeholder `healthOk = true`
- `web/src/i18n/index.ts` - registers 9 feature namespaces inline in the `resources` config (both EN and TR)
- `web/src/mocks/handlers.ts` - refactored to import and spread the 9 per-feature handler arrays

## Decisions Made

- Plan's atomic-per-task commit rule was not followed; backfilled SUMMARY.md documents the squashed delivery.
- The plan proposed a single `namespaces/{area}.ts` per feature exporting `{en, tr}` empty stubs registered via `i18n.addResourceBundle`. The implementation instead shipped two sibling files per feature (`{area}.ts` for EN, `{area}.tr.ts` for TR), each default-exporting a flat object, with real translations already populated. Registration was done inline in the `i18n.init({ resources })` config rather than via post-init `addResourceBundle` calls. Net effect is equivalent for Wave 4 (each namespace still owned by a single per-feature file); this is simpler on one axis and more opinionated on another.
- The plan proposed a `web/src/mocks/handlers/index.ts` barrel file. The implementation skipped it - `handlers.ts` imports each per-area file directly. One fewer indirection; Wave 4 collision boundary is unchanged.
- The plan told Task 4 to preserve a bootstrap `/v1/health` handler in `handlers.ts`. The implementation moved that responsibility into `mocks/handlers/health.ts` so the aggregator has zero inline handlers. The sanity behavior is preserved (the handler still ships in the default export), just via a different file.
- `buildWsUrl` is a standalone exported function so the D-03 compliance test can assert it directly without standing up the hook.

## Deviations from Plan

### Auto-fixed Issues

**1. [Shape deviation - i18n namespace layout] Split per-feature module into EN + TR sibling files**
- **Found during:** Task 4 (i18n + msw scaffolding)
- **Plan specified:** One file per area exporting `export const en: Record<string, unknown> = {}` and `export const tr: Record<string, unknown> = {}`, then registered post-init via `i18n.addResourceBundle(lng, ns, bundle.en/tr)`
- **Shipped instead:** Two files per area - `{area}.ts` (EN default export) and `{area}.tr.ts` (TR default export) - each containing real translations, registered inline in the `resources` object of `i18n.init(...)`
- **Why this is fine:** Wave 4 plans still own a dedicated file per namespace (collision-free) and `i18n/index.ts` is still frozen after Plan 04. The ownership contract is preserved.
- **Files affected:** `web/src/i18n/index.ts` and all 18 files under `web/src/i18n/namespaces/`

**2. [Missing artifact - msw barrel] `mocks/handlers/index.ts` not created**
- **Found during:** Task 4 (msw scaffolding)
- **Plan specified:** A barrel file `web/src/mocks/handlers/index.ts` re-exporting all 9 handler arrays, imported by `handlers.ts` as `./handlers/index`
- **Shipped instead:** `handlers.ts` imports each per-area file directly (`./handlers/agents`, `./handlers/tasks`, ...) and spreads them into the `handlers` export
- **Why this is fine:** The shared-file conflict surface (`handlers.ts`) is still frozen; Wave 4 plans still only touch `handlers/{area}.ts`. The barrel was an implementation hint, not a contract.
- **Files affected:** `web/src/mocks/handlers.ts`

**3. [Location change - bootstrap handler] `/v1/health` stub moved from handlers.ts to handlers/health.ts**
- **Found during:** Task 4 (msw scaffolding)
- **Plan specified:** Keep Plan 01's `/v1/health` stub as a `bootstrapHandlers` array inside `handlers.ts`
- **Shipped instead:** The `/v1/health` handler lives in `web/src/mocks/handlers/health.ts`; `handlers.ts` has no inline handlers
- **Why this is fine:** The handler still ships in the default `handlers` export (health.ts is spread), so `useHealth.test.ts` and any Plan 01 sanity test that hits `/v1/health` via msw still pass. The `health` namespace owner (Plan 04-06) can extend its own file without touching the aggregator.

---

**Total deviations:** 3 (all shape-only; ownership contract and Wave 4 conflict-avoidance goal fully preserved)
**Impact on plan:** None on correctness or on downstream plans. Wave 4 per-area ownership boundary still holds.

## Issues Encountered

None documented. Commit message claims green typecheck, 22 tests passing (4 added in this plan), and 526 KB JS bundle after build.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Wave 4 plans (04-05 Agents+Workflows, 04-05b Tasks, 04-06 Visibility) can consume `useAgents`, `useTasks`, `useCreateTask`, `useCancelTask`, `useWorkflows`, `useDlq`, `useRetryDlq`, `useCosts`, `useMemoryEntries`, `useLocks` with fully typed data and live WS-driven updates.
- They can extend i18n and msw by editing only their own per-area files under `web/src/i18n/namespaces/` and `web/src/mocks/handlers/`. `i18n/index.ts` and `mocks/handlers.ts` are frozen for the rest of Phase 04.
- The Topbar health dot is live against `/v1/health`; the WS status banner is driven by `useUIStore.setWsStatus` from the WS hook.

---
*Phase: 04-command-center-ui*
*Plan: 04-04*
*Completed: 2026-04-13 (backfill written later)*
