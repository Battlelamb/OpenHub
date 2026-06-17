# Phase 10: Task Evidence Timeline + Verification Detail - Context

**Gathered:** 2026-06-17
**Status:** Ready for planning
**Mode:** Reconstructed from already-approved Phase 10 plan, STATE, and continue-here artifact after 10-01/10-02 were shipped.

<domain>
## Phase Boundary

Phase 10 makes every OpenHub task carry durable, queryable, internal/private evidence so operators can inspect logs, commands, changed files, artifacts, PRs, reviews, quality gates, and merged timeline activity from the task detail workflow page.

The phase continues from shipped slices 10-01 and 10-02:

- 10-01 shipped task evidence persistence primitives.
- 10-02 shipped authenticated evidence create/list API endpoints.
- Remaining work starts at 10-03: unified task timeline API, then UI rendering, verification lifecycle/quality-gate semantics, and full closeout.

</domain>

<decisions>
## Implementation Decisions

### Evidence Privacy and Safety
- Evidence is internal/private by default.
- Do not add public evidence sharing in Phase 10.
- Public-safe DTO discipline from ANP work still applies: no raw labels, raw metadata, credentials, local secret paths, command secrets, or unsanitized logs in public surfaces.
- Prefer sanitized structured summaries over raw command/log blobs.
- Keep `content`, `metadata`, and timeline payloads shaped so secret-like keys are stripped or represented as redacted/truncated metadata.

### API Contract
- Add `GET /v1/tasks/{task_id}/timeline` for 10-03.
- The endpoint must require authentication and return 404 for nonexistent tasks.
- Timeline items merge trace events and task evidence in chronological order.
- Timeline DTOs must identify item source/type without exposing unsafe internals.
- Dashboard UI work is out of scope for 10-03 and belongs to 10-04.

### UI Contract
- Task detail keeps the embedded Workflow Canvas; evidence/timeline UI is additive, not a replacement.
- Render evidence/logs/commands/files/artifacts/quality-gate status in a compact operator-focused panel.
- Use existing React/Vite/TanStack Query dashboard patterns and stable test selectors.

### Verification Lifecycle
- `quality_gate` evidence should represent verification outcomes, but agent self-claims must not be treated as final human verification.
- Quality-gate data should be queryable and visible without enabling automatic self-close bypass.

### Claude's Discretion
- Implementation details are at agent discretion when they preserve the existing repository/service/API patterns and the explicit Phase 10 plan guardrails.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- Existing task evidence persistence models/repository and `TaskEvidenceService` from 10-01/10-02.
- Existing authenticated task routes in `app/api/routes_tasks.py`.
- Existing task detail route at `web/src/routes/_authed/tasks/$taskId.tsx` with embedded Workflow Canvas behavior.
- Existing frontend query/API client patterns under `web/src/hooks/queries/` and API service modules.

### Established Patterns
- Backend uses FastAPI, Pydantic v2, repository/service layering, SQLAlchemy/Alembic plus legacy SQL migrations, and pytest.
- Frontend uses React, Vite, TanStack Query, typed API helpers, component tests, and `npm run build` as a required dashboard gate.
- GSD/OpenHub work must be small, backend-wired, tested, committed, pushed, CI-verified, and live-smoked before being called done.

### Integration Points
- 10-03 connects task evidence rows and trace event rows into one task timeline endpoint.
- 10-04 consumes the timeline/evidence API on the task detail route.
- 10-05 adds verification/quality-gate semantics on top of evidence without public exposure or self-verification bypass.

</code_context>

<specifics>
## Specific Ideas

- Continue from `.planning/phases/10-task-evidence-timeline/.continue-here.md`.
- First executable slice is 10-03 unified task timeline API.
- Keep tests TDD-shaped: prove missing route/contract first, then implement.
- Do not tag, release, publish, or mutate production data unless explicitly required by closeout and verified safely.

</specifics>

<deferred>
## Deferred Ideas

- Public evidence sharing surfaces.
- Plankton hook merge into OpenHub `.claude/settings.json`.
- Release/tag/publish action; still requires explicit operator version and target.

</deferred>
