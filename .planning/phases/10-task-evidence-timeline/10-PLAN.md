---
phase: 10
name: Task Evidence Timeline + Verification Detail
status: in_progress
wave: task-evidence-timeline
created: 2026-05-31
updated: 2026-05-31T13:55:31Z
owner: OpenHub GSD
---

# Phase 10 — Task Evidence Timeline + Verification Detail Implementation Plan

> **For Hermes:** Use GSD discipline and test-driven-development for each implementation slice. Keep work small, backend-wired, verified, committed, pushed, and live-smoked before calling a slice done.

**Goal:** Make every OpenHub task carry durable, queryable evidence so operators can inspect logs, commands, changed files, artifacts, PRs, reviews, and quality-gate results from the task detail workflow page.

**Architecture:** Add a first-class `task_evidence` persistence surface behind Pydantic models and a repository/service layer. Later slices expose API endpoints, merge evidence with trace events into a timeline DTO, and render that timeline on the task detail page. Evidence is internal/private by default; public surfaces must never expose raw labels, raw metadata, credentials, local paths, command secrets, or unsanitized logs.

**Tech Stack:** FastAPI, Pydantic v2, SQLite/Turso-compatible SQL via Alembic, repository/service pattern, pytest, React/Vite/TanStack Query/Workflow Canvas in later slices.

---

## Success criteria

1. A `task_evidence` table exists through Alembic and legacy migration paths with indexes for task lookup, type filtering, source agent filtering, and timeline ordering.
2. Backend models validate supported evidence types: `test`, `log`, `diff`, `artifact`, `pr`, `review`, `command`, `quality_gate`.
3. Evidence JSON fields round-trip through repository code as typed dictionaries/lists.
4. `POST /v1/tasks/{task_id}/evidence` and `GET /v1/tasks/{task_id}/evidence` exist with auth, task existence checks, and safe response DTOs.
5. A task timeline API merges trace spans and evidence in chronological order.
6. Dashboard task detail shows Evidence / Logs / Timeline / Commands / Files / Artifacts without replacing the embedded Workflow Canvas.
7. Verification lifecycle and `quality_gate` evidence are represented without letting agents self-close tasks without verification.
8. Tests cover backend model/repository/API behavior, frontend rendering, and at least one E2E task detail evidence flow.

## Non-goals

- No Plankton hook merge into OpenHub `.claude/settings.json` in this phase.
- No public evidence sharing surface.
- No automatic human-review bypass.
- No release/tag/publish action unless the operator explicitly chooses a version and target.
- No storage of raw secrets in evidence payloads; logs must be sanitized before storage or marked as redacted.

## Risk controls

- Evidence is private/internal by default.
- Prefer sanitized summaries over raw command/log blobs.
- Store command output as structured content with explicit `redacted` / `truncated` flags when available.
- Keep raw labels/metadata out of future public DTOs.
- Use TDD for every backend and frontend behavior change.
- Verify against local test DB; do not mutate live Turso from tests unless `OPENHUB_TEST_USE_TURSO=1` is explicitly set.

## Planned slices

### 10-01 — Backend evidence schema + models

**Objective:** Add first-class task evidence persistence primitives without exposing API routes yet.

**Files:**
- Create: `tests/unit/test_task_evidence_models.py`
- Create: `tests/unit/test_task_evidence_repository.py`
- Create: `alembic/versions/0006_task_evidence.py`
- Create: `database/migrations/004_task_evidence.sql`
- Create: `app/database/repositories/task_evidence.py`
- Modify: `app/models/tasks.py`
- Modify: `app/database/repositories/__init__.py`
- Modify: `app/database/__init__.py`

**TDD commands:**

```bash
.venv/bin/python -m pytest tests/unit/test_task_evidence_models.py tests/unit/test_task_evidence_repository.py -q --tb=short
```

Expected RED before implementation: imports fail for `TaskEvidence*` and `TaskEvidenceRepository`.

Expected GREEN after implementation: focused tests pass.

**Commit message:** `feat: add task evidence persistence primitives`

### 10-02 — Task evidence service + API endpoints

**Objective:** Add authenticated create/list endpoints for task evidence.

**Files:**
- Create/modify: `app/services/task_evidence_service.py`
- Modify: `app/api/routes_tasks.py`
- Test: `tests/integration/test_task_evidence_endpoints.py`

**Routes:**
- `POST /v1/tasks/{task_id}/evidence`
- `GET /v1/tasks/{task_id}/evidence`

**Acceptance:** nonexistent tasks return 404; authenticated agents/admin can submit safe evidence; response does not echo forbidden fields.

### 10-03 — Unified task timeline API

**Objective:** Merge `trace_events` spans and `task_evidence` rows into one chronological timeline DTO.

**Files:**
- Modify: `app/api/routes_tasks.py`
- Test: `tests/unit/test_task_timeline_endpoint.py`

**Route:**
- `GET /v1/tasks/{task_id}/timeline`

### 10-04 — Task detail UI evidence/timeline panel

**Objective:** Render evidence, logs, commands, files, artifacts, quality gate results, and timeline state below/alongside the embedded Workflow Canvas.

**Files:**
- Modify: `web/src/routes/_authed/tasks/$taskId.tsx`
- Add/modify hooks under `web/src/hooks/queries/`
- Test: task detail component tests

### 10-05 — Verification lifecycle + quality gate foundation

**Objective:** Represent verification states and `quality_gate` outcomes without treating agent self-claim as final completion.

**Files:**
- Modify task models/status handling only if needed; otherwise add verification DTO/state layer.
- Add service tests for status transitions and quality gate evidence.

### 10-06 — Full verification, live smoke, and closeout

**Objective:** Run focused/full backend/frontend/E2E/GSD gates, update evidence files, commit/push, verify CI and live health.

## Ready-to-run next command

```bash
.venv/bin/python -m pytest tests/unit/test_task_evidence_models.py tests/unit/test_task_evidence_repository.py -q --tb=short
```
