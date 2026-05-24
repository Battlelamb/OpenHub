# Roadmap: OpenHub v1.0

## Overview

OpenHub ships as a self-hosted multi-agent coordination platform: FastAPI backend, React/Vite command center, SQLite/Turso persistence, WebSocket-backed live updates, vector search, and GSD-managed delivery.

The original five-phase roadmap is complete. Phase 06 was added after release readiness to make Tasks/Kanban/Workflow Canvas real rather than cosmetic. Phase 07 is now the polish and packaging pass before the next release decision.

## Current Truth

- **Repo:** `/home/brunhilde/OpenHub`
- **Remote:** `https://github.com/Battlelamb/OpenHub.git`
- **Branch:** `master`
- **Current HEAD:** `993622b`
- **Latest tag:** `v0.1.0`
- **Live hub:** `https://hub.brunhilde.cloud`
- **Runtime status:** healthy; ACN has 1 node / 1 agent online
- **GSD status:** installed and configured; Opus/max-effort standard preserved

## Phase Summary

- [x] **Phase 1: Backend Hardening** — auth, capabilities JSON, heartbeat monitor, CORS, migrations, RFC 7807, metrics/logging
- [x] **Phase 2: WebSocket + Test Suite** — authenticated UI WebSocket, ConnectionManager, backend auth/capability/lifecycle coverage
- [x] **Phase 3: Vector Database** — opt-in semantic search using Turso/libSQL vectors and embedding hooks
- [x] **Phase 4: Command Center UI** — React/Vite dashboard for agents, tasks, workflows, DLQ, costs, memory, locks, health, settings
- [x] **Phase 5: Release Readiness** — docs, pip install path, Docker hardening, graceful shutdown, Playwright E2E, v0.1.0 release
- [x] **Phase 6: Kanban + Workflow Canvas** — task Kanban, backend status transitions, drag/drop persistence, embedded workflow canvas
- [ ] **Phase 7: Product Polish + Deployment Packaging** — dashboard truth audit/fixes, deploy/package smoke, CI command alignment, release decision

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

## Phase 7: Product Polish + Deployment Packaging — PLANNED

**Goal:** Remove remaining product/release friction and align docs, dashboard truth, deployment packaging, and test commands with the live system.

**Success criteria:**

1. Dashboard agent/task/workflow views use the correct source of truth and do not show legacy-empty or misleading data when ACN is healthy.
2. README/deployment docs match the actual production shape: `hub.brunhilde.cloud`, user systemd services, Cloudflare tunnel, and current bridge service names.
3. Docker, pip, and local start paths are smoke-tested or explicitly documented with bounded caveats.
4. Test commands in GSD config match the actual repo tools and do not reference missing linters as required gates unless installed/configured.
5. Runtime ops cleanup is documented: correct bridge active, stale legacy bridge disabled.
6. Full verification evidence exists before the next tag/release decision.

**Planned slices:**

- [ ] **07-01 — Dashboard truth audit**: compare live dashboard/API data paths against ACN, tasks, workflows, and seed-data behavior.
- [ ] **07-02 — Dashboard truth fixes**: patch misleading UI/API fallbacks found in 07-01, with tests.
- [ ] **07-03 — Deployment packaging smoke**: verify README quickstart, pip command, Docker Compose, and live Cloudflare assumptions.
- [ ] **07-04 — Test/CI command alignment**: align `.gsdrc.toml`, package scripts, and documented verification commands with installed tooling.
- [ ] **07-05 — Runtime ops cleanup docs**: document active services, disabled legacy bridge, recovery checks, and secret-safe diagnostics.
- [ ] **07-06 — Full verification + tag decision**: backend tests, frontend tests, build, E2E, live smoke, changelog/tag decision.

## Verification Gates

Before claiming a future feature or phase complete:

- Backend tests for changed backend behavior
- Frontend tests for changed UI behavior
- E2E or bounded live smoke for cross-layer flows
- `npm run build` for dashboard changes
- Secret scan when touching `.gsd`, `.claude`, `.hermes`, env examples, systemd units, or auth docs
- Commit + push + live verification when the user expects production state

## Progress

- **Completed phases:** 6 / 7
- **Completed plans:** 45 / 51
- **Current phase:** 07 Product Polish + Deployment Packaging
- **Next slice:** 07-01 Dashboard truth audit
