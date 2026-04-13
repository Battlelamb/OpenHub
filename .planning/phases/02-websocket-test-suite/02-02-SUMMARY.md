---
phase: 02-websocket-test-suite
plan: 02
subsystem: websocket
tags: [websocket, connection-manager, prometheus, async, d-09, d-10, d-11, d-12, d-14, d-15]
requires:
  - app/config.py (Settings class via pydantic-settings)
  - app/logging.py (get_logger)
  - prometheus_client (Gauge, Counter)
  - fastapi.WebSocket
provides:
  - app/services/connection_manager.py:ConnectionManager
  - WS_CONNECTIONS_ACTIVE (Prometheus gauge, labels: type)
  - WS_EVENTS_SENT_TOTAL (Prometheus counter, labels: event_type)
  - WS_ERRORS_TOTAL (Prometheus counter)
  - Settings.max_ws_agents (env: AGENTHUB_MAX_WS_AGENTS)
  - Settings.max_ws_ui (env: AGENTHUB_MAX_WS_UI)
affects:
  - app/api/routes_websocket.py (will be refactored by plan 02-04 to use ConnectionManager instead of module-level _connections)
tech-stack:
  added: []
  patterns: [async-singleton-service, tiered-event-broadcast, prometheus-instrumentation, snapshot-iteration]
key-files:
  created:
    - app/services/connection_manager.py
  modified:
    - app/config.py
decisions:
  - "Event payload format: {event, data, timestamp} matching D-01 existing agent endpoint"
  - "Batch interval hardcoded to 5.0s class attribute (BATCH_INTERVAL_SEC) for easy test override"
  - "Token expiry warning window hardcoded to 60s class attribute (TOKEN_EXPIRY_WARNING_SEC)"
  - "Close code 4003 on stop() (server_error) matches D-14 close frame semantics"
  - "Close code 4001 on expired JWT (auth_expired) matches D-14"
  - "refresh_ui_expiry() added as encapsulated mutator so the upcoming /v1/ws/ui endpoint (02-04) does not need to touch _ui_expiry directly (addresses 02-04 review concern HIGH)"
  - "disconnect_agent/disconnect_ui use dict.pop() so double-disconnect is idempotent and gauge decrement only happens when the key was present"
  - "Failed sends auto-disconnect the offending client after broadcast iteration finishes (two-pass to avoid mutating the snapshot mid-flight)"
metrics:
  duration: ~4min
  completed_date: 2026-04-12
---

# Phase 02 Plan 02: ConnectionManager Class Summary

ConnectionManager singleton service with dual agent/UI WebSocket pools, tiered event broadcasting (immediate critical + 5s batched non-critical), Prometheus metrics, and JWT expiry tracking, built ready for the /v1/ws/ui endpoint and service-hook plans that follow.

## What Was Built

- **`app/config.py`**: Two new settings fields wired into the existing `AGENTHUB_` env prefix:
  - `max_ws_agents: int = 100` (AGENTHUB_MAX_WS_AGENTS)
  - `max_ws_ui: int = 10` (AGENTHUB_MAX_WS_UI)

- **`app/services/connection_manager.py`** (442 lines): `ConnectionManager` class plus module-level Prometheus metrics.

  Public surface:
  - Lifecycle: `start()`, `stop()` - manages background batch loop task
  - Agent pool: `connect_agent`, `disconnect_agent`, `broadcast_to_agents(exclude=...)`
  - UI pool: `connect_ui`, `disconnect_ui`, `broadcast_to_ui(critical=True)`, `send_to_client`
  - Token tracking: `refresh_ui_expiry(client_id, new_exp)` (encapsulated mutator)
  - Testing hook: `flush_batch()` returns count of events flushed
  - Properties: `agent_count`, `ui_client_count`, `connected_agents`, `connected_ui_clients`

  Module-level metrics:
  - `WS_CONNECTIONS_ACTIVE = Gauge(..., ["type"])` with type="agent" or "ui"
  - `WS_EVENTS_SENT_TOTAL = Counter(..., ["event_type"])`
  - `WS_ERRORS_TOTAL = Counter(...)`

## Tasks Executed

| Task | Name | Commit | Files |
| ---- | ---- | ------ | ----- |
| 1 | Add WS connection limit settings to config.py | 2417bf7 | app/config.py |
| 2 | Create ConnectionManager class | 1878eb8 | app/services/connection_manager.py |

## Cross-AI Review Fixes Applied

All three HIGH/MEDIUM concerns from 02-REVIEWS.md Plan 02-02 were addressed inline during implementation:

1. **(HIGH) Dict mutation during iteration** - Both `broadcast_to_ui` and `broadcast_to_agents` iterate over `list(self._ui_clients.items())` / `list(self._agents.items())` snapshots. Failed clients are collected in a `failed: List[str]` and disconnected only after the iteration completes, so `disconnect_ui` / `disconnect_agent` can never mutate the dict mid-iteration.

2. **(HIGH) `_batch_loop` silent death on flush failure** - The batch loop wraps both `_check_token_expiry()` and `flush_batch()` in separate `try / except Exception` blocks with structured error logging and `WS_ERRORS_TOTAL.inc()`. `asyncio.CancelledError` is re-raised (the outer try/except catches it to log) so `stop()` can still cancel the task cleanly. A failed send will no longer kill the background task.

3. **(MEDIUM) `_check_token_expiry` invocation vague** - Made explicit: `_batch_loop` calls `_check_token_expiry()` on every cycle (5s) before `flush_batch()`. It also snapshots `self._ui_expiry.items()` before iterating and defers disconnects to a second pass.

Additional review fix incorporated from Plan 02-04 concerns: `refresh_ui_expiry(client_id, new_exp)` method added so the upcoming /v1/ws/ui endpoint can update tracked JWT expiry without touching `_ui_expiry` directly. This preserves encapsulation for the downstream plan.

## Verification

- `python3 -c "from app.config import get_settings; s = get_settings(); print(f'agents={s.max_ws_agents} ui={s.max_ws_ui}')"` prints `agents=100 ui=10`.
- `python3 -c "from app.services.connection_manager import ConnectionManager, WS_CONNECTIONS_ACTIVE, WS_EVENTS_SENT_TOTAL, WS_ERRORS_TOTAL; cm = ConnectionManager(); print(f'OK agent_count={cm.agent_count} ui_count={cm.ui_client_count}')"` prints `OK agent_count=0 ui_count=0`.
- All acceptance criteria greps match expected counts (class/method signatures present, metric references present).
- Existing test suite: not applicable in this worktree (tests/ directory does not exist yet; plan 02-01 / 02-03 build the suite).

## Deviations from Plan

None - plan executed exactly as written. The cross-AI review recommendations were treated as part of the plan (per execution hint) and applied inline, not as deviations.

## Success Criteria

- [x] ConnectionManager importable with all methods
- [x] Dual pools (agent/UI) with configurable limits
- [x] broadcast_to_ui method for critical + batched non-critical events
- [x] Prometheus metrics: WS_CONNECTIONS_ACTIVE, WS_EVENTS_SENT_TOTAL, WS_ERRORS_TOTAL
- [x] Existing tests still pass (no tests/ directory present - import smoke passes)

## Known Stubs

None. This plan builds infrastructure only; all behavior is exercised by subsequent plans (02-04 endpoint, 02-05 service hooks, 02-06 integration tests). The ConnectionManager is fully functional - nothing is mocked or placeholder.

## Self-Check: PASSED

- FOUND: app/config.py (modified, verified max_ws_agents/max_ws_ui)
- FOUND: app/services/connection_manager.py (442 lines, imports clean)
- FOUND: commit 2417bf7 in worktree-agent-a41064e2 git log
- FOUND: commit 1878eb8 in worktree-agent-a41064e2 git log
