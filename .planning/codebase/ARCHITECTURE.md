# Architecture

**Analysis Date:** 2026-04-07

## Pattern Overview

**Overall:** Layered service-oriented architecture with FastAPI as the HTTP boundary

**Key Characteristics:**
- Strict layer separation: routes -> services -> repositories -> database
- Repository pattern provides a typed ORM-like abstraction over raw SQLite/Turso SQL
- Services hold all business logic; routes only parse HTTP input and delegate
- Dependency injection via FastAPI `Depends()` - service instances are created per request, not shared singletons
- No async ORM - all database access is synchronous with thread-local connections

## Layers

**API Layer (HTTP boundary):**
- Purpose: Parse and validate HTTP input, call services, format responses
- Location: `app/api/`
- Contains: FastAPI `APIRouter` instances, Pydantic request/response models inline or imported from `app/models/`
- Depends on: `app/services/`, `app/auth/`, `app/database/connection.py`
- Used by: HTTP clients, `app/bridge/agent_bridge.py`, WebSocket clients

**Service Layer (business logic):**
- Purpose: All domain logic, orchestration between repositories, cross-entity operations
- Location: `app/services/`
- Contains: `TaskService`, `AgentService`, `HeartbeatService`, `CapabilityMatcher`, `DiscoveryService`, `RemoteAgentService`, `HatchetService`, `WorkflowCoordinator`
- Depends on: `app/database/repositories/`, `app/models/`
- Used by: `app/api/` route modules

**Repository Layer (data access):**
- Purpose: Typed CRUD over individual database tables; isolates SQL from business logic
- Location: `app/database/repositories/`
- Contains: `BaseRepository` (generic ABC), `AgentRepository`, `TaskRepository`, `ACNNodeRepository`, `RemoteAgentMappingRepository`
- Depends on: `app/database/connection.py` (`Database` class)
- Used by: `app/services/`

**Database Layer:**
- Purpose: Connection management, query execution, SQLite/Turso abstraction
- Location: `app/database/connection.py`
- Contains: `Database` class with thread-local connections, `get_database()` singleton factory
- Depends on: `sqlite3` (stdlib), `libsql_experimental` (optional Turso)
- Used by: `app/database/repositories/`, routes that bypass repositories for direct SQL (P1/P2 routes)

**Auth Layer (cross-cutting):**
- Purpose: JWT verification, API key validation, RBAC enforcement
- Location: `app/auth/`
- Contains: `jwt_auth.py`, `api_keys.py`, `dependencies.py`, `redis_cache.py`, `rbac/enforcer.py`, `rbac/policies.py`
- Depends on: `app/database/connection.py`, Redis (optional)
- Used by: All `app/api/` route modules via FastAPI `Depends()`

**Bridge Layer (client SDK):**
- Purpose: Lightweight HTTP client for remote agents to connect to the hub
- Location: `app/bridge/agent_bridge.py`
- Contains: `AgentBridge` class - handles registration, heartbeat loop, task polling
- Depends on: `httpx` (async HTTP)
- Used by: External agents running `scripts/run_bridge.py`

## Data Flow

**Agent Task Assignment Flow:**

1. Agent POSTs `POST /v1/tasks` with `TaskCreate` payload
2. `routes_tasks.py` calls `TaskService.create_task()`
3. `TaskService` creates task record via `TaskRepository.create()` (status=QUEUED)
4. `TaskService._attempt_auto_assignment()` calls `CapabilityMatcher.find_best_agent()`
5. `CapabilityMatcher` queries `AgentRepository` for online/idle agents, scores by capability overlap
6. If match found, `TaskService` updates task to CLAIMED and sets `owner_agent_id`
7. If agent is WebSocket-connected, `routes_websocket.push_event()` fires `task_assigned` event
8. Agent polls `GET /v1/tasks/my-tasks` or receives via WebSocket, then POSTs `PATCH /v1/tasks/{id}/start`
9. Agent completes with `POST /v1/tasks/{id}/complete`

**ACN Remote Agent Onboarding Flow:**

1. Admin calls `POST /v1/acn/admin/invite` with `X-Admin-Key` header - gets a single-use invite code
2. Remote agent calls `POST /v1/acn/join` with invite code and registration payload
3. `routes_acn.py` calls `RemoteAgentService.register_node()` and then creates an API key via `APIKeyManager`
4. Agent receives permanent `oh_...` API key in response
5. All subsequent calls use `X-API-Key: oh_...` header

**Workflow Engine Flow (DAG):**

1. Client POSTs `POST /v1/workflows/create` with ordered steps array
2. `routes_workflow.py` persists workflow record in `workflows` table (status=created)
3. First step is immediately created as a Task via `TaskService.create_task()`
4. When step N task completes (`POST /v1/tasks/{id}/complete`), workflow engine checks current step
5. If more steps remain, creates step N+1 task using previous step's output as input payload
6. Workflow reaches `completed` when last step task completes

**State Management:**
- All state is persisted to SQLite/Turso - no in-memory state stores for core entities
- WebSocket connections held in-memory dict `_connections: Dict[str, WebSocket]` in `routes_websocket.py` (process-local)
- Rate limit sliding windows held in-memory `_rate_limits: Dict[str, List[float]]` in `routes_p2.py` (process-local)
- ACN invite codes held in-memory `_invite_store: Dict` in `routes_acn.py` (process-local, single-use by design)
- Redis used optionally for JWT token blacklisting; system degrades gracefully without it

## Key Abstractions

**BaseRepository (`app/database/repositories/base.py`):**
- Purpose: Generic typed CRUD base for all database entities
- Pattern: Abstract class `BaseRepository[T]` with `_row_to_model()` and `_model_to_dict()` as abstract methods; concrete classes implement these converters
- Methods provided: `create`, `get_by_id`, `update`, `delete`, `list_all`, `find_by`, `find_one_by`, `count`, `exists`, `bulk_create`, `bulk_update`, `execute_custom_query`

**Database (`app/database/connection.py`):**
- Purpose: Unified SQL interface that works with both local SQLite and Turso (libsql cloud)
- Pattern: Thread-local connections via `threading.local()`; named param syntax (`:param`) auto-converted to positional `?` for Turso compatibility
- Key methods: `execute`, `fetch_one`, `fetch_all`, `transaction()` (context manager), `execute_many`

**Pydantic Model Mixins (`app/models/base.py`):**
- Purpose: Composable model pieces - `IDMixin` (UUID id), `TimestampMixin` (created_at, updated_at), `MetadataMixin` (labels, metadata)
- Pattern: Multiple inheritance - e.g., `Agent(IDMixin, TimestampMixin, MetadataMixin)`
- Config: `extra='forbid'`, `use_enum_values=True`, `validate_assignment=True`

**CapabilityMatcher (`app/services/capability_matcher.py`):**
- Purpose: Scores available agents against task capability requirements
- Pattern: Returns `CapabilityMatch` dataclass with `match_score`, `matched_capabilities`, `missing_capabilities`, `confidence_score`
- Used by: `TaskService` during auto-assignment at task creation time

**AgentBridge (`app/bridge/agent_bridge.py`):**
- Purpose: Client-side bridge that connects a remote agent process to the hub via HTTP
- Pattern: Async loop with configurable `heartbeat_interval` and `task_poll_interval`; registers handler via `set_task_handler(fn)` callback

## Entry Points

**ASGI Application:**
- Location: `app/main.py` - `app` variable (FastAPI instance)
- Triggers: `uvicorn app.main:app --host 0.0.0.0 --port 7788`
- Responsibilities: Router assembly, CORS setup, error handler setup, database table bootstrap in `lifespan()` context manager

**Development Server:**
- Location: `app/main.py` - `run_server()` function
- Triggers: `python -m app.main` or `uvicorn app.main:app --reload`

**Bridge Runner:**
- Location: `scripts/run_bridge.py`
- Triggers: Direct script execution by remote agent process

**Docker:**
- Location: `Dockerfile`, `docker-compose.yml` at project root

## Error Handling

**Strategy:** HTTP exceptions at the route layer; exceptions propagate from services and are caught in routes or middleware

**Patterns:**
- Routes raise `HTTPException` with appropriate status codes directly
- Services raise `ValueError` for business rule violations (e.g., duplicate names)
- `app/middleware.py` contains `RequestTimingMiddleware` (logs every request/response) and global exception handlers set via `setup_error_handlers(app)`
- Database errors propagate up from repositories with structured log entries before re-raising
- Auth failures raise `HTTPException(401)` from dependency functions; these short-circuit before routes execute

## Cross-Cutting Concerns

**Logging:** `structlog` via `app/logging.py` - `get_logger(__name__)` returns a bound logger. Log calls use keyword-style structured fields: `logger.info("event_name", key=value)`. JSON output in production, colored console in debug mode.

**Validation:** Pydantic v2 at the route layer (request bodies) and model layer. Field validators on `AgentCreate` enforce capability name charset and agent name format.

**Authentication:** Two paths - (1) JWT Bearer tokens for interactive/admin sessions via `app/auth/dependencies.py` `CurrentAgent`/`CurrentAdmin` typed dependencies; (2) `X-API-Key` header validated inline in most route modules via `APIKeyManager.validate_api_key()`. ACN admin endpoints use a separate `X-Admin-Key` header.

**Settings:** `pydantic_settings.BaseSettings` subclass in `app/config.py` with `AGENTHUB_` prefix. Single global instance returned by `get_settings()`.

---

*Architecture analysis: 2026-04-07*
