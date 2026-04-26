---
status: testing
phase: 04-command-center-ui
source:
  - 04-VERIFICATION.md (human_verification items, deferred_to_uat: true)
started: 2026-04-19T18:00:00Z
updated: 2026-04-19T18:00:00Z
deployed_to: hub.brunhilde.cloud (master @ ea9550c, 2026-04-19T14:45:26Z)
supersedes: 04-UAT-initial.md
---

## Current Test

number: 2
name: Live JWT Login - happy + invalid paths
expected: |
  At https://hub.brunhilde.cloud/dashboard/login submit valid admin credentials.
  Verify: POST /v1/auth/login succeeds, you land in the dashboard, JWT is in
  memory only (DevTools > Application > Local Storage shows NO access_token),
  invalid creds show an inline RFC 7807 toast, reload keeps you signed in
  until tab close (no persistence).
awaiting: user response

## Tests

### 1. Cold Start Smoke Test
expected: |
  Kill any running uvicorn and vite dev server. From a fresh shell:
    1. `source .venv/bin/activate`
    2. `cd web && npm run build && cd ..`
    3. `uvicorn app.main:app --host 0.0.0.0 --port 7788`
  Startup logs show no ModuleNotFoundError and include `dashboard_mounted`.
  Then curl/open http://localhost:7788/v1/health - returns 200 JSON.
  Then open http://localhost:7788/dashboard/ in a browser - the OpenHub shell
  renders (login page or dashboard depending on auth state), NOT "Not Found"
  and NOT a blank page.
result: pass
venue: VPS hub.brunhilde.cloud (not local)
journey:
  - Deploy attempt 1 failed at pip install -r requirements.txt (pydantic-core source build failed on Python 3.13; installed pydantic was 2.12.5, requirements.txt pinned 2.4.2; surgical psutil install worked instead)
  - Deploy attempt 2 failed at npm run build (TS2307 "Cannot find module '@/lib/...'" because .gitignore:13 'lib/' rule silently excluded web/src/lib/ since phase 4 bootstrap — 6 utility files never committed; also 7 implicit-any errors surfaced by VPS clean build that local cached build had masked)
  - Deploy attempt 3 green: git pull ea9550c, npm ci + npm run build + systemctl restart all succeeded, service active on pid 865234
verification:
  - curl http://127.0.0.1:7788/v1/health -> 200 JSON {"status":"healthy", version 0.1.0, pid 865234}
  - curl https://hub.brunhilde.cloud/dashboard/ -> HTTP/2 200, <title>OpenHub Command Center</title>, body has id="root" and /dashboard/assets/ references
  - curl https://hub.brunhilde.cloud/dashboard/agents/foo -> SPA fallback returns id="root" (deep link works)
  - /v1/health, /docs still 200 (catch-all doesn't shadow backend routes)
observation:
  - Pre-existing HARD-09 leftover: journalctl shows "can't compare offset-naive and offset-aware datetimes" in heartbeat_service once at startup. Non-fatal, service continues. Tracked as phase 1 residual, not a phase 4 regression.

### 2. Live JWT Login - happy + invalid paths
expected: |
  At /dashboard/login: submit valid admin credentials. POST /v1/auth/login
  succeeds, you land in the dashboard, and the JWT is in memory only -
  open DevTools > Application > Local Storage and verify NO `access_token`
  or similar key. Sign out, then submit invalid credentials on the login
  form. An inline error toast appears (RFC 7807 shape, not a generic
  alert). Finally, reload /dashboard/ while signed in - you remain
  authenticated within the tab, but closing and reopening the tab should
  land you back on the login page (no persistence).
result: pass-after-fixes
severity: blocker (3 sequential bugs surfaced, all fixed)
journey:
  - First Playwright run on /dashboard/agents -> "Something went wrong!" error boundary. Console: `Error: redirect:/login?redirect=%2Fagents`. Root cause web/src/routes/_authed.tsx threw plain Error('redirect:...') instead of TanStack Router's typed redirect() helper. Fix in commit 86d3030.
  - Second run -> "TypeError: Cannot convert object to primitive value" from beforeLoad. location.search is an OBJECT in TanStack Router; concatenating with location.pathname coerced object to primitive and threw. Fix in commit da6a2ca - use location.pathname only.
  - Third run -> POST /v1/auth/login -> 404. Backend has /v1/auth/admin/login (OAuth2PasswordRequestForm, form-encoded), NOT the JSON /v1/auth/login the frontend was hitting. Also backend response shape is {agent_id, role, permissions} not nested {user: {...}}. Fix in commit 5c8d0af.
verification_pass:
  - Login flow end-to-end on https://hub.brunhilde.cloud/dashboard/login with omer / OpenHub2026!
  - JWT memory-only confirmed: localStorage empty, only sessionStorage has tsr-scroll-restoration-v1_3 (ephemeral, not auth)
  - Sidebar all 11 nav items render correctly
  - Topbar (brand, hub-status indicator, theme toggle, user menu) all present
  - Auth guard redirect /dashboard/agents while signed-out -> /dashboard/login?redirect=%2Fagents works
deferred_subitems:
  - "test: invalid credential RFC 7807 toast (not yet exercised by Playwright run)"
  - "test: F5 reload persistence within tab"
  - "test: tab-close-and-reopen returns to login (token isn't in localStorage so should pass automatically)"

## Major Gap Discovered: Backend / Frontend Endpoint Mismatch

Phase 4 frontend was built against an idealized REST API that does not match the actual backend routes. msw mocks in unit tests masked this because they returned canned data at whatever path the frontend asked for. Once Test 2 unblocked the dashboard, every feature route 404s on its data fetch.

| Frontend hook | Frontend path | Backend reality | Status |
|---------------|---------------|-----------------|--------|
| useAgents | GET /v1/agents | no flat list; closest GET /v1/agents/discover/available | BROKEN |
| useTasks | GET /v1/tasks | no flat list; closest GET /v1/tasks/search | BROKEN |
| useTask | GET /v1/tasks/{id} | matches: /v1/tasks/{task_id} | OK |
| useCreateTask | POST /v1/tasks | matches with trailing slash: /v1/tasks/ | OK |
| useCancelTask | POST /v1/tasks/{id}/cancel | matches | OK |
| useWorkflows | GET /v1/workflows | matches with trailing slash: /v1/workflows/ | OK |
| useWorkflow | GET /v1/workflows/{id} | matches | OK |
| useDlq | GET /v1/dlq | matches with trailing slash: /v1/dlq/ | OK |
| useRetryDlq | POST /v1/dlq/{id}/retry | matches | OK |
| useCosts | GET /v1/costs | no flat list; backend has /v1/costs/summary | BROKEN |
| useMemory | GET /v1/memory | no flat list; backend has /v1/memory/keys | BROKEN |
| useLocks | GET /v1/locks | no flat list; backend has /v1/locks/status | BROKEN |
| useHealth | GET /v1/health | matches | OK |
| useTaskTrace | GET /v1/tasks/{id}/trace | matches (shipped in 04-09) | OK |

### Resolution (Plan 04-10, 2026-04-26)

Plan 04-10 closed this gap. Updated table:

| Frontend hook | Frontend path | Backend reality | Status |
|---------------|---------------|-----------------|--------|
| useAgents | GET /v1/agents/discover/available | matches; adapter renames agent_id->id, agent_name->name | RESOLVED |
| useTasks | GET /v1/tasks/search?page=1&limit=100 | matches; adapter unwraps {tasks,total,page,limit} | RESOLVED |
| useTask | GET /v1/tasks/{id} | matches; adapter renames assigned_agent_id->agent_id, last_error->error | UNCHANGED OK |
| useCreateTask | POST /v1/tasks/ (trailing slash) | matches without 307 redirect | HARDENED |
| useCancelTask | POST /v1/tasks/{id}/cancel | matches | UNCHANGED OK |
| useWorkflows | GET /v1/workflows/ | NEW backend list endpoint added in 04-10 Task 1 | RESOLVED |
| useWorkflow | GET /v1/workflows/{id} | matches; adapter renames run_id->id | UNCHANGED OK |
| useDlq | GET /v1/dlq/ | matches; auth swap to JWT-or-X-Admin-Key in 04-10 Task 1 | RESOLVED |
| useRetryDlq | POST /v1/dlq/{id}/retry | matches; same auth swap | UNCHANGED OK |
| useCosts | GET /v1/costs/summary | matches; auth swap to JWT in 04-10 Task 1 | RESOLVED |
| useMemoryEntries | GET /v1/memory/keys | matches; auth swap to JWT in 04-10 Task 1 | RESOLVED |
| useLocks | GET /v1/locks/ | NEW backend list endpoint added in 04-10 Task 1 | RESOLVED |
| useHealth | GET /v1/health | matches | UNCHANGED OK |
| useTaskTrace | GET /v1/tasks/{id}/trace | matches (shipped in 04-09) | UNCHANGED OK |

All previously broken hooks now resolve against real backend endpoints with correct auth (JWT). No fragile trailing-slash redirects remain.

**Recommendation:** Phase 4 needs a second gap-closure plan (04-10) that systematically aligns the broken hooks (useAgents, useTasks-list, useCosts, useMemory, useLocks) and their msw handlers to real backend endpoints + response shapes. Five hooks broken; three more (workflows, dlq, tasks-create) only work because of FastAPI's auto-redirect from /path to /path/ on trailing slash, which is fragile.

### 3. Live Agent Status Updates via WebSocket
expected: |
  Open /dashboard/agents in a browser tab. In a separate terminal, flip
  an agent's status via the backend (e.g., curl POST to an admin endpoint,
  or stop a running agent's heartbeat). Within a few seconds, the agent
  row in the UI updates its status badge (online -> offline, etc.) and
  last-seen timestamp without a page refresh. No manual reload needed.
  The /v1/ws/ui socket stays connected throughout (no reconnect banner).
result: [pending]

### 4. Task Create + Cancel Round-Trip
expected: |
  On /dashboard/tasks, click "Create Task". Form opens, agent selector
  populated, submit with a valid payload. The new task appears in the
  list within a second (WebSocket-driven, not a manual refresh). While
  it's running, click Cancel on the task row. An AlertDialog confirms
  with the UI-SPEC copy. Confirm - status transitions to cancelled in
  real time. No page reload.
result: [pending]

### 5. DLQ Manual Retry
expected: |
  Seed the DLQ with a failed task (backend CLI, direct DB insert, or
  deliberately-failing agent). Navigate to /dashboard/dlq - the failed
  task appears. Click Retry. Confirm dialog fires POST /v1/dlq/{id}/retry.
  After the response, the item disappears from the DLQ list (query
  invalidation) and can optionally be found back in /dashboard/tasks as
  a re-queued task.
result: [pending]

### 6. Distributed Trace Viewer (UI-12)
expected: |
  Need a task with at least one trace_events row. Either:
    - Trigger a real agent run that writes spans, OR
    - Insert a test row:
      `INSERT INTO trace_events (task_id, name, event_type, data, duration_ms) VALUES (...);`
  Open /dashboard/tasks/{that-task-id}. Scroll to the Trace section.
  TraceTimeline shows the actual span(s) with the correct category color
  (llm=violet-400, tool=sky-400, db=amber-400, http=emerald-400,
  internal=zinc-500, error=red-500), label, and duration badge. Not an
  empty placeholder, not a loading spinner that never resolves.
result: [pending]

### 7. Mobile Layout Collapse (UI-15)
expected: |
  Resize the browser to <768px width (or Chrome DevTools > device toolbar
  > iPhone 14 Pro or similar). Observable changes on /dashboard/agents
  and /dashboard/tasks:
    - Tables collapse to card layout (each row is a stacked card, no
      horizontal scroll)
    - Sidebar hides behind a hamburger/sheet toggle in the topbar
    - Topbar remains usable (health dot, theme toggle, user menu
      accessible)
    - Text wraps cleanly, no horizontal overflow on any list page
  Resize back to desktop - table layout returns, sidebar becomes persistent.
result: [pending]

## Summary

total: 7
passed: 2
issues: 1
pending: 5
skipped: 0
blocked: 0
notes: Test 2 pass-after-fixes (3 sequential bugs fixed inline). Discovered larger backend/frontend endpoint mismatch affecting 5 hooks; tracked as gap requiring plan 04-10.

## Gaps

[none yet]
