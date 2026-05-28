# Roadmap: OpenHub v1.0

## Overview

OpenHub ships as a self-hosted multi-agent coordination platform: FastAPI backend, React/Vite command center, SQLite/Turso persistence, WebSocket-backed live updates, vector search, and GSD-managed delivery.

The original five-phase roadmap is complete. Phase 06 made Tasks/Kanban/Workflow Canvas real rather than cosmetic. Phase 07 completed the polish and packaging pass. Phase 08 is now open to add CI + release automation so the verified local gates become repeatable GitHub checks.

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
- [ ] **Phase 8: CI + Release Automation** — GitHub Actions gates, CI follow-up, Docker dashboard packaging, release guardrails, dependency drift guard

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

## Phase 8: CI + Release Automation — IN PROGRESS

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
- [ ] **08-03 — Docker dashboard packaging**: prove or harden dashboard-in-image packaging.
- [ ] **08-04 — Release/tag automation guardrail**: add manual release workflow/docs without auto-publishing secrets.
- [ ] **08-05 — Dependency drift guard**: detect backend/frontend dependency drift in CI.

## Verification Gates

Before claiming a future feature or phase complete:

- Backend tests for changed backend behavior
- Frontend tests for changed UI behavior
- E2E or bounded live smoke for cross-layer flows
- `npm run build` for dashboard changes
- Secret scan when touching `.gsd`, `.claude`, `.hermes`, env examples, systemd units, or auth docs
- Commit + push + live verification when the user expects production state

## Progress

- **Completed phases:** 7 / 8
- **Completed plans:** 53 / 56
- **Current phase:** Phase 08 — CI + Release Automation
- **Current slice:** 08-03 — Docker dashboard packaging
- **Next slice:** 08-04 — Release/tag automation guardrail
