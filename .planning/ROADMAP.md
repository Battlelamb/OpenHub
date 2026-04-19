# Roadmap: OpenHub v1.0

## Overview

OpenHub ships in five phases derived from its requirement categories and their dependencies. Backend correctness must precede tests (a broken auth stub invalidates the test baseline). WebSocket event types must be stable before the frontend implements its consumer. The vector DB service is isolated enough to ship standalone as an opt-in backend feature. The command center UI is the longest phase - 16 requirements across the full dashboard surface. Release readiness caps everything: docs, pip install path, graceful shutdown, and Playwright E2E tests all depend on a complete, stable system.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Backend Hardening** - Fix silent correctness bugs and security holes before any test is written
- [ ] **Phase 2: WebSocket + Test Suite** - Stable real-time event contract and backend test coverage
- [ ] **Phase 3: Vector Database** - Semantic search service via Turso/libSQL native vectors, shipped as opt-in beta
- [ ] **Phase 4: Command Center UI** - React + Vite dashboard with live agent/task/workflow control
- [ ] **Phase 5: Release Readiness** - Open source docs, pip install path, graceful shutdown, E2E tests

## Phase Details

### Phase 1: Backend Hardening
**Goal**: The backend is correct, secure, and observable - auth works for real, capabilities are stored as JSON, heartbeat monitor runs, CORS is locked down, schema lives in versioned migrations, and OpenAPI docs are exposed
**Depends on**: Nothing (first phase)
**Requirements**: HARD-01, HARD-02, HARD-03, HARD-04, HARD-05, HARD-06, HARD-07, HARD-08, HARD-09, HARD-10, OSS-02, PROD-01, PROD-02, PROD-04
**Success Criteria** (what must be TRUE):
  1. A request without a valid JWT or API key to any protected endpoint returns 401 - the auth stub in app/dependencies.py no longer accepts any 8-character string
  2. Admin credentials are not hardcoded - the server refuses to start without credentials configured via environment variable or first-run setup
  3. An agent registered with a list of capabilities can be matched to a task - json.loads() on stored capabilities succeeds
  4. Offline agents are detected automatically - the heartbeat monitor starts with the application and marks agents offline after missing heartbeats
  5. The /docs endpoint is accessible and all endpoints show correct auth requirements and structured error response shapes
**Plans**: 9 plans

Plans:
- [x] 01-00-PLAN.md - Test scaffold: pytest infrastructure, conftest.py, shared fixtures, stub tests
- [x] 01-01-PLAN.md - Auth stub removal, shared API key dep, capabilities JSON fix, admin credential env vars
- [x] 01-02-PLAN.md - Heartbeat monitor wiring into lifespan
- [x] 01-03-PLAN.md - CORS lockdown, datetime.utcnow() partial fix (4 high-impact files)
- [x] 01-04-PLAN.md - Alembic schema migration consolidation
- [x] 01-05-PLAN.md - RFC 7807 error format, OpenAPI /docs enabled
- [x] 01-06-PLAN.md - slowapi rate limiting (app/limiter.py), Prometheus metrics, structlog enhancement
- [x] 01-07-PLAN.md - Codebase-wide datetime.utcnow() sweep (10 remaining files, 29 occurrences)
- [ ] 01-08-PLAN.md - Gap closure: P2 auth consolidation, RFC 7807 rate limiter, Prometheus wiring, middleware fixes

### Phase 2: WebSocket + Test Suite
**Goal**: Dashboard clients can connect to a stable WebSocket endpoint and receive live events, and the backend has a test suite covering auth, capability matching, and the task/agent lifecycle
**Depends on**: Phase 1
**Requirements**: WS-01, WS-02, WS-03, WS-04, WS-05, WS-06, TEST-01, TEST-02, TEST-03, TEST-04, TEST-05
**Success Criteria** (what must be TRUE):
  1. A dashboard client authenticates the WebSocket connection via initial message frame - no token appears in the URL query string or server logs
  2. Agent status changes (online/offline/idle) appear in the connected dashboard client within one second of the state change
  3. Task lifecycle events (created, claimed, running, completed, failed) appear in the connected dashboard client in real time
  4. All auth tests pass: JWT creation and validation, API key verification, RBAC enforcement by role
  5. All capability matching tests pass: exact match, fuzzy match, scoring edge cases
  6. Integration tests for task lifecycle (create, claim, start, complete, fail, retry) and agent heartbeat/offline detection all pass
**Plans**: 6 plans

Plans:
- [x] 02-01-PLAN.md - Test infrastructure fix (real JWT fixtures) and auth unit tests (TEST-01)
- [x] 02-02-PLAN.md - ConnectionManager class with dual pools, tiered broadcasting, Prometheus metrics (WS-02, WS-03)
- [x] 02-03-PLAN.md - Capability matcher, task lifecycle, and agent lifecycle tests (TEST-02, TEST-03, TEST-04)
- [x] 02-04-PLAN.md - /v1/ws/ui endpoint with JWT auth via initial message frame (WS-01)
- [ ] 02-05-PLAN.md - Service event hooks for broadcasting agent/task/workflow events (WS-04, WS-05, WS-06)
- [x] 02-06-PLAN.md - WebSocket integration tests and ConnectionManager unit tests (TEST-05)

### Phase 3: Vector Database
**Goal**: Semantic search over memories, tasks, and artifacts is available via a REST API backed by Turso/libSQL native vector columns, shipped as an opt-in beta feature
**Depends on**: Phase 1
**Requirements**: VEC-01, VEC-02, VEC-03, VEC-04, VEC-05, VEC-06
**Success Criteria** (what must be TRUE):
  1. A vector similarity search query over stored memories returns semantically relevant results using vector_distance_cos
  2. Vectors survive a server restart - a record written before restart is findable by similarity search after restart, confirming F32_BLOB persistence
  3. New memory, task, and artifact writes automatically generate and store embeddings without manual intervention
  4. The feature is documented as experimental/opt-in - the server starts and operates normally with vector search disabled
**Plans**: 6 plans

Plans:
- [x] 03-01-PLAN.md - Alembic vector migration, config/zvec cleanup, vector_availability module, Wave 0 test scaffolds
- [x] 03-02-PLAN.md - VectorSearchService + Turso vector32 binding smoke test (gating plan)
- [x] 03-03-PLAN.md - EmbeddingService with lazy-loaded local and OpenAI backends
- [x] 03-04-PLAN.md - Auto-indexing BackgroundTasks hooks on 4 write paths + 5-min retry worker
- [x] 03-05-PLAN.md - Unified /v1/search endpoint + per-entity shortcuts + Pydantic models
- [x] 03-06-PLAN.md - VEC-06 opt-in beta: startup warning, OpenAPI tag, README/CHANGELOG/.env.example

### Phase 4: Command Center UI
**Goal**: A developer self-hosting OpenHub can log in, see live agent status, manage tasks, inspect workflows, and access the full visibility stack (DLQ, cost tracking, traces, memory, locks) from a browser
**Depends on**: Phase 2
**Requirements**: UI-01, UI-02, UI-03, UI-04, UI-05, UI-06, UI-07, UI-08, UI-09, UI-10, UI-11, UI-12, UI-13, UI-14, UI-15, UI-16
**Success Criteria** (what must be TRUE):
  1. User can log in with a JWT credential and the token is stored in memory - not in localStorage or URL params
  2. The agent board shows live online/offline/idle status with last-seen timestamps, updating automatically without page refresh when an agent changes state
  3. User can create a task from the UI, select a target agent, and cancel a running task - all reflected in real time via WebSocket
  4. The DLQ panel shows failed tasks and user can trigger a manual retry from the UI
  5. Cost tracking, distributed trace viewer, shared memory viewer, and resource lock panel are all accessible and show real data
  6. The layout is usable on a mobile browser - tables collapse to cards at small screen widths
**Plans**: 8 plans

Plans:
- [x] 04-01-PLAN.md - Wave 0: scaffold web/ (Vite + React 19 + TS + Tailwind v4 + shadcn + Vitest + msw)
- [x] 04-02-PLAN.md - App shell: sidebar + topbar + theme + i18n (TR+EN) + reconnecting banner
- [x] 04-03-PLAN.md - Auth layer: Zustand in-memory store + api-client RFC 7807 + LoginForm + _authed guard
- [x] 04-04-PLAN.md - Data layer: query-key factory + all query hooks + useWebSocketSync hybrid merge/invalidate
- [x] 04-05-PLAN.md - Operations: agents, tasks (create/cancel/trace), workflows + ResponsiveList + TraceTimeline
- [x] 04-06-PLAN.md - Visibility: DLQ/costs/memory/locks/health/settings/traces + JsonViewer
- [x] 04-07-PLAN.md - Production integration: FastAPI StaticFiles mount at /dashboard + smoke tests + README
- [x] 04-08-PLAN.md - Gap closure: psutil manifest, router basepath + favicon, SPA fallback catch-all, strict deep-link tests

### Phase 5: Release Readiness
**Goal**: OpenHub can be discovered, installed, and contributed to by open source developers - README quickstart works in under 5 minutes, pip install path exists, Docker Compose is hardened, graceful shutdown is implemented, and Playwright E2E tests cover critical flows
**Depends on**: Phase 4
**Requirements**: OSS-01, OSS-03, OSS-04, OSS-05, OSS-06, PROD-03, TEST-06
**Success Criteria** (what must be TRUE):
  1. A developer unfamiliar with the project can follow the README and have OpenHub running locally within 5 minutes via either Docker or pip install
  2. pip install openhub && openhub start produces a running server - no manual steps beyond setting credentials
  3. Docker Compose starts with health checks and restart policies - a container that crashes restarts automatically
  4. Stopping the server drains in-flight tasks and closes WebSocket connections cleanly - no tasks are silently dropped
  5. Playwright E2E tests pass for login, agent list view, task create, and task cancel flows
**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3 -> 4 -> 5

Note: Phase 3 depends only on Phase 1 and can be planned in parallel with Phase 2 if desired.

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Backend Hardening | 0/7 | Not started | - |
| 2. WebSocket + Test Suite | 0/6 | Not started | - |
| 3. Vector Database | 0/6 | Not started | - |
| 4. Command Center UI | 0/TBD | Not started | - |
| 5. Release Readiness | 0/TBD | Not started | - |
