---
status: testing
phase: 04-command-center-ui
source:
  - 04-VERIFICATION.md (human_verification items, deferred_to_uat: true)
started: 2026-04-19T18:00:00Z
updated: 2026-04-19T18:00:00Z
supersedes: 04-UAT-initial.md
---

## Current Test

number: 1
name: Cold Start Smoke Test
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
result: [pending]

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
result: [pending]

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
passed: 0
issues: 0
pending: 7
skipped: 0
blocked: 0

## Gaps

[none yet]
