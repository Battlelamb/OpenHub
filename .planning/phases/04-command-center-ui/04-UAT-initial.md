---
status: complete
phase: 04-command-center-ui
source:
  - 04-01-SUMMARY.md
  - 04-02-SUMMARY.md
  - 04-03-SUMMARY.md
  - 04-07-SUMMARY.md
started: 2026-04-19T00:00:00Z
updated: 2026-04-19T11:30:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Cold Start Smoke Test
expected: Kill any running uvicorn. Build web (npm run build) and start uvicorn fresh on port 7788. Server boots, startup logs show "dashboard_mounted", /v1/health returns 200, /dashboard/ returns HTML containing id="root".
result: issue
reported: "Fresh `pip install -r requirements.txt` does NOT install psutil, yet app/api/routes_health.py:7 imports it at module load, so `uvicorn app.main:app` fails with ModuleNotFoundError: No module named 'psutil' before any route can respond. Once psutil is installed manually, /v1/health and /dashboard/ both return 200 and the startup log shows dashboard_mounted."
severity: major

### 2. Dashboard loads at /dashboard/
expected: Open http://localhost:7788/dashboard/ in a browser. Page loads without JS errors. You see the OpenHub command center shell: left sidebar, topbar, dark background. No blank page, no 404.
result: issue
reported: "Browser verified via Playwright. /dashboard/ returns the built index.html (title = OpenHub Command Center) and the React app bootstraps, but the rendered page shows ONLY the text 'Not Found' on a black background - no sidebar, no topbar, no login form. The screenshot (.playwright-mcp/phase4-dashboard-not-found.png) shows a dark void with 'Not Found' in the top-left. Root cause is the TanStack Router has no basepath - it receives the URL path '/dashboard/' and finds no matching route in its tree (routes are declared at '/', '/login', '/agents', etc.). Also /vite.svg returns 404 because the favicon href in web/index.html is absolute instead of relative to the /dashboard/ base."
severity: blocker

### 3. Login flow
expected: If not authenticated, visiting /dashboard/ (or a protected route) shows the login page with email + password fields. Submitting valid credentials navigates into the dashboard. Submitting invalid credentials shows an inline RFC 7807 error (not a generic alert).
result: blocked
blocked_by: prior-phase
reason: "Blocked by Test 2 bug: router basepath missing means every path renders 'Not Found'. /dashboard/login does not even reach the SPA - it returns the backend's RFC 7807 404 because StaticFiles(html=True) does not do SPA fallback (same root as Test 12). Login form is untestable until router basepath + SPA fallback are fixed."

### 4. Sidebar navigation
expected: Sidebar shows three groups: Operations (Agents, Tasks, Workflows), Visibility (DLQ, Costs, Traces, Memory, Locks), Admin (Health, Settings). Clicking each nav item navigates to the matching route. Active item is visually highlighted (emerald accent).
result: blocked
blocked_by: prior-phase
reason: "Sidebar never mounts because the router has no basepath and falls through to Not Found before AppShell renders. Blocked by Test 2."

### 5. Theme toggle (dark/light)
expected: Topbar has a theme toggle. Default is dark (zinc-950 background). Clicking toggles to light theme across the whole app. Toggle persists while navigating between pages.
result: blocked
blocked_by: prior-phase
reason: "Topbar never renders. Blocked by Test 2."

### 6. Language toggle (TR/EN)
expected: Settings or topbar exposes a language toggle. Switching to Turkish translates nav items and common labels (e.g., "Agents" -> "Ajanlar", "Sign Out" -> "Çıkış"). Switching back to English restores English labels.
result: blocked
blocked_by: prior-phase
reason: "Topbar never renders. Blocked by Test 2."

### 7. Agents list + detail
expected: /agents shows a list of agents. On desktop (>=md) it renders as a table; on mobile (<md) it renders as cards (UI-15 responsive pattern). Each row shows status badge with correct color. Clicking an agent navigates to /agents/$agentId with capabilities and heartbeat info visible.
result: blocked
blocked_by: prior-phase
reason: "Route never matches; blocked by Test 2 router basepath issue."

### 8. Tasks: list, create, cancel, trace
expected: /tasks shows a task list with filters. A "Create Task" button opens a dialog; submitting creates a new task that appears in the list. Clicking Cancel on a running task opens an AlertDialog confirmation; confirming cancels the task. Clicking a task opens /tasks/$taskId showing a TraceTimeline (vertical timeline with category colors).
result: blocked
blocked_by: prior-phase
reason: "Route never matches; blocked by Test 2 router basepath issue."

### 9. Workflows list + detail
expected: /workflows shows workflows with step status badges. Clicking a workflow opens /workflows/$workflowId with per-step status visible.
result: blocked
blocked_by: prior-phase
reason: "Route never matches; blocked by Test 2 router basepath issue."

### 10. Visibility pages (DLQ, Costs, Memory, Locks, Health, Traces)
expected: Each visibility route loads without errors. DLQ shows failed items with a retry action. Costs shows per-agent cost tracking. Memory shows shared memory entries with a JSON inspector (expandable tree using <details>). Locks shows resource locks with conflict warnings. Health shows current health status. Traces route loads (placeholder OK).
result: blocked
blocked_by: prior-phase
reason: "Routes never match; blocked by Test 2 router basepath issue."

### 11. Reconnecting banner (WebSocket)
expected: Stop the backend while the dashboard is open. Within a few seconds the top of the page shows a "Reconnecting..." banner. Restart the backend; banner disappears and live data resumes.
result: blocked
blocked_by: prior-phase
reason: "App shell never renders; blocked by Test 2 router basepath issue."

### 12. Deep link / SPA fallback
expected: With the backend running, open http://localhost:7788/dashboard/agents/foo directly in a new tab (or hit it with curl). The response is the SPA index.html (contains id="root"), not a 404. Client-side router then handles the path.
result: issue
reported: "curl http://127.0.0.1:7788/dashboard/agents/foo returns HTTP 404 in production. FastAPI's StaticFiles(html=True) only serves index.html for directory requests, not for arbitrary non-existent subpaths. Users who refresh the browser on /dashboard/agents/<id> or share a deep-link URL get a 404 instead of the SPA. The existing smoke test in tests/unit/test_static_mount.py acknowledges this and accepts 404 as 'graceful', but real SPA fallback is not implemented - a catch-all route or custom handler is needed."
severity: major

### 13. API routes still work alongside /dashboard
expected: GET http://localhost:7788/v1/health still returns the JSON health payload (not index.html). The /dashboard static mount does NOT shadow /v1/* API routes.
result: pass
note: curl /v1/health returns valid JSON, content-type application/json. Dashboard mount does not interfere with API routes.

## Summary

total: 13
passed: 1
issues: 3
blocked: 9
pending: 0
skipped: 0

## Gaps

- truth: "Fresh install from requirements.txt must produce a server that boots"
  status: failed
  reason: "psutil is imported by app/api/routes_health.py:7 but is not declared in requirements.txt or pyproject.toml. Running `pip install -r requirements.txt` then `uvicorn app.main:app` fails immediately with ModuleNotFoundError before any request is served."
  severity: major
  test: 1
  artifacts:
    - requirements.txt
    - pyproject.toml
    - app/api/routes_health.py
  missing:
    - psutil declaration in requirements.txt (and pyproject.toml [tool.poetry.dependencies])

- truth: "Opening /dashboard/ must render the OpenHub command center shell (sidebar + topbar + content), not a Not Found page"
  status: failed
  reason: "TanStack Router is created at web/src/main.tsx:19 as `createRouter({ routeTree, context: { queryClient } })` with no `basepath` option. Vite build uses `base: '/dashboard/'` so assets load, but when the browser URL is '/dashboard/' the router receives that full path and finds no matching route (routes are declared as '/', '/login', '/agents', etc. in routeTree.gen.ts). Every URL under /dashboard renders TanStack Router's default 404. Playwright snapshot confirms: page body is empty except the text 'Not Found'. Additional minor issue: web/index.html contains `<link rel=\"icon\" href=\"/vite.svg\">` which returns 404 because the absolute href does not respect the /dashboard/ base."
  severity: blocker
  test: 2
  artifacts:
    - web/src/main.tsx (line 19 - createRouter call)
    - web/vite.config.ts (line 8 - base: '/dashboard/')
    - web/index.html (favicon link with absolute href)
    - web/src/routeTree.gen.ts
    - .playwright-mcp/phase4-dashboard-not-found.png (visual evidence)
  missing:
    - `basepath: '/dashboard'` (or `import.meta.env.BASE_URL.replace(/\\/$/, '')`) passed to createRouter
    - Favicon href changed to `./vite.svg` or the file copied under a /dashboard-relative path
    - Browser smoke test that navigates to /dashboard/ and asserts sidebar / login form renders, not just that index.html HTTP 200

- truth: "Deep-link URLs under /dashboard must fall back to index.html so the SPA router can handle them (refresh / shareable links)"
  status: failed
  reason: "curl -o /dev/null -w %{http_code} http://127.0.0.1:7788/dashboard/agents/foo returns 404. Mount at app/main.py:323-328 uses StaticFiles(directory=..., html=True), which only serves index.html for directory requests, not arbitrary non-existent subpaths. A catch-all FastAPI route (or custom StaticFiles subclass) is required to return index.html for /dashboard/* when no asset matches. Test in tests/unit/test_static_mount.py:42-52 hides the regression by accepting 404 as 'graceful'."
  severity: major
  test: 12
  artifacts:
    - app/main.py (lines 318-335 - StaticFiles mount)
    - tests/unit/test_static_mount.py (the deep-link test accepts 404, masking the bug)
  missing:
    - SPA fallback handler for /dashboard/{path:path} that returns web/dist/index.html when no asset matches (and path is NOT /v1/*, /admin, /metrics, etc.)
    - Strict test that asserts 200 + id="root" in response body for a deep-link path under /dashboard/
