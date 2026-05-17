# Task Lifecycle Inventory — Verification-First Preparation

Date: 2026-05-17

Purpose: Phase 1.1 inventory before adding task evidence and verification gates.

## Files inspected

- `app/models/tasks.py`
- `app/database/repositories/tasks.py`
- `app/services/task_service.py`
- `app/api/routes_tasks.py`
- `tests/integration/test_task_lifecycle.py`
- `app/database/migrations.py`

## Current task statuses

Current `TaskStatus` in `app/models/tasks.py`:

```text
queued
claimed
running
waiting_approval
completed
failed
dead_letter
cancelled
```

## Current lifecycle behavior

Current happy path:

```text
queued -> claimed -> running -> completed
```

Current failure/retry path:

```text
running -> queued    # retryable failure while retry_count < max_retries
running -> failed    # non-retryable or retry exhausted
```

Current cancellation path:

```text
queued/claimed/running/waiting_approval -> cancelled
```

Current expired lease cleanup:

```text
claimed with expired lease -> queued
```

## Current API endpoints relevant to lifecycle

From `app/api/routes_tasks.py`:

```text
POST /v1/tasks/                         create
GET  /v1/tasks/search                   search/filter
GET  /v1/tasks/stats/overview           stats
GET  /v1/tasks/{task_id}                read
GET  /v1/tasks/{task_id}/trace          trace timeline
PUT  /v1/tasks/{task_id}                update
POST /v1/tasks/{task_id}/claim          claim
POST /v1/tasks/{task_id}/start          start
POST /v1/tasks/{task_id}/progress       progress
POST /v1/tasks/{task_id}/complete       complete
POST /v1/tasks/{task_id}/fail           fail/retry
POST /v1/tasks/{task_id}/cancel         cancel
GET  /v1/tasks/agent/{agent_id}         agent tasks
GET  /v1/tasks/available/for-me         available tasks
DELETE /v1/tasks/{task_id}              admin delete
POST /v1/tasks/admin/cleanup/expired-leases
POST /v1/tasks/search                   semantic task search shortcut
```

## Current completion model

`TaskComplete` currently accepts:

- `result_summary`
- `output`
- `artifact_ids`
- `metrics`

`TaskService.complete_task(...)` currently:

1. Requires the task to be owned by the current agent.
2. Allows completion only from `running` or `waiting_approval`.
3. Sets `status = completed` immediately.
4. Sets `completed_at`, `result_summary`, `output`, `artifact_ids`, `duration_seconds`.
5. Stores completion metrics in `payload.completion_metrics` when present.
6. Frees the agent by setting agent status to `idle` and `current_task = None`.

Important gap: completion currently means final done. There is no intermediate `completed_claimed`, no evidence requirement, and no verification gate.

## Current persistence shape

`TaskRepository._row_to_model(...)` maps these task columns:

- `id`
- `title`
- `description`
- `task_type`
- `priority`
- `status`
- `required_capabilities`
- `owner_agent_id`
- `claimed_at`
- `started_at`
- `completed_at`
- `lease_until`
- `retry_count`
- `max_retries`
- `last_error`
- `deadline_at`
- `idempotency_key`
- `labels`
- `payload`
- `result_summary`
- `output`
- `artifact_ids`
- `duration_seconds`
- `created_at`
- `updated_at`

No dedicated `task_evidence` or `task_verification_runs` table exists yet.

## Current tests

`tests/integration/test_task_lifecycle.py` covers:

- create valid task
- create with missing fields
- claim queued task
- start claimed task
- full create -> claim -> start -> complete ending in `completed`
- non-retryable fail ending in `failed`
- re-claiming already claimed task rejected

Current test expectation to change later:

```python
assert complete.json()["status"] == "completed"
assert fetched.json()["status"] == "completed"
```

This should remain as compatibility only if the endpoint response preserves a legacy alias; internally, the future verification-first flow should move to `completed_claimed`, `verification_running`, `verified`, or `needs_review`.

## Migration system notes

Migrations are file-based SQL migrations under `database/migrations/`, discovered by `MigrationManager` with filenames matching:

```text
NNN_description.sql
```

A future task evidence migration should add a new numbered SQL file, not inline schema changes directly into service code.

## Recommended next implementation slice

Next TDD slice should be small and model-only:

1. Add failing tests for task evidence Pydantic models.
2. Add `TaskEvidenceKind`, `TaskEvidenceCreate`, and `TaskEvidence` to `app/models/tasks.py`.
3. Sanitize secret-like metadata keys before storage/response.
4. Run only the focused model test first.
5. Then run the existing task lifecycle integration test to ensure no behavior changed yet.

Proposed first test file:

```text
tests/unit/test_task_evidence_model.py
```

Proposed first commit:

```text
feat(tasks): add typed evidence models
```
