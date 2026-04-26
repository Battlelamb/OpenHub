---
phase: 04-command-center-ui
verified: 2026-04-26T17:30:00Z
status: human_needed
score: 6/6 success criteria verified in code; 16/16 UI requirements Complete; integration tests now back the formerly mocked-only paths
re_verification:
  previous_status: passed
  previous_score: "6/6 success criteria verified in code; 16/16 UI requirements Complete (msw-only evidence basis)"
  evidence_basis_change: "Prior `passed` rested on msw + vitest, which UAT Test 2 proved unreliable: msw returned canned data at any path the frontend asked for, masking 5 broken hooks (useAgents, useTasks list, useCosts, useMemoryEntries, useLocks) and 3 fragile-redirect-only hooks (useWorkflows, useDlq, useCreateTask). Current verification rests on real-backend integration tests (`tests/integration/test_dashboard_paths_live.py`, 7/7 PASS) plus live VPS deploy at `https://hub.brunhilde.cloud` (HTTP 200 health) at master HEAD `a0a085a`."
  gaps_closed:
    - "Auth path bugs surfaced by Playwright UAT: typed redirect helper (commit 86d3030), pathname-only redirect param (da6a2ca), backend admin/login + response shape (5c8d0af) - login now works end-to-end with real JWT"
    - "5 fictitious-path hooks aligned to real backend: useAgents -> /v1/agents/discover/available, useTasks -> /v1/tasks/search, useCosts -> /v1/costs/summary, useMemoryEntries -> /v1/memory/keys, useLocks -> /v1/locks/ (NEW endpoint)"
    - "3 trailing-slash-redirect-only hooks hardened: useWorkflows -> new /v1/workflows/ endpoint, useDlq -> /v1/dlq/ with dual-auth, useCreateTask -> POST /v1/tasks/ explicit slash"
    - "Auth surface aligned: 4 routes swapped ApiKeyAuth -> CurrentAgent (JWT) for dashboard reads; new _dashboard_or_admin_key dual-auth dep on DLQ keeps legacy CLI working"
    - "msw handlers updated to mock REAL backend paths and envelopes (not idealized REST), so future unit tests cannot drift from production again"
    - "4 real bugs auto-fixed during 04-10 execution: route ordering /search vs /{task_id} (routes_tasks.py), inverted sqlite3.Row guard (routes_memory.py + routes_p2.py), Workflow.updated_at fallback (useWorkflows adapter)"
  gaps_remaining: []
  regressions: []
  new_commits:
    - hash: 86d3030
      impact: "fix(04): use TanStack redirect() helper in auth guard"
    - hash: da6a2ca
      impact: "fix(04): only pass pathname (not search object) to redirect param"
    - hash: 5c8d0af
      impact: "fix(04): wire LoginForm to actual backend admin endpoint + response shape"
    - hash: f4dd6d3
      impact: "Plan 04-10 doc + initial integration test scaffolding"
    - hash: fdfb3cd
      impact: "feat(04-10) Task 1: GET /v1/locks/, GET /v1/workflows/, auth swap on costs/memory/locks; _dashboard_or_admin_key on DLQ; +8 unit tests"
    - hash: 8973f94
      impact: "feat(04-10) Task 2: useAgents + useTasks aligned to real paths via adapter; msw handlers updated"
    - hash: 5dff6ff
      impact: "feat(04-10) Task 3: useCosts + useMemoryEntries aligned via adapter"
    - hash: 92751b0
      impact: "feat(04-10) Task 4: useLocks + useWorkflows + useDlq aligned via adapter"
    - hash: 3967cfb
      impact: "fix(04-10) Task 5: tests/integration/test_dashboard_paths_live.py (7 tests, all PASS); route reorder in routes_tasks.py; sqlite3.Row guard fixes in routes_memory.py + routes_p2.py"
    - hash: b220a46
      impact: "docs(04-10): UAT.md gap resolution table - all 5 BROKEN rows -> RESOLVED"
    - hash: a0a085a
      impact: "docs(04-10): VPS deploy outcome - master HEAD a0a085a live at hub.brunhilde.cloud, /v1/health -> 200, service active"
human_verification:
  - test: Live JWT login happy path + invalid credential error
    expected: POST /v1/auth/admin/login succeeds; token in memory; invalid credentials show RFC 7807 toast; refresh of /dashboard keeps you signed in only until tab close (no persistence).
    why_human: Visual DOM observation needed for inline RFC 7807 toast; tab-close persistence is a runtime browser behavior.
    automated_coverage_added: "Happy path is now exercised by `test_dashboard_paths_live.py` fixture (real JWT issuance against live admin user) and by UAT Test 2 result: pass-after-fixes verified on production at https://hub.brunhilde.cloud/dashboard/login. Invalid-cred toast shape, sessionStorage-only behavior, and tab-close-and-reopen still need browser exercise."
    deferred_to_uat: true
    uat_status: "Test 2 happy path PASS (verified live VPS); deferred sub-items: invalid creds RFC 7807 toast, F5 reload, tab-close-and-reopen"
  - test: Live agent status updates without page refresh
    expected: Open /dashboard/agents in one tab; flip an agent's status from another; UI row updates within seconds via /v1/ws/ui without reloading.
    why_human: WebSocket patch behavior is only observable with a running hub + a real agent state transition.
    automated_coverage_added: "useAgents now hits real /v1/agents/discover/available (verified by integration test test_agents_discover_returns_200_with_jwt). Initial render is proven; live WS patch path still requires browser observation."
    deferred_to_uat: true
    uat_status: "Test 3 pending"
  - test: Task create + cancel flow end-to-end
    expected: Click "Create Task", submit, new task appears in list (WebSocket-driven); click Cancel on a running task, AlertDialog confirms, status transitions to cancelled in real time.
    why_human: Requires uvicorn + WS broadcast; msw mocks in tests do not exercise the live WS pipeline.
    automated_coverage_added: "useTasks list (GET /v1/tasks/search) and useCreateTask (POST /v1/tasks/) now both have integration test coverage in test_dashboard_paths_live.py. WS-driven update path still requires live observation."
    deferred_to_uat: true
    uat_status: "Test 4 pending"
  - test: DLQ manual retry
    expected: /dashboard/dlq shows failed tasks; clicking Retry fires POST /v1/dlq/{id}/retry and the item disappears after invalidation.
    why_human: Requires backend DLQ seeded with a failed task to observe round-trip.
    automated_coverage_added: "useDlq list (GET /v1/dlq/) now JWT-admin authed and integration-tested (test_dlq_list_accepts_jwt_admin). Retry round-trip with seeded DLQ row still pending."
    deferred_to_uat: true
    uat_status: "Test 5 pending"
  - test: Distributed trace viewer renders real spans (UI-12)
    expected: Open /dashboard/tasks/{id}; TraceTimeline displays actual tool-call spans from the task, not an empty placeholder.
    why_human: Visual rendering of category colors and span layout cannot be grep-verified.
    automated_coverage_added: "Backend /v1/tasks/{id}/trace endpoint covered by test_task_trace_endpoint.py (2 tests, 04-09). useTaskTrace -> TraceTimeline wiring verified in code. Visual span rendering with seeded trace_events row still pending."
    deferred_to_uat: true
    uat_status: "Test 6 pending"
  - test: Mobile layout collapse at small viewport (UI-15)
    expected: Resize browser to <768 px; agents and tasks tables collapse to cards; sidebar hides behind a toggle; topbar remains usable.
    why_human: Responsive breakpoint effect is visual-only; grep confirms the CSS classes exist but cannot prove layout quality.
    automated_coverage_added: "None - this remains a purely visual gate (md:hidden / md:flex Tailwind class presence is grep-verified, layout quality is not)."
    deferred_to_uat: true
    uat_status: "Test 7 pending"
notes:
  evidence_basis:
    prior: "msw + vitest only (proven insufficient: 5 hooks pointed at fictitious paths, 3 more relied on fragile FastAPI 307 redirects, all green in unit tests because msw mocks the path-as-asked rather than the real backend contract)"
    current: "Real-backend integration tests via FastAPI TestClient with real JWT and real DB (`tests/integration/test_dashboard_paths_live.py` -> 7 passed in 0.76s, just re-run); live VPS deploy at master HEAD `a0a085a`; production health check 200 OK; all 7 dashboard hooks resolve against real endpoints with real auth (no fictitious paths, no 307 redirects)"
  test_re_run:
    command: "python -m pytest tests/integration/test_dashboard_paths_live.py -v --no-cov"
    result: "7 passed, 11 warnings in 0.76s"
    timestamp: "2026-04-26T17:30:00Z"
  vps_health_re_run:
    command: "curl https://hub.brunhilde.cloud/v1/health"
    result: "HTTP 200"
    timestamp: "2026-04-26T17:30:00Z"
  working_tree:
    - path: web/package-lock.json
      state: modified
      impact: none on verification; out of scope
    - path: .kilo/, .playwright-mcp/, phase4-dashboard-not-found.png
      state: untracked
      impact: none on verification; UAT artifacts and tooling caches
---

# Phase 4: Command Center UI Verification Report

**Phase Goal:** A developer self-hosting OpenHub can log in, see live agent status, manage tasks, inspect workflows, and access the full visibility stack (DLQ, cost tracking, traces, memory, locks) from a browser.

**Verified:** 2026-04-26T17:30:00Z (third re-verification, post-04-10 endpoint mismatch closure)
**Status:** human_needed (code paths now backed by real-backend integration tests; six pre-ship UAT items retained for browser exercise)
**Re-verification:** Yes - post-04-10 backend/frontend endpoint alignment closure

## Evidence Basis Change (Critical)

The prior verification (`3e96e3f`, status `passed`) was based on msw + vitest. UAT Test 2 against the live VPS proved that evidence basis was insufficient: msw returns canned data at whatever path the frontend asks for, so five hooks pointed at fictitious endpoints (`/v1/agents`, `/v1/tasks`, `/v1/costs`, `/v1/memory`, `/v1/locks`) all looked green in unit tests but 404'd against the real backend. Three more (`useWorkflows`, `useDlq`, `useCreateTask`) only worked through FastAPI's auto-307-redirect on trailing slashes - fragile.

This re-verification (after plan 04-10) rests on:

1. **Real-backend integration tests** (`tests/integration/test_dashboard_paths_live.py`): 7 tests using FastAPI TestClient + real JWT issuance + real SQLite DB. **Just re-run: 7 passed in 0.76s.**
2. **Live VPS deploy:** master HEAD `a0a085a` is active at `https://hub.brunhilde.cloud`. Health check returns HTTP 200. Service is up.
3. **Code-level alignment proof:** `grep -rn "/v1/" web/src/hooks/queries/` shows every hook now hits a backend-verified endpoint. No fictitious paths remain.
4. **msw handler realignment:** all 7 handlers updated in 04-10 to mock the REAL backend paths and envelopes, so future unit tests can no longer drift from production.

This is the difference between "tests are green" and "the goal is achieved."

## Re-Verification (Post-04-10) - Success Criteria

| # | Success Criterion | Re-Verification Check | Status |
| - | ----------------- | --------------------- | ------ |
| 1 | JWT login, token in memory | UAT Test 2 PASS on live VPS after 3 inline auth fixes (86d3030, da6a2ca, 5c8d0af). Login flow exercised end-to-end at hub.brunhilde.cloud/dashboard/login with real JWT. localStorage confirmed empty. | PASS (live VPS verified) |
| 2 | Live agent status via WS | useAgents now hits `/v1/agents/discover/available` (test_agents_discover_returns_200_with_jwt PASS). Adapter renames agent_id->id, agent_name->name. WS sync handler unchanged. | PASS (initial fetch live-verified; WS patch still browser-only) |
| 3 | Task create + cancel in real time | useTasks -> `/v1/tasks/search?page=1&limit=100` (test_tasks_search_returns_200_with_jwt PASS), useCreateTask -> `POST /v1/tasks/` with explicit trailing slash (test_tasks_create_returns_201_with_jwt PASS). | PASS (HTTP path live-verified; WS path still browser-only) |
| 4 | DLQ manual retry | useDlq -> `/v1/dlq/` with new `_dashboard_or_admin_key` dual-auth (test_dlq_list_accepts_jwt_admin PASS). Retry path unchanged but now also accepts JWT. | PASS (auth path live-verified) |
| 5 | Visibility stack (costs, memory, locks, traces, workflows) | useCosts -> `/v1/costs/summary` (test_costs_summary_returns_200_with_jwt PASS), useMemoryEntries -> `/v1/memory/keys` (test_memory_keys_returns_200_with_jwt PASS), useLocks -> NEW `/v1/locks/` (test_locks_list_returns_200_with_jwt PASS), useWorkflows -> NEW `/v1/workflows/` (test_workflows_list_returns_200_with_jwt PASS). UI-12 trace wiring (04-09) unchanged and intact. | PASS (all 5 panels backed by integration tests) |
| 6 | Mobile-usable layout, table-to-card collapse | ResponsiveList.tsx hidden md:table-header-group / md:hidden CSS classes unchanged. Code path unchanged from prior verification. | PASS (code; visual still browser-only) |

**Score:** 6/6 success criteria verified in code, 5/6 with integration test coverage proving real backend integration. Criterion 6 is grep-verified only (visual gate).

## UAT 04-10 Resolution Table - Audit

Audited the 7 RESOLVED rows in `04-UAT.md` "Resolution (Plan 04-10)" table against the codebase:

| Hook | Claimed path | grep verification | Status |
| ---- | ------------ | ------------------ | ------ |
| useAgents | `/v1/agents/discover/available` | useAgents.ts:35 hits this exact path; agent_name->name adapter at :22 | VERIFIED |
| useTasks | `/v1/tasks/search?page=1&limit=100` | useTasks.ts:57 builds this path with QueryString; envelope unwrap proven by adapter | VERIFIED |
| useTask | `/v1/tasks/{id}` | useTasks.ts:67; assigned_agent_id->agent_id, last_error->error renames present | VERIFIED |
| useCreateTask | `POST /v1/tasks/` | useTasks.ts:87 uses trailing slash explicitly | VERIFIED |
| useCancelTask | `POST /v1/tasks/{id}/cancel` | useTasks.ts:101 | VERIFIED |
| useWorkflows | `GET /v1/workflows/` (NEW) | useWorkflows.ts:34 + routes_workflows.py:222 `@router.get("/", response_model=List[WorkflowResponse])` | VERIFIED |
| useWorkflow | `GET /v1/workflows/{id}` | useWorkflows.ts:44; run_id->id rename at :18 | VERIFIED |
| useDlq | `GET /v1/dlq/` | useDlq.ts:42; retry_count->retries, last_error->error renames present | VERIFIED |
| useRetryDlq | `POST /v1/dlq/{id}/retry` | useDlq.ts:52 | VERIFIED |
| useCosts | `GET /v1/costs/summary` | useCosts.ts:39; agent_name fallback at :27 | VERIFIED |
| useMemoryEntries | `GET /v1/memory/keys` | useMemory.ts:45; size_bytes=0 placeholder per plan decision | VERIFIED |
| useLocks | `GET /v1/locks/` (NEW) | useLocks.ts:11 + routes_p1.py:112 `@lock_router.get("/")` | VERIFIED |
| useHealth | `GET /v1/health` | unchanged | VERIFIED |
| useTaskTrace | `GET /v1/tasks/{id}/trace` | unchanged from 04-09 | VERIFIED |

**Search for fictitious paths:** `grep -rn "api<.*>('/v1/agents')\|api('/v1/agents')\|api<.*>('/v1/tasks')\|api('/v1/tasks')\|/v1/costs'\|/v1/memory'\|/v1/locks'" web/src/hooks/queries/` returns ZERO matches. The old paths are gone.

## Goal Achievement - Success Criteria (Consolidated)

| #   | Criterion                                                                  | Status                                | Evidence                                                                                                                                                                                                            |
| --- | -------------------------------------------------------------------------- | ------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | JWT login, token in memory (no localStorage, no URL params)                | PASS (live VPS verified)              | UAT Test 2 pass-after-fixes; localStorage confirmed empty in DevTools; Zustand-only auth-store; LoginForm now hits actual `/v1/auth/admin/login` with form-encoded payload                                          |
| 2   | Live online/offline/idle agent status with auto-updates                    | PASS (HTTP path live-verified)        | useAgents -> `/v1/agents/discover/available` (integration test PASS); useWebSocketSync agent_status_changed handler unchanged; ReconnectingBanner + exponential backoff intact                                      |
| 3   | Create task, select agent, cancel running task, real-time WS reflect       | PASS (HTTP paths live-verified)       | useTasks -> `/v1/tasks/search` (PASS); useCreateTask -> `POST /v1/tasks/` (PASS); AlertDialog cancel + useCancelTask path unchanged; WS sync handler unchanged                                                      |
| 4   | DLQ panel shows failed tasks, manual retry trigger                         | PASS (auth path live-verified)        | useDlq -> `/v1/dlq/` with `_dashboard_or_admin_key` (PASS); retry mutation unchanged                                                                                                                                |
| 5   | Cost, trace, memory, lock panels all accessible and show real data         | PASS (all 5 backed by integration)    | useCosts (`/v1/costs/summary` PASS), useMemoryEntries (`/v1/memory/keys` PASS), useLocks (NEW `/v1/locks/` PASS), useWorkflows (NEW `/v1/workflows/` PASS); UI-12 trace wiring from 04-09 unchanged                  |
| 6   | Mobile-usable layout, table-to-card collapse                               | PASS (code; needs visual UAT)         | ResponsiveList.tsx hidden md: pattern; Sidebar.tsx hidden md:flex; unchanged                                                                                                                                        |

## Requirements Coverage (UI-01..UI-16)

All 16 UI-* entries verified `[x]` and `Complete` in REQUIREMENTS.md (lines 43-58 checklist + 151-166 tracking table). No `Pending` entries. Code evidence below:

| Req   | Path Verification | Status |
| ----- | ----------------- | ------ |
| UI-01 | LoginForm now hits real `/v1/auth/admin/login` (5c8d0af); auth guard uses TanStack typed redirect (86d3030) | PASS |
| UI-02 | useAgents -> `/v1/agents/discover/available`; integration test PASS | PASS |
| UI-03 | useTasks -> `/v1/tasks/search`; integration test PASS | PASS |
| UI-04 | useCreateTask -> `POST /v1/tasks/`; integration test PASS | PASS |
| UI-05 | useCancelTask -> `POST /v1/tasks/{id}/cancel` (unchanged) | PASS |
| UI-06 | useWorkflows -> NEW `/v1/workflows/`; integration test PASS | PASS |
| UI-07 | useAgent -> `/v1/agents/{id}` (per-detail; TODO marker for adapter parity at 04-11) | PASS |
| UI-08 | useHealth -> `/v1/health`; live VPS returns 200 | PASS |
| UI-09 | api-client.ts ApiError + sonner toast (unchanged) | PASS |
| UI-10 | useDlq -> `/v1/dlq/` with dual-auth; integration test PASS | PASS |
| UI-11 | useCosts -> `/v1/costs/summary`; integration test PASS | PASS |
| UI-12 | useTaskTrace -> `/v1/tasks/{id}/trace` (04-09); routes/_authed/tasks/$taskId.tsx:5,82 wiring intact | PASS |
| UI-13 | useMemoryEntries -> `/v1/memory/keys`; integration test PASS | PASS |
| UI-14 | useLocks -> NEW `/v1/locks/`; integration test PASS | PASS |
| UI-15 | ResponsiveList.tsx unchanged; visual UAT deferred | PASS (code) |
| UI-16 | useWebSocketSync exponential backoff + ReconnectingBanner (unchanged) | PASS |

**Orphaned requirements:** None.
**Stale REQUIREMENTS.md entries:** None.

## Behavioral Spot-Checks (Re-Run)

| Behavior                                                       | Command                                                              | Result                              | Status |
| -------------------------------------------------------------- | -------------------------------------------------------------------- | ----------------------------------- | ------ |
| Real-backend integration test gate                             | `python -m pytest tests/integration/test_dashboard_paths_live.py -v --no-cov` | **7 passed in 0.76s**               | PASS   |
| Live VPS health endpoint                                       | `curl -s -o /dev/null -w "%{http_code}" https://hub.brunhilde.cloud/v1/health` | **200**                             | PASS   |
| No fictitious dashboard paths in hooks                         | `grep -rn "api<.*>('/v1/agents')\|/v1/costs'\|/v1/memory'\|/v1/locks'" web/src/hooks/queries/` | **0 matches**                       | PASS   |
| New backend endpoints registered                               | `grep "router.get" app/api/routes_workflows.py app/api/routes_p1.py` | `/v1/workflows/` line 222; `/v1/locks/` line 112 | PASS   |
| Dual-auth dep wired on DLQ                                     | `grep "_dashboard_or_admin_key" app/api/routes_p2.py`                | 4 hits (1 def + 3 route uses)       | PASS   |
| msw handlers updated to real paths                             | `grep -n "/v1/" web/src/mocks/handlers/{agents,tasks,dlq}.ts`        | All point at `/v1/agents/discover/available`, `/v1/tasks/search`, `/v1/dlq/` | PASS |
| UI-12 wiring still intact                                      | `grep -n "useTaskTrace" web/src/routes/_authed/tasks/\$taskId.tsx`   | imports + invocation at lines 5, 82 | PASS   |
| Branch on master                                               | `git branch --show-current`                                          | `master`                            | PASS   |

## Deferred UAT Checklist (Pre-Ship)

Six items retained from prior verification under `human_verification:` in frontmatter. They are now classified by automated-coverage status:

- **Test 2 (login):** PASS-AFTER-FIXES on live VPS for happy path. Sub-items still pending: invalid-cred RFC 7807 toast, F5 reload, tab-close-and-reopen.
- **Tests 3-5 (live agent WS / task WS / DLQ retry round-trip):** HTTP fetch paths and auth paths are now backed by integration tests, but live WS broadcasting and seeded DLQ retry observation still require browser exercise.
- **Test 6 (UI-12 trace render):** Backend endpoint and React wiring are integration- and unit-tested; visual span rendering with seeded `trace_events` row still pending.
- **Test 7 (mobile collapse):** Pure visual gate, no automated coverage possible.

These remain **pre-ship browser UAT items**, but the goal-backward verification level for Phase 4 is significantly stronger than at the prior `passed` checkpoint: every code path that UAT Test 2 proved was broken now has real-backend integration test coverage.

## Recommendation

**Phase 4 is COMPLETE at the code level. Status: `human_needed` for the 6 pre-ship browser UAT items.**

- 6/6 success criteria verified in code; 5/6 backed by real-backend integration tests (the sixth, mobile, is visual-only).
- 16/16 UI requirements shipped and reflected in REQUIREMENTS.md (no Pending).
- All 5 BROKEN hooks from UAT discovery are RESOLVED with grep-verifiable evidence in 04-UAT.md resolution table.
- All 3 fragile-redirect-only hooks are HARDENED with explicit paths.
- New `tests/integration/test_dashboard_paths_live.py` is the durable evidence base; msw mocks now mirror real backend so future unit tests cannot regress to fictitious paths.
- Live VPS at master HEAD `a0a085a` returns 200 OK on /v1/health.

Phase can proceed to Phase 5 once the deferred browser UAT items (3-7) are exercised by the human against the live VPS.

---

_Verified: 2026-04-26T17:30:00Z_
_Verifier: Claude (gsd-verifier)_
_Prior verification: 2026-04-19T17:15:00Z (status: passed, msw-only evidence basis)_
_Evidence basis change: msw + vitest -> real-backend integration tests + live VPS deploy_
