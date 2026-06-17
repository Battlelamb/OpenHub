---
phase: 10
name: Task Evidence Timeline + Verification Detail
status: in_progress
wave: task-evidence-timeline
created: 2026-05-31
updated: 2026-05-31T15:39:46Z
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
.venv/bin/python -m pytest tests/unit/test_task_verification_service.py tests/integration/test_task_verification_lifecycle.py tests/integration/test_task_lifecycle.py -q --tb=short
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

**Status:** Complete, pushed, CI-verified, deployed, and live-smoked. Added `TaskEvidenceService`, safe `TaskEvidenceResponse`, endpoint integration tests, principal source attribution, task existence checks, and secret-like content-key stripping. Focused/full backend and GSD verify gates passed; CI run `26716859212` passed; public unauthenticated `GET /v1/tasks/smoke-task/evidence` returns `401`, proving the route is live behind auth.

### 10-03 — Unified task timeline API

**Objective:** Merge `trace_events` spans and `task_evidence` rows into one chronological timeline DTO.

**Files:**
- Modify: `app/api/routes_tasks.py`
- Test: `tests/unit/test_task_timeline_endpoint.py`

**Route:**
- `GET /v1/tasks/{task_id}/timeline`

**Status:** Shipped on 2026-06-17. RED endpoint tests first failed with missing route. GREEN added `TaskTimelineItem`, authenticated route, task existence `404`, chronological merge of `trace_events` and `task_evidence`, safe timeline DTO shaping, and recursive secret-like key stripping for trace payloads. Focused endpoint tests passed (`8 passed`); related evidence/model/trace gate passed (`15 passed`); full backend suite passed (`python -m pytest tests/ -x -q --tb=short`, exit 0 with 9 expected Turso-vector skips). Dependency drift, GSD health/consistency, diff check, and changed-file secret scan passed. Branch CI run `27686969161` passed after the dashboard audit fix; master CI run `27687173141` passed all jobs; `openhub-api.service` was restarted; local/public health returned `200`; local/public unauthenticated `GET /v1/tasks/smoke-task/timeline` returned `401`.

### 10-04 — Task detail UI evidence/timeline panel

**Objective:** Render evidence, logs, commands, files, artifacts, quality gate results, and timeline state below/alongside the embedded Workflow Canvas.

**Files:**
- Modified: `web/src/routes/_authed/tasks/$taskId.tsx`
- Modified: `web/src/hooks/queries/useTasks.ts`
- Modified: `web/src/lib/query-keys.ts`
- Modified: `web/src/types/entities.ts`
- Modified: `web/src/mocks/handlers/tasks.ts`
- Test: `web/src/routes/_authed/tasks/-task-detail-workflow.test.tsx`

**Status:** Shipped on 2026-06-17. RED route test first failed because task detail did not render `Evidence Timeline` or fetch `/v1/tasks/{task_id}/timeline`. GREEN added frontend `TaskTimelineItem` typing, `qk.tasks.timeline`, `useTaskTimeline`, MSW timeline handler, and an additive Evidence Timeline panel under the embedded Workflow Canvas. The panel renders source/type/outcome, actor, trace id, duration, artifact IDs, and sanitized payload JSON while preserving the canvas as the working surface.

**Verification:** focused route test passed (`2 passed`); full frontend gate passed (`npm run lint -- --max-warnings=0`, `npm run typecheck`, full Vitest `50 passed`, `npm run build` with Vite 8.0.16). `npm audit --audit-level=moderate`, dependency drift, GSD health/consistency, `git diff --check`, and changed-file secret scan passed. Commit `819ea2a` was pushed, branch CI run `27694168399` passed all jobs, fast-forwarded to `master`, master CI run `27694461737` passed all jobs, `openhub-api.service` restarted, public health returned `200`, public `/dashboard/tasks/smoke-task` returned `200`, public bundle contains `Evidence Timeline`, and public unauthenticated `GET /v1/tasks/smoke-task/timeline` returned `401`.

### 10-05 — Verification lifecycle + quality gate foundation

**Objective:** Represent verification states and `quality_gate` outcomes without treating agent self-claim as final completion.

**Status:** Locally verified on 2026-06-17. RED service/HTTP/UI tests first failed because verification lifecycle service/endpoint and `waiting_approval` UI support were missing, and agent `/complete` still self-closed tasks. GREEN added `TaskVerificationState`, `TaskVerificationService`, authenticated `GET /v1/tasks/{task_id}/verification`, completion-claim semantics that move tasks to `waiting_approval` without final `completed`, explicit admin/human closeout path, latest `quality_gate` outcome readiness, and frontend `waiting_approval` Kanban/status support.

**Verification:** focused backend gate passed (`11 passed`); related backend gate passed (`24 passed`); full backend suite passed with 9 expected Turso-vector skips; full frontend gate passed (`lint`, `typecheck`, Vitest `50 passed`, build); `npm audit`, dependency drift, GSD health/consistency, `git diff --check`, and changed/untracked secret scan passed locally. Commit/push/CI/live proof is handled by 10-06.

**Files:**
- `app/models/tasks.py` — `TaskVerificationState` DTO.
- `app/services/task_verification_service.py` — derived verification lifecycle service.
- `app/services/task_service.py` — `/complete` completion-claim semantics and `waiting_approval` admin transitions.
- `app/api/routes_tasks.py` — `GET /v1/tasks/{task_id}/verification`, response/broadcast semantics, admin transition validation.
- `tests/unit/test_task_verification_service.py` — quality-gate readiness and latest-outcome service coverage.
- `tests/integration/test_task_verification_lifecycle.py` and `tests/integration/test_task_lifecycle.py` — HTTP/lifecycle contract coverage.
- `web/src/types/entities.ts`, `web/src/components/common/StatusBadge.tsx`, `web/src/components/kanban/KanbanBoard.tsx`, `web/src/components/kanban/KanbanBoard.test.tsx` — `waiting_approval` frontend support.

### 10-06 — Full verification, live smoke, and closeout

**Objective:** Run focused/full backend/frontend/E2E/GSD gates, update evidence files, commit/push, verify CI and live health.

## Ready-to-run next command

```bash
.venv/bin/python -m pytest tests/unit/test_task_verification_service.py tests/integration/test_task_verification_lifecycle.py tests/integration/test_task_lifecycle.py -q --tb=short
```
