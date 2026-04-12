---
phase: 02-websocket-test-suite
plan: 03
subsystem: tests/core-backend
tags: [tests, capability-matcher, task-lifecycle, agent-lifecycle, TEST-02, TEST-03, TEST-04]
requirements: [TEST-02, TEST-03, TEST-04]
dependency_graph:
  requires:
    - app/services/capability_matcher.py
    - app/services/agent_service.py
    - app/services/task_service.py
    - app/api/routes_tasks.py
    - app/api/routes_agents.py
    - tests/conftest.py
  provides:
    - "TEST-02 unit coverage: CapabilityMatcher exact/partial/no-match, best selection, edge cases"
    - "TEST-03 integration coverage: task create / claim / start / complete / fail via HTTP"
    - "TEST-04 integration coverage: agent register / heartbeat / list / status via HTTP"
  affects:
    - "app/services/task_service.py - 3 payload-dict bind sites now json.dumps before DB update"
tech_stack:
  added: []
  patterns:
    - "Real tempfile SQLite test DB (no mocks) per D-16"
    - "Per-test agent registration + JWT minting with real agent.id as sub"
    - "Ghost capabilities (uuid suffix) prevent auto-assignment contamination"
    - "test_client fixture consumed even in unit tests to guarantee lifespan has run"
key_files:
  created:
    - tests/unit/test_capability_matcher.py
    - tests/integration/test_task_lifecycle.py
    - tests/integration/test_agent_lifecycle.py
  modified:
    - app/services/task_service.py
decisions:
  - "Use AgentService directly (not HTTP) in matcher unit tests to avoid auth overhead"
  - "For integration tests, mint JWT per test with sub=<real agent id> since get_current_agent() looks up sub in the agents table"
  - "test_fail_task forces max_retries=0 to guarantee terminal FAILED state regardless of retryable flag"
  - "test_register_agent hits /v1/agents/register with no auth header - that route is intentionally anonymous per routes_agents.py"
metrics:
  duration_minutes: 6
  tasks_completed: 2
  tests_added: 19
  files_changed: 4
  completed_at: "2026-04-12"
---

# Phase 2 Plan 03: Core Backend Tests Summary

19 new tests covering the CapabilityMatcher (TEST-02), full task lifecycle via HTTP (TEST-03), and agent register/heartbeat/list via HTTP (TEST-04), plus a Rule 1 auto-fix of three dict-binding bugs in TaskService.

## What Shipped

- **tests/unit/test_capability_matcher.py** - 7 tests (163 lines)
  - `test_exact_match_single_capability` - agent `["python"]` vs required `["python"]` -> score 1.0
  - `test_exact_match_multiple_capabilities` - superset agent scores 1.0 on subset requirement
  - `test_partial_match` - half-cover yields strict `0 < score < 1`
  - `test_no_match_returns_none` - random uuid capability leaves no match
  - `test_best_agent_selection` - tag-isolated competing agents, higher scorer wins
  - `test_empty_required_capabilities_returns_none` - empty list yields None (not 0/crash)
  - `test_case_insensitive_matching` - upper-case required, lower-case stored

- **tests/integration/test_task_lifecycle.py** - 7 tests (239 lines)
  - `test_create_task` - POST /v1/tasks/ returns 200 with `id` and a valid status
  - `test_create_task_missing_fields` - incomplete body returns 422
  - `test_claim_task` - ghost-cap task stays QUEUED then claims via HTTP
  - `test_start_task` - create -> claim -> start, persisted status becomes `running`
  - `test_complete_task_full_lifecycle` - full create -> claim -> start -> complete -> `completed`
  - `test_fail_task_non_retryable` - `max_retries=0 + retryable=False` -> `failed`
  - `test_claim_already_claimed_task` - second claim returns 400

- **tests/integration/test_agent_lifecycle.py** - 5 tests (115 lines)
  - `test_register_agent` - POST /v1/agents/register, 200, correct agent body
  - `test_register_duplicate_name_conflict` - duplicate name yields 409
  - `test_agent_heartbeat_keeps_agent_online` - register -> JWT -> heartbeat -> still in /online
  - `test_agent_list_contains_registered_agents` - both registrations visible via /v1/agents/online
  - `test_registered_agent_status_is_online` - status field is `"online"` after registration

## Test Results

`.venv/bin/python -m pytest tests/ --no-cov` -> **33 passed, 1 skipped** (baseline: 14 passed, 1 skipped).

Delta: +19 tests, 0 regressions.

## Deviations from Plan

### Rule 1 - Bug: TaskService bound raw `dict` into SQLite updates

- **Found during:** Task 2, `test_fail_task_non_retryable` verification run
- **Issue:** `TaskService.fail_task` builds an error-details payload and assigns the Python `dict` directly to `update_data["payload"]`. `task_repo.update` passes that into `sqlite3.execute`, which raises `Error binding parameter 4: type 'dict' is not supported`. The route swallows it as a 400 "Failed to process task failure". The same pattern exists in `complete_task` (when `completion.metrics` is set) and `cancel_task` (when `reason` is set). `update_progress` already used `json.dumps` - the three sites were simply inconsistent.
- **Fix:** Wrap `update_data["payload"] = _json.dumps(current_payload)` in all three methods.
- **Files modified:** `app/services/task_service.py` (lines 319, 398, 446)
- **Commit:** b34b1c5

### Review flag: approval-first registration (MEDIUM)

The cross-AI review warned that agents registered directly might be filtered out if an approval queue existed. Investigation showed **no approval-first code in the current branch** - `AgentService.register_agent` sets status to `ONLINE` on creation and no route/service filters by "approved". No workaround was needed. Documented here so future reviewers of the related branch commit (48d887d) know this plan did not interact with it.

## Design Notes

- **Why ghost capabilities?** `task_service.create_task` runs `_attempt_auto_assignment` synchronously. If a task's `required_capabilities` match any ONLINE agent in the DB, the service immediately claims the task for that agent and flips its status to CLAIMED/BUSY. That makes any later explicit `/claim` call fail. Using a uuid-suffixed capability (`ghost-<uuid>`) guarantees the matcher finds nobody and the task sits in QUEUED until the test drives it.
- **Why mint JWTs per test?** `get_current_agent` in `app/auth/dependencies.py` resolves the token `sub` against the agents table and rejects tokens whose subject isn't a real agent row. The session-scoped `admin_headers` fixture mints `sub="test-admin"`, which is not a real agent - admin routes that require `CurrentAdmin` would fail with 401. Integration tests therefore register a real agent first, then create a JWT with that agent's uuid as `sub` and `role="agent"`.
- **Why `test_client` in a unit test?** The matcher tests never make HTTP calls, but they need the `agents` table to exist. The cleanest way to guarantee that is to consume the `test_client` fixture, which triggers the app lifespan and creates all tables. Without it, a fresh run against a brand-new tempfile DB would fail on the first `agent_repo.create`.

## Deferred Issues

None discovered in this plan that are in scope. Pre-existing passlib/bcrypt skip from Plan 01 is unchanged.

## Files Touched

| File | Kind | Commit |
| ---- | ---- | ------ |
| tests/unit/test_capability_matcher.py | created (163 lines) | 193311a |
| tests/integration/test_task_lifecycle.py | created (239 lines) | b34b1c5 |
| tests/integration/test_agent_lifecycle.py | created (115 lines) | b34b1c5 |
| app/services/task_service.py | modified (Rule 1 fix, 3 sites) | b34b1c5 |

## Commits

- `193311a` test(02-03): add TEST-02 capability matcher unit tests
- `b34b1c5` test(02-03): add TEST-03 task and TEST-04 agent lifecycle integration tests

## Self-Check: PASSED

- tests/unit/test_capability_matcher.py - FOUND
- tests/integration/test_task_lifecycle.py - FOUND
- tests/integration/test_agent_lifecycle.py - FOUND
- .planning/phases/02-websocket-test-suite/02-03-SUMMARY.md - FOUND
- Commit 193311a - FOUND
- Commit b34b1c5 - FOUND
