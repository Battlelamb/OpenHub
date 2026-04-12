---
phase: 02
reviewers: [claude-agent]
reviewed_at: 2026-04-11T12:00:00Z
plans_reviewed: [02-01-PLAN.md, 02-02-PLAN.md, 02-03-PLAN.md, 02-04-PLAN.md, 02-05-PLAN.md, 02-06-PLAN.md]
notes: "Gemini CLI and Codex CLI failed (missing API keys). Review performed by independent Claude agent with fresh context."
---

# Cross-AI Plan Review - Phase 02

## Independent Agent Review

### Plan 02-01 - Auth Tests + conftest Fix

**Summary:** Well-scoped Wave 1 plan that fixes the urgent placeholder token blocker and builds TEST-01 auth tests.

**Strengths:** Correctly identifies placeholder token as silent failure risk. Mechanically checkable acceptance criteria. Clean two-task scope.

**Concerns:**
- MEDIUM: Session-scoped JWT fixtures may expire if test suite runs longer than token TTL. Should set `expires_delta=timedelta(hours=24)` explicitly.
- MEDIUM: `test_api_key_validate_valid` depends on DB initialization via `test_client` fixture side effect - fragile pattern.
- LOW: RBAC test content deferred to executor interpretation of policy file - could lead to wrong assertions.

**Suggestions:** Set explicit long expiry in test fixtures. Add `db_ready` fixture that directly initializes tables.

---

### Plan 02-02 - ConnectionManager Class

**Summary:** Well-detailed core WS infrastructure. Concrete interface spec, good Prometheus patterns, excellent `flush_batch()` escape hatch for deterministic testing.

**Strengths:** Single-threaded async avoids thread-safety issues. `flush_batch()` for testing is genuinely good design. Properly separates connection pools per D-09.

**Concerns:**
- HIGH: `_batch_loop` has no general exception handler around `flush_batch()`. If a send fails and propagates, the batch loop task dies silently. Need bare `except Exception` with logging.
- HIGH: `disconnect_ui` during `broadcast_to_ui` iteration will raise `RuntimeError` (dict changed during iteration). Must iterate over `list(self._ui_clients.items())` snapshot.
- MEDIUM: `_check_token_expiry` invocation location is vague. Must be explicitly called in `_batch_loop` on every cycle.
- MEDIUM: `stop()` closing all connections may raise `WebSocketDisconnect` in tests.

**Suggestions:** Snapshot dict before iteration in broadcast methods. Wrap `flush_batch()` in `_batch_loop` with bare except. Make `_check_token_expiry` call explicit in batch loop.

---

### Plan 02-03 - Core Backend Tests

**Summary:** Solid test coverage for existing backend. Three test files map cleanly to three requirements.

**Strengths:** Unique agent names via UUID prevent cross-test contamination. Pattern of reading source before writing tests.

**Concerns:**
- HIGH: Task 2 combines two integration test files (7+ and 5+ behaviors) into one atomic task. Split into two tasks for debuggability.
- MEDIUM: Approval-first registration (committed 48d887d) may block capability matcher tests if only approved agents are matched. Plan does not address this.
- MEDIUM: Expected error code for `test_claim_already_claimed` not specified (409 or 400?).

**Suggestions:** Add approval bypass for test agents. Split Task 2 into two separate tasks.

---

### Plan 02-04 - WS UI Endpoint

**Summary:** Clean endpoint creation. Auth flow and close codes correctly specified. Lifespan ordering explicit.

**Strengths:** Correct WebSocket protocol order (accept before close). 10-second auth timeout prevents connection leaks. Lifespan ordering spelled out.

**Concerns:**
- HIGH: Direct mutation of `cm._ui_expiry[client_id]` in token refresh flow breaks encapsulation. Should use a `refresh_ui_expiry()` method on ConnectionManager.
- MEDIUM: Router import inline in main.py instead of module-level violates isort conventions.
- MEDIUM: Welcome event uses `agent_id` field for UI client - semantically wrong, should be `client_id`.
- LOW: Refresh token failure handling not specified.

**Suggestions:** Add `refresh_ui_expiry()` method. Move import to module-level. Document refresh failure handling.

---

### Plan 02-05 - Service Event Hooks (WS-04, WS-05, WS-06)

**Summary:** Correctly identifies async/sync boundary problem. Pivots to route-handler broadcasts. CRITICAL: internal contradiction between two approaches.

**Strengths:** `getattr(request.app.state, "connection_manager", None)` guard preserves existing tests. Callback injection for async HeartbeatService is correct.

**Concerns:**
- HIGH: Plan contradicts itself - first proposes service callbacks, then says "REVISED APPROACH: emit from route handlers." Autonomous executor may implement both, causing double-broadcasting.
- HIGH: WorkflowCoordinator cannot emit WS-06 events from route handlers if workflow operations run as background tasks. Critical gap for WS-06.
- MEDIUM: HeartbeatService `__init__` currently takes only `database`. If revised approach removes service callback additions, lifespan wiring in Task 2 will fail.
- MEDIUM: Which route functions need `Request` parameter added is not enumerated.

**Suggestions:** Remove initial callback approach entirely. Commit to one pattern. Explicitly state WorkflowCoordinator event emission mechanism. Enumerate route signature changes.

---

### Plan 02-06 - WS Integration Tests

**Summary:** Thorough test coverage with good pitfall awareness. WS-06 trigger mechanism is problematic.

**Strengths:** All 7 behaviors clearly specified. Correct sync TestClient usage. Good teardown verification.

**Concerns:**
- HIGH: `asyncio.get_event_loop().run_until_complete()` for WS-06 test will fail in Starlette TestClient (separate event loop in background thread). Needs concrete alternative.
- HIGH: `test_ws_ui_disconnect_cleanup` asserts `ui_client_count == 0` - fails if any prior test left stale connections. Should check relative decrement.
- MEDIUM: `asyncio_mode = "auto"` not confirmed in pyproject.toml. If missing, async tests pass silently without running.
- LOW: Bare `except Exception` in auth failure test masks unexpected errors. Should catch `WebSocketDisconnect`.

**Suggestions:** Add test-only HTTP trigger endpoint for WS-06 or proper event loop fixture. Assert relative count change. Narrow exception clauses.

---

## Consensus Summary

### Top Concerns (by severity)

1. **Plan 05 internal contradiction on event emission strategy (HIGH)** - Callback vs route-handler approach both described. Must pick one before execution. WorkflowCoordinator gap means WS-06 may be unimplementable as written.

2. **Plan 02 dict mutation during iteration (HIGH)** - `broadcast_to_ui` iterating `_ui_clients` while `disconnect_ui` can mutate it. Runtime crash risk.

3. **Plan 06 WS-06 test trigger mechanism broken (HIGH)** - `run_until_complete()` won't work across TestClient thread boundary. No concrete alternative specified.

4. **Session-scoped fixture state leakage (MEDIUM-HIGH)** - In-memory SQLite + ConnectionManager persist across all tests. Plans 03 and 06 lack isolation guarantees.

5. **Approval-first registration may break TEST-02 (MEDIUM)** - Capability matcher tests register agents directly but approval gate may filter them from matching queries.

### Agreed Strengths

- ConnectionManager design with separate pools and `flush_batch()` is well-thought-out
- Tiered event model (critical immediate + batched non-critical) is clean
- Wave ordering and dependency graph are correct (after checker fix)
- Test plans read source before writing tests - prevents assumption drift

### Risk Assessment: MEDIUM-HIGH

Plans 01-04 are individually sound. Plans 05-06 have structural issues that will likely cause execution failures unless the contradictions and broken test triggers are resolved before execution.

### Recommended Pre-Execution Fixes

1. **Plan 05:** Delete the initial callback approach text. Commit to route-handler pattern. Add explicit WorkflowCoordinator event emission mechanism (callback for async coordinator, or dedicated endpoint).
2. **Plan 02:** Add `list()` snapshot before dict iteration in broadcast methods. Add exception handling in `_batch_loop`.
3. **Plan 06:** Replace `run_until_complete()` with a concrete test trigger (test-only HTTP endpoint or proper async fixture). Fix absolute count assertions to relative.
4. **Plan 03:** Note approval-first registration and add bypass or direct-insert fixture for test agents.

---

*Reviewed: 2026-04-11*
*Reviewer: Claude Agent (independent fresh context)*
*Note: Gemini CLI and Codex CLI unavailable (API keys not configured)*
