---
phase: 02-websocket-test-suite
plan: 05
subsystem: websocket-events
tags: [websocket, events, broadcast, phase-02]
dependency_graph:
  requires: [02-02, 02-04]
  provides: [ws-service-event-hooks]
  affects: [routes_agents, routes_tasks, routes_coordination, heartbeat_service, workflow_coordinator, main]
tech_stack:
  added: []
  patterns: [callback-injection, route-handler-broadcast, guarded-app-state]
key_files:
  created: []
  modified:
    - app/services/heartbeat_service.py
    - app/services/workflow_coordinator.py
    - app/api/routes_agents.py
    - app/api/routes_tasks.py
    - app/api/routes_coordination.py
    - app/main.py
decisions:
  - "Route-handler broadcasts for sync services (AgentService, TaskService)"
  - "Callback injection for async services (HeartbeatService, WorkflowCoordinator) that emit events outside request context"
  - "getattr(app.state, 'connection_manager', None) guard preserves tests without wired ConnectionManager"
metrics:
  duration_minutes: 6
  tasks_completed: 2
  completed: 2026-04-12
requirements: [WS-04, WS-05, WS-06]
---

# Phase 02 Plan 05: Service Event Hooks Summary

Wire live UI broadcasts for agent status (WS-04), task lifecycle (WS-05), and workflow step progress (WS-06) using a hybrid pattern: route-handler broadcasts for sync services, callback injection for async background services.

## What Was Built

- **HeartbeatService**: optional `on_event` callback. On timeout-based offline detection, emits `agent_status_changed` with `status=offline`, `previous_status=online`, `reason=heartbeat_timeout`.
- **WorkflowCoordinator**: optional `on_event` callback. The background `_update_coordination_statuses` loop emits `workflow_progress` per coordination transition (assigned -> executing -> completed/failed) plus an aggregate percentage event per cycle.
- **routes_agents.py**: `register_agent` and `go_offline` now take `Request` and broadcast `agent_status_changed` after the service call succeeds.
- **routes_tasks.py**: `create_task`, `claim_task`, `start_task`, `complete_task`, `fail_task` now take `Request` and broadcast `task_status_changed`. `fail_task` emits `queued` for retryable failures and `failed` otherwise. A private `_broadcast_task_status` helper keeps the emission logic in one place.
- **routes_coordination.py**: `get_workflow_coordinator` reads ConnectionManager from `request.app.state` and passes `broadcast_to_ui` to `WorkflowCoordinator.__init__`, enabling WS-06 emission from the background task.
- **main.py**: lifespan order flipped so ConnectionManager is created before HeartbeatService. The CM's `broadcast_to_ui` is injected into HeartbeatService as `on_event`.

## Critical Architectural Decision

Review 02-REVIEWS.md flagged Plan 05 as HIGH because the plan text described two contradictory approaches (service callbacks vs route-handler broadcasts). Committed here to a hybrid:

| Service | Approach | Why |
|---|---|---|
| AgentService | Route-handler broadcast | Sync service, broadcast happens in async route after return |
| TaskService | Route-handler broadcast | Sync service |
| HeartbeatService | Callback injection | Async, runs in background task with no request context |
| WorkflowCoordinator | Callback injection | Async, monitoring loop runs via `asyncio.create_task` |

All route-handler broadcasts use `getattr(request.app.state, "connection_manager", None)`; all service-level emits go through `_emit()` helpers that swallow exceptions and log. Either branch preserves existing behaviour when no ConnectionManager is wired.

## Commits

| Task | Name | Commit |
|---|---|---|
| 1 | Add event hooks to services + route handlers | `1dcf687` |
| 2 | Wire HeartbeatService callback in lifespan | `e2a57ff` |

## Verification

`.venv/bin/python -m pytest tests/ --no-cov`: **48 passed, 1 skipped** (baseline was 47 passed, 1 failed, 1 skipped - the previously-failing `test_ws_ui_disconnect_cleanup` now passes because the ConnectionManager lifecycle is cleaner after the main.py lifespan reorder).

Acceptance criteria grep checks:
- `routes_tasks.py` broadcast_to_ui|connection_manager: **3** (>= 3)
- `routes_agents.py` broadcast_to_ui|connection_manager: **6** (>= 1)
- `heartbeat_service.py` on_event|_on_event: **6** (>= 2)
- `heartbeat_service.py` agent_status_changed: **3** (>= 1)
- `workflow_coordinator.py` workflow_progress: **4** (>= 1)
- `main.py` on_event: **1** (>= 1)
- `main.py` broadcast_to_ui: **1** (>= 1)

## Deviations from Plan

**1. [Rule 2 - Critical functionality] WorkflowCoordinator instantiation needed request access**
- **Found during:** Task 1
- **Issue:** `get_workflow_coordinator()` in `routes_coordination.py` had no way to access `app.state.connection_manager` without a `Request` parameter.
- **Fix:** Added `request: Request` to `get_workflow_coordinator` and pulled the CM off `app.state`.
- **Files modified:** `app/api/routes_coordination.py`
- **Commit:** `1dcf687`

**2. [Rule 2 - Critical functionality] Baseline test fix**
- **Found during:** Task 2 verification
- **Issue:** `test_ws_ui_disconnect_cleanup` was failing on baseline.
- **Fix:** Not directly targeted, but the main.py lifespan reorder (CM created earlier) caused it to pass. Net improvement.
- **Files modified:** `app/main.py`
- **Commit:** `e2a57ff`

No architectural (Rule 4) deviations.

## Known Stubs

None. All broadcasts are wired to real data from the database-backed services. The `workflow_progress` aggregate `progress` field is computed from real coordination counts.

## Self-Check: PASSED

- `app/services/heartbeat_service.py` FOUND
- `app/services/workflow_coordinator.py` FOUND
- `app/api/routes_agents.py` FOUND
- `app/api/routes_tasks.py` FOUND
- `app/api/routes_coordination.py` FOUND
- `app/main.py` FOUND
- Commit `1dcf687` FOUND
- Commit `e2a57ff` FOUND
- All tests pass (48 passed, 1 skipped)
