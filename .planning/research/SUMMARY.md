# Project Research Summary

**Project:** OpenHub v1.0
**Domain:** Multi-agent AI coordination platform - self-hosted command center
**Researched:** 2026-04-07
**Confidence:** HIGH (grounded in existing codebase audit + verified patterns)

## Executive Summary

OpenHub is a self-hosted multi-agent coordination hub: a FastAPI backend that coordinates AI coding agents (Claude Code, Cursor, Copilot) via task routing, shared memory, resource locks, and cost tracking. The backend is functionally mature across its core surfaces - task management, agent registration, capability matching, workflow orchestration, and auth. The v1.0 milestone is fundamentally a visibility and hardening problem: there is no frontend, zero tests, several silent security holes, and features that are wired but not actually functional (heartbeat monitoring never starts, Hatchet workflows are simulated in-memory, zvec is installed but not called). The gap between "code exists" and "working product" is the defining challenge of this milestone.

The recommended approach is a strict backend-first hardening pass before building anything new. Five specific bugs must be fixed before the test suite is written: the auth stub in `app/dependencies.py` that accepts any 8-character string, hardcoded admin credentials, capabilities stored as Python `str()` instead of JSON, the heartbeat monitor never started, and CORS wildcard as the default. Only after these are fixed and a test baseline is established should the three new slabs be built: WebSocket extension for the dashboard, the vector DB service (ChromaDB embedded, replacing unused zvec), and the React + Vite command center UI. The frontend stack - React 18 + Vite + TanStack Query + shadcn/ui + Zustand - is well-researched and appropriate for a single-page dashboard with no SSR requirement.

The key risks are: shipping an open source release that documents features as real when they are simulated (Hatchet workflows), or that contains the admin backdoor and token-in-URL WebSocket auth (CVE-class issue post-release). Both are preventable with the hardening-first order. The secondary risk is frontend architecture: WebSocket state management handled naively (setState on every message, no reconnect logic) will produce a broken dashboard under any real agent load. Zustand slices + message buffering + exponential backoff reconnection must be the architecture decision before the first component is written, not a fix added later.

---

## Key Findings

### Recommended Stack

The backend stack is fixed (FastAPI 0.104.1, SQLite WAL, Python 3.11+, Pydantic v2). No changes to backend dependencies are needed for WebSocket hardening or test coverage - pytest, pytest-asyncio, httpx, and slowapi are all already declared in requirements.txt but unused. The one backend addition is ChromaDB (embedded mode, in-process) to replace zvec 0.1.0 which has no active usage in the codebase and unclear maintenance status.

The frontend is net-new: React 18.3 + Vite 5 + TypeScript 5 chosen for pure SPA with no SSR requirement. TanStack Router for type-safe routing, TanStack Query for server state (REST fetches with WebSocket-triggered invalidation), Zustand for UI-only client state, shadcn/ui + Tailwind + Recharts for components. Native browser WebSocket API wrapped in a custom `useWebSocket` hook - no socket.io or external WS library.

**Core technologies:**
- React 18 + Vite 5 + TypeScript 5: SPA dashboard, no SSR needed, faster than Next.js for this use case
- TanStack Query 5: server state, stale-while-revalidate, WebSocket invalidation bridge
- TanStack Router 1.x: type-safe routing for agent/task/workflow cross-links
- shadcn/ui + Tailwind 3: component library with full source control, Recharts charts included
- Zustand 4: UI-only state (selected agent, sidebar, filters) - no server data
- ChromaDB (embedded): in-process vector DB with file persistence, replaces unused zvec
- Native WebSocket API: custom hook with exponential backoff, no socket.io

### Expected Features

The backend surfaces features that users of a coordination platform expect but cannot currently see. The entire differentiator stack - capability routing, cost tracking, resource locks, shared memory, DLQ - is built but invisible. The v1.0 frontend must make this visible. The research is clear: the dashboard is the product surface, and a platform with no UI will not be adopted by open source users regardless of backend quality.

**Must have (table stakes - blocking v1.0):**
- Live agent status board with real-time online/offline/idle status (WebSocket-driven)
- Task list with filterable status, real-time updates, create/cancel actions from UI
- JWT login form and auth gate (hub is exposed on network)
- Agent detail view: capabilities, current task, cost summary, heartbeat history
- Workflow step-list view (read-only status badges, not drag-drop builder)
- DLQ panel with manual retry button
- Health indicator using `/v1/health`
- Comprehensive test suite (backend unit + integration) - zero tests is the largest stability risk
- README quickstart and OpenAPI docs exposed (open source adoption lives on first impressions)

**Should have (differentiators to surface in v1.0):**
- Cost tracking display per agent - rare in self-hosted tools
- Distributed trace viewer in task detail - already in backend, UI is the gap
- Shared memory key/value viewer
- Resource lock panel with active lock display
- Semantic search over context via vector DB (ship as opt-in beta)
- Mobile-responsive layout (Tailwind breakpoints)

**Defer to v1.x (post-launch):**
- Visual workflow builder (drag-drop DAG) - 3-4x complexity of step-list view
- OAuth/SSO - JWT + API keys covers self-hosted use case
- Multi-tenancy - explicitly out of scope in PROJECT.md
- Real-time log streaming - solved by Grafana/Loki, not OpenHub's job
- Native mobile app - responsive web covers mobile browsers
- Plugin marketplace - premature before core is stable

### Architecture Approach

Three new slabs attach to the existing layered FastAPI backend (routes -> services -> repositories -> SQLite). The React SPA is served from `frontend/dist/` via FastAPI `StaticFiles` mount at `/ui` in production; Vite proxy handles backend calls in development. WebSocket extends the existing `/v1/ws` endpoint with a parallel `/v1/ws/ui` endpoint that authenticates via initial message frame (not URL query param) using JWT. ChromaDB runs embedded alongside SQLite with auto-indexing hooks on memory, task, and artifact write paths.

**Major components:**
1. React + Vite Command Center (`frontend/`) - SPA, Zustand global state, TanStack Query server state, single `useWebSocket` hook with reconnect
2. WebSocket Extension (`routes_websocket.py`) - new `/v1/ws/ui` endpoint, `ConnectionManager` class replacing module-level dict, `broadcast_to_ui()` helper, 6 new dashboard event types
3. Vector Service (`app/services/vector_service.py`) - ChromaDB PersistentClient, lazy-initialized, 3 collections (memory/tasks/artifacts), auto-index hooks
4. Backend Hardening (cross-cutting) - auth stub fix, capabilities JSON bug, heartbeat monitor wired, schema migration consolidation, CORS defaults locked down, OpenAPI docs enabled

### Critical Pitfalls

1. **Testing against a broken auth baseline** - The auth stub in `app/dependencies.py` accepts any 8-character string. Tests written before this is fixed will pass against the stub and mask the real auth being broken. Fix stub and hardcoded `admin/admin123` credentials before writing a single test.

2. **WebSocket token in URL query string** - `?token=oh_...` appears in Nginx access logs, browser history, and monitoring tools. CVE-class issue post open source release. Mitigation: accept token as the first WebSocket message frame, reject connections that do not authenticate within 5 seconds.

3. **Module-level `_connections` dict breaks silently** - Duplicate agent IDs overwrite silently; `--workers 2+` means cross-worker broadcasts silently drop. Build a `ConnectionManager` class with connect/disconnect cleanup from the start.

4. **Capabilities stored as Python `str()` not JSON** - `str(list)` produces single-quoted Python repr that `json.loads()` cannot parse. Task assignment silently fails for agents registered via the auth path. Two-line fix in `routes_auth.py` must land before any capability-matching tests are written.

5. **Repeating the Hatchet pattern with vector DB** - Hatchet service simulates all orchestration in-memory. zvec is installed but never called. Risk: vector DB "integration" ships as another in-memory fake. Verify ChromaDB file persistence with a restart test before claiming the feature done.

6. **Schema DDL inline in `main.py` lifespan** - 125 lines of DDL inline with a separate `database/migrations/` that does not cover the inline tables. Open source users cannot upgrade without wiping their database. Consolidate DDL into versioned migrations before adding any new tables.

---

## Implications for Roadmap

Based on combined research, 4 phases recommended. The ordering is dependency-driven: correctness before visibility, backend before frontend, testing woven through rather than bolted on at the end.

### Phase 1: Backend Hardening + Security
**Rationale:** The existing backend has silent correctness bugs and security holes that invalidate any test suite written before they are fixed. Non-negotiable prerequisite for everything else. No new dependencies - pure cleanup.
**Delivers:** Correct, tested, secure backend foundation - auth stub deleted, capabilities stored as JSON, heartbeat monitor wired into lifespan, CORS defaults locked down, datetime utcnow unified, OpenAPI docs enabled, schema DDL consolidated into versioned migrations, passlib replaced, duplicate auth helpers extracted to single module.
**Addresses:** Auth gate (table stakes), structured error display, correct agent capability matching
**Avoids:** Pitfalls 1 (broken auth baseline), 3 (schema migration), 5 (zvec/Hatchet pattern), 6 (heartbeat never starts), 8 (API key full table scan), 11 (CORS wildcard), 12 (simulated features documented as real), 13 (utcnow), 14 (duplicate auth helpers), 15 (passlib), 16 (docs disabled)

### Phase 2: WebSocket Extension + Backend Test Suite
**Rationale:** WebSocket event types must be stable before the frontend implements its WS client. Backend tests begin here - auth is now correct, making pytest/httpx useful. Test infrastructure is already declared in requirements.txt but unused.
**Delivers:** `/v1/ws/ui` endpoint with JWT initial-message auth, `ConnectionManager` class replacing module-level dict, `broadcast_to_ui()` helper, 6 dashboard event types wired into existing route call sites. Backend test suite: unit tests for WS auth, capability matching; integration tests for task lifecycle, agent heartbeat/offline detection.
**Uses:** pytest, pytest-asyncio, httpx (all already in requirements.txt - zero new packages)
**Avoids:** Pitfalls 2 (token in URL), 4 (module-level dict), 7 (no reconnect - defines event contract before frontend implements consumer)

### Phase 3: Vector DB Service
**Rationale:** Completely isolated from the UI - can ship as a backend-only feature without the frontend being done. Auto-indexing hooks are small additions to existing routes. Ships as opt-in beta with documented experimental status.
**Delivers:** `app/services/vector_service.py` (ChromaDB PersistentClient, lazy-initialized, 3 collections), `app/api/routes_vector.py` (search/index/delete/collections endpoints), auto-index hooks in memory/task/artifact write paths, zvec removed from requirements.txt, restart-persistence test confirming vectors survive server restarts.
**Implements:** Vector Service architecture component
**Avoids:** Pitfall 10 (in-memory fake pattern - verified by mandatory restart test)

### Phase 4: React + Vite Command Center
**Rationale:** Longest phase due to UI surface area. Depends on Phase 2 for stable WS event types. Can consume vector search API from Phase 3 via plain REST. Architecture decisions (Zustand slices, message buffering, reconnect logic) must be made before the first component is written.
**Delivers:** Full `frontend/` project, all dashboard pages (agents, tasks, workflows, memory, tools, DLQ), WebSocket hook with exponential backoff reconnect and "reconnecting..." banner, JWT login flow, cost tracking display, trace viewer in task detail, prod serving via FastAPI StaticFiles at `/ui`, Playwright E2E tests for critical paths.
**Uses:** React 18 + Vite 5 + TypeScript 5, TanStack Query 5 + TanStack Router 1.x, Zustand 4, shadcn/ui + Tailwind 3 + Recharts, Vitest + React Testing Library + Playwright
**Avoids:** Pitfalls 7 (no reconnect), 9 (setState on every WS message - Zustand + 100ms flush buffer required)

### Phase Ordering Rationale

- Phase 1 before everything: correctness bugs and security holes in the backend invalidate any work built on top of them. Auth must be correct before tests are written. Schema must be in migrations before new tables are added.
- Phase 2 before Phase 4: WS event contract must be stable before the frontend implements its consumer. Defining events server-side first means no API churn during UI development.
- Phase 3 before Phase 4 (weakly): vector search is a plain REST API; the frontend can call it regardless of whether Phase 3 is complete. But Phase 3 ships faster standalone and validates the persistence model before the UI depends on it.
- Tests woven through Phases 2-4, not deferred: a dedicated "testing phase" at the end creates a waterfall risk where tests reveal structural bugs in work that is already considered done.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 1 (auth hardening):** A planning-time code read of `routes_auth.py:244-252`, `app/dependencies.py`, and `routes_auth.py:88-90` is needed to confirm exact fix scope before estimating. The CONCERNS.md audit identified these but full fix scope needs code reading.
- **Phase 3 (vector DB):** ChromaDB embedded mode API surface against existing `AGENTHUB_ZVEC_PATH` and `AGENTHUB_EMBEDDING_MODEL` config keys needs verification. Sentence-transformers model download behavior on first startup must be understood before recommending lazy vs. eager initialization.

Phases with standard patterns (skip deep research):
- **Phase 2 (WebSocket):** ConnectionManager class, initial-message auth, and broadcast helper are well-documented FastAPI patterns with multiple verified implementations.
- **Phase 4 (frontend):** React + Vite + TanStack Query + shadcn/ui is the 2025 community consensus stack with extensive official documentation. No novel patterns required.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Backend stack is fixed/live. Frontend stack has official docs and wide community verification. Only uncertainty is ChromaDB version pinning for embedded API stability. |
| Features | HIGH | Feature list grounded in direct codebase audit (what exists vs. what is visible), not speculation. Table stakes derived from coordination platform landscape analysis. |
| Architecture | HIGH | Extends existing patterns rather than replacing them. Component boundaries derived from existing codebase structure. Data flows verified against actual route module call chains. |
| Pitfalls | HIGH | Pitfalls 1-6 grounded in specific file/line references from codebase audit. Not inferred - directly observable. Pitfalls 7-12 are well-documented FastAPI/React patterns with verified sources. |

**Overall confidence:** HIGH

### Gaps to Address

- **ChromaDB startup time and model download:** Sentence-transformers model (~90MB) downloads on first use. Decide during Phase 3 planning: download at Docker build time (Dockerfile), or lazy-load with a loading indicator. This affects the "one-command setup" table stakes feature.
- **Hatchet integration status:** HatchetService has `_hatchet_client = None` with in-memory simulation. Research did not determine whether real Hatchet integration is in scope for v1.0 or whether simulated workflows should be labeled experimental. This is a product decision needed before Phase 1 documentation audit.
- **pip install path:** FEATURES.md lists one-command setup as table stakes. Docker Compose exists but `pip install openhub && openhub start` does not exist yet. Clarify whether this is in-scope for v1.0 or whether Docker Compose is sufficient.
- **Frontend serving with Caddy on VPS:** The live VPS at hub.brunhilde.cloud uses Caddy as reverse proxy. Verify Caddy config handles SPA fallback routing for `/ui/*` -> `index.html` before Phase 4 ships.

---

## Sources

### Primary (HIGH confidence)
- FastAPI WebSocket official docs (fastapi.tiangolo.com) - WebSocket patterns, auth, StaticFiles serving
- TanStack official docs (tanstack.com) - Router vs React Router comparison, Query v5 API
- shadcn/ui official docs (ui.shadcn.com) - Vite installation, chart components
- zvec GitHub + PyPI (github.com/alibaba/zvec, pypi.org/project/zvec) - version history, 0.2.1b0 availability
- LangChain State of Agent Engineering 2026 - feature expectations for coordination platforms
- CrewAI open source (crewai.com) - competitive feature set reference
- Codebase audit: `/home/omer/projects/OpenHub/.planning/codebase/CONCERNS.md` - pitfalls 1-6 sourced from direct code reading

### Secondary (MEDIUM confidence)
- FastAPI WebSocket auth patterns (hexshift.medium.com) - initial-message auth pattern
- ChromaDB vs Qdrant comparison (zenvanriel.com) - embedded mode rationale
- Zustand vs Jotai 2025 (reactlibraries.com) - dashboard state management consensus
- Vector DB comparison 2025 (liquidmetal.ai) - in-process vs server-process tradeoffs
- AI Agent Dashboard Platforms 2026 (thecrunch.io) - feature landscape

### Tertiary (MEDIUM-LOW confidence)
- WebSocket reconnection patterns (websocket.org/guides/reconnection) - backoff strategy
- React WebSocket state management (connect.hashblock/medium.com) - render churn pattern
- Open source project pitfalls (daytona.io) - documentation accuracy warnings

---
*Research completed: 2026-04-07*
*Ready for roadmap: yes*
