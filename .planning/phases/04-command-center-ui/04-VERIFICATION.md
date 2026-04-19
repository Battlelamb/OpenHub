---
phase: 04-command-center-ui
verified: 2026-04-19T15:35:00Z
status: human_needed
score: 5/6 automated success criteria verified; 1/6 has a code-level gap and 5/6 require browser UAT
human_verification:
  - test: Live JWT login happy path + invalid credential error
    expected: POST /v1/auth/login succeeds; token in memory; invalid credentials show RFC 7807 toast; refresh of /dashboard keeps you signed in only until tab close (no persistence).
    why_human: Requires a live backend with a real credential and DOM observation; no static check can prove the token never touches localStorage at runtime.
  - test: Live agent status updates without page refresh
    expected: Open /dashboard/agents in one tab; change an agent's status via API (or stop its heartbeat) from another; UI row updates within seconds via /v1/ws/ui without reloading.
    why_human: WebSocket patch behavior is only observable with a running hub + a real agent state transition.
  - test: Task create + cancel flow end-to-end
    expected: Click "Create Task", submit, new task appears in list (WebSocket-driven); click Cancel on a running task, AlertDialog confirms, status transitions to cancelled in real time.
    why_human: Requires uvicorn + WS broadcast; msw mocks in tests do not exercise the live WS pipeline.
  - test: DLQ manual retry
    expected: /dashboard/dlq shows failed tasks; clicking Retry fires POST /v1/dlq/{id}/retry and the item disappears after invalidation.
    why_human: Requires backend DLQ seeded with a failed task to observe round-trip.
  - test: Distributed trace viewer renders real spans (UI-12)
    expected: Open /dashboard/tasks/{id}; TraceTimeline displays actual tool-call spans from the task, not an empty placeholder.
    why_human: Code currently passes hardcoded spans={[]}; even with a running backend, the page will show an empty timeline. See gaps block below.
  - test: Mobile layout collapse at small viewport (UI-15)
    expected: Resize browser to <768 px (or Chrome DevTools mobile); agents and tasks tables collapse to cards; sidebar hides behind a toggle; topbar remains usable.
    why_human: Responsive breakpoint effect is visual-only; grep confirms the CSS classes exist but cannot prove layout quality.
gaps:
  - truth: "Distributed trace viewer in task detail shows tool calls, sub-steps, timing (UI-12 / success criterion 5 partial)"
    status: failed
    reason: "TraceTimeline in web/src/routes/_authed/tasks/$taskId.tsx:72 is invoked with hardcoded spans={[]}. No query hook fetches spans, no field on the Task entity carries them, and no backend /v1/tasks/{id}/trace endpoint is consumed. The component renders but the timeline is always empty, so the 'visibility stack ... show real data' success criterion fails for traces specifically."
    artifacts:
      - path: web/src/routes/_authed/tasks/$taskId.tsx
        issue: "TraceTimeline spans prop hardcoded to [] at line 72"
      - path: web/src/routes/_authed/traces.tsx
        issue: "Standalone /traces route is a static placeholder ('Select a task to view its trace'); no data hook"
      - path: web/src/hooks/queries/
        issue: "No useTaskTrace / useSpans hook exists to fetch spans from the backend"
    missing:
      - "A query hook (e.g. useTaskTrace(taskId)) that calls a backend endpoint returning span data"
      - "Wire the hook result into TraceTimeline spans prop in tasks/$taskId.tsx"
      - "Either a backend /v1/tasks/{id}/trace endpoint or a documented upstream source of span data for UI-12"
  - truth: "REQUIREMENTS.md reflects which UI requirements are actually shipped"
    status: partial
    reason: "REQUIREMENTS.md:45-58 still lists UI-03, UI-04, UI-05, UI-06, UI-07, UI-09, UI-12, UI-15, UI-16 as Pending and the bottom table lists UI-15, UI-16 as Pending, even though plans 04-04 (UI-08, UI-16), 04-05 (UI-02, UI-06, UI-07, UI-15), 04-05b (UI-03, UI-04, UI-05, UI-12), 04-06 (UI-10, UI-11, UI-13, UI-14), 04-07 (all 16), 04-08 (UI-01, UI-02, UI-08) claim them. The code confirms UI-03, UI-04, UI-05, UI-06, UI-07, UI-09, UI-15, UI-16 are implemented; UI-12 is the only one that really remains pending. REQUIREMENTS.md is stale and should be flipped to match reality."
    artifacts:
      - path: .planning/REQUIREMENTS.md
        issue: "UI checklist items 43-58 + tracking table rows 150-166 out of sync with code"
    missing:
      - "Mark UI-03, UI-04, UI-05, UI-06, UI-07, UI-09, UI-15, UI-16 as [x] Complete in REQUIREMENTS.md"
      - "Keep UI-12 as Pending (tracked above as the real gap)"
      - "Update the requirement status table rows 150-166 accordingly"
notes:
  working_tree:
    - path: web/README.md
      state: untracked
      impact: none on verification; 04-07 artifact
    - path: web/package-lock.json
      state: modified
      impact: none on verification; out of scope
    - path: .planning/phases/04-command-center-ui/04-07-SUMMARY.md
      state: untracked
      impact: none on verification; generated during 04-07 execution
    - path: app/main.py
      state: modified (pre-existing before this verification)
      impact: already verified via static_mount pytest (6/6 pass)
---

# Phase 4: Command Center UI Verification Report

**Phase Goal:** A developer self-hosting OpenHub can log in, see live agent status, manage tasks, inspect workflows, and access the full visibility stack (DLQ, cost tracking, traces, memory, locks) from a browser.

**Verified:** 2026-04-19T15:35:00Z
**Status:** human_needed
**Re-verification:** No - initial phase verification after 8 plans including 04-08 gap closure

## Summary

Phase 4 ships a real, working command center with JWT auth, TanStack Router SPA, live WebSocket sync, visibility pages for DLQ/costs/memory/locks/health, responsive layout, and deep-link SPA fallback. The 04-08 gap closures (psutil dependency, router basepath, SPA fallback) are all verified in code and regression tests.

One substantive code gap remains: **UI-12 (distributed trace viewer) is a HOLLOW_PROP** - TraceTimeline is wired but always receives `spans={[]}`. The rest of the visibility stack renders real data from live query hooks.

REQUIREMENTS.md is stale and under-reports completion; see gaps block above.

## Goal Achievement - Success Criteria

| #   | Criterion                                                                  | Status             | Evidence                                                                                                                                                         |
| --- | -------------------------------------------------------------------------- | ------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | JWT login, token in memory (no localStorage, no URL params)                | PASS (code)        | web/src/stores/auth-store.ts: Zustand-only, no persist middleware, no localStorage calls. auth-store.test.ts:32 asserts zero localStorage.setItem during setSession. Grep `localStorage` in src/ returns only the test assertion. |
| 2   | Live online/offline/idle agent status with auto-updates                    | PASS (code)        | web/src/hooks/useWebSocketSync.ts handles `agent_status_changed`, `heartbeat` events via qc.setQueryData on qk.agents. AppShell.tsx:7 mounts useWebSocketSync(). ReconnectingBanner at /components/layout. Exponential backoff MAX_DELAY=30s with jitter. |
| 3   | Create task, select agent, cancel running task, real-time WS reflect       | PASS (code)        | web/src/routes/_authed/tasks/index.tsx: TaskCreateForm + AlertDialog cancel flow via useCancelTask(). useWebSocketSync handles `task_status_changed` + `task_progress` into qk.tasks. |
| 4   | DLQ panel shows failed tasks, manual retry trigger                         | PASS (code)        | web/src/routes/_authed/dlq.tsx uses useRetryDlq() -> POST /v1/dlq/{id}/retry, AlertDialog confirmation, invalidates qk.dlq on success.                           |
| 5   | Cost, trace, memory, lock panels all accessible and show real data         | PARTIAL            | costs.tsx, memory.tsx, locks.tsx, health.tsx all bind to live query hooks. DLQ already covered. **Trace viewer is a HOLLOW_PROP: `<TraceTimeline spans={[]} />`** in tasks/$taskId.tsx:72 and standalone /traces is a static placeholder. |
| 6   | Mobile-usable layout, table-to-card collapse                               | PASS (code, needs visual UAT) | web/src/components/common/ResponsiveList.tsx flips `hidden md:table-header-group` / `md:hidden` blocks at md breakpoint. Sidebar.tsx:68 `hidden md:flex`. Vitest render test surfaces a benign `<table><div>` DOM nest warning but 28/28 tests pass. |

**Score:** 5/6 criteria verified in code; UI-12 is the only code-level blocker. All 6 still need browser UAT to prove they behave correctly at runtime.

## Requirements Coverage (UI-01..UI-16)

| Req   | Claimed By Plan(s)    | REQUIREMENTS.md Status | Code Evidence                                                                                 | Verified |
| ----- | --------------------- | ---------------------- | --------------------------------------------------------------------------------------------- | -------- |
| UI-01 | 04-03, 04-07, 04-08   | Complete                | auth-store.ts + login.tsx + api-client.ts; 04-08 basepath lets /dashboard/login resolve       | PASS     |
| UI-02 | 04-05, 04-07, 04-08   | Complete                | agents/index.tsx + AgentStatusBadge + WS `agent_status_changed` patching                       | PASS     |
| UI-03 | 04-05b, 04-07         | **STALE: Pending**      | tasks/index.tsx with status filter + WS patching                                               | PASS     |
| UI-04 | 04-05b, 04-07         | **STALE: Pending**      | TaskCreateForm.tsx + /v1/tasks POST via useCreateTask                                          | PASS     |
| UI-05 | 04-05b, 04-07         | **STALE: Pending**      | tasks/index.tsx AlertDialog + useCancelTask -> POST /v1/tasks/{id}/cancel                      | PASS     |
| UI-06 | 04-05, 04-07          | **STALE: Pending**      | workflows/index.tsx + workflows/$workflowId.tsx with step status badges                        | PASS     |
| UI-07 | 04-05, 04-07          | **STALE: Pending**      | agents/$agentId.tsx drilldown                                                                  | PASS     |
| UI-08 | 04-04, 04-07, 04-08   | Complete                | Topbar.tsx uses useHealth(); /v1/health regression-tested in test_static_mount.py             | PASS     |
| UI-09 | 04-03, 04-07          | **STALE: Pending**      | api-client.ts raises ProblemDetail; sonner toast on failure; i18n-driven                       | PASS     |
| UI-10 | 04-06, 04-07          | Complete                | dlq.tsx with retry mutation                                                                    | PASS     |
| UI-11 | 04-06, 04-07          | Complete                | costs.tsx bound to useCosts()                                                                  | PASS     |
| UI-12 | 04-05b, 04-07         | Pending (correct)       | **TraceTimeline rendered but `spans={[]}` hardcoded; traces.tsx is a static placeholder**       | **FAIL** |
| UI-13 | 04-06, 04-07          | Complete                | memory.tsx with useMemoryEntries()                                                             | PASS     |
| UI-14 | 04-06, 04-07          | Complete                | locks.tsx with useLocks() + conflict warnings                                                  | PASS     |
| UI-15 | 04-02, 04-05, 04-07   | **STALE: Pending**      | ResponsiveList.tsx hidden/md: pattern; Sidebar mobile-collapse                                 | PASS (needs visual UAT) |
| UI-16 | 04-04, 04-07          | **STALE: Pending**      | useWebSocketSync.ts exponential backoff MAX_DELAY=30s + jitter; ReconnectingBanner.tsx          | PASS     |

**Orphaned requirements:** None. All 16 are claimed by at least one plan.

**Stale REQUIREMENTS.md entries:** 8 items (UI-03, UI-04, UI-05, UI-06, UI-07, UI-09, UI-15, UI-16) marked Pending despite code being in place. See gaps block.

## 04-08 Gap Closure Verification

| Claim                                                                  | Evidence                                                                                                                 | Status |
| ---------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------ | ------ |
| psutil declared in requirements.txt and pyproject.toml                 | `requirements.txt:56` `psutil==5.9.8`; `pyproject.toml:26` `psutil = "^5.9.8"`                                            | PASS   |
| TanStack Router basepath derived from BASE_URL                         | `web/src/main.tsx:21` `const basepath = import.meta.env.BASE_URL.replace(/\/$/, '') || '/'` passed to createRouter         | PASS   |
| FastAPI catch-all /dashboard/{path} serves index.html                  | `app/main.py:345` `@app.get("/dashboard/{full_path:path}")` + FileResponse index.html with path-traversal guard            | PASS   |
| Favicon served at /dashboard/vite.svg                                  | `web/index.html` favicon href = `./vite.svg`; `web/public/vite.svg` exists                                                 | PASS   |
| Regression tests pass                                                  | `pytest tests/unit/test_static_mount.py` -> **6 passed** (test_dashboard_root_serves_index, test_dashboard_deep_link_falls_back_to_index, test_dashboard_asset_served, test_api_routes_still_take_precedence, test_built_index_references_dashboard_base, test_favicon_served_under_dashboard) | PASS   |
| Frontend regression suite green                                        | `cd web && npm run test -- --run` -> **28/28 passed** (10 files)                                                         | PASS   |

All three UAT-discovered gaps are closed with code evidence and passing regression guards.

## Anti-Patterns Found

| File                                        | Line | Pattern                                 | Severity | Impact                                                 |
| ------------------------------------------- | ---- | --------------------------------------- | -------- | ------------------------------------------------------ |
| web/src/routes/_authed/tasks/$taskId.tsx    | 72   | Hardcoded empty prop `spans={[]}`       | Blocker (UI-12) | Trace viewer always empty; criterion 5 fails for traces. |
| web/src/routes/_authed/traces.tsx           | 10-24 | Static placeholder route, no data hook  | Warning  | Standalone /traces gives no data; task detail is the primary trace surface anyway, but the route advertises a visualization it does not deliver. |
| web/src/components/common/ResponsiveList.tsx | 37-49 | `<div>` inside `<tr>`/`<table>` flow   | Info     | Vitest logs a DOM-structure warning; tests still pass. Harmless visually but worth cleaning up. |

## Behavioral Spot-Checks

| Behavior                                            | Command                                                     | Result           | Status |
| --------------------------------------------------- | ----------------------------------------------------------- | ---------------- | ------ |
| Frontend builds, typechecks, tests                  | `cd web && npm run test -- --run`                           | 28 passed (10 files) | PASS   |
| Backend SPA fallback + base-href + favicon guards   | `python3 -m pytest tests/unit/test_static_mount.py --no-cov` | 6 passed         | PASS   |
| psutil importable                                   | `grep psutil requirements.txt pyproject.toml`               | Both declared    | PASS   |
| Router basepath code present                        | `grep 'BASE_URL' web/src/main.tsx`                          | Line 21 matches  | PASS   |
| Catch-all SPA route registered                      | `grep '/dashboard/{full_path:path}' app/main.py`            | Line 345 matches | PASS   |

## Working-Tree Items (Non-Blocking)

- `web/README.md` - untracked 04-07 artifact; flag to user, not a verification blocker.
- `web/package-lock.json` - modified; out of scope per user instructions.
- `.planning/phases/04-command-center-ui/04-07-SUMMARY.md` - untracked; generated during 04-07 execution. Safe to include in a follow-up commit.
- `app/main.py` - modified; diff corresponds to the already-verified 04-08 SPA fallback work. No drift from plan.

## Recommendation

**Proceed to Phase 5 with a documented carry-forward: UI-12 trace viewer.**

- Five of six success criteria pass at the code level and only need human UAT confirmation.
- One success criterion (visibility stack) is partially blocked by UI-12 alone; DLQ, costs, memory, locks, and health all render real data.
- Updating REQUIREMENTS.md to reflect reality is a low-risk housekeeping fix and does not require a new plan.
- The 04-08 UAT gaps are fully closed with regression tests that will fail loudly if the fixes regress.

---

_Verified: 2026-04-19T15:35:00Z_
_Verifier: Claude (gsd-verifier)_
