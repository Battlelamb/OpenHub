---
phase: 04-command-center-ui
plan: 06
subsystem: ui
tags: [react, tanstack-router, shadcn, tailwind, i18next, msw, typescript, jsonviewer, sheet, alertdialog]

# Dependency graph
requires:
  - phase: 04-command-center-ui/04-02
    provides: AppShell, Sidebar links for dlq/costs/traces/memory/locks/health/settings, Sheet primitive, i18n common/nav namespaces
  - phase: 04-command-center-ui/04-03
    provides: authStore, api<T> wrapper, _authed guard wiring
  - phase: 04-command-center-ui/04-04
    provides: useDlq / useRetryDlq / useCosts / useMemoryEntries / useLocks / useHealth hooks, typed DlqItem / CostItem / MemoryItem / ResourceLock / HealthResponse entities, per-feature i18n namespaces, per-feature msw handler modules
  - phase: 04-command-center-ui/04-05
    provides: _authed.tsx pathless layout, ResponsiveList compositional primitive (Header/Row/Cell), shadcn badge + table primitives, i18n namespace shape ({ en, tr } const exports)
  - phase: 04-command-center-ui/04-05b
    provides: shadcn alert-dialog primitive, createRoute + parentRoute routing convention
provides:
  - DLQ route (/dlq) with retry AlertDialog using UI-SPEC confirm body copy
  - Costs route (/costs) with tabular-nums per-agent spend table
  - Memory route (/memory) with Eye-icon Sheet inspector wrapping JsonViewer
  - Locks route (/locks) with amber-500 conflict warning badge
  - Health route (/health) rendering useHealth() payload as pretty JSON
  - Settings route (/settings) with theme toggle and language toggle via ui-store
  - Traces route (/traces) placeholder ("select a task to view its trace")
  - JsonViewer primitive at web/src/components/common/JsonViewer.tsx (expandable monospace tree via native <details>)
  - Visibility i18n namespaces filled with UI-SPEC EN + TR copy (dlq/costs/memory/locks/health/settings)
affects: [04-07, 04-08]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "JsonViewer: native <details open> collapse with syntax-aware color tokens (emerald strings, sky numbers, violet booleans, zinc null, monospace text-xs)"
    - "DLQ retry flow: AlertDialog with UI-SPEC verbatim body ('Retry task: This re-queues the task with a fresh lease. Continue?'), confirm triggers useRetryDlq.mutate(task_id)"
    - "Memory inspector: Sheet opened from Eye icon button, JsonViewer renders value_preview (may be object/array/primitive/null), font-mono SheetTitle shows key"
    - "Locks conflict warning: amber-500/10 bg + amber-400 text badge with 'WARN' label only when lock.conflict === true"
    - "Settings language toggle: reads i18n.language, swaps via i18n.changeLanguage() and mirrors to ui-store.setLanguage so the choice persists"
    - "Compositional ResponsiveList (Header/Row/Cell) reused — no generic rewrite even though Plan 04-06 action blocks suggested <ResponsiveList<T> items columns cardRender emptyState> API"

key-files:
  created:
    - web/src/components/common/JsonViewer.tsx
    - web/src/components/common/JsonViewer.test.tsx
    - web/src/routes/_authed/dlq.tsx
    - web/src/routes/_authed/costs.tsx
    - web/src/routes/_authed/memory.tsx
    - web/src/routes/_authed/locks.tsx
    - web/src/routes/_authed/health.tsx
    - web/src/routes/_authed/settings.tsx
    - web/src/routes/_authed/traces.tsx
  modified:
    - web/src/i18n/namespaces/dlq.ts
    - web/src/i18n/namespaces/costs.ts
    - web/src/i18n/namespaces/memory.ts
    - web/src/i18n/namespaces/locks.ts
    - web/src/i18n/namespaces/health.ts
    - web/src/i18n/namespaces/settings.ts
    - web/src/mocks/handlers/dlq.ts
    - web/src/mocks/handlers/costs.ts
    - web/src/mocks/handlers/memory.ts
    - web/src/mocks/handlers/locks.ts
    - web/src/mocks/handlers/health.ts
    - web/src/mocks/handlers/settings.ts
    - web/src/routeTree.gen.ts

key-decisions:
  - "Used existing compositional ResponsiveList (Header/Row/Cell) rather than rewriting it as a generic <T> component — Plan 04-06's action blocks assumed a generic API that Plan 05 never actually shipped. Rewriting would regress 04-05 and 04-05b routes."
  - "Routes wired with createRoute + parentRoute (the concrete Plan 05/05b pattern) rather than createFileRoute — TanStack Router plugin still auto-generates routeTree.gen.ts from the file tree, so the wiring works either way."
  - "Plan 04-06's msw handlers/health.ts spec would have left /v1/health unhandled — kept the existing Plan 04 /v1/health mock in place (documented as Rule 1 deviation) to avoid breaking useHealth + Topbar health dot."
  - "Visibility i18n namespaces (dlq/costs/memory/locks/health/settings) overwritten with plan-specified UI-SPEC copy; existing placeholder keys from Plan 04/05 replaced since the new route components consume the new keys (title, columns.*, retryCta, retryConfirmBody, inspectLabel, emptyHeading, emptyBody)."
  - "Traces page copy is inlined (EN only) per plan's own instruction; no dedicated traces i18n namespace added."
  - "tsconfig.app.tsbuildinfo and web/package-lock.json left uncommitted to avoid churn; tsbuildinfo is a local incremental cache and package-lock.json was modified by an earlier plan outside 04-06 scope."

patterns-established:
  - "JsonViewer at web/src/components/common/JsonViewer.tsx is the canonical nested-JSON inspector; future routes needing to show opaque JSON payloads (payloads, traces, logs) should reuse rather than redefine."
  - "Visibility routes follow a consistent empty-state shape: rounded-lg bordered card with t('emptyHeading') + t('emptyBody'); same pattern as Plan 05 agents/workflows routes."
  - "amber-500 is the UI-SPEC conflict/warn color token; reuse the exact class composition (bg-amber-500/10 px-2 py-0.5 text-xs font-medium text-amber-400) for any future warn-state pills."

requirements-completed: ["UI-10", "UI-11", "UI-13", "UI-14"]

# Metrics
duration: ~10 min
completed: 2026-04-19
---

# Phase 4 Plan 06: Visibility Feature Routes Summary

**DLQ retry + Costs + Memory inspector + Locks conflict warnings shipped; JsonViewer primitive added and every sidebar link now resolves including Traces, Health, and Settings placeholders.**

## Performance

- **Duration:** ~10 min
- **Started:** 2026-04-19T12:10:00Z
- **Completed:** 2026-04-19T12:20:42Z
- **Tasks:** 3 (all committed atomically)
- **Files created:** 9
- **Files modified:** 13 (i18n namespaces, msw handlers, routeTree.gen.ts)

## Accomplishments

- `/dlq` list renders DlqItem rows with Retry button triggering AlertDialog; confirm body uses exact UI-SPEC copy ("Retry task: This re-queues the task with a fresh lease. Continue?") and confirm invokes `useRetryDlq.mutate(task_id)`.
- `/costs` per-agent spend table with `tabular-nums` on total_tokens (`.toLocaleString()`) and total_cost_usd (`$x.xx` via `.toFixed(2)`).
- `/memory` key/size/age list with per-row Eye icon Button opening a right-side Sheet that inspects `value_preview` via the new JsonViewer; `formatSize` (B/KB/MB) and `formatAge` (s/m/h) keep cells compact and aligned.
- `/locks` resource-lock table; rows with `lock.conflict === true` render an amber-500 "WARN" badge (`bg-amber-500/10 text-amber-400`).
- `/health` shows live `useHealth()` payload as pretty-printed JSON inside a monospace panel (falls back to `{status: 'unknown'}` while loading).
- `/settings` toggles theme via `ui-store.toggleTheme` and swaps i18n language (`i18n.changeLanguage` + `ui-store.setLanguage`) — no backend call needed.
- `/traces` placeholder renders "Select a task to view its trace" so the sidebar link resolves without 404.
- `JsonViewer.test.tsx` covers primitive rendering, nested object keys, and array indices (3 tests, all pass).
- All six visibility i18n namespaces overwritten with UI-SPEC TR + EN copy tied to the route components' key shape (`title`, `columns.*`, `retryCta`, `retryConfirmBody`, `emptyHeading`, `emptyBody`, `inspectLabel`).
- MSW handlers now typed as `HttpHandler[]` and match the plan's stubs (dlq list empty + retry `{ok:true}`, costs/memory/locks empty arrays) — health handler kept non-empty (see deviations).

## UI-SPEC Token Enforcement

| Token | Used In | Class Composition |
|-------|---------|-------------------|
| emerald-400 | JsonViewer string values | `text-emerald-400` |
| sky-400 | JsonViewer number values | `text-sky-400` |
| violet-400 | JsonViewer boolean values | `text-violet-400` |
| zinc-500 | JsonViewer null values | `text-zinc-500` |
| amber-500 | Locks conflict badge | `bg-amber-500/10 text-amber-400 px-2 py-0.5 text-xs font-medium` |
| red-400 | DLQ error column | `font-mono text-xs text-red-400` |
| tabular-nums | Costs + Memory numeric cells | `font-mono tabular-nums` |

## Task Commits

Each task was committed atomically:

1. **Task 1: JsonViewer + visibility i18n + msw stubs** — `3396a42` (feat)
2. **Task 2: DLQ, Costs, Locks, Traces, Health, Settings routes** — `7114bbc` (feat)
3. **Task 3: Memory route with Sheet + JsonViewer inspector** — `8726396` (feat)

## Verification Gate

- `cd web && npm run typecheck` -> 0 errors
- `cd web && npm run test -- --run` -> 10 test files / 28 tests passed (3 new JsonViewer tests; no regressions in the 25 pre-existing)
- `cd web && npm run build` -> 722.25 kB JS bundle, built in 5.3s (bundle-size warning is pre-existing)

## Files Created/Modified

### Created

- `web/src/components/common/JsonViewer.tsx` - Monospace JSON tree primitive with syntax-aware colors, native `<details>` collapse
- `web/src/components/common/JsonViewer.test.tsx` - 3 tests (primitive, nested object, array)
- `web/src/routes/_authed/dlq.tsx` - DLQ list + retry AlertDialog
- `web/src/routes/_authed/costs.tsx` - Per-agent cost table with tabular-nums
- `web/src/routes/_authed/memory.tsx` - Memory list + Sheet inspector with JsonViewer
- `web/src/routes/_authed/locks.tsx` - Resource locks table with amber conflict badge
- `web/src/routes/_authed/health.tsx` - useHealth payload inspector
- `web/src/routes/_authed/settings.tsx` - Theme + language toggles
- `web/src/routes/_authed/traces.tsx` - Placeholder until per-task trace view ships

### Modified

- `web/src/i18n/namespaces/dlq.ts` - Overwritten with UI-SPEC retry copy
- `web/src/i18n/namespaces/costs.ts` - Overwritten with cost-tracking copy
- `web/src/i18n/namespaces/memory.ts` - Overwritten with shared-memory copy + inspectLabel key
- `web/src/i18n/namespaces/locks.ts` - Overwritten with resource-lock column labels
- `web/src/i18n/namespaces/health.ts` - Overwritten with simple { title } namespace
- `web/src/i18n/namespaces/settings.ts` - Overwritten with simple { title } namespace
- `web/src/mocks/handlers/dlq.ts` - Typed HttpHandler[]: list empty + retry `{ok:true}`
- `web/src/mocks/handlers/costs.ts` - Typed HttpHandler[]: list empty
- `web/src/mocks/handlers/memory.ts` - Typed HttpHandler[]: list empty
- `web/src/mocks/handlers/locks.ts` - Typed HttpHandler[]: list empty
- `web/src/mocks/handlers/health.ts` - Typed HttpHandler[]: keeps /v1/health mock (deviation)
- `web/src/mocks/handlers/settings.ts` - Typed HttpHandler[]: empty (no network path)
- `web/src/routeTree.gen.ts` - Regenerated with 6 new visibility route entries (+126 lines)

### Frozen aggregators NOT touched (verified)

- `web/src/i18n/index.ts` - untouched (only namespace files edited)
- `web/src/mocks/handlers.ts` - untouched (only handler files edited)

## Decisions Made

- Used existing compositional `ResponsiveList` (Header/Row/Cell subcomponents) instead of a generic `<ResponsiveList<T> items columns cardRender emptyState>` rewrite. The plan's action blocks assumed the generic API, but the primitive Plan 05 actually shipped is compositional and is consumed as such by both `agents/index.tsx` and `tasks/index.tsx`. Rewriting would regress those routes and violate the scope boundary.
- Followed the Plan 05/05b `createRoute({ getParentRoute: () => parentRoute, path, component })` convention rather than `createFileRoute` from the plan's examples. TanStack Router's vite plugin regenerates `routeTree.gen.ts` from the file tree regardless of which primitive is used inside the file, so routing still works identically.
- Kept the `/v1/health` msw handler in `handlers/health.ts` despite the plan instructing an empty handler array. Removing the mock would break `useHealth` in dev and fail the existing `useHealth.test.ts` sanity test; this is a Rule 1 correctness fix.
- Did NOT add a `traces` i18n namespace — the plan's own action block notes Traces copy is inlined under `common`, so adding a dedicated namespace would drift.
- Followed plan-specified empty-array stubs for costs/memory/locks msw handlers, even though the pre-existing stubs had richer mock data. The plan explicitly said OVERWRITE; dev UX regression is minor (routes render empty state cards) and the UI-SPEC empty copy ships with every route for exactly this case.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] ResponsiveList generic API does not exist**

- **Found during:** Task 2 (DLQ route skeleton)
- **Issue:** Plan 04-06's action blocks show `<ResponsiveList<T> items={...} columns={[...]} cardRender={...} emptyState={...}>`. The actual primitive at `web/src/components/common/ResponsiveList.tsx` is compositional with `ResponsiveList.Header`, `ResponsiveList.Row`, `ResponsiveList.Cell` subcomponents. Both existing consumers (`agents/index.tsx`, `tasks/index.tsx`, `tasks/$taskId.tsx` indirectly) use the compositional API. A generic rewrite would require touching all of those (out of scope for 04-06) and regress Plan 05/05b.
- **Fix:** Adopted the compositional API for all six visibility routes. Empty state renders a standalone bordered card outside the `ResponsiveList` (matching agents/index.tsx pattern) rather than being passed as a prop.
- **Files modified:** `web/src/routes/_authed/dlq.tsx`, `costs.tsx`, `locks.tsx`, `memory.tsx` (and `health.tsx`, `settings.tsx`, `traces.tsx` which do not need ResponsiveList at all)
- **Verification:** typecheck clean, build clean, all routes render under `/dlq`, `/costs`, etc., empty-state copy visible when handlers return `[]`.
- **Committed in:** `7114bbc` (Task 2) and `8726396` (Task 3)

**2. [Rule 1 - Bug] Plan's msw health handler spec would break `/v1/health` interception**

- **Found during:** Task 1 (msw overwrite)
- **Issue:** Plan 04-06 action block says `handlers/health.ts` should export `[]` with a comment claiming the bootstrap handler lives in `handlers.ts`. The actual frozen aggregator at `web/src/mocks/handlers.ts` has no bootstrap handlers — Plan 04-04's deviation #3 moved `/v1/health` into `handlers/health.ts`. Shipping an empty array would leave `useHealth` and `useHealth.test.ts` without a mock response.
- **Fix:** Kept the existing `/v1/health` handler in `handlers/health.ts`, re-typed the export as `HttpHandler[]`, and documented via inline comment why the file is non-empty.
- **Files modified:** `web/src/mocks/handlers/health.ts`
- **Verification:** useHealth.test.ts still passes; Topbar health dot still shows green in dev.
- **Committed in:** `3396a42` (Task 1)

**3. [Rule 3 - Blocking] Routing convention mismatch**

- **Found during:** Task 2 (DLQ route skeleton)
- **Issue:** Plan 04-06 uses `createFileRoute('/_authed/dlq')`. Plan 05 and 05b shipped routes via `createRoute({ getParentRoute: () => parentRoute, path: '/...' })` and the existing `routeTree.gen.ts` follows that shape. Mixing conventions inside the same `_authed/` tree would make the regeneration output inconsistent.
- **Fix:** Used `createRoute` + `parentRoute` for all six new routes to match existing convention.
- **Files modified:** all six route files in `web/src/routes/_authed/`
- **Verification:** `npm run build` regenerates `routeTree.gen.ts` cleanly with all six routes registered; dev server resolves each path.
- **Committed in:** `7114bbc`, `8726396`

---

**Total deviations:** 3 (2 Rule 3 blocking, 1 Rule 1 bug)
**Impact on plan:** All three deviations preserve the plan's user-facing intent (routes render, retry works, inspector opens, visibility sidebar fully resolves). Must-haves from frontmatter are all met. Requirements UI-10, UI-11, UI-13, UI-14 all verifiable.

## Issues Encountered

None. The ResponsiveList / createRoute / health-handler mismatches were all detected before writing the route code and resolved via deviation rules without blocking progress.

## Known Stubs

- `web/src/routes/_authed/traces.tsx` - Placeholder page. The real per-task trace view depends on backend-emitted trace spans, which are not yet produced. Plan 04-07 or a later phase will wire this to the TraceTimeline primitive from 04-05b once the data is available. Documented here so it isn't mistaken for missing visibility work.
- `web/src/mocks/handlers/{dlq,costs,memory,locks}.ts` - Return empty arrays per plan spec. Dev UX sees empty-state cards in all four routes unless the real backend is running on :7788 behind the vite proxy. This is intentional per Plan 04-06's instruction to overwrite Plan 04's seed mocks.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- All sidebar destinations from Plan 04-02's Sidebar.tsx now have matching route files. Plan 04-07 can focus on e2e / UAT / polish without adding more surface.
- `JsonViewer` is available at `web/src/components/common/JsonViewer.tsx` for any future inspector use (trace payloads, artifact previews, debug dumps).
- `useRetryDlq` mutation flow is exercised end-to-end: AlertDialog -> mutate(task_id) -> `/v1/dlq/:id/retry` POST -> query invalidation. Wiring real backend behavior is unblocked.
- Memory inspector Sheet pattern (opens from a row-level Eye button, shows monospace key in title, renders JsonViewer) is reusable for any detail-view-in-side-panel need.

## Self-Check: PASSED

Files verified on disk:

- web/src/components/common/JsonViewer.tsx
- web/src/components/common/JsonViewer.test.tsx
- web/src/routes/_authed/dlq.tsx
- web/src/routes/_authed/costs.tsx
- web/src/routes/_authed/memory.tsx
- web/src/routes/_authed/locks.tsx
- web/src/routes/_authed/health.tsx
- web/src/routes/_authed/settings.tsx
- web/src/routes/_authed/traces.tsx
- .planning/phases/04-command-center-ui/04-06-SUMMARY.md

Commits verified in git log:

- 3396a42 feat(04-06): add JsonViewer + visibility i18n + msw stubs
- 7114bbc feat(04-06): add DLQ, Costs, Locks, Traces, Health, Settings routes
- 8726396 feat(04-06): add Memory route with Sheet + JsonViewer inspector

---
*Phase: 04-command-center-ui*
*Plan: 04-06*
*Completed: 2026-04-19*
