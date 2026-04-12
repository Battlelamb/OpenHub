---
phase: 02-websocket-test-suite
plan: 04
subsystem: websocket
tags: [fastapi, websocket, jwt, authentication, connection-manager]

requires:
  - phase: 02-websocket-test-suite/02
    provides: ConnectionManager with connect_ui/disconnect_ui/refresh_ui_expiry
provides:
  - "/v1/ws/ui WebSocket endpoint for dashboard clients"
  - "JWT authentication via initial message frame (D-03), no token in URL"
  - "Close code 4001 for auth failures, 4002 for connection limit"
  - "Ping/pong and mid-connection token refresh protocol"
  - "ConnectionManager wired into app lifespan, accessible via app.state"
affects: [02-05-service-event-hooks, 02-06-end-to-end-integration]

tech-stack:
  added: []
  patterns:
    - "WebSocket auth via first-message JSON frame (not query param)"
    - "app.state.connection_manager dependency access for routes"
    - "Module-level router imports in main.py (isort-clean)"

key-files:
  created:
    - app/api/routes_ws_ui.py
  modified:
    - app/main.py

key-decisions:
  - "Welcome envelope sets agent_id=null and carries session identity in data.client_id (UI clients are not agents)"
  - "Refresh token failure is non-fatal: existing JWT continues to govern the session; the batch loop disconnects on real expiry"
  - "ConnectionManager.stop() runs before HeartbeatService.stop() so open sockets close while the runtime is still live"
  - "ConnectionManager and ws_ui_router imported at module level in main.py (review MED fix)"

patterns-established:
  - "Auth handshake: accept() -> receive_text(timeout=10s) -> verify JWT -> cm.connect_ui"
  - "Use cm.refresh_ui_expiry(client_id, new_exp) - never mutate cm._ui_expiry directly"

requirements-completed: [WS-01]

duration: ~15min
completed: 2026-04-12
---

# Phase 02 Plan 04: WebSocket UI Endpoint Summary

**Dashboard /v1/ws/ui WebSocket endpoint with first-frame JWT auth, ConnectionManager wiring into app lifespan, and encapsulated token-refresh flow**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-04-12T11:25:00Z (approx, worktree sync)
- **Completed:** 2026-04-12T11:37:07Z
- **Tasks:** 2
- **Files modified:** 2 (1 created, 1 modified)

## Accomplishments
- `/v1/ws/ui` endpoint authenticates via first-frame JSON `{token: "..."}`; no JWT in URL query or access logs
- Close codes wired: 4001 auth failure (missing/invalid/expired/malformed/timeout), 4002 connection limit, 4003 server-not-ready
- Welcome envelope sends `{event, agent_id=null, timestamp, data.client_id, data.role}` - UI clients not misrepresented as agents
- Ping/pong responder and mid-session token refresh handler both delegate to ConnectionManager via `app.state.connection_manager`
- Token refresh uses the `refresh_ui_expiry()` public API introduced in Plan 02 (no `_ui_expiry` dict mutation)
- `ConnectionManager` created in lifespan startup, stored on `app.state`, stopped on shutdown before HeartbeatService
- `ws_ui_router` and `ConnectionManager` imported at module level in `main.py` (isort-clean)

## Task Commits

1. **Task 1: Create /v1/ws/ui endpoint** - `3bb3dcf` (feat)
2. **Task 2: Wire ConnectionManager into lifespan and include WS UI router** - `d5fb4d4` (feat)

## Files Created/Modified
- `app/api/routes_ws_ui.py` (created, 224 lines) - WebSocket endpoint with JWT first-frame auth, welcome event, ping/pong, token refresh, cleanup
- `app/main.py` (modified) - Added module-level imports, lifespan startup/shutdown wiring, router inclusion

## Decisions Made
- **Welcome envelope uses `agent_id=null` + `data.client_id`** - UI clients should not be misrepresented as agents (review MED fix). Preserves the canonical event envelope shape while being semantically honest.
- **Refresh failure is non-fatal** - If a client sends `refresh_token` with an invalid/expired JWT, log a warning and keep the existing session alive. The ConnectionManager batch loop will disconnect the client on actual expiry. This avoids dropping a still-valid session over a client-side mistake.
- **Imports at module level** - `ConnectionManager` and `ws_ui_router` imported at the top of `main.py` alongside other router imports, not inline in lifespan or mid-file. Matches review MED guidance and isort conventions.
- **Shutdown order** - `connection_manager.stop()` runs before `heartbeat_service.stop_monitoring()` so open WebSockets close cleanly while the rest of the runtime is still live.

## Deviations from Plan

The plan body originally instructed direct mutation of `cm._ui_expiry[client_id]` and an inline import of the ws_ui router inside `main.py`. The cross-AI review flagged both as HIGH/MEDIUM issues and recommended using `cm.refresh_ui_expiry(...)` and module-level imports. Both fixes were applied during execution per the review hints provided in the prompt. This is a Rule 2 adjustment (correctness/encapsulation).

### Auto-fixed Issues

**1. [Rule 2 - Encapsulation] Use refresh_ui_expiry() instead of mutating _ui_expiry dict**
- **Found during:** Task 1 (endpoint creation)
- **Issue:** Plan text said `cm._ui_expiry[client_id] = new_payload["exp"]`. This mutates a private attribute of ConnectionManager and breaks encapsulation (review HIGH).
- **Fix:** Called `cm.refresh_ui_expiry(client_id, new_exp)` (public API added in Plan 02-02) and also added a guard for unknown client_id via the method's return value semantics.
- **Files modified:** app/api/routes_ws_ui.py
- **Verification:** grep for `_ui_expiry` returns 0 matches in the new file; `refresh_ui_expiry` is called once.
- **Committed in:** 3bb3dcf

**2. [Rule 2 - Style] Module-level imports in main.py**
- **Found during:** Task 2 (lifespan/router wiring)
- **Issue:** Plan text embedded `from .services.connection_manager import ConnectionManager` and `from .api.routes_ws_ui import router as ws_ui_router` inline inside lifespan/mid-file. Review MED flagged this as an isort-convention violation.
- **Fix:** Moved both imports to the top of `main.py` alongside the other router imports. Lifespan now references the already-imported `ConnectionManager`, and `app.include_router(ws_ui_router)` uses the module-level symbol.
- **Files modified:** app/main.py
- **Verification:** Imports appear in lines 5-18 of `main.py`; `grep "from .services.connection_manager"` yields only the top-level import.
- **Committed in:** d5fb4d4

**3. [Rule 2 - Semantic correctness] Welcome envelope agent_id=null for UI clients**
- **Found during:** Task 1 (endpoint creation)
- **Issue:** Plan text set `"agent_id": client_id` in the welcome event. Review MED flagged that UI clients are not agents and carrying their identity in `agent_id` is semantically wrong.
- **Fix:** Welcome envelope now emits `"agent_id": None` and the session identity is carried in `data.client_id`. This keeps the canonical envelope shape (`event`, `agent_id`, `timestamp`, `data`) while being semantically honest.
- **Files modified:** app/api/routes_ws_ui.py
- **Verification:** Grep confirms the welcome `send_json` body contains `"agent_id": None` and `"client_id": client_id`.
- **Committed in:** 3bb3dcf

**4. [Rule 2 - Robustness] Non-fatal refresh-token failure handling (LOW review item)**
- **Found during:** Task 1 (endpoint creation)
- **Issue:** Plan did not specify what to do if a refresh JWT fails verification. Dropping the connection on a bad refresh would kill an otherwise-valid session.
- **Fix:** On `ExpiredSignatureError`/`InvalidTokenError` during refresh, log `ws_ui_refresh_rejected` and continue. The batch loop's expiry check still disconnects when the original JWT lapses, so security is preserved.
- **Files modified:** app/api/routes_ws_ui.py
- **Verification:** Manual inspection of the refresh_token branch.
- **Committed in:** 3bb3dcf

---

**Total deviations:** 4 auto-fixed (all Rule 2, all driven by the cross-AI review's HIGH/MEDIUM/LOW feedback flagged in the executor prompt)
**Impact on plan:** No scope change. All fixes tighten encapsulation/semantics/robustness. All acceptance criteria still satisfied.

## Issues Encountered

- The worktree was initially stale (pointed at commit `2772ae9`, missing `.planning/` and the ConnectionManager implementation). Resolved by fetching and hard-resetting to `gsd/phase-02-websocket-test-suite` (commit `11afcbd`) before executing the plan. No code impact.
- The worktree has no local `.venv`. Used the main repo's venv at `/home/omer/projects/OpenHub/.venv/bin/python` for import-checks and pytest runs.
- `pydantic-settings` requires `AGENTHUB_ADMIN_USER` / `AGENTHUB_ADMIN_PASSWORD`. Temporarily copied `.env` from the main repo for verification runs and removed it before committing.

## Verification

- `grep 'websocket("/v1/ws/ui")' app/api/routes_ws_ui.py` -> 1
- `grep "verify_token" app/api/routes_ws_ui.py` -> 3
- `grep "4001" app/api/routes_ws_ui.py` -> 8 (>=2 required)
- `grep "4002" app/api/routes_ws_ui.py` -> 2 (>=1 required)
- `grep "connection_manager" app/api/routes_ws_ui.py` -> 2 (>=1 required)
- `grep -E "token.*Query|query.*token" app/api/routes_ws_ui.py` -> 0 (no token in URL)
- `grep -c "connection_manager" app/main.py` -> 7 (>=3 required)
- `grep -c "ws_ui_router" app/main.py` -> 2 (>=2 required)
- `grep -c "ConnectionManager" app/main.py` -> 3 (>=1 required)
- `python -m pytest tests/ --no-cov` -> 14 passed, 1 skipped (pre-existing passlib/bcrypt skip)
- `python -c "from app.main import app; ..."` -> confirms `/v1/ws/ui` route registered

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `/v1/ws/ui` endpoint is ready for Plan 02-05 (service event hooks) which will call `cm.broadcast_to_ui(...)` to push events to dashboard clients
- Plan 02-06 (end-to-end tests) can exercise the full connect -> welcome -> broadcast -> disconnect flow against the running app
- No blockers

## Self-Check: PASSED

- [x] `app/api/routes_ws_ui.py` exists
- [x] `app/main.py` exists and imports pass
- [x] Commit `3bb3dcf` in git log
- [x] Commit `d5fb4d4` in git log
- [x] All existing tests still green (14 passed, 1 pre-existing skip)

---
*Phase: 02-websocket-test-suite*
*Completed: 2026-04-12*
