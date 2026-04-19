---
phase: 04-command-center-ui
plan: 05b
subsystem: ui
tags: [react, tanstack-router, shadcn, tailwind, i18next, msw, react-hook-form, zod, typescript]

# Dependency graph
requires:
  - phase: 04-command-center-ui/04-02
    provides: AppShell, Topbar, i18n common/nav namespaces
  - phase: 04-command-center-ui/04-03
    provides: authStore, api<T> wrapper, router-ref
  - phase: 04-command-center-ui/04-04
    provides: useTasks/useTask/useCreateTask/useCancelTask hooks, useAgents hook, typed Task entity, tasks i18n namespace stub, tasks msw handler stub
  - phase: 04-command-center-ui/04-05
    provides: _authed.tsx layout, ResponsiveList<T> primitive, StatusBadge module (TaskStatusBadge), shadcn badge + table primitives
provides:
  - Tasks list route (/tasks) with status filter Select, create dialog, inline cancel AlertDialog
  - Task detail route (/tasks/$taskId) with header, metadata grid, and TraceTimeline slot
  - TaskCreateForm: react-hook-form + zod schema, useCreateTask mutation, useAgents agent selector
  - TraceTimeline<TraceSpan> primitive with 6 UI-SPEC category color tokens (llm/tool/db/http/internal/error) and nested span rendering
  - Tasks i18n namespace filled with EN+TR copy (title, CTAs, cancelConfirmBody, columns, fields, status labels, trace empty states)
  - Tasks msw handler stub filled with list/detail/create/cancel mocks
  - shadcn primitives: dialog, alert-dialog, select, textarea
affects: [04-07, 04-08]

# Tech tracking
tech-stack:
  added:
    - shadcn/ui dialog primitive
    - shadcn/ui alert-dialog primitive
    - shadcn/ui select primitive
    - shadcn/ui textarea primitive
  patterns:
    - "TraceTimeline<TraceSpan> nested recursive Node rendering with per-category border/dot/bar color tokens and proportional duration bars (width = span.duration_ms / rootDuration * 100%)"
    - "Cancel action uses AlertDialog (not native confirm) with UI-SPEC verbatim copy from tasks.cancelConfirmBody, destructive styling on confirm button, keep-running label on cancel button"
    - "TaskStatusBadge and ResponsiveList IMPORTED from Plan 05 — zero duplication of the UI-SPEC color map or the responsive table/card pattern"
    - "Route handlers wired via createRoute + parentRoute (from _authed) rather than createFileRoute, matching Plan 05's _authed.tsx parent pattern"

key-files:
  created:
    - web/src/routes/_authed/tasks/index.tsx
    - web/src/routes/_authed/tasks/$taskId.tsx
    - web/src/components/forms/TaskCreateForm.tsx
    - web/src/components/common/TraceTimeline.tsx
    - web/src/components/common/TraceTimeline.test.tsx
    - web/src/components/ui/dialog.tsx
    - web/src/components/ui/alert-dialog.tsx
    - web/src/components/ui/select.tsx
    - web/src/components/ui/textarea.tsx
  modified:
    - web/src/i18n/namespaces/tasks.ts
    - web/src/mocks/handlers/tasks.ts
    - web/src/routeTree.gen.ts
    - web/package.json
    - web/package-lock.json
    - web/tsconfig.app.tsbuildinfo

key-decisions:
  - "TaskStatusBadge and ResponsiveList are imported from Plan 05 with no redefinition — the UI-SPEC Task status color map lives in exactly one place."
  - "Frozen aggregators (web/src/i18n/index.ts, web/src/mocks/handlers.ts) were NOT touched. Only the feature-owned stubs web/src/i18n/namespaces/tasks.ts and web/src/mocks/handlers/tasks.ts were overwritten."
  - "Tasks routes wire into Plan 05's _authed parent via createRoute + parentRoute rather than createFileRoute, keeping the auth-guarded shell consistent for the feature surface."
  - "TraceTimeline renders a placeholder empty state at the detail route (root={null}) because trace span data is not yet produced by the backend — the shape is ready for real data in later phases."
  - "Plan's atomic-per-task commit rule was not followed; all three tasks were squashed into a single retrospective commit, SUMMARY.md backfilled afterward."

patterns-established:
  - "TraceTimeline primitive at web/src/components/common/TraceTimeline.tsx handles all future trace rendering with typed TraceSpan + children[] recursion."
  - "Feature-owned i18n namespace files (web/src/i18n/namespaces/{feature}.ts) remain the single source of EN+TR copy; the aggregator (i18n/index.ts) is registered once by Plan 05 and not touched by feature plans."
  - "Feature-owned msw handler files (web/src/mocks/handlers/{feature}.ts) are the only place feature plans add mock routes; the aggregator (mocks/handlers.ts) spreads them and is not re-edited per feature."
  - "Destructive actions use AlertDialog with exact UI-SPEC copy keys, not native window.confirm or custom modals."

requirements-completed: ["UI-03", "UI-04", "UI-05", "UI-12"]

# Metrics
duration: unknown (backfill)
completed: 2026-04-13
---

# Phase 4 - Plan 05b Summary: Tasks Feature Routes

**Operations Tasks surface delivered: /tasks list with status filter and create dialog, inline cancel with AlertDialog confirmation, /tasks/$taskId detail page with TraceTimeline primitive and 6 UI-SPEC category color tokens.**

## Performance

- **Duration:** unknown (backfill)
- **Completed:** 2026-04-13
- **Commit timestamp:** 2026-04-13T17:58:48+03:00
- **Tasks planned:** 3 (all delivered in one squashed commit)
- **Files created:** 9
- **Files modified:** 6

## Accomplishments

- /tasks list route consuming useTasks({ status? }) with a Select-driven status filter across all 6 TaskStatus values, a create-task Dialog triggered from the page header, and an inline cancel AlertDialog on each queued/claimed/running row
- /tasks/$taskId detail route with title, TaskStatusBadge, id + agent metadata grid, and a TraceTimeline slot rendering the trace empty state until real span data arrives
- TaskCreateForm built on react-hook-form + zod: title (required), description, priority (int 1-5), agent_id (optional); calls useCreateTask.mutateAsync and closes dialog on success
- TraceTimeline<TraceSpan> component: vertical timeline, depth-based left padding (16px per level, capped at 6), per-category border + dot + duration-bar colors matching UI-SPEC verbatim (llm=violet-400, tool=sky-400, db=amber-400, http=emerald-400, internal=zinc-500, error=red-500), proportional duration bar widths, recursive children rendering
- Tasks i18n namespace overwritten with full EN+TR copy: title, CTAs, dialogTitle, dispatchCta, cancelCta, cancelConfirmBody (exact UI-SPEC destructive-action body), cancelConfirmBack ("Keep running"), columns map, fields map, status map, trace empty-state strings
- Tasks msw handlers overwritten with realistic list/detail/create/cancel mocks (not just empty arrays), typed as HttpHandler[]
- 4 shadcn primitives installed: dialog, alert-dialog, select, textarea (badge and table already installed by Plan 05)

## Trace Category Color Map (UI-SPEC verbatim, lines 270-286)

| Category | Token    |
|----------|----------|
| llm      | violet-400 |
| tool     | sky-400  |
| db       | amber-400 |
| http     | emerald-400 |
| internal | zinc-500 |
| error    | red-500  |

## Task Commits

All three planned tasks were delivered in a single retrospective commit. The plan's atomic-per-task commit rule was not followed.

1. **Single squashed commit:** `51c2879` - "Phase 4 Wave 4 Plan 04-05b: Tasks feature routes"

_Note: Atomic-per-task rule not followed; SUMMARY.md backfilled afterward._

## Files Created/Modified

### Created
- `web/src/routes/_authed/tasks/index.tsx` - Tasks list route with filter + create dialog + inline cancel AlertDialog
- `web/src/routes/_authed/tasks/$taskId.tsx` - Task detail route with header, metadata grid, TraceTimeline slot
- `web/src/components/forms/TaskCreateForm.tsx` - react-hook-form + zod task create form
- `web/src/components/common/TraceTimeline.tsx` - Vertical trace timeline primitive with 6 category color tokens
- `web/src/components/common/TraceTimeline.test.tsx` - Tests: renders root name, renders nested children, renders nothing on null
- `web/src/components/ui/dialog.tsx` - shadcn Dialog primitive
- `web/src/components/ui/alert-dialog.tsx` - shadcn AlertDialog primitive
- `web/src/components/ui/select.tsx` - shadcn Select primitive
- `web/src/components/ui/textarea.tsx` - shadcn Textarea primitive

### Modified
- `web/src/i18n/namespaces/tasks.ts` - Overwritten with full EN+TR copy
- `web/src/mocks/handlers/tasks.ts` - Overwritten with list/detail/create/cancel mocks (HttpHandler[]-typed)
- `web/src/routeTree.gen.ts` - Regenerated route tree (+42 lines for /tasks and /tasks/$taskId)
- `web/package.json` / `web/package-lock.json` - New shadcn primitive deps
- `web/tsconfig.app.tsbuildinfo` - Rebuilt incremental typecheck cache

### Frozen aggregators NOT touched (verified)
- `web/src/i18n/index.ts` - untouched
- `web/src/mocks/handlers.ts` - untouched

## Decisions Made

- Plan's atomic-per-task commit rule was not followed; all three tasks were squashed into one retrospective commit (`51c2879`). SUMMARY.md was backfilled afterward.
- TaskStatusBadge and ResponsiveList are imported from Plan 05's `web/src/components/common/StatusBadge.tsx` and `web/src/components/common/ResponsiveList.tsx` — no redefinition. This honors the plan's explicit no-duplication rule for the UI-SPEC color map and the responsive table/card pattern.
- Frozen aggregators `web/src/i18n/index.ts` and `web/src/mocks/handlers.ts` were not touched. Only feature-owned `web/src/i18n/namespaces/tasks.ts` and `web/src/mocks/handlers/tasks.ts` were overwritten, preserving Wave 4 per-feature ownership.
- Routes use `createRoute({ getParentRoute: () => parentRoute, ... })` with `parentRoute` imported from the Plan 05 `_authed.tsx` layout, rather than `createFileRoute('/_authed/tasks/')` as shown in the plan's example. This matches the concrete parent-route wiring Plan 05 established and keeps the auth guard in effect for the Tasks surface. Functionally equivalent.
- TraceTimeline in the detail route renders with `root={null}` (empty state) because the backend does not yet emit trace span data. The primitive and TraceSpan type are ready for real data in later phases.

## Deviations from Plan

### Auto-fixed Issues

**1. [Missing artifact] TaskCreateForm.test.tsx was not shipped despite Task 2 being marked `tdd="true"`**
- **Found during:** N/A - visible in `git show --stat`: `web/src/components/forms/TaskCreateForm.test.tsx` does not appear
- **Plan specified:** A co-located test that intercepts POST /v1/tasks via msw and asserts `receivedBody.title === 'Do the thing'` and `receivedBody.priority === 3`
- **Shipped instead:** Only `TaskCreateForm.tsx` (175 lines). No test file.
- **Why this matters:** Plan 04's test contract for the form-layer was lost; form correctness relies on typecheck + manual exercise of the dialog flow. Commit message still claims "25 frontend tests passing (added 2 new)" - those 2 were the TraceTimeline tests only, not the intended form test.
- **Files affected:** `web/src/components/forms/TaskCreateForm.test.tsx` (missing)

**2. [Route API shape] `createRoute` + `parentRoute` wiring used instead of `createFileRoute`**
- **Found during:** N/A - visible in the commit's route files
- **Plan specified:** `export const Route = createFileRoute('/_authed/tasks/')({ component: TasksList })` and `createFileRoute('/_authed/tasks/$taskId')` for the detail
- **Shipped instead:** `export const Route = createRoute({ getParentRoute: () => parentRoute, path: '/tasks', component: TasksList })` with `import { Route as parentRoute } from '../../_authed'`
- **Why this is fine:** Plan 05 introduced a concrete `_authed.tsx` layout route. The concrete pattern (createRoute + parentRoute import) binds the tasks routes to that parent and keeps the auth `beforeLoad` guard in effect. Same user-facing outcome: /tasks and /tasks/$taskId render inside the authed shell.
- **Files affected:** `web/src/routes/_authed/tasks/index.tsx`, `web/src/routes/_authed/tasks/$taskId.tsx`, `web/src/routeTree.gen.ts`

---

**Total deviations:** 2 (1 missing test artifact, 1 route API shape deviation with equivalent outcome)
**Impact on plan:** The missing TaskCreateForm.test.tsx is a real test-coverage gap that should be closed in a follow-up. The route API shape deviation is benign and aligns with Plan 05's layout pattern. All four requirements (UI-03, UI-04, UI-05, UI-12) are functionally met.

## Issues Encountered

None documented in the commit. Commit message claims 25 frontend tests passing, TypeScript typecheck green, 706 KB JS bundle.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- /tasks list route renders with msw mock data and WS-merged updates from Plan 04's useTasks hook; status filter Select switches between all 6 TaskStatus values; create dialog dispatches POST /v1/tasks; cancel AlertDialog confirms then calls POST /v1/tasks/:id/cancel.
- /tasks/$taskId detail route renders task header, metadata grid, and the TraceTimeline component with empty-state copy; when backend starts emitting trace spans the primitive accepts the TraceSpan shape without changes.
- TraceTimeline primitive is available at `web/src/components/common/TraceTimeline.tsx` for reuse in any detail page that needs nested-span visualization.
- Shared primitives TaskStatusBadge and ResponsiveList continue to be owned solely by Plan 05's files; future Task-related UI should import rather than redefine.
- Follow-up work: write TaskCreateForm.test.tsx (msw POST /v1/tasks assertion) to close the Plan 05b test-coverage gap.

---
*Phase: 04-command-center-ui*
*Plan: 04-05b*
*Completed: 2026-04-13 (backfill written later)*
