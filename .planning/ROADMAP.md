# Roadmap: OpenHub v1.0

## Overview

OpenHub ships as a self-hosted multi-agent coordination platform: FastAPI backend, React/Vite command center, SQLite/Turso persistence, WebSocket-backed live updates, vector search, and GSD-managed delivery.

The original five-phase roadmap is complete. Phase 06 made Tasks/Kanban/Workflow Canvas real rather than cosmetic. Phase 07 completed the polish and packaging pass. Phase 08 completed CI + release automation. Phase 09 completed a bounded ANP compatibility spike: public-safe agent description JSON-LD and `.well-known/agent-descriptions` discovery without replacing OpenHub ACN trust or verification gates. Phase 10 is now open to turn task detail pages into durable evidence/timeline workspaces.

## Current Truth

- **Repo:** `/home/brunhilde/OpenHub`
- **Remote:** `https://github.com/Battlelamb/OpenHub.git`
- **Branch:** `master`
- **Git truth:** use `git status --short --branch` and `git log --oneline -5`; Phase 08 starts after `c3cddff`
- **Latest tag:** `v0.1.0`
- **Live hub:** `https://hub.brunhilde.cloud`
- **Runtime status:** healthy; ACN status reports 8 agents / 1 online after 07-06 restart smoke
- **GSD status:** installed and configured; hybrid policy uses Claude Opus 4.7 for planning/research and GPT 5.5 via Codex for implementation/execution slices

## Phase Summary

- [x] **Phase 1: Backend Hardening** — auth, capabilities JSON, heartbeat monitor, CORS, migrations, RFC 7807, metrics/logging
- [x] **Phase 2: WebSocket + Test Suite** — authenticated UI WebSocket, ConnectionManager, backend auth/capability/lifecycle coverage
- [x] **Phase 3: Vector Database** — opt-in semantic search using Turso/libSQL vectors and embedding hooks
- [x] **Phase 4: Command Center UI** — React/Vite dashboard for agents, tasks, workflows, DLQ, costs, memory, locks, health, settings
- [x] **Phase 5: Release Readiness** — docs, pip install path, Docker hardening, graceful shutdown, Playwright E2E, v0.1.0 release
- [x] **Phase 6: Kanban + Workflow Canvas** — task Kanban, backend status transitions, drag/drop persistence, embedded workflow canvas
- [x] **Phase 7: Product Polish + Deployment Packaging** — dashboard truth audit/fixes, deploy/package smoke, CI command alignment, runtime ops docs, full verification, and tag decision evidence
- [x] **Phase 8: CI + Release Automation** — GitHub Actions gates, CI follow-up, Docker dashboard packaging, release guardrails, dependency drift guard
- [x] **Phase 9: ANP Compatibility Spike** — public-safe ANP Agent Description JSON-LD and `.well-known/agent-descriptions` discovery, without replacing OpenHub ACN auth/trust
- [ ] **Phase 10: Task Evidence Timeline + Verification Detail** — task evidence persistence, logs/timeline APIs, dashboard evidence panels, and verification/quality-gate foundation

## Phase 1: Backend Hardening — COMPLETE

**Goal:** Make backend correctness and security trustworthy before UI/test expansion.

**Shipped:**

- Real protected-route auth behavior
- Required admin credential configuration
- Capability JSON storage fixes
- Heartbeat monitor wiring
- CORS lockdown
- Alembic migration consolidation
- RFC 7807-style error work
- Rate limiting / metrics / structured logging improvements
- datetime timezone sweep
- Gap closure for P2 auth and middleware issues

## Phase 2: WebSocket + Test Suite — COMPLETE

**Goal:** Stable real-time contract and backend test baseline.

**Shipped:**

- Real JWT fixtures and auth unit tests
- ConnectionManager with UI/agent pools
- Capability matcher tests
- Task lifecycle and agent lifecycle tests
- `/v1/ws/ui` with initial-frame JWT auth
- WebSocket integration tests
- Event-hook work carried into later dashboard/live-sync slices

## Phase 3: Vector Database — COMPLETE

**Goal:** Opt-in semantic search over memories/tasks/artifacts.

**Shipped:**

- Vector migration and feature availability checks
- Turso/libSQL vector binding smoke path
- Embedding service with local/OpenAI backends
- Auto-indexing hooks and retry worker
- Unified `/v1/search` endpoint
- Beta docs and environment examples

## Phase 4: Command Center UI — COMPLETE

**Goal:** Browser dashboard for operators.

**Shipped:**

- Vite/React/TypeScript/Tailwind/shadcn web app
- Auth layer with in-memory Zustand token store
- TanStack Query data hooks and WebSocket invalidation
- Agents/tasks/workflows surfaces
- DLQ, costs, memory, locks, health, settings, traces
- Static dashboard mount under FastAPI
- Deep-link/dashboard routing fixes
- Endpoint mismatch closure and responsive-list cleanup

## Phase 5: Release Readiness — COMPLETE

**Goal:** Make OpenHub installable, understandable, and releasable.

**Shipped:**

- GSD loop initialization
- Release-readiness snapshot
- Stuck work recovery UX
- Graceful shutdown
- Docker Compose hardening
- pip install path
- README quickstart polish
- Playwright E2E tests
- `v0.1.0` tag

## Phase 6: Kanban + Workflow Canvas — COMPLETE

**Goal:** Make Tasks/Kanban/Workflow Canvas backend-wired and verified, not just visual.

**Shipped:**

- Backend unit tests for admin task status transitions
- Backend integration tests for `PATCH /v1/tasks/{task_id}/status`
- Valid transition map and assignment reset behavior
- Kanban board with all task status columns
- Drag/drop mutation to backend and query refetch
- Frontend component tests for Kanban behavior
- Playwright E2E for drag/drop → API → DB/refetch
- Task detail route with embedded workflow canvas
- Runtime workflow persistence fix
- Live smoke verified after push

## Phase 7: Product Polish + Deployment Packaging — COMPLETE

**Goal:** Remove remaining product/release friction and align docs, dashboard truth, deployment packaging, and test commands with the live system.

**Success criteria:**

1. Dashboard agent/task/workflow views use the correct source of truth and do not show legacy-empty or misleading data when ACN is healthy.
2. README/deployment docs match the actual production shape: `hub.brunhilde.cloud`, user systemd services, Cloudflare tunnel, and current bridge service names.
3. Docker, pip, and local start paths are smoke-tested or explicitly documented with bounded caveats.
4. Test commands in GSD config match the actual repo tools and do not reference missing linters as required gates unless installed/configured.
5. Runtime ops cleanup is documented: correct bridge active, stale legacy bridge disabled.
6. Full verification evidence exists before the next tag/release decision.

**Planned slices:**

- [x] **07-01 — Dashboard truth audit**: compare live dashboard/API data paths against ACN, tasks, workflows, and seed-data behavior.
- [x] **07-02 — Dashboard truth fixes**: health dashboard now separates service health, ACN registry truth, and task search truth, with Vitest coverage.
- [x] **07-03 — Deployment packaging smoke**: verified README quickstart, pip package build/entrypoint, Docker Compose config, and bounded dashboard/Docker caveats.
- [x] **07-04 — Test/CI command alignment**: installed dashboard ESLint tooling, added flat config, upgraded Vitest to clear audit, and aligned GSD verify commands.
- [x] **07-05 — Runtime ops cleanup docs**: documented active services, disabled legacy bridge, Cloudflare Tunnel route, secret-safe diagnostics, env permissions, recovery checks, and heartbeat timestamp follow-up.
- [x] **07-06 — Full verification + tag decision**: full backend/frontend/E2E/GSD/live gate passed; heartbeat timestamp advisory fixed and deployed; release tag deferred pending explicit version choice.

## Phase 8: CI + Release Automation — COMPLETE

**Goal:** Convert verified local OpenHub gates into repeatable GitHub CI and release guardrails without exposing local credentials.

**Success criteria:**

1. GitHub Actions CI runs backend tests, frontend audit/lint/typecheck/tests/build, Compose/package smoke, and Playwright dashboard E2E.
2. CI uses dummy credentials and temp SQLite state only.
3. First CI run is inspected and CI-only failures are fixed with evidence.
4. Docker dashboard packaging is either proven or its bounded caveat is explicitly tracked.
5. Release/tag automation remains manual and safe until operator selects a version/publish target.
6. Dependency drift between `requirements.txt`, `pyproject.toml`, and frontend lockfile is guarded.

**Planned slices:**

- [x] **08-01 — GitHub Actions CI workflow**: added `.github/workflows/ci.yml` with backend, frontend, package/Compose, and Playwright jobs; locally verified before push.
- [x] **08-02 — CI result follow-up**: first run failed before jobs due invalid job-level `runner.temp`; fixed path, rerun passed all 4 CI jobs.
- [x] **08-03 — Docker dashboard packaging**: Docker image now builds/bundles `web/dist`; CI run `26600306093` proved `/dashboard` and bundled asset serving from the running container.
- [x] **08-04 — Release/tag automation guardrail**: manual read-only release verification workflow and docs added; no auto-tags or registry publishing.
- [x] **08-05 — Dependency drift guard**: backend/frontend dependency drift script, tests, GSD command, and CI job added.

## Phase 9: ANP Compatibility Spike — COMPLETE

**Goal:** Expose a public-safe ANP compatibility surface for OpenHub agents while keeping OpenHub ACN identity, scoped keys, task routing, evidence bundles, and review gates authoritative.

**Success criteria:**

1. `GET /.well-known/agent-descriptions` returns an ANP-style JSON-LD `CollectionPage`.
2. `GET /v1/anp/agents/{agent_id}/ad.json` returns an ANP-style Agent Description document for explicitly public agents only.
3. Private/default agents are excluded and return 404 from public ANP routes.
4. No secrets, raw metadata, IPs, hostnames, workspace paths, API keys, bearer tokens, or admin values appear in public responses.
5. Discovery pagination, base URL generation, schema shape, and public/private filtering are covered by tests.
6. Docs mark ANP compatibility as experimental and clearly distinguish it from `did:wba` auth/E2EE future work.

**Planned slices:**

- [x] **09-01 — ANP mapping design**: documented OpenHub → ANP ADP/ADSP field mapping and secret-safe public policy in `docs/ANP_COMPATIBILITY.md`.
- [x] **09-02 — Serializer service**: added pure `Agent` → ANP JSON-LD mapping with default-private public filtering and no raw metadata/label serialization.
- [x] **09-03 — Per-agent ADP endpoint**: added `GET /v1/anp/agents/{agent_id}/ad.json` for public agents only; private/missing agents return `404`.
- [x] **09-04 — Well-known discovery endpoint**: added `GET /.well-known/agent-descriptions` with public-only pagination and `next` links.
- [x] **09-05 — Docs + verification closeout**: README/docs, evidence, GSD state, and verification closeout updated.

## Phase 10: Task Evidence Timeline + Verification Detail — IN PROGRESS

**Goal:** Make every task carry durable, queryable evidence so operators can inspect logs, commands, changed files, artifacts, PRs, reviews, and quality-gate results from the task detail workflow page.

**Success criteria:**

1. `task_evidence` persistence exists with typed models, JSON round-tripping, and task/type/source/timeline indexes.
2. Authenticated evidence create/list endpoints exist and validate task existence.
3. A task timeline endpoint merges trace events and evidence in chronological order.
4. Dashboard task detail renders Logs / Timeline / Evidence / Commands / Files / Artifacts while preserving the embedded Workflow Canvas.
5. Verification lifecycle and `quality_gate` outcomes are represented without allowing agents to self-close work without verification.
6. Backend/frontend/E2E/GSD/live verification evidence is recorded before closeout.

**Planned slices:**

- [x] **10-01 — Backend evidence schema + models**: added table/migrations, Pydantic models, repository, and focused backend tests.
- [x] **10-02 — Task evidence service + API endpoints**: added authenticated create/list endpoints, task existence checks, principal source attribution, safe response DTOs, and integration tests.
- [x] **10-03 — Unified task timeline API**: added authenticated `GET /v1/tasks/{task_id}/timeline`, task existence checks, chronological trace/evidence merge, safe internal `TaskTimelineItem` DTO, and backend verification; publish/CI/live proof pending before slice is called shipped.
- [ ] **10-04 — Task detail UI evidence/timeline panel**: render evidence/logs/commands/files/artifacts/quality-gate results.
- [ ] **10-05 — Verification lifecycle + quality gate foundation**: represent verification state and `quality_gate` evidence outcomes.
- [ ] **10-06 — Full verification + live closeout**: run gates, update evidence, push, verify CI/live, and summarize.

## Verification Gates

Before claiming a future feature or phase complete:

- Backend tests for changed backend behavior
- Frontend tests for changed UI behavior
- E2E or bounded live smoke for cross-layer flows
- `npm run build` for dashboard changes
- Secret scan when touching `.gsd`, `.claude`, `.hermes`, env examples, systemd units, or auth docs
- Commit + push + live verification when the user expects production state

## Progress

- **Completed phases:** 9 / 10
- **Completed plans:** 64 / 67
- **Current phase:** Phase 10 — Task Evidence Timeline + Verification Detail
- **Current slice:** 10-03 — Unified task timeline API locally verified; publish/CI/live proof pending
- **Next slice:** 10-04 — Task detail UI evidence/timeline panel
