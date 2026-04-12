---
phase: 02-websocket-test-suite
plan: 06
subsystem: testing
tags: [pytest, websocket, testclient, starlette, connection-manager, jwt]

requires:
  - phase: 02-websocket-test-suite/02
    provides: ConnectionManager with connect_ui/disconnect_ui/broadcast_to_ui/flush_batch
  - phase: 02-websocket-test-suite/04
    provides: /v1/ws/ui endpoint wired through app.state.connection_manager
provides:
  - "tests/unit/test_connection_manager.py - 8 unit tests (pool mgmt, limits, broadcast isolation, batch flush)"
  - "tests/integration/test_websocket.py - 7 integration tests (auth success/fail, ping, cleanup, workflow_progress)"
  - "TEST-05 WebSocket integration coverage"
  - "WS-06 workflow_progress broadcast verification"
affects: []

tech-stack:
  added: []
  patterns:
    - "MockWebSocket stand-in for ConnectionManager unit tests"
    - "monkeypatch settings.max_ws_ui/max_ws_agents for limit enforcement"
    - "ws.portal.call(coro) to drive async ConnectionManager methods on the ASGI worker loop"
    - "Relative ui_client_count assertions with race-safe polling after context exit"

key-files:
  created:
    - tests/unit/test_connection_manager.py
    - tests/integration/test_websocket.py
  modified: []

key-decisions:
  - "MockWebSocket unit-test double: minimal send_json/close capture, avoids real ASGI plumbing"
  - "monkeypatch targets cm_module.settings (the module reference ConnectionManager reads) rather than reinstantiating"
  - "WS-06 broadcast triggered via ws.portal.call to keep the coroutine on the same event loop that owns the WebSocket"
  - "Disconnect cleanup uses relative count_before assertion + bounded poll to tolerate session-scoped client state and ASGI worker-thread timing"
  - "Synchronous test functions throughout integration file per research Pitfall 3 (TestClient + async test collisions)"

patterns-established:
  - "Unit-testing async ConnectionManager methods via pytest-asyncio auto mode with MockWebSocket"
  - "Driving ConnectionManager from an integration test via ws.portal.call(coro)"
  - "WebSocketDisconnect(code=4001) assertion pattern for server-initiated auth close frames"

requirements-completed: [TEST-05, WS-06]

duration: ~10min
completed: 2026-04-12
---

# Phase 02 Plan 06: WebSocket Test Coverage Summary

**End-to-end test coverage for the /v1/ws/ui dashboard endpoint plus ConnectionManager unit coverage: 8 unit tests over pool management/limits/broadcast isolation/batch flush, and 7 integration tests over JWT auth success + failure + ping + cleanup + WS-06 workflow_progress broadcast, all green against the real ASGI stack.**

## Performance

- **Duration:** ~10 min
- **Started:** 2026-04-12T11:40:54Z
- **Completed:** 2026-04-12T11:50:00Z (approx)
- **Tasks:** 2
- **Files created:** 2
- **Files modified:** 0

## Accomplishments

- Unit tests for ConnectionManager cover connect/disconnect, limits (both pools), broadcast isolation (UI pool only), batch buffering with deterministic flush, and safe disconnect of unknown ids
- Integration tests exercise the full /v1/ws/ui endpoint through Starlette's TestClient, including real JWT auth and real WebSocketDisconnect(4001) handling for invalid/missing/expired tokens
- WS-06 proven end-to-end: `broadcast_to_ui("workflow_progress", ...)` scheduled on the ASGI worker loop via `ws.portal.call` actually delivers the event to the connected UI client; payload fields (workflow_id, step, status, progress_pct) are asserted
- Disconnect cleanup test uses relative (count_before) assertion + 2s bounded poll to eliminate both session-scoped state leakage and ASGI worker-thread race conditions
- Full test suite: 48 passed, 1 pre-existing skip (passlib/bcrypt backend)

## Task Commits

1. **Task 1: ConnectionManager unit tests** - `2f5a50e` (test)
2. **Task 2: WebSocket integration tests (TEST-05, WS-06)** - `b148873` (test)

## Files Created/Modified

- `tests/unit/test_connection_manager.py` (created, 168 lines) - 8 async unit tests with MockWebSocket
- `tests/integration/test_websocket.py` (created, 192 lines) - 7 sync integration tests using TestClient.websocket_connect

## Decisions Made

- **MockWebSocket double for unit tests** - A minimal class with just `send_json` and `close` coroutines and a `sent: list` capture. Avoids importing Starlette WebSocket or running the full app, keeps unit tests truly isolated from ASGI.
- **monkeypatch the module-level settings reference** - ConnectionManager reads `settings.max_ws_ui` at call time from `app.services.connection_manager.settings`. Patching that reference lets limit tests shrink the cap to 2 deterministically without touching global config.
- **ws.portal.call for WS-06 trigger** - The test explicitly prefers the `WebSocketTestSession.portal` over all alternatives flagged in the review:
  - `asyncio.get_event_loop().run_until_complete` would try to run on the test thread's loop, not the ASGI worker's - the ConnectionManager's `_ui_clients[...]` WebSocket belongs to the worker loop and send_json would fail or hang
  - `anyio.from_thread.start_blocking_portal` would create a *new* portal on a different loop - same problem
  - `ws.portal` is the same portal the ASGI worker was started in, so `portal.call(coro)` runs the coroutine on the exact loop that owns the socket
- **Relative disconnect-cleanup assertion** - Session-scoped `test_client` means the ConnectionManager singleton on `app.state` persists across tests; absolute `== 0` would be flaky. Using `count_before` + short bounded poll handles both the session-scope and the server-side finally-block running on a different thread after the client context exits.
- **Synchronous test functions throughout the integration file** - Research Pitfall 3: mixing `async def test_*` with sync TestClient causes "RuntimeError: event loop already running" with pytest-asyncio auto mode. All integration tests are `def test_*`.
- **Expired token tests use a distinct subject** - `test-admin-expired` to avoid polluting the primary session fixture's client_id inside ConnectionManager pool state.

## Deviations from Plan

The review in the executor prompt flagged 4 HIGH issues for this plan; all were honored and the implementation differs from the plan text accordingly. These are Rule 2 corrections (critical functionality / correctness) and Rule 1 (bug prevention).

### Auto-fixed Issues

**1. [Rule 1 - Bug] WS-06 trigger does not use `asyncio.get_event_loop().run_until_complete()`**
- **Found during:** Task 2 (WS-06 test design)
- **Issue:** Plan text suggested `asyncio.get_event_loop().run_until_complete(manager.broadcast_to_ui(...))`. This would fail under Starlette TestClient because the ASGI app (and therefore the WebSocket object) runs on a separate event loop on a background worker thread - the test thread's loop is a different loop. Calling `send_json` on a WebSocket from the wrong loop either raises or hangs.
- **Fix:** Use `ws.portal.call(_trigger)` where `ws` is the `WebSocketTestSession` and `ws.portal` is the anyio portal bound to the ASGI worker's event loop. This is the same portal that started the ASGI app and is the only correct way to schedule a coroutine on the loop that owns the WebSocket. The plan's "Option B: test-only HTTP endpoint" was considered but rejected - `portal.call` is simpler, keeps the test self-contained, and does not require modifying `conftest.py` or adding a test-only route.
- **Files modified:** tests/integration/test_websocket.py
- **Verification:** `test_ws_ui_workflow_progress_event` passes and asserts all four payload fields (workflow_id, step, status, progress_pct) arrive at the UI client
- **Committed in:** b148873

**2. [Rule 1 - Bug] Disconnect cleanup uses relative assertion + race-safe poll, not absolute `== 0`**
- **Found during:** Task 2 (first run produced `assert 1 == 0` failure)
- **Issue:** Two problems stacked. First, session-scoped `test_client` means the ConnectionManager singleton persists across tests; an absolute `ui_client_count == 0` check would break whenever another test left a stale connection. Second, the server's `finally: await cm.disconnect_ui(...)` runs on the ASGI worker thread *after* the client context exits on the test thread, so the decrement is not guaranteed to be visible immediately - a plain post-context assertion races the worker.
- **Fix:** Read `count_before = cm.ui_client_count` before connecting, assert `+1` inside the with-block, and after the with-block exits poll `cm.ui_client_count` for up to 2 seconds until it returns to `count_before`. Bounded poll avoids hanging on real failures.
- **Files modified:** tests/integration/test_websocket.py
- **Verification:** Test passes on full-suite run and in isolation
- **Committed in:** b148873

**3. [Rule 2 - Correctness] Narrow exception handling on auth failure tests**
- **Found during:** Task 2 (planning)
- **Issue:** Plan text used bare `except Exception` in auth failure tests. Review HIGH flagged this as over-broad: it would also swallow assertion errors inside the try block and hide real bugs.
- **Fix:** All three auth-failure tests catch `WebSocketDisconnect` specifically, assert `exc.code == 4001`, and use a `try/except/else: raise AssertionError` pattern so a missing disconnect loudly fails the test.
- **Files modified:** tests/integration/test_websocket.py
- **Verification:** Grep shows 3 `WebSocketDisconnect` catches, 0 bare `except Exception`, 9 `4001` references
- **Committed in:** b148873

**4. [Rule 2 - Correctness] Verified asyncio_mode = "auto" before writing async unit tests**
- **Found during:** Task 1 (before writing unit tests)
- **Issue:** Review HIGH warned that missing `asyncio_mode = "auto"` would make bare `async def test_*` collect as coroutine warnings without actually running.
- **Fix:** Confirmed `pyproject.toml` line 59 contains `asyncio_mode = "auto"`. No explicit `@pytest.mark.asyncio` decorators needed. Also confirmed pytest-asyncio 0.21.1 is installed. Unit tests are plain `async def`.
- **Files modified:** none (verification only)
- **Verification:** `grep asyncio_mode pyproject.toml` -> `asyncio_mode = "auto"`; unit tests run as coroutines (8 passed)
- **Committed in:** 2f5a50e

---

**Total deviations:** 4 auto-fixed (all driven by the cross-AI review's HIGH feedback)
**Impact on plan:** No scope change. All fixes preserve the stated success criteria.

## Issues Encountered

- First run of `test_ws_ui_disconnect_cleanup` failed with `assert 1 == 0` because the server-side `finally: await cm.disconnect_ui(...)` runs on the ASGI worker thread after the test thread has exited the `with` block. Fixed with the bounded poll described above - permanent fix, not a flake workaround.
- No other issues. All other tests passed on first run.

## Verification

### Unit tests (Task 1)
- `grep -c "def test_" tests/unit/test_connection_manager.py` -> 8 (>=6 required)
- `grep -c "ConnectionManager" tests/unit/test_connection_manager.py` -> 4 (>=2 required)
- `grep -cE "connect_ui|connect_agent" tests/unit/test_connection_manager.py` -> 9 (>=3 required)
- `grep -c "broadcast_to_ui" tests/unit/test_connection_manager.py` -> 3 (>=1 required)
- `grep -c "flush_batch" tests/unit/test_connection_manager.py` -> 4 (>=1 required)
- `.venv/bin/python -m pytest tests/unit/test_connection_manager.py --no-cov` -> 8 passed

### Integration tests (Task 2)
- `grep -c "def test_" tests/integration/test_websocket.py` -> 7 (>=6 required)
- `grep -c "websocket_connect.*ws/ui" tests/integration/test_websocket.py` -> 7 (>=3 required)
- `grep -c "4001" tests/integration/test_websocket.py` -> 9 (>=2 required)
- `grep -c "send_json.*token" tests/integration/test_websocket.py` -> 7 (>=2 required)
- `grep -c "event.*connected" tests/integration/test_websocket.py` -> 4 (>=1 required)
- `grep -c "workflow_progress" tests/integration/test_websocket.py` -> 6 (>=2 required)
- `.venv/bin/python -m pytest tests/integration/test_websocket.py --no-cov` -> 7 passed

### Full suite
- `.venv/bin/python -m pytest tests/ --no-cov` -> **48 passed, 1 skipped** (pre-existing passlib/bcrypt skip from Plan 01)

## User Setup Required

None - no external service or configuration changes needed.

## Next Phase Readiness

- Phase 02 is now complete: all 6 plans executed (02-01 through 02-06)
- TEST-05 (WebSocket integration tests) and WS-06 (workflow_progress broadcast) are fully covered with live ASGI-level assertions
- ConnectionManager has both unit (this plan) and integration (this plan) coverage
- No deferred items, no blockers

## Self-Check: PASSED

- [x] `tests/unit/test_connection_manager.py` exists and contains 8 tests
- [x] `tests/integration/test_websocket.py` exists and contains 7 tests
- [x] Commit `2f5a50e` in git log
- [x] Commit `b148873` in git log
- [x] Full test suite green (48 passed, 1 pre-existing skip)
- [x] All acceptance criteria for both tasks verified via grep counts

---
*Phase: 02-websocket-test-suite*
*Completed: 2026-04-12*
