---
phase: 03-vector-database
plan: 04
subsystem: auto-indexing
tags: [vector, background-tasks, retry-worker, lifespan, tdd]
requires:
  - app.services.vector_search_service.VectorSearchService (Plan 02)
  - app.services.embedding_service.get_embedding_service (Plan 03)
  - app.database.vector_availability.is_vector_enabled (Plan 01)
provides:
  - app.services.embedding_hooks.schedule_embedding
  - app.services.embedding_hooks._embed_and_store
  - app.services.embedding_retry_worker.start_retry_worker
  - app.services.embedding_retry_worker.stop_retry_worker
  - app.services.embedding_retry_worker._run_once
affects:
  - app/api/routes_memory.py (write_memory schedules embedding for both insert + update)
  - app/api/routes_tasks.py (create_task schedules embedding for description)
  - app/api/routes_artifacts.py (upload_artifact schedules embedding, base64 decode best-effort)
  - app/api/routes_messaging.py (send_message schedules embedding for direct messages)
  - app/main.py lifespan (starts/stops embedding_retry_worker)
tech_stack:
  added: []
  removed: []
  patterns:
    - BackgroundTasks scheduled inside route handler after successful insert
    - Never-raises coroutine contract (Pitfall 6 mitigation - swallowed BG errors)
    - Cheap defensive 30000-char truncation aligned with EmbeddingService cap
    - asyncio.create_task lifespan worker with CancelledError-clean shutdown
    - structlog contextvars trace_id propagation into background tasks
key_files:
  created:
    - app/services/embedding_hooks.py
    - app/services/embedding_retry_worker.py
  modified:
    - app/api/routes_memory.py
    - app/api/routes_tasks.py
    - app/api/routes_artifacts.py
    - app/api/routes_messaging.py
    - app/main.py
    - tests/unit/test_auto_index.py
    - tests/unit/test_retry_worker.py
    - tests/integration/test_auto_indexing.py
decisions:
  - "Auto-indexing on memory writes covers both INSERT and UPDATE paths so search reflects in-place value rewrites; tasks/artifacts/messages have no UPDATE handlers in scope so re-embed-on-update is deferred."
  - "Artifact embedding decodes base64 payloads best-effort with errors='replace'; binary blobs whose decoded form is empty short-circuit the schedule helper (no failed row created)."
  - "Broadcast and thread messages are NOT auto-indexed - only the /v1/messages/send direct-message handler embeds. Broadcasting fans out N rows; embedding all N would be wasteful since they share one content string."
  - "Retry worker stops BEFORE WebSocket / heartbeat services in shutdown so its in-flight DB updates land while the connection layer is still live."
  - "schedule_embedding always reads is_vector_enabled at call time (not module import) so monkeypatching in tests works without resetting cached state."
metrics:
  duration: 6m
  completed: 2026-04-13T06:58:49Z
  tasks: 2
  files_created: 2
  files_modified: 8
  commits: 4
---

# Phase 03 Plan 04: Auto-Indexing & Retry Worker Summary

Wires the 4 content-producing write paths (memory, tasks, artifacts, messages) to schedule background embedding jobs via FastAPI BackgroundTasks, and starts a 5-minute polling retry worker in the app lifespan that re-embeds any rows whose embedding_status is NULL or 'failed'. Both are no-ops on local SQLite. This fulfills VEC-04 end-to-end.

## What Was Done

### Task 1 - Auto-indexing background hooks (TDD)

- **app/services/embedding_hooks.py** (new):
  - `_MAX_TEXT_CHARS = 30000` mirrors the OpenAI backend cap so retry and write paths agree on the upper bound.
  - `schedule_embedding(background_tasks, entity_type, entity_id, text)` short-circuits in three cases: `is_vector_enabled() is False`, unknown entity_type, or empty/None text. On success it captures `structlog.contextvars["trace_id"]` if present, then `background_tasks.add_task(_embed_and_store, ...)`.
  - `_embed_and_store(entity_type, entity_id, text, trace_id)` is the never-raises coroutine. Empty/whitespace text returns silently (no failed row). Missing backend logs and calls `mark_failed("no embedding backend configured")`. Truncation happens here so retries see the exact same input bound. The full embed call is wrapped in try/except - any exception logs `embedding_failed` and calls `mark_failed(str(e))`. Even mark_failed is wrapped so a transient DB hiccup cannot escape into the BackgroundTasks runner (Pitfall 6).

- **Route insertions** (line numbers post-edit):

  | Route | File | Hook Line | Inserted After |
  |-------|------|-----------|----------------|
  | memory write (UPDATE branch) | app/api/routes_memory.py | 63 | UPDATE shared_memory ... |
  | memory write (INSERT branch) | app/api/routes_memory.py | 77 | INSERT INTO shared_memory ... |
  | task create | app/api/routes_tasks.py | 99 | broadcast_task_status |
  | artifact upload | app/api/routes_artifacts.py | 69 | logger.info("artifact_uploaded") |
  | message send | app/api/routes_messaging.py | 116 | logger.info("message_sent") |

  All five sites pass through `schedule_embedding`, so the short-circuit logic lives in one place. Memory was the only entity with both INSERT and UPDATE paths in scope; the others only have create handlers in their current router shape, so re-embed-on-update is documented as deferred (see "Deferred / Out of Scope" below).

- **Artifact base64 handling**: `routes_artifacts.upload_artifact` decodes base64 inputs best-effort via `base64.b64decode(...).decode("utf-8", errors="replace")` so plain-text and JSON artifacts get embedded. Truly binary blobs become an empty string and the schedule helper short-circuits (no failed row written, no embed wasted on noise).

- **tests/unit/test_auto_index.py** (replaced 2 xfail stubs with 10 real tests):
  - `test_schedule_embedding_noop_when_disabled`: monkeypatches `is_vector_enabled -> False`, asserts `add_task` was NOT called.
  - `test_schedule_embedding_adds_task`: positive path; asserts `add_task` was called with `_embed_and_store` + the right args.
  - `test_schedule_embedding_skips_unknown_entity_type` / `test_schedule_embedding_skips_empty_text`: both short-circuit cases.
  - `test_embed_and_store_handles_none_backend`: `get_embedding_service -> None`; asserts mark_failed called with "no embedding backend" message and no exception raised.
  - `test_embed_and_store_handles_backend_exception`: backend.embed raises RuntimeError("boom"); asserts mark_failed called with "boom" and no exception escapes.
  - `test_embed_and_store_writes_embedding_on_success`: positive happy path, asserts write_embedding called once with the correct args.
  - `test_embed_and_store_truncates_long_text`: 60000-char input -> backend.embed sees a 30000-char string.
  - `test_embed_and_store_skips_empty_text`: whitespace-only input -> backend.embed never called.
  - `test_embed_and_store_marks_failed_on_empty_result`: backend returns `[]` -> mark_failed called.

- **tests/integration/test_auto_indexing.py** (replaced 1 xfail stub with 5 real tests):
  - Created a `seeded_admin_agent` fixture that inserts a `test-admin` row into the `agents` table so message-send and task-create routes can resolve sender/owner.
  - Created an `admin_api_key` fixture that uses `APIKeyManager.create_api_key` directly (no HTTP) with explicit valid scopes (the `/v1/auth/api-keys` endpoint does not exist in the current routes_auth surface).
  - Tests:
    - `test_memory_write_triggers_embedding` - POST /v1/memory/write -> backend.embed called with `["hello memory"]`, write_embedding called with entity_type="memory".
    - `test_message_send_triggers_embedding` - POST /v1/messages/send -> entity_type="message", text="hi msg".
    - `test_artifact_upload_triggers_embedding` - POST /v1/artifacts/upload -> entity_type="artifact", text="artifact body".
    - `test_task_create_triggers_embedding` - POST /v1/tasks/ -> entity_type="task", text="task description text". Uses `required_capabilities: ["general"]` because the request validator rejects empty lists.
    - `test_memory_write_noop_when_vector_disabled` - is_vector_enabled patched to False -> backend.embed never called, write_embedding never called.

### Task 2 - Embedding retry worker (TDD)

- **app/services/embedding_retry_worker.py** (new):
  - Module-level `RETRY_INTERVAL_SECONDS = 300` (D-13), `BATCH_LIMIT = 50`, `_MAX_TEXT_CHARS = 30000`.
  - `_run_once()` is the testable inner iteration: short-circuits if `is_vector_enabled() is False` or `get_embedding_service()` is None. Iterates `ENTITY_CONFIG.keys()` and for each entity type calls `svc.list_unindexed(entity_type, limit=BATCH_LIMIT)`. Per-row processing wraps embed + write_embedding in try/except so one bad row can't poison the rest of the batch; failure paths call `mark_failed`. Empty content rows are marked failed with "empty content" so they don't get re-attempted forever. Returns the count of successfully embedded rows.
  - `_loop(interval)` is the long-running wrapper: while True, calls `_run_once`, then `await asyncio.sleep(interval)`. Catches `CancelledError` for clean shutdown logging.
  - `start_retry_worker(interval=RETRY_INTERVAL_SECONDS)`: short-circuits when vector is disabled (logs `embedding_retry_worker_skipped_vector_disabled`); guards against double-start; otherwise stores the task in module-level `_worker_task`.
  - `stop_retry_worker()`: cancels the task, awaits it, swallows CancelledError, clears the handle.

- **app/main.py lifespan**:
  - Imports `start_retry_worker` and `stop_retry_worker` from `embedding_retry_worker` inside the lifespan body (matches the existing pattern of in-function imports for service wiring).
  - **Startup order**: connection_manager -> heartbeat_service -> embedding_retry_worker (last so the DB is fully migrated and other services already running). Wrapped in try/except + log so a worker startup failure can never break app boot.
  - **Shutdown order** (reverse): stop_retry_worker FIRST so its in-flight DB updates can land while the connection layer is still up, then connection_manager, then heartbeat_service. Each shutdown call is wrapped in try/except + log for the same reason.

- **tests/unit/test_retry_worker.py** (replaced 1 xfail stub with 8 real tests):
  - `test_worker_skips_when_vector_disabled` - is_vector_enabled patched to False -> `_worker_task` stays None.
  - `test_run_once_returns_zero_when_vector_disabled` - direct call to `_run_once` with vector disabled returns 0.
  - `test_run_once_returns_zero_when_no_backend` - get_embedding_service patched to None returns 0.
  - `test_run_once_processes_rows` - list_unindexed returns 2 memory rows -> write_embedding called twice, returns 2.
  - `test_run_once_iterates_all_entity_types` - 1 row per entity type -> 4 write_embedding calls, all 4 entity_types observed in args.
  - `test_run_once_handles_item_failure` - first embed raises RuntimeError -> second row still succeeds, mark_failed called for the first.
  - `test_run_once_skips_empty_content` - whitespace-only content row -> write_embedding never called, mark_failed("empty content").
  - `test_stop_cancels_running_task` - start with interval=10, yield once, stop -> `_worker_task` is None.

## Verification

```bash
.venv/bin/python -m pytest tests/unit/test_auto_index.py tests/unit/test_retry_worker.py tests/integration/test_auto_indexing.py -v --tb=short --no-cov -m "not turso"
# 23 passed (10 + 8 + 5)

.venv/bin/python -m pytest tests/ --tb=short --no-cov -m "not turso"
# 94 passed, 1 skipped, 8 deselected, 3 xfailed
# (Plan 04 retry-worker xfail stub is GONE - replaced by 8 real passing tests)

AGENTHUB_ADMIN_USER=x AGENTHUB_ADMIN_PASSWORD=y .venv/bin/python -c "from app.main import app; print('ok')"
# ok

grep -q "schedule_embedding" app/services/embedding_hooks.py        # OK
grep -q "_embed_and_store" app/services/embedding_hooks.py           # OK
grep -q "except Exception" app/services/embedding_hooks.py           # OK (Pitfall 6)
grep -q "mark_failed" app/services/embedding_hooks.py                # OK
grep -q "schedule_embedding" app/api/routes_memory.py                # OK
grep -q "schedule_embedding" app/api/routes_tasks.py                 # OK
grep -q "schedule_embedding" app/api/routes_artifacts.py             # OK
grep -q "schedule_embedding" app/api/routes_messaging.py             # OK
grep -q "BackgroundTasks" app/api/routes_memory.py                   # OK
grep -q "BackgroundTasks" app/api/routes_tasks.py                    # OK
grep -q "BackgroundTasks" app/api/routes_artifacts.py                # OK
grep -q "BackgroundTasks" app/api/routes_messaging.py                # OK
grep -q "async def start_retry_worker" app/services/embedding_retry_worker.py  # OK
grep -q "async def stop_retry_worker" app/services/embedding_retry_worker.py   # OK
grep -q "RETRY_INTERVAL_SECONDS = 300" app/services/embedding_retry_worker.py  # OK
grep -q "asyncio.CancelledError" app/services/embedding_retry_worker.py        # OK
grep -q "list_unindexed" app/services/embedding_retry_worker.py                # OK
grep -q "start_retry_worker" app/main.py                                       # OK
grep -q "stop_retry_worker" app/main.py                                        # OK
```

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Integration test fixture path - api-key creation endpoint doesn't exist**
- **Found during:** Task 1 GREEN (integration tests setup)
- **Issue:** Plan suggested creating an admin API key via `POST /v1/auth/api-keys` and parsing the response, but `routes_auth.py` does not expose that endpoint (only `/agent/register`, `/agent/login`, `/admin/login`, `/refresh`, `/logout`, `/me`, `/verify`).
- **Fix:** Switched the `admin_api_key` fixture to call `APIKeyManager.create_api_key` directly with explicit valid scopes (`task:read`, `task:create`, `task:update`, `artifact:read`, `artifact:upload`, `system:monitor`, `system:admin`). The first attempt with `["*"]` failed because `_validate_scopes` filters against the `APIKeyType.ADMIN` allowlist of real scope strings.
- **Files modified:** tests/integration/test_auto_indexing.py
- **Commit:** f6cf7ab

**2. [Rule 3 - Blocking] Tasks/messages routes need a real agent row**
- **Found during:** Task 1 GREEN (integration tests for task and message)
- **Issue:** `POST /v1/tasks/` returned 401 "Agent not found or deactivated" because the JWT subject `test-admin` had no row in the `agents` table. The `/v1/messages/send` route has the same shape.
- **Fix:** Added a `seeded_admin_agent` fixture that inserts a minimal `agents` row with id="test-admin" before tests that touch task or message creation.
- **Files modified:** tests/integration/test_auto_indexing.py
- **Commit:** f6cf7ab

**3. [Rule 3 - Blocking] TaskCreate model rejects empty required_capabilities**
- **Found during:** Task 1 GREEN (test_task_create_triggers_embedding)
- **Issue:** Pydantic model demands `min_length=1` for `required_capabilities`; first attempt sent `[]` and got 422.
- **Fix:** Bumped the test payload to `["general"]`.
- **Files modified:** tests/integration/test_auto_indexing.py
- **Commit:** f6cf7ab

## Re-embedding On Update - Scope Decision

Of the 4 entity types, only `shared_memory` has an in-place UPDATE handler in the current router shape (`POST /v1/memory/write` upserts). That update path now schedules a re-embedding so search reflects the new value.

The other 3 entities are append-only as far as their router code is concerned:

- **tasks**: there is `PUT /v1/tasks/{task_id}` which can change description, but the current `update_task` handler does not pass `BackgroundTasks` and the plan's done criterion only required create-path coverage. Documented as deferred.
- **artifacts**: no PUT handler exists - artifacts are immutable in the current API surface.
- **messages**: messages are append-only - no edit endpoint.

If a downstream plan needs re-embedding on `PUT /v1/tasks/{task_id}`, the change is mechanical: add `background_tasks: BackgroundTasks` to the handler signature and call `schedule_embedding(background_tasks, "task", task_id, updates.description)` after the update.

## Surprises in Existing Routes

- **routes_messaging.py uses a custom `_require_api_key` helper** rather than the shared `ApiKeyAuth` from `api_key_deps.py`. Left it alone for this plan - swapping helpers would be a refactor with no behavior change for VEC-04.
- **routes_artifacts.py uses a Pydantic model with a `content` field** that holds either text or base64. The auto-index hook decodes base64 best-effort so the stored vector reflects the source bytes; non-decodable blobs short-circuit at the empty-text check.
- **routes_tasks.py already had a `_broadcast_task_status` helper** for WS-05; the embedding schedule call sits AFTER the broadcast so a broadcast failure won't skip indexing and vice versa.

## Known Gotchas For Downstream Plans

- **schedule_embedding reads `is_vector_enabled` at call time**, not module import. Tests must monkeypatch the function reference inside `app.services.embedding_hooks`, not the global `app.database.vector_availability.is_vector_enabled`.
- **Background tasks run synchronously in TestClient.** This is what makes the integration tests work without an event-loop dance - FastAPI's TestClient executes BackgroundTasks before returning the response. In production they fire after the response is sent.
- **The retry worker uses module-level `_worker_task`.** Tests must reset `embedding_retry_worker._worker_task = None` before calling `start_retry_worker` if a previous test left a handle behind.
- **Empty-content rows get mark_failed("empty content")** instead of being silently skipped. This prevents the worker from re-attempting them every 5 minutes forever. If a future plan adds rows whose content is intentionally empty (e.g. file metadata only), the retry worker will mark them failed - that's a feature, not a bug, and downstream filters can skip 'failed' status as appropriate.
- **Truncation happens at 30000 chars in BOTH the auto-index hook and the retry worker.** Plans that need full-document embeddings must chunk before scheduling, not after.
- **Plan 05 will need to handle re-indexing on entity DELETE.** The current `delete_memory` and `delete_artifact` handlers do NOT clean up the embedding column - on Turso this is fine because the row vanishes, but if Plan 05 introduces a separate vectors table or external store, it will need explicit cleanup hooks.
- **Trace ID propagation works via structlog.contextvars.** Plans that bind other contextvars (request_id, user_id) before calling routes can extend `_embed_and_store`'s `log.bind` call to propagate them too.

## Self-Check: PASSED

- app/services/embedding_hooks.py: FOUND
- app/services/embedding_retry_worker.py: FOUND
- app/api/routes_memory.py (schedule_embedding): FOUND at lines 63, 77
- app/api/routes_tasks.py (schedule_embedding): FOUND at line 99
- app/api/routes_artifacts.py (schedule_embedding): FOUND at line 69
- app/api/routes_messaging.py (schedule_embedding): FOUND at line 116
- app/main.py (start_retry_worker / stop_retry_worker): FOUND
- tests/unit/test_auto_index.py (10 real tests, no xfail stubs): FOUND
- tests/unit/test_retry_worker.py (8 real tests, no xfail stub): FOUND
- tests/integration/test_auto_indexing.py (5 real tests, no xfail stub): FOUND
- Commit d3c9a2f (RED auto-index tests): FOUND
- Commit f6cf7ab (GREEN auto-index hooks + 4 routes): FOUND
- Commit b3e0c73 (RED retry worker tests): FOUND
- Commit af5ee3c (GREEN retry worker + lifespan wiring): FOUND
