---
last_mapped_commit: 13fcce7400bd66c4e9b5412c9ed677cd215f019a
---
<!-- refreshed: 2026-05-25 -->
# Architecture

**Analysis Date:** 2026-05-25

## System Overview

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                          OpenHub Coordination Layer                         │
│                          `app/main.py`, `web/src/`                          │
├───────────────────────┬──────────────────────┬──────────────────────────────┤
│ REST/WS API            │ React Dashboard       │ Bridge / Agent Clients       │
│ `app/api/routes_*.py`  │ `web/src/routes/`     │ `app/bridge/agent_bridge.py` │
└───────────┬───────────┴──────────┬───────────┴──────────────┬───────────────┘
            │                       │                          │
            ▼                       ▼                          ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ Services: tasks, agents, ACN, workflows, search, events, heartbeat          │
│ `app/services/`, `app/auth/`, `app/models/`                                 │
└───────────────────────────────────────────┬─────────────────────────────────┘
                                            ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ Persistence / Runtime State                                                 │
│ `app/database/connection.py`, `app/database/repositories/`, `data/state/`    │
│ SQLite default, optional Turso/libSQL, optional Redis cache                  │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Component Responsibilities

| Component | Responsibility | File |
|-----------|----------------|------|
| FastAPI app factory/lifespan | Start migrations, background workers, heartbeat monitor, WebSocket manager, dashboard static mount | `app/main.py` |
| Settings | Load `AGENTHUB_` configuration and required admin/JWT fields | `app/config.py` |
| Auth | JWTs, API keys, current-user dependencies, RBAC | `app/auth/jwt_auth.py`, `app/auth/api_keys.py`, `app/auth/dependencies.py`, `app/auth/rbac/` |
| Agents | Local agent registration, heartbeat, discovery, capability matching | `app/api/routes_agents.py`, `app/services/agent_service.py`, `app/services/discovery_service.py` |
| ACN | Invite-based remote node/agent registry and remote task routing | `app/api/routes_acn.py`, `app/database/repositories/acn_nodes.py`, `app/database/repositories/remote_agent_mappings.py` |
| Tasks | Queue lifecycle, claims, leases, recovery, transitions, traces | `app/api/routes_tasks.py`, `app/services/task_service.py`, `app/database/repositories/tasks.py` |
| Workflows | Workflow run APIs and coordination planning | `app/api/routes_workflows.py`, `app/api/routes_workflow.py`, `app/services/workflow_coordinator.py`, `app/services/hatchet_service.py` |
| Search/vector memory | Embedding hooks, retry worker, semantic search API | `app/api/routes_search.py`, `app/services/embedding_hooks.py`, `app/services/embedding_retry_worker.py`, `app/services/vector_search_service.py` |
| Dashboard | Authenticated SPA for agents, tasks, workflows, health, memory, costs, locks, DLQ | `web/src/routes/`, `web/src/components/`, `web/src/hooks/queries/` |

## Pattern Overview

**Overall:** Layered FastAPI service architecture with a React SPA dashboard and raw-SQL repository persistence.

**Key Characteristics:**
- API routers are grouped by domain in `app/api/routes_*.py` and mounted centrally from `app/main.py`.
- Business logic belongs in `app/services/`; repositories under `app/database/repositories/` wrap SQL details.
- Pydantic models under `app/models/` define API and service contracts.
- Dashboard uses route modules under `web/src/routes/`, shared query hooks under `web/src/hooks/queries/`, and typed entities in `web/src/types/entities.ts`.
- Real-time UI sync reuses `/v1/ws/ui`, `ConnectionManager`, and `web/src/hooks/useWebSocketSync.ts`.

## Layers

**Transport Layer:**
- Purpose: Expose REST, WebSocket, static dashboard, and metrics endpoints.
- Location: `app/main.py`, `app/api/routes_*.py`.
- Contains: FastAPI routers, dependencies, response models, WebSocket handlers.
- Depends on: auth dependencies, services, database connection.
- Used by: dashboard, bridge agents, external API clients.

**Service Layer:**
- Purpose: Own business operations that should not be duplicated in route handlers.
- Location: `app/services/`.
- Contains: `TaskService`, `HeartbeatService`, `ConnectionManager`, `WorkflowCoordinator`, `VectorSearchService`, embedding hooks/workers.
- Depends on: repositories, models, settings.
- Used by: API routers and lifespan startup/shutdown.

**Persistence Layer:**
- Purpose: Provide SQLite/Turso access and table-specific repository operations.
- Location: `app/database/connection.py`, `app/database/repositories/`, `alembic/`.
- Contains: raw SQL execution, row conversion, Turso retry on stale connection, repository CRUD.
- Depends on: settings and sqlite/libSQL clients.
- Used by: services, routers, tests.

**Dashboard Layer:**
- Purpose: User-facing command center.
- Location: `web/src/`.
- Contains: TanStack Router routes, TanStack Query hooks, Zustand stores, components, i18n namespaces, MSW tests.
- Depends on: `/v1/*` APIs and `/v1/ws/ui`.
- Used by: operators at `/dashboard` after `web/dist` is built.

## Data Flow

### Primary Task Request Path
1. Client creates/searches/updates tasks through `/v1/tasks/*` in `app/api/routes_tasks.py`.
2. Route authenticates via JWT/API-key dependencies in `app/auth/`.
3. `TaskService` in `app/services/task_service.py` validates state transitions, capability matching, leases, progress, and recovery.
4. `TaskRepository` in `app/database/repositories/tasks.py` persists task rows through `Database.execute()` in `app/database/connection.py`.
5. UI state is refreshed through REST query hooks in `web/src/hooks/queries/useTasks.ts` and real-time events in `web/src/hooks/useWebSocketSync.ts`.

### ACN Invite / Remote Agent Flow
1. Admin creates invites through `/v1/acn/admin/invite` or dashboard wrapper `/v1/acn/dashboard/invite` in `app/api/routes_acn.py`.
2. Remote agent joins through `/v1/acn/join` and receives/uses a per-agent key.
3. Node/agent heartbeat and mapping are stored through ACN repositories in `app/database/repositories/`.
4. Dashboard agent state should use ACN status/health endpoints rather than legacy local-agent-only counts.

### Dashboard Login Flow
1. `web/src/components/forms/LoginForm.tsx` posts admin credentials through `web/src/lib/api-client.ts`.
2. `/v1/auth/admin/login` in `app/api/routes_auth.py` returns JWTs.
3. `web/src/stores/auth-store.ts` stores tokens; `api()` attaches `Authorization: Bearer ...` to subsequent requests.
4. Synthetic admin JWT subjects are accepted by backend auth dependencies, covered by `tests/unit/test_admin_dashboard_auth.py`.

### Vector Search Flow
1. Write paths schedule embeddings through `app/services/embedding_hooks.py` where implemented.
2. `app/services/embedding_retry_worker.py` processes pending rows when vector/Turso is enabled.
3. `POST /v1/search` in `app/api/routes_search.py` embeds the query, fans out over entity types, merges hits, and returns `SearchResponse`.
4. Local SQLite or missing embedding configuration returns graceful 503 through `require_vector` and embedding availability checks.

**State Management:**
- Backend persistent state is SQLite/Turso, with optional Redis token cache.
- Dashboard state is TanStack Query cache + Zustand auth/UI stores.
- WebSocket events update or invalidate TanStack Query keys in `web/src/hooks/useWebSocketSync.ts`.

## Key Abstractions

**Task:**
- Purpose: Unit of agent work with status, lease, owner, progress, retry/error data, and trace/evidence fields.
- Examples: `app/models/tasks.py`, `app/services/task_service.py`, `app/api/routes_tasks.py`.
- Pattern: service-mediated state machine; avoid direct row mutation outside TaskService/repository routes.

**Agent / ACN Node:**
- Purpose: Local or remote worker identity with capabilities, heartbeat, node mapping, and API-key metadata.
- Examples: `app/models/agents.py`, `app/models/acn.py`, `app/api/routes_agents.py`, `app/api/routes_acn.py`.
- Pattern: distinguish node liveness from per-agent liveness; do not let node heartbeat falsely mark every mapped agent online.

**ConnectionManager:**
- Purpose: Manage UI WebSocket clients and broadcast task/agent/workflow events.
- Examples: `app/services/connection_manager.py`, `app/api/routes_ws_ui.py`, `web/src/hooks/useWebSocketSync.ts`.
- Pattern: reuse existing `/v1/ws/ui` path; do not create parallel dashboard sockets.

**Database:**
- Purpose: Hide SQLite vs Turso details behind one synchronous wrapper.
- Examples: `app/database/connection.py`, repositories under `app/database/repositories/`.
- Pattern: use named SQL parameters in app code; `Database._adapt_params()` handles libSQL positional conversion.

## Entry Points

**API server:**
- Location: `app/main.py`.
- Triggers: `openhub`, `python -m uvicorn app.main:app`, Docker CMD.
- Responsibilities: lifespan startup/shutdown, router registration, dashboard mount, root endpoint.

**Dashboard SPA:**
- Location: `web/src/main.tsx`, `web/src/routes/`.
- Triggers: Vite dev server, static assets under `web/dist` mounted at `/dashboard`.
- Responsibilities: authenticated UI for tasks, agents, workflows, health, locks, traces, DLQ, memory, settings.

**Agent bridge:**
- Location: `app/bridge/agent_bridge.py`, `scripts/run_bridge.py`.
- Triggers: CLI/supervisor process with hub URL and per-agent API key.
- Responsibilities: heartbeat, polling, task claim/start/complete/fail, result submission.

## Architectural Constraints

- **Threading:** `Database` uses thread-local connections in `app/database/connection.py`; asynchronous routes call synchronous DB methods, so avoid long blocking loops inside request handlers.
- **Global state:** `settings` in `app/config.py` and `_database` in `app/database/connection.py` are module-level singletons; tests set env before importing `app.main`.
- **Dashboard mount:** `/dashboard` only exists when `web/dist/index.html` exists; API image checks alone do not prove dashboard packaging.
- **Vector feature gate:** `/v1/search` is beta/opt-in and requires Turso/vector availability; local SQLite should fail gracefully with 503.
- **Auth split:** admin JWTs, agent JWTs, and API keys have separate dependency paths; do not leak `AGENTHUB_ACN_ADMIN_KEY` to browser clients.

## Anti-Patterns

### Using `/v1/health` as dashboard truth
**What happens:** Health route still exposes some legacy placeholder counts.
**Why it's wrong:** It can report service health while ACN/task truth lives in separate endpoints.
**Do this instead:** Use `/v1/acn/status`, `/v1/acn/health`, `/v1/tasks/search`, and targeted dashboard hooks in `web/src/hooks/queries/`.

### Duplicating WebSocket stacks
**What happens:** New dashboard features add their own socket path.
**Why it's wrong:** It bypasses `ConnectionManager` and existing reconnection/cache invalidation logic.
**Do this instead:** Broadcast through `app.state.connection_manager.broadcast_to_ui` and consume in `web/src/hooks/useWebSocketSync.ts`.

### Reading secrets for docs or diagnostics
**What happens:** `.env` or key files get read while mapping/debugging.
**Why it's wrong:** Codebase maps are committed and would leak credentials.
**Do this instead:** Read `.env.example` for variable names only; never read real `.env` contents.

## Error Handling

**Strategy:** RFC 7807 problem responses for API errors, with structured logging and request IDs.

**Patterns:**
- Rate limit errors are converted to problem details by `rfc7807_rate_limit_handler()` in `app/main.py`.
- API client wraps failed responses in `ApiError` from `web/src/lib/api-client.ts`.
- Services log failures with context and either raise or return state-machine booleans, e.g. `TaskService.claim_task()` in `app/services/task_service.py`.

## Cross-Cutting Concerns

**Logging:** `structlog` configured by `app/logging.py`; use structured event names and fields.
**Validation:** Pydantic models in `app/models/` and request models local to route files.
**Authentication:** JWT/API-key dependencies in `app/auth/`; RBAC policy files in `app/auth/rbac/policies/`.
**Real-time sync:** `ConnectionManager` + `/v1/ws/ui` + `useWebSocketSync()`.
**Persistence:** raw SQL repositories over `Database`, SQLite default, Turso optional.

---

*Architecture analysis: 2026-05-25*
