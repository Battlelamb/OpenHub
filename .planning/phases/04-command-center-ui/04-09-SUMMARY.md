---
phase: 04-command-center-ui
plan: 09
subsystem: ui
tags: [fastapi, tanstack-query, react, trace, msw, pytest, vitest, typescript]

# Dependency graph
requires:
  - phase: 04-command-center-ui/04-04
    provides: qk factory (qk.tasks.trace already defined), api<T> wrapper, TanStack Query hook pattern (useTask)
  - phase: 04-command-center-ui/04-05b
    provides: Task detail route, TraceTimeline component, initial tasks i18n namespace with trace.emptyHeading/emptyBody
provides:
  - Backend endpoint GET /v1/tasks/{task_id}/trace returning TraceSpan[] from trace_events
  - TraceSpan + TraceCategory types hoisted to web/src/types/entities.ts (single source of truth)
  - useTaskTrace(taskId) TanStack Query hook
  - TraceSection wrapper in tasks/$taskId.tsx with loading (animate-pulse), error (role=alert), empty (TraceTimeline default), data states
  - msw handler /v1/tasks/:id/trace seeding 3 realistic spans for dev + tests
  - i18n tasks.trace.loading and tasks.trace.errorTitle (EN + TR)
  - UI-12 closed in REQUIREMENTS.md checklist and traceability table
affects: [Phase 5]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "TraceSpan as a canonical type in web/src/types/entities.ts; TraceTimeline and useTaskTrace both import it - removes two-file drift risk"
    - "useTaskTrace mirrors useTask verbatim: enabled guard, ['tasks','none','trace'] disabled-key fallback, qk.tasks.trace(taskId) live key"
    - "TraceSection component extracts loading/error/empty/data branching from the detail page so the route stays declarative"
    - "msw-specific-before-generic: /v1/tasks/:id/trace handler placed BEFORE /v1/tasks/:id to prevent order-dependent swallowing"
    - "event_type=error takes precedence over data.category in the backend row->span mapping; unknown categories fall back to 'internal' (neutral zinc timeline row)"

key-files:
  created:
    - tests/unit/test_task_trace_endpoint.py
    - web/src/hooks/queries/useTaskTrace.ts
    - web/src/hooks/queries/useTaskTrace.test.ts
  modified:
    - app/api/routes_tasks.py
    - web/src/types/entities.ts
    - web/src/components/common/TraceTimeline.tsx
    - web/src/routes/_authed/tasks/$taskId.tsx
    - web/src/mocks/handlers/tasks.ts
    - web/src/i18n/namespaces/tasks.ts
    - .planning/REQUIREMENTS.md

key-decisions:
  - "Backend endpoint over schema change or WebSocket event. Adding GET /v1/tasks/{id}/trace is a direct inverse of the existing POST /v1/traces/event: zero schema work, zero ws plumbing, reads rows that agents can already write. Schema change was out of scope for a gap closure; a trace_span_added WS event would have required Phase 2 protocol changes we can't absorb here."
  - "Optional JWT auth (CurrentAgent = None) over ApiKeyAuth to match the rest of routes_tasks.py. The dashboard authenticates with JWT; ApiKeyAuth would have broken the UI consumer."
  - "Bare List[Dict] return shape (not {events: [...]}) so the UI consumes the raw array without an extra .events dereference; matches the shape TraceTimeline already expects."
  - "TraceSpan hoisted to entities.ts rather than re-declared in useTaskTrace.ts. A component and a hook depending on the same shape must not keep independent copies - this avoids a silent drift between what the hook returns and what TraceTimeline renders."
  - "Skeleton fallback: animate-pulse zinc-800 divs instead of shadcn Skeleton. web/src/components/ui/skeleton.tsx is not installed (confirmed via ls); running `npx shadcn@latest add skeleton` would have introduced a new dependency outside this plan's files_modified scope for a single loading indicator. The fallback matches Skeleton's visual (same background token, same animation) and the plan's own 'if Skeleton missing, use animate-pulse' escape hatch."
  - "useTaskTrace.test.ts (.ts not .tsx) with React.createElement wrapper instead of JSX. Matches useHealth.test.ts sibling convention in this repo; rewriting to .tsx was unnecessary. Two existing .ts hook tests already use this exact pattern."

patterns-established:
  - "Frontend: any resource hook fetching a backend endpoint should live under web/src/hooks/queries/ and re-use qk.<resource>.<shape>(...) from lib/query-keys.ts - adding a new hook is a single-file change with no registration step."
  - "Frontend: when a component-internal type needs to be consumed by a query hook too, hoist it to web/src/types/entities.ts rather than duplicating."
  - "Backend: routes that serve UI should use CurrentAgent = None (optional JWT) rather than ApiKeyAuth unless they're strictly agent-to-hub."

requirements-completed: ["UI-12"]

# Metrics
duration: 45min
completed: 2026-04-19
---

# Phase 4 Plan 09: UI-12 Trace Viewer Gap Closure Summary

**Closed the last Phase 4 code gap: TraceTimeline now receives real spans from a new GET /v1/tasks/{task_id}/trace endpoint via a useTaskTrace TanStack Query hook, instead of the hardcoded spans={[]} that the verifier flagged.**

## Performance

- **Duration:** ~45 minutes (single executor session)
- **Completed:** 2026-04-19
- **Tasks:** 3 (all committed atomically per plan)
- **Files created:** 3
- **Files modified:** 7

## Accomplishments

- New backend endpoint `GET /v1/tasks/{task_id}/trace` (app/api/routes_tasks.py) returning a List[Dict] shaped as `TraceSpan[]` from the existing `trace_events` table, filtered by `task_id` and ordered by `created_at ASC`. Zero schema change.
- Row-to-span mapping (`_trace_row_to_span`) handles:
  - `event_type == "error"` -> category = "error" (overrides data.category)
  - `data.category` in (llm, tool, db, http, internal, error) flows through
  - Anything else falls back to "internal" (neutral zinc timeline row, no crash)
  - `data.level` typecasts to int with 0 fallback; `completed_at` read from data
- `TraceSpan` + `TraceCategory` types hoisted from `TraceTimeline.tsx` to `web/src/types/entities.ts` - component and hook now share a single definition.
- `useTaskTrace(taskId)` hook at `web/src/hooks/queries/useTaskTrace.ts` mirrors `useTask`'s shape: `enabled: !!taskId`, `['tasks','none','trace']` disabled-key, `qk.tasks.trace(taskId)` live key, types as `TraceSpan[]`.
- `TraceSection` wrapper component in `tasks/$taskId.tsx` owns the loading/error/empty/data branching so the route stays declarative.
- msw handler seeds a realistic 3-span mock (tool + llm + tool at two indent levels) for dev and vitest.
- i18n: `tasks.trace.loading` and `tasks.trace.errorTitle` in EN + TR (no em dashes, per project rule).
- UI-12 flipped to `[x]`/Complete in `REQUIREMENTS.md` (checklist line 54 and traceability table line 162).

## Backend endpoint decision rationale

Three options were on the table; this plan locked option (d) over (a)/(b)/(c):

| Option | Why rejected |
|--------|-------------|
| (a) Add new columns to `tasks` and store spans inline | Schema change; requires Alembic migration + repo changes; heavy for a gap closure. |
| (b) Broadcast a new `trace_span_added` WebSocket event | Would require Phase 2 WS protocol addition; `useWebSocketSync.ts` dispatch table has no slot; out of scope. |
| (c) Pure frontend mock, keep UI empty in prod | Fails success criterion 5 ("show real data") the moment a real backend has spans. |
| (d) **Inverse read of `POST /v1/traces/event`**: new `GET /v1/tasks/{task_id}/trace` reading `trace_events.task_id` | Zero schema change, zero protocol change, reuses the existing `get_trace` pattern in `routes_p1.py:148`. **Chosen.** |

The key insight: `trace_events.task_id` already exists per `alembic/versions/0001_initial_schema.py:149-155`. Agents already write rows with `task_id` via `POST /v1/traces/event`. The missing piece was purely a read-by-task-id endpoint - the direct inverse of the existing write path.

## Before / after: the one-line fix

**Before** (`web/src/routes/_authed/tasks/$taskId.tsx:72`):

```tsx
<div>
  <h2 className="text-lg font-medium text-zinc-50 mb-4">Trace</h2>
  <TraceTimeline spans={[]} />
</div>
```

**After** (same location, plus a local `TraceSection` component at the bottom of the file):

```tsx
<div>
  <h2 className="text-lg font-medium text-zinc-50 mb-4">Trace</h2>
  <TraceSection taskId={taskId} />
</div>

// ...

function TraceSection({ taskId }: { taskId: string }) {
  const { t } = useTranslation('tasks')
  const { data, isLoading, error } = useTaskTrace(taskId)

  if (isLoading) {
    return (
      <div aria-label={t('trace.loading')} className="space-y-2">
        <div className="h-6 w-2/3 rounded bg-zinc-800 animate-pulse" />
        <div className="h-6 w-1/2 rounded bg-zinc-800 animate-pulse" />
        <div className="h-6 w-3/4 rounded bg-zinc-800 animate-pulse" />
      </div>
    )
  }

  if (error) {
    const title = error instanceof ApiError ? error.problem.title : t('trace.errorTitle')
    const detail = error instanceof ApiError ? error.problem.detail : String(error)
    return (
      <div role="alert" className="rounded-lg border border-red-500/50 bg-red-500/10 p-4">
        <div className="text-sm font-medium text-red-400">{title}</div>
        {detail ? <div className="text-xs text-red-400/80 mt-1">{detail}</div> : null}
      </div>
    )
  }

  return <TraceTimeline spans={data ?? []} />
}
```

## REQUIREMENTS.md diff

```diff
- [ ] **UI-12**: Distributed trace viewer in task detail showing tool calls, sub-steps, timing
+ [x] **UI-12**: Distributed trace viewer in task detail showing tool calls, sub-steps, timing
```

```diff
- | UI-12 | Phase 4 | Pending |
+ | UI-12 | Phase 4 | Complete |
```

Stale entries for UI-03/04/05/06/07/09/15/16 noted in `04-VERIFICATION.md` gap 2 were already addressed by an earlier doc commit (`ea0d57f`); nothing else to flip here.

## Test results

**Backend (new):** `python -m pytest tests/unit/test_task_trace_endpoint.py -v --no-cov` -> **2 passed**
- `test_task_trace_returns_empty_list_when_no_spans`: GET with no rows returns `[]` (not 404).
- `test_task_trace_returns_shaped_spans_when_rows_exist`: inserts two rows, asserts id/name/category/duration_ms/level/started_at all present, asserts `event_type='error'` overrides to `category='error'`, and asserts `ORDER BY created_at ASC`.

**Backend (regression):** baseline run on this branch without my changes reports 55 passed / 26 failed. Same run with my changes reports **57 passed / 26 failed**. **Zero regressions; +2 new passes.** The 26 failures are pre-existing (vector/Turso and connection_manager suites; unrelated to UI-12).

**Frontend:** `cd web && npm run test -- --run` -> **30/30 passed** across 11 test files. Baseline before this plan was 28/28 across 10 files; the delta is the 2 new `useTaskTrace.test.ts` cases (plus its new test file).

**Typecheck:** `npx tsc --noEmit` exits 0.

**Production build:** `npm run build` exits 0 (723.29 kB JS, 35.46 kB CSS; identical footprint to 04-08).

## Task commits

1. `8c5cd7d` - feat(04-09): add GET /v1/tasks/{task_id}/trace endpoint (UI-12)
   - `app/api/routes_tasks.py` (endpoint + `_trace_row_to_span`)
   - `tests/unit/test_task_trace_endpoint.py` (2 pytest cases)

2. `8be2099` - feat(04-09): add useTaskTrace hook + TraceSpan type + msw mock (UI-12)
   - `web/src/types/entities.ts` (+TraceSpan, +TraceCategory)
   - `web/src/components/common/TraceTimeline.tsx` (import instead of redeclare)
   - `web/src/hooks/queries/useTaskTrace.ts` (new hook)
   - `web/src/hooks/queries/useTaskTrace.test.ts` (2 vitest cases, `.ts` + `React.createElement`)
   - `web/src/mocks/handlers/tasks.ts` (new trace handler inserted before `:id`)
   - `web/src/i18n/namespaces/tasks.ts` (+trace.loading, +trace.errorTitle EN/TR)

3. `fabf304` - feat(04-09): wire useTaskTrace into task detail + flip UI-12 to Complete
   - `web/src/routes/_authed/tasks/$taskId.tsx` (TraceSection; removes `spans={[]}`)
   - `.planning/REQUIREMENTS.md` (checklist + traceability table flip)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocker] Added `seeded_admin_agent` fixture to the backend test file**
- **Found during:** Task 1 verification - `python -m pytest tests/unit/test_task_trace_endpoint.py` returned 401 ("Agent not found or deactivated") instead of 200.
- **Issue:** The plan's reference pattern `current_agent: CurrentAgent = None` does NOT disable auth when a bearer token is sent. The `CurrentAgent = Annotated[AuthenticatedAgent, Depends(get_current_agent)]` dep always runs if credentials are present, and `get_current_agent` looks up `sub='test-admin'` in the `agents` table. Conftest's session DB starts empty, so the lookup fails with 401.
- **Fix:** Ported the `seeded_admin_agent` fixture pattern from `tests/integration/test_auto_indexing.py` into `tests/unit/test_task_trace_endpoint.py`. It INSERTs a `test-admin` agent row if missing, is idempotent across tests, and is scoped to this test file only.
- **Files modified:** `tests/unit/test_task_trace_endpoint.py` (fixture added)
- **Commit:** `8c5cd7d`

**2. [Shape deviation - checker R-2] Used animate-pulse div fallback instead of shadcn Skeleton**
- **Found during:** Task 3 file setup - `ls web/src/components/ui/` confirmed `skeleton.tsx` is not present (only alert-dialog/badge/button/card/dialog/dropdown-menu/form/input/label/select/separator/sheet/sonner/table/textarea/tooltip).
- **Plan specified:** Import `{ Skeleton } from '@/components/ui/skeleton'`.
- **Shipped instead:** Three `<div className="h-6 w-... rounded bg-zinc-800 animate-pulse" />` placeholders inside an aria-labeled container. Same visual (zinc-800 + animate-pulse), no new shadcn install, same i18n aria-label.
- **Why this is fine:** The plan itself listed this exact fallback as an acceptable path. Adding Skeleton via `npx shadcn@latest add skeleton` would have added files outside the plan's declared `files_modified` list and introduced a dep for a single loading indicator.
- **Files modified:** `web/src/routes/_authed/tasks/$taskId.tsx`
- **Commit:** `fabf304`

**3. [Shape deviation - checker R-1] Kept useTaskTrace.test.ts as `.ts` and used `React.createElement` wrapper**
- **Found during:** Task 2 setup - reviewed sibling hook tests (`useWebSocketSync.test.ts`, `useHealth.test.ts`) to match convention.
- **Plan specified:** `.ts` filename but used JSX `<QueryClientProvider>` in the sample body.
- **Shipped instead:** `.ts` filename + `React.createElement(QueryClientProvider, { client: qc }, children)` wrapper (exactly mirroring `useHealth.test.ts`).
- **Why this is fine:** Existing sibling hook tests in the repo use this pattern; no JSX in `.ts` (vite/vitest would have rejected it or required a rename). Zero behavior difference at runtime.
- **Files modified:** `web/src/hooks/queries/useTaskTrace.test.ts`
- **Commit:** `8be2099`

---

**Total deviations:** 3 (1 blocker fix + 2 shape fixes).
**Impact on plan:** All behaviorally equivalent. Tests green, types green, build green. Plan `must_haves.truths` all satisfied.

## Issues encountered

### Pre-existing baseline failures (documented, not caused by this plan)

`tests/unit/` has 26 failing tests at baseline (verified by stashing my changes and rerunning). Failures are clustered in:
- `test_retry_worker.py` (8 failures - vector/Turso-specific)
- `test_connection_manager.py` (8 failures - WS ConnectionManager tests)
- `test_auto_index.py` (6 failures - embedding hook tests)
- `test_embedding_service.py` (4 failures - openai/ollama backend tests)

None of these exercise the trace endpoint or touch routes_tasks.py. They are orthogonal to this plan.

### Markdown lint warnings in REQUIREMENTS.md

IDE diagnostics flagged MD060 (table column style) on lines 106/119 and MD032 (blanks around lists) on line 176 after my UI-12 edits. These warnings are pre-existing (same lines, same content structure as before my change); MY edits were a single-word substitution ("Pending" -> "Complete") that could not have introduced column-style warnings. Out of scope; logged here for the verifier.

## User Setup Required

None.

## Next Phase Readiness

Phase 4 success criterion 5 ("Cost, trace, memory, lock panels all accessible and show real data") is now satisfied for traces. Phase 4 verification's only code-level blocker is closed. Phase 5 can proceed without carrying UI-12 forward as a known gap.

Phase 5 agents writing spans via `POST /v1/traces/event` with `task_id` populated will see them render automatically in `/dashboard/tasks/<task_id>` - no additional wiring needed.

## Self-Check: PASSED

All 11 declared files present on disk:
- `app/api/routes_tasks.py` (modified)
- `tests/unit/test_task_trace_endpoint.py` (created)
- `web/src/types/entities.ts` (modified)
- `web/src/components/common/TraceTimeline.tsx` (modified)
- `web/src/hooks/queries/useTaskTrace.ts` (created)
- `web/src/hooks/queries/useTaskTrace.test.ts` (created)
- `web/src/mocks/handlers/tasks.ts` (modified)
- `web/src/i18n/namespaces/tasks.ts` (modified)
- `web/src/routes/_authed/tasks/$taskId.tsx` (modified)
- `.planning/REQUIREMENTS.md` (modified)
- `.planning/phases/04-command-center-ui/04-09-SUMMARY.md` (created)

All 3 task commits reachable from HEAD:
- `8c5cd7d` Task 1 - backend endpoint + pytest
- `8be2099` Task 2 - hook + type hoist + msw + i18n
- `fabf304` Task 3 - route wire + REQUIREMENTS flip
