# Architecture Patterns

**Domain:** Multi-agent coordination platform - command center UI + WebSocket + vector DB extension
**Researched:** 2026-04-07
**Overall confidence:** HIGH (grounded in existing codebase + verified patterns)

---

## Existing System Summary

The backend is a mature layered FastAPI application:

```
routes (HTTP boundary)
  -> services (business logic)
    -> repositories (typed SQL)
      -> Database (SQLite/Turso, thread-local connections)
```

Cross-cutting: `auth/` (JWT + API keys + Casbin), `structlog` logging, `pydantic_settings` config.

Key existing capabilities relevant to this milestone:
- WebSocket endpoint at `/v1/ws` already exists in `routes_websocket.py` with `push_event()` and `broadcast_event()` helpers called by other route modules when state changes.
- In-memory `_connections: Dict[str, WebSocket]` holds active WS connections (process-local, no shared state across workers).
- Vector store directory already provisioned at `./data/zvec/` with `AGENTHUB_EMBEDDING_MODEL` config key present.
- Static admin UI at `GET /admin` serves `app/static/admin.html` - a single vanilla JS file that will be replaced.
- CORS middleware already configured; all routes versioned under `/v1/`.

---

## Recommended Architecture

Three new system slabs added to the existing backend, plus a frontend process in development:

```
+------------------------------------------+
|           React + Vite (SPA)             |
|  Command Center UI - port 5173 (dev)     |
|  Served from FastAPI /ui/* (prod)        |
|                                          |
|  useWebSocket hook  <-> /v1/ws           |
|  REST calls         <-> /v1/**           |
|  Auth via JWT       <-> /v1/auth/login   |
+------------------------------------------+
            |               |
            | HTTP/REST      | WebSocket
            v               v
+------------------------------------------+
|           FastAPI Backend                |
|  app/main.py - existing entry point      |
|                                          |
|  [NEW] routes_ui.py   - static SPA serve |
|  [NEW] routes_vector.py - /v1/vector/*  |
|  [EXTEND] routes_websocket.py           |
|    - add UI client connection pool       |
|    - add dashboard-specific event types  |
+------------------------------------------+
            |               |
            |               v
            |   +---------------------------+
            |   |  Vector Service           |
            |   |  ChromaDB (embedded mode) |
            |   |  ./data/zvec/             |
            |   |  sentence-transformers    |
            |   +---------------------------+
            v
+------------------------------------------+
|  SQLite (WAL mode) / Turso               |
|  All existing tables - no changes        |
+------------------------------------------+
```

---

## Component Boundaries

### Component 1: React + Vite Command Center

| Attribute | Detail |
|-----------|--------|
| Location | `frontend/` at project root |
| Build output | `frontend/dist/` |
| Dev port | 5173 (proxied to 7788 via Vite config) |
| Prod serving | FastAPI `StaticFiles` mount at `/ui` + index fallback |
| Auth | JWT stored in `localStorage`; sent as `Authorization: Bearer` on REST, as `?token=` on WS |
| State | Zustand for global state (agents, tasks, connection status). React Query for server state (REST data). |
| Real-time | Single `useWebSocket` custom hook; reconnects with exponential backoff (500ms base, 12 retries) |
| Routing | React Router v6 - `/`, `/agents`, `/tasks`, `/workflows`, `/memory`, `/tools` |

Internal component boundaries within the UI:

```
frontend/src/
  api/          - typed fetch wrappers for every /v1/ endpoint
  hooks/        - useWebSocket, useAgents, useTasks, useWorkflows
  store/         - Zustand slices (connectionStore, agentStore, taskStore)
  components/
    layout/     - Sidebar, Header, ConnectionBadge
    agents/     - AgentCard, AgentList, AgentDetail
    tasks/      - TaskBoard (Kanban), TaskRow, TaskDetail
    workflows/  - WorkflowGraph, WorkflowStep
    shared/     - Button, Badge, Table, Modal, Toast
  pages/        - one file per route, composes components
  main.tsx      - app entry, router, providers
```

### Component 2: WebSocket Extension (Backend)

The existing `routes_websocket.py` authenticates only via API keys (agent-facing). The UI needs JWT-based WS auth for human dashboard sessions.

Additions to `routes_websocket.py`:
- Second connection pool `_ui_connections: Dict[str, WebSocket]` keyed by session user ID (decoded from JWT).
- Second WS endpoint `/v1/ws/ui` that accepts `?token=<jwt>` and validates with `verify_token()` from `auth/jwt_auth.py`.
- `broadcast_to_ui(event_type, data)` helper that pushes to all UI sessions.
- Call sites: any route that already calls `push_event()` or `broadcast_event()` also calls `broadcast_to_ui()` for relevant events.

New event types added for the dashboard (on top of existing `task_assigned`, `message_received`, etc.):

| Event | Trigger | Payload |
|-------|---------|---------|
| `agent_online` | agent registers/heartbeat resumes | `{agent_id, name, status}` |
| `agent_offline` | heartbeat expires | `{agent_id, name}` |
| `task_created` | task POSTed | `{task_id, title, status, assigned_to}` |
| `task_status_changed` | task patch (claim/start/complete/fail) | `{task_id, old_status, new_status}` |
| `workflow_advanced` | workflow step completes | `{workflow_id, step, status}` |
| `cost_recorded` | cost entry written | `{agent_id, model, cost_usd}` |

### Component 3: Vector Database Service

Purpose: semantic search over shared memory, task descriptions, artifacts, and agent capabilities to support context retrieval during multi-agent workflows.

**Recommended library: ChromaDB in embedded mode**

Rationale:
- Already `./data/zvec/` directory configured in settings (`AGENTHUB_ZVEC_PATH`).
- `AGENTHUB_EMBEDDING_MODEL` config already present (`sentence-transformers/all-MiniLM-L6-v2`).
- ChromaDB embedded runs in-process with no extra Docker service - critical for the self-host open source target.
- ChromaDB 2025 Rust core rewrite: 4x faster, true multithreading, Python GIL no longer a bottleneck.
- Adds one Python dependency (`chromadb`) vs sqlite-vec which requires a compiled C extension with platform-specific wheels.
- Alternative (sqlite-vec) is better if strict "single database file" is a goal; defer unless ChromaDB proves unsuitable.

Service location: `app/services/vector_service.py`

```
VectorService
  __init__(settings)
    - initializes ChromaDB PersistentClient(path=settings.zvec_path)
    - loads or creates named collections: "memory", "tasks", "artifacts"
  upsert(collection, id, text, metadata)
  search(collection, query_text, n_results, filters)
  delete(collection, id)
  get_collections() -> list
```

API surface: `app/api/routes_vector.py`

```
POST   /v1/vector/search          - semantic search across a collection
POST   /v1/vector/index           - manually index a document
DELETE /v1/vector/documents/{id}  - remove document from index
GET    /v1/vector/collections     - list collections + document counts
```

Auto-indexing hooks (write-path integration):
- `routes_memory.py` POST/PUT: after writing to SQLite, call `VectorService.upsert("memory", ...)`.
- `routes_tasks.py` POST (task created): call `VectorService.upsert("tasks", ...)` with title + description.
- `routes_artifacts.py` POST (upload): call `VectorService.upsert("artifacts", ...)` with filename + description.

This keeps vector writes on the existing request path - no separate indexing job needed at this scale.

---

## Data Flow

### Flow 1: Dashboard Initial Load

```
Browser loads /ui -> FastAPI serves dist/index.html
  -> React app boots, reads JWT from localStorage
  -> If no JWT: redirect to /login, POST /v1/auth/login, store JWT
  -> React Query fetches: GET /v1/agents, /v1/tasks, /v1/workflows in parallel
  -> useWebSocket opens ws://host/v1/ws/ui?token=<jwt>
  -> Server sends "connected" event with session info
  -> Dashboard renders populated state
```

### Flow 2: Live Agent Status Update

```
Agent process -> POST /v1/agents/{id}/heartbeat
  -> routes_agents.py -> AgentService.update_heartbeat()
  -> AgentService calls broadcast_to_ui("agent_online", {agent_id, ...})
  -> WebSocket pushes to all connected UI sessions
  -> useWebSocket hook receives message -> dispatches to Zustand agentStore
  -> AgentCard re-renders with updated status (no REST poll required)
```

### Flow 3: Task Assignment via Dashboard

```
User clicks "Create Task" in UI
  -> POST /v1/tasks with task payload + JWT
  -> routes_tasks.py -> TaskService.create_task()
  -> TaskService._attempt_auto_assignment() -> CapabilityMatcher
  -> If assigned: push_event(agent_id, "task_assigned", ...) to agent WS
  -> TaskService calls broadcast_to_ui("task_created", {...})
  -> UI WS receives task_created -> Zustand taskStore updated
  -> VectorService.upsert("tasks", task.id, task.title + description, metadata)
  -> TaskBoard re-renders with new card in QUEUED/CLAIMED column
```

### Flow 4: Semantic Memory Search

```
Agent/User POSTs /v1/vector/search with {collection: "memory", query: "auth tokens"}
  -> routes_vector.py -> VectorService.search("memory", query, n=10)
  -> ChromaDB runs embedding + cosine similarity
  -> Returns [{id, text, metadata, score}] ranked by relevance
  -> Caller uses results to enrich task context
```

### Flow 5: Production Static File Serving

```
FastAPI main.py mounts:
  app.mount("/ui", StaticFiles(directory="frontend/dist", html=True), name="ui")
  # Fallback: GET /ui/* -> index.html (handled by html=True flag)
  # GET /admin -> backward compat redirect to /ui (keeps existing agents working)
```

---

## Suggested Build Order (Phase Dependencies)

The three new slabs have different dependency profiles. Recommended build sequence:

### Phase A: Backend WebSocket Extension (no new dependencies)

Build first because:
- Zero new Python dependencies.
- UI needs events to be defined before implementing WS client.
- Unblocks the dashboard team (can test with wscat before UI exists).

Deliverables: `/v1/ws/ui` endpoint, `broadcast_to_ui()` helper, all new event types wired into existing route call sites.

### Phase B: Vector Service (new Python dependency, isolated)

Build second because:
- Completely isolated from the UI - can be shipped as a backend-only feature.
- Auto-indexing hooks go into existing routes (memory, tasks, artifacts) - small, well-scoped additions.
- `VectorService` has no dependency on anything in Phase A or Phase C.

Deliverables: `VectorService`, `routes_vector.py`, auto-index hooks in memory/task/artifact routes.

### Phase C: React + Vite Frontend (depends on Phase A for WS, uses Phase B via REST)

Build third because:
- Requires the WS event types from Phase A to be stable.
- Can call `/v1/vector/search` as a plain REST endpoint - does not require Phase B to be done first, but benefits from it.
- Longest-running phase due to UI surface area.
- Vite proxy config talks to backend on 7788 during development.

Deliverables: Full `frontend/` project, all dashboard pages, WebSocket integration, prod serving via `StaticFiles`.

### Phase D: Testing + Polish (depends on all phases)

Build last because:
- E2E tests require both frontend and backend.
- Unit tests for `VectorService` and WS extension can be written during Phase A/B but run as a suite in D.

Deliverables: pytest unit/integration for vector + WS, Playwright e2e for critical UI paths.

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: Shared In-Memory State for WS Connections Across Workers

**What goes wrong:** If uvicorn is run with `--workers 2+`, the `_connections` and `_ui_connections` dicts are per-process. Agent A's WS connection is in Worker 1; task completion fires in Worker 2 - no event delivered.

**Why it happens:** FastAPI's in-process dict approach works for single-worker but silently breaks with multiple workers.

**Prevention for v1.0:** Document that OpenHub must run as `--workers 1` (or `--reload` dev mode). This is acceptable for a self-hosted single-instance deployment. In v2, replace with Redis Pub/Sub as the WS event bus.

**Detection:** Missing WS events despite successful task state changes in multi-worker mode.

### Anti-Pattern 2: Importing VectorService in Route Modules at Module Load Time

**What goes wrong:** ChromaDB loads the embedding model (sentence-transformers ~90MB) on import. If `routes_vector.py` is imported at app startup unconditionally, startup time increases ~3-5 seconds and ~300MB RAM is consumed even if no vector features are used.

**Prevention:** Lazy-initialize `VectorService` on first request via a `get_vector_service()` FastAPI dependency with `functools.lru_cache`. Import `chromadb` inside the service class `__init__`, not at module top-level.

### Anti-Pattern 3: Polling REST from the UI Instead of Using WebSocket Events

**What goes wrong:** UI polls `GET /v1/agents` every 5 seconds. With 50 dashboard tabs open this is 10 req/s of unnecessary load. State also lags by up to 5 seconds.

**Prevention:** Seed UI state with one initial REST fetch on mount. All subsequent updates come from WebSocket events. REST is used only for explicit user actions (create task, filter, search). React Query with `staleTime: Infinity` and manual invalidation on WS events.

### Anti-Pattern 4: JWT in WebSocket URL Query Params Logged in Access Logs

**What goes wrong:** `ws://host/v1/ws/ui?token=eyJ...` - the full JWT appears in Nginx/uvicorn access logs. Tokens are typically long-lived (hours) and log files are often retained weeks.

**Prevention:** Accept the token as the first WebSocket message after connection (not in URL query param). Workflow: client connects -> server accepts but does not consider authenticated -> client sends `{"type": "auth", "token": "..."}` -> server validates -> server sends `{"event": "authenticated"}`. Only then add to `_ui_connections`. The URL remains clean.

### Anti-Pattern 5: Vector Index Growing Unbounded

**What goes wrong:** Every task creation indexes into ChromaDB. After 100K tasks the index becomes slow and the zvec directory grows to gigabytes.

**Prevention:** Add a `max_collection_size` config. When exceeded, oldest entries are evicted (LRU strategy). For v1.0, document the limitation and add a `/v1/vector/collections` endpoint showing document counts so operators can monitor.

---

## Scalability Notes (for roadmap context)

| Concern | v1.0 (self-hosted, 1-10 agents) | v2 future |
|---------|--------------------------------|-----------|
| WS connections | In-memory dict, single worker | Redis Pub/Sub event bus |
| Vector search | ChromaDB embedded, ~100K docs | ChromaDB server mode or Qdrant |
| Static serving | FastAPI StaticFiles | CDN / Nginx |
| DB | SQLite WAL (already Turso-ready) | Turso production |

---

## Sources

- FastAPI WebSockets official: https://fastapi.tiangolo.com/advanced/websockets/
- ChromaDB embedded mode comparison: https://zenvanriel.com/ai-engineer-blog/chroma-vs-qdrant-local-development/
- sqlite-vec (successor to sqlite-vss): https://github.com/asg017/sqlite-vss
- WebSocket reconnect patterns: https://websocket.org/guides/reconnection/
- React WebSocket dashboard patterns: https://medium.com/@connect.hashblock/i-built-a-real-time-dashboard-in-react-using-websockets-and-recoil-076d69b4eeff
- FastAPI + React Vite full-stack 2025: https://www.joshfinnie.com/blog/fastapi-and-react-in-2025/
- ChromaDB 2025 Rust rewrite performance: https://encore.dev/articles/best-vector-databases

---

*Architecture analysis: 2026-04-07*
