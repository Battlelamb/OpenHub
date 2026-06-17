# Phase 10 Summary — Task Evidence Timeline + Verification Detail

Status: complete
Updated: 2026-06-17T14:41:40Z

## Goal

Make OpenHub task execution auditable without letting agent self-claims masquerade as verified completion. Phase 10 added private/internal task evidence, a unified task timeline, dashboard task-detail evidence visibility, and a verification lifecycle foundation around `quality_gate` evidence.

## Shipped

- **10-01 — Backend evidence schema + models**
  - `TaskEvidenceType`, `TaskEvidenceOutcome`, `TaskEvidenceCreate`, `TaskEvidence`.
  - `task_evidence` database migrations and repository.
- **10-02 — Task evidence service + API endpoints**
  - Authenticated `POST /v1/tasks/{task_id}/evidence`.
  - Authenticated `GET /v1/tasks/{task_id}/evidence`.
  - Safe response DTOs, source attribution from auth, task existence checks, and secret-like content-key stripping.
- **10-03 — Unified task timeline API**
  - Authenticated `GET /v1/tasks/{task_id}/timeline`.
  - Chronological merge of `task_evidence` and `trace_events`.
  - Safe internal `TaskTimelineItem` shaping and recursive secret-like trace payload stripping.
- **10-04 — Task detail UI evidence/timeline panel**
  - Frontend `TaskTimelineItem` type, `qk.tasks.timeline`, `useTaskTimeline`, MSW handler.
  - Additive Evidence Timeline panel below the embedded Workflow Canvas.
- **10-05 — Verification lifecycle + quality gate foundation**
  - `TaskVerificationState` DTO and `TaskVerificationService`.
  - Authenticated `GET /v1/tasks/{task_id}/verification`.
  - Agent `/complete` now records a completion claim and moves work to `waiting_approval`; it no longer final-closes tasks.
  - Latest `quality_gate` outcome derives readiness for explicit admin/human completion.
  - Frontend `waiting_approval` status/Kanban support.
- **10-06 — Full verification/live closeout**
  - Branch and master CI verified.
  - Service restarted and live-smoked.
  - GSD artifacts updated.

## Security / correctness posture

- Evidence remains private/internal by default.
- No public evidence sharing was added in Phase 10.
- Agent self-claims do not become canonical `completed` status.
- `quality_gate` evidence drives verification state but does not bypass human/admin closeout.
- Evidence/timeline DTOs strip obvious secret-like keys from structured content.
- Release/tag creation remains deferred pending explicit operator version/target approval.

## Verification

Local 10-05 gates:

```text
.venv/bin/python -m pytest tests/unit/test_task_verification_service.py tests/integration/test_task_verification_lifecycle.py tests/integration/test_task_lifecycle.py -q --tb=short
→ 11 passed

.venv/bin/python -m pytest tests/unit/test_task_evidence_models.py tests/unit/test_task_evidence_repository.py tests/unit/test_task_verification_service.py tests/integration/test_task_evidence_endpoints.py tests/integration/test_task_verification_lifecycle.py tests/integration/test_task_lifecycle.py -q --tb=short
→ 24 passed

.venv/bin/python -m pytest tests/ -q --tb=short
→ passed, with 9 expected Turso-vector skips

cd web && npm run lint -- --max-warnings=0
cd web && npm run typecheck
cd web && npm run test -- --run
cd web && npm run build
→ passed; Vitest 50 passed

npm --prefix web audit --audit-level=moderate
→ 0 vulnerabilities

python scripts/check_dependency_drift.py
node .codex/get-shit-done/bin/gsd-tools.cjs validate health
node .codex/get-shit-done/bin/gsd-tools.cjs validate consistency
git diff --check
changed/untracked secret scan
→ passed
```

CI:

```text
Branch CI run 27696708960 on 96f8443 → passed all jobs
Master CI run 27697005665 on 96f8443 → passed all jobs
```

Live smoke after deploy/restart:

```text
systemctl --user restart openhub-api.service
local /v1/health/simple → HTTP 200
local unauthenticated /v1/tasks/smoke-task/verification → HTTP 401
public https://hub.brunhilde.cloud/v1/health/simple → HTTP 200
public unauthenticated https://hub.brunhilde.cloud/v1/tasks/smoke-task/verification → HTTP 401
public https://hub.brunhilde.cloud/dashboard/tasks/smoke-task → HTTP 200
public dashboard bundle /dashboard/assets/index-n7mqYpZH.js contains waiting_approval
```
