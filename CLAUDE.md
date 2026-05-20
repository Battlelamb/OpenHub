# CLAUDE.md - OpenHub

This file provides guidance to Claude Code when working with the OpenHub project.

## GSD + Claude Code Operating Contract

- Use the local GSD installation in `.claude/` for planning, execution, verification, and phase discipline.
- Use Claude Opus 4.7 for all GSD phases and variations unless the human operator explicitly overrides it.
  - Preferred Claude Code invocation: `claude -p "<task>" --model opus --effort max --max-turns <n>`.
  - GSD config resolves Anthropic Opus to `claude-opus-4-7`.
- Credential source is local only: `ANTHROPIC_API_KEY` or Claude Code OAuth. Never write real credentials to files or chat.
- Work in small GSD slices: refresh state -> discuss/plan -> execute in fresh context/worktree -> verify -> document evidence -> commit.
- OpenHub is security-first: preserve known-good tokens, avoid leaking `ak_...`/`oh_...`/provider keys, and keep admin actions auditable.
- Verification-first rule: do not claim a change is complete until backend/frontend tests or an explicit bounded smoke check have passed.

## Project Overview

**OpenHub** is a multi-agent coordination platform that enables multiple AI agents (Claude Code, Cursor, Copilot, etc.) to work together on the same codebase without conflicts.

**GitHub**: https://github.com/Battlelamb/OpenHub.git
**Location**: `/home/brunhilde/OpenHub` (Linux / WSL2 development environment)

## Repository Structure

```
OpenHub/
├── app/                          # Main application
│   ├── api/                      # FastAPI route endpoints
│   │   ├── routes_agents.py      # Agent management + discovery + monitoring
│   │   ├── routes_tasks.py       # Task lifecycle management
│   │   ├── routes_workflows.py   # Hatchet workflow orchestration
│   │   ├── routes_coordination.py # Smart agent-workflow coordination
│   │   ├── routes_auth.py        # JWT authentication endpoints
│   │   ├── routes_admin.py       # Administrative functions
│   │   └── routes_health.py      # Health check
│   ├── auth/                     # Authentication & Security
│   │   ├── jwt_auth.py           # JWT token management
│   │   ├── api_keys.py           # API key system
│   │   ├── dependencies.py       # FastAPI auth dependencies
│   │   ├── redis_cache.py        # Redis token caching
│   │   └── rbac/                 # Casbin role-based access control
│   ├── database/                 # Database layer
│   │   ├── connection.py         # SQLite connection management
│   │   ├── migrations.py         # Migration system
│   │   └── repositories/         # Data access layer
│   ├── models/                   # Pydantic data models
│   │   ├── agents.py             # Agent models
│   │   ├── tasks.py              # Task models
│   │   └── events.py             # Event models
│   ├── services/                 # Business logic
│   │   ├── agent_service.py      # Agent registration & management
│   │   ├── heartbeat_service.py  # Agent health monitoring
│   │   ├── capability_matcher.py # Smart agent-capability matching
│   │   ├── discovery_service.py  # Agent discovery & monitoring
│   │   ├── task_service.py       # Task lifecycle management
│   │   ├── hatchet_service.py    # Hatchet workflow integration
│   │   └── workflow_coordinator.py # Agent-workflow coordination
│   ├── config.py                 # Application settings
│   ├── main.py                   # FastAPI app entry point
│   └── logging.py                # Structured logging
├── docs/                         # Specifications & plans
│   ├── CODEX_PLAN.md
│   ├── MULTI_AGENT_HUB_SPEC.md
│   ├── PROJECT_ROADMAP.md
│   ├── ARCHITECTURE_EVALUATION.md
│   └── DEVELOPMENT_RULES.md
├── database/                     # SQL migrations
├── scripts/                      # Setup & utility scripts
├── tests/                        # Test suite
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── pyproject.toml
```

## Technical Stack

- **Python 3.11+** with FastAPI + Uvicorn + WebSockets
- **SQLite** with WAL mode and migration system
- **Pydantic v2** for data validation
- **Hatchet** for workflow orchestration (AI agent pipelines)
- **JWT + API Keys + Casbin RBAC** for authentication
- **Redis** for token caching (optional, graceful degradation)
- **Docker** for deployment

## Development Commands

```bash
# Run development server
uvicorn app.main:app --host 0.0.0.0 --port 7788 --reload

# Docker deployment
docker-compose up --build

# Health check
curl http://localhost:7788/v1/health
```

## API Architecture

### Authentication
- **JWT tokens**: Interactive sessions (login/refresh)
- **API Keys**: Service-to-service communication (permanent)
- **RBAC**: Casbin policy-based role authorization
- Roles: `admin`, `agent`, `viewer`

### Core Endpoints
- **Health**: `GET /v1/health`
- **Agents**: `/v1/agents/*` (register, heartbeat, discover, monitor)
- **Tasks**: `/v1/tasks/*` (create, claim, start, complete, fail, search)
- **Workflows**: `/v1/workflows/*` (create, templates, status, cancel)
- **Coordination**: `/v1/coordination/*` (plan, execute, status)
- **Auth**: `/v1/auth/*` (login, refresh, API keys)
- **Admin**: `/v1/admin/*` (stats, cleanup)

### Task State Flow
```
QUEUED → CLAIMED → RUNNING → COMPLETED/FAILED
          ↓                      ↓
     (lease expires)        (retry if retryable)
          ↓                      ↓
        QUEUED ←─────────────── QUEUED
```

## Implementation Progress

Phase tracking follows the GSD roadmap in `.planning/ROADMAP.md` (5 phases; 1-4 complete, 5 in progress).

### Completed Phases:
- ✅ **Phase 1 — Backend Hardening**: real auth enforcement, capabilities stored as JSON, heartbeat monitor, CORS lockdown, Alembic migrations, RFC 7807 errors, rate limiting, OpenAPI docs
- ✅ **Phase 2 — WebSocket + Test Suite**: first-frame JWT WebSocket auth, `ConnectionManager` with live agent/task events, backend test suite (auth, capability matching, lifecycle)
- ✅ **Phase 3 — Vector Database**: Turso/libSQL native F32_BLOB vectors, local + OpenAI embedding backends, `/v1/search` — shipped as opt-in beta
- ✅ **Phase 4 — Command Center UI**: React + Vite dashboard with live agent/task/workflow control, DLQ, cost tracking, distributed trace viewer

### Current Phase:
- 🔄 **Phase 5 — Release Readiness**: open source docs, pip install path, hardened Docker Compose, graceful shutdown, Playwright E2E tests (GSD operating loop in progress)

## Configuration

Environment variables (prefix: `AGENTHUB_`):
- `AGENTHUB_HOST=0.0.0.0`
- `AGENTHUB_PORT=7788`
- `AGENTHUB_DB_PATH=./data/state/agenthub.db`
- `AGENTHUB_ARTIFACT_DIR=./data/artifacts`
- `AGENTHUB_TASK_LEASE_TTL_SEC=60`
- `AGENTHUB_LOG_LEVEL=INFO`
- `AGENTHUB_HATCHET_SERVER_URL=http://localhost:8080`

## Development Style

- **Slow, clean, and small steps** (yavaş, temiz ve küçük adımlar)
- Production-grade code quality with fine detail
- Structured logging throughout
- Repository pattern with service layer architecture
- Clean separation of concerns

<!-- GSD:project-start source:PROJECT.md -->
## Project

**OpenHub v1.0 - Production Ready**

OpenHub is a multi-agent coordination platform that enables multiple AI agents (Claude Code, Cursor, Copilot, etc.) to work together on the same codebase without conflicts. It provides agent registration, task management, workflow orchestration, and real-time coordination through a centralized hub. v1.0 targets open source release with a command center UI, production-grade backend, and responsive mobile web support.

**Core Value:** Any developer can self-host OpenHub, connect their AI agents, and coordinate multi-agent workflows from a single command center - reliably and without conflicts.

### Constraints

- **Backend stack**: Python 3.11+ / FastAPI / SQLite (already established, not changing)
- **Frontend stack**: React + Vite (chosen for lightweight SPA dashboard)
- **Deployment**: Must support both Docker and pip install for open source accessibility
- **Compatibility**: Must maintain existing API contracts - agents already running in production
<!-- GSD:project-end -->

<!-- GSD:stack-start source:codebase/STACK.md -->
## Technology Stack

## Languages
- Python 3.11+ - All application code (runtime is 3.12.3 in local WSL env)
## Runtime
- CPython 3.12.3 (local WSL2), pinned to ^3.11 in `pyproject.toml`
- pip via `requirements.txt` (production installs)
- Poetry via `pyproject.toml` (dev tooling and dependency declarations)
- Lockfile: Not detected (no `poetry.lock` or `requirements.lock` committed)
## Frameworks
- FastAPI 0.104.1 - Web framework, all REST and WebSocket endpoints
- Uvicorn 0.24.0 (with `[standard]` extras) - ASGI server, hot reload in dev
- Starlette - Underlying ASGI toolkit (bundled with FastAPI), used directly for `BaseHTTPMiddleware`
- Pydantic v2 2.4.2 - All request/response models in `app/models/`
- pydantic-settings 2.0.3 - `app/config.py` `Settings` class with `AGENTHUB_` env prefix
- SQLAlchemy 2.0.23 - Declared as dependency; actual DB operations use raw SQL via custom `Database` class in `app/database/connection.py`
- Alembic 1.12.1 - Migration framework declared; runtime DDL is executed inline in `app/main.py` lifespan
- PyJWT 2.8.0 (with `[crypto]`) - JWT access and refresh token creation/verification (`app/auth/jwt_auth.py`)
- passlib 1.7.4 (with `[bcrypt]`) - Password hashing for admin users (`bcrypt` scheme)
- Casbin 1.25.0 - RBAC policy enforcement via file-based `rbac_model.conf` + `rbac_policy.csv` (`app/auth/rbac/enforcer.py`)
- slowapi 0.1.9 - Rate limiting (declared in `requirements.txt`; not yet wired into middleware)
- httpx 0.25.2 (async) - Outgoing HTTP: webhook delivery (`app/services/event_delivery_service.py`), agent bridge polling (`app/bridge/agent_bridge.py`)
- websockets 12.0 - WebSocket support; endpoint at `GET /v1/ws` (`app/api/routes_websocket.py`)
- structlog 23.2.0 - JSON logging in production, console renderer in debug; configured in `app/logging.py`
- prometheus-client 0.19.0 - Declared dependency; not yet actively instrumented in route handlers
- zvec 0.1.0 - Local vector storage at `./data/zvec` path; configured via `Settings.zvec_path` and `Settings.embedding_model`
- redis 5.0.1 - Async Redis client (`redis.asyncio`) for token caching and blacklisting (`app/auth/redis_cache.py`)
- pytest 7.4.3
- pytest-asyncio 0.21.1
- pytest-cov 4.1.0
- black 23.11.0 - Code formatting, line length 88, target Python 3.11
- isort 5.12.0 - Import sorting (`profile = "black"`)
- flake8 6.1.0 - Linting
- mypy 1.7.1 - Static type checking (`disallow_untyped_defs = true`)
## Key Dependencies
- `fastapi==0.104.1` - Entire API surface lives here; version pinned hard
- `pydantic==2.4.2` - v2 API (not v1 compatible); all models use v2 patterns
- `pyjwt[crypto]==2.8.0` - Auth token signing; `jwt_secret_key` must be set in production
- `casbin==1.25.0` - RBAC policies live in `app/auth/rbac/policies/` as `.conf`/`.csv` files
- `sqlalchemy==2.0.23` - Declared but DB layer uses a custom raw-SQL `Database` wrapper, not SQLAlchemy ORM sessions
- `alembic==1.12.1` - Declared; migrations not actively used - tables created via DDL in `app/main.py` lifespan startup
- `redis==5.0.1` - Optional: Redis is gracefully degraded if unavailable
- `zvec==0.1.0` - Local vector store; path created at startup (`./data/zvec`)
- `python-multipart==0.0.6` - Required for FastAPI file upload support (`routes_artifacts.py`)
- `python-dotenv==1.0.0` - `.env` file loading for local dev
- `click==8.1.7` - CLI entrypoints in `scripts/`
- `httpx==0.25.2` - Used in `AgentBridge` client and webhook delivery
## Configuration
- All config in `app/config.py` via `pydantic-settings` `Settings` class
- Environment variable prefix: `AGENTHUB_`
- Key variables required for production:
- `pyproject.toml` - Poetry build config, black/isort/mypy/pytest settings
- `Dockerfile` - `python:3.11-slim` base, installs `requirements.txt`, exposes 7788
- `docker-compose.yml` - Two services: `agenthub` (port 7788) + `redis:7-alpine` (port 6379)
## Platform Requirements
- Python 3.11+
- Redis (optional, graceful degradation)
- Docker + Docker Compose (for containerized dev)
- Run command: `uvicorn app.main:app --host 0.0.0.0 --port 7788 --reload`
- Deployed as systemd service on VPS at `hub.brunhilde.cloud`
- Docker image via `docker-compose.yml`
- Health check endpoint: `GET /v1/health`
- Optional cloud DB via Turso (libSQL) - falls back to local SQLite if not configured
- Port: 7788
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

## Naming Patterns
- Route modules: `routes_{noun}.py` - e.g., `routes_agents.py`, `routes_tasks.py`, `routes_p1.py`
- Service modules: `{noun}_service.py` - e.g., `agent_service.py`, `task_service.py`
- Repository modules: `{noun}.py` inside `database/repositories/` - e.g., `agents.py`, `tasks.py`
- Model modules: `{noun}.py` inside `models/` - e.g., `agents.py`, `tasks.py`, `base.py`
- `snake_case` throughout - both sync and async functions
- Route handler names match their HTTP semantic: `create_task`, `get_agent`, `send_heartbeat`, `go_offline`
- Private/internal helpers prefixed with underscore: `_row_to_model`, `_model_to_dict`, `_monitor_loop`, `_auth`, `_sender`
- Service-level dependency factories named `get_{noun}_service()` in route files
- `PascalCase` for all classes
- Service classes: `{Noun}Service` - e.g., `AgentService`, `TaskService`, `HeartbeatService`
- Repository classes: `{Noun}Repository` - e.g., `AgentRepository`, `TaskRepository`
- Model classes: descriptive noun or noun+verb: `AgentCreate`, `AgentUpdate`, `AgentHeartbeat`, `TaskClaim`, `TaskComplete`
- Response models: `{Noun}Response` or `{Noun}ListResponse` - e.g., `AgentRegistrationResponse`, `TaskResponse`
- Mixin classes: `{Noun}Mixin` - e.g., `TimestampMixin`, `IDMixin`, `MetadataMixin`
- Exception classes: `{Noun}Error` extending `HTTPException` - e.g., `AgentNotFoundError`, `TaskConflictError`
- `snake_case` throughout
- Boolean variables: prefixed with `_running`, `_use_turso`, `is_active`
- Private module-level state uses underscore prefix: `_rate_limits`, `_RATE_LIMIT_WINDOW`, `_RATE_LIMIT_MAX`
- `SCREAMING_SNAKE_CASE` for module-level constants: `TURSO_AVAILABLE`, `_RATE_LIMIT_WINDOW`, `_RATE_LIMIT_MAX`
- Class name in `PascalCase`, values in `SCREAMING_SNAKE_CASE`
- String enums inherit `(str, Enum)` so values serialize as strings automatically
- Int enums inherit `(IntEnum)` for priority levels
- Examples: `AgentStatus`, `TaskStatus`, `TaskPriority`, `TaskType`
## Code Style
- Tool: `black` with `line-length = 88`
- Target: Python 3.11
- Config in `pyproject.toml`: `[tool.black]`
- Tool: `isort` with `profile = "black"`, `line_length = 88`
- Config in `pyproject.toml`: `[tool.isort]`
- Tool: `mypy` targeting Python 3.11
- `warn_return_any = true`, `warn_unused_configs = true`, `disallow_untyped_defs = true`
- All functions have type annotations on parameters and return values
- Tool: `flake8` (declared in dev deps, no custom config file found)
## Import Organization
- Route files use `..` (two levels up from `api/`)
- Repository files use `...` (three levels up from `database/repositories/`)
## Module-Level Logger Pattern
## Error Handling
- Validation errors: `raise ValueError(f"...")` for business rule violations
- Boolean returns for update/delete operations that can legitimately fail: `return False` on failure after logging
- `RequestValidationError` - returns 422 with structured field errors
- `HTTPException` / `StarletteHTTPException` - returns structured JSON with `error_code`
- `Exception` (catch-all) - returns 500, hides details in production (`settings.debug` gate)
- `AgentNotFoundError(agent_id)`, `TaskNotFoundError(task_id)` - 404
- `AgentBusyError(agent_id)`, `TaskConflictError(detail)` - 409
- `APIKeyValidationError(detail)` - 401
- `RateLimitError(detail)` - 429
## Logging
- `agent_registration_started`, `agent_registered_successfully`
- `task_creation_failed`, `entity_created`, `entity_updated`
- `request_started`, `request_completed`, `request_failed`
- `debug` - low-frequency reads, stat queries, verification passes
- `info` - state transitions, registration, startup/shutdown events
- `warning` - not-found lookups, auth failures, duplicate attempts, degraded state
- `error` - unexpected exceptions, DB failures, auth errors
## Pydantic Model Design
- `populate_by_name=True`
- `validate_assignment=True`
- `use_enum_values=True`
- `extra='forbid'` - no extra fields allowed
- `by_alias=True` for serialization
- `IDMixin` - adds `id: str` with UUID factory
- `TimestampMixin` - adds `created_at`, `updated_at`
- `MetadataMixin` - adds `labels: Dict[str, str]`, `metadata: Dict[str, Any]`
- Domain model example: `class Agent(IDMixin, TimestampMixin, MetadataMixin)`
- `AgentCreate` - required fields only, strict validation
- `AgentUpdate` - all fields `Optional`, same validators
- `Agent` - full domain model with ID + timestamps
## Service Layer Design
## Repository Layer Design
- `_row_to_model(row: Dict[str, Any]) -> T` - DB row to Pydantic model
- `_model_to_dict(model: T) -> Dict[str, Any]` - Pydantic model to DB dict
## Authentication Type Aliases
## Comments
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

## Pattern Overview
- Strict layer separation: routes -> services -> repositories -> database
- Repository pattern provides a typed ORM-like abstraction over raw SQLite/Turso SQL
- Services hold all business logic; routes only parse HTTP input and delegate
- Dependency injection via FastAPI `Depends()` - service instances are created per request, not shared singletons
- No async ORM - all database access is synchronous with thread-local connections
## Layers
- Purpose: Parse and validate HTTP input, call services, format responses
- Location: `app/api/`
- Contains: FastAPI `APIRouter` instances, Pydantic request/response models inline or imported from `app/models/`
- Depends on: `app/services/`, `app/auth/`, `app/database/connection.py`
- Used by: HTTP clients, `app/bridge/agent_bridge.py`, WebSocket clients
- Purpose: All domain logic, orchestration between repositories, cross-entity operations
- Location: `app/services/`
- Contains: `TaskService`, `AgentService`, `HeartbeatService`, `CapabilityMatcher`, `DiscoveryService`, `RemoteAgentService`, `HatchetService`, `WorkflowCoordinator`
- Depends on: `app/database/repositories/`, `app/models/`
- Used by: `app/api/` route modules
- Purpose: Typed CRUD over individual database tables; isolates SQL from business logic
- Location: `app/database/repositories/`
- Contains: `BaseRepository` (generic ABC), `AgentRepository`, `TaskRepository`, `ACNNodeRepository`, `RemoteAgentMappingRepository`
- Depends on: `app/database/connection.py` (`Database` class)
- Used by: `app/services/`
- Purpose: Connection management, query execution, SQLite/Turso abstraction
- Location: `app/database/connection.py`
- Contains: `Database` class with thread-local connections, `get_database()` singleton factory
- Depends on: `sqlite3` (stdlib), `libsql_experimental` (optional Turso)
- Used by: `app/database/repositories/`, routes that bypass repositories for direct SQL (P1/P2 routes)
- Purpose: JWT verification, API key validation, RBAC enforcement
- Location: `app/auth/`
- Contains: `jwt_auth.py`, `api_keys.py`, `dependencies.py`, `redis_cache.py`, `rbac/enforcer.py`, `rbac/policies.py`
- Depends on: `app/database/connection.py`, Redis (optional)
- Used by: All `app/api/` route modules via FastAPI `Depends()`
- Purpose: Lightweight HTTP client for remote agents to connect to the hub
- Location: `app/bridge/agent_bridge.py`
- Contains: `AgentBridge` class - handles registration, heartbeat loop, task polling
- Depends on: `httpx` (async HTTP)
- Used by: External agents running `scripts/run_bridge.py`
## Data Flow
- All state is persisted to SQLite/Turso - no in-memory state stores for core entities
- WebSocket connections held in-memory dict `_connections: Dict[str, WebSocket]` in `routes_websocket.py` (process-local)
- Rate limit sliding windows held in-memory `_rate_limits: Dict[str, List[float]]` in `routes_p2.py` (process-local)
- ACN invite codes held in-memory `_invite_store: Dict` in `routes_acn.py` (process-local, single-use by design)
- Redis used optionally for JWT token blacklisting; system degrades gracefully without it
## Key Abstractions
- Purpose: Generic typed CRUD base for all database entities
- Pattern: Abstract class `BaseRepository[T]` with `_row_to_model()` and `_model_to_dict()` as abstract methods; concrete classes implement these converters
- Methods provided: `create`, `get_by_id`, `update`, `delete`, `list_all`, `find_by`, `find_one_by`, `count`, `exists`, `bulk_create`, `bulk_update`, `execute_custom_query`
- Purpose: Unified SQL interface that works with both local SQLite and Turso (libsql cloud)
- Pattern: Thread-local connections via `threading.local()`; named param syntax (`:param`) auto-converted to positional `?` for Turso compatibility
- Key methods: `execute`, `fetch_one`, `fetch_all`, `transaction()` (context manager), `execute_many`
- Purpose: Composable model pieces - `IDMixin` (UUID id), `TimestampMixin` (created_at, updated_at), `MetadataMixin` (labels, metadata)
- Pattern: Multiple inheritance - e.g., `Agent(IDMixin, TimestampMixin, MetadataMixin)`
- Config: `extra='forbid'`, `use_enum_values=True`, `validate_assignment=True`
- Purpose: Scores available agents against task capability requirements
- Pattern: Returns `CapabilityMatch` dataclass with `match_score`, `matched_capabilities`, `missing_capabilities`, `confidence_score`
- Used by: `TaskService` during auto-assignment at task creation time
- Purpose: Client-side bridge that connects a remote agent process to the hub via HTTP
- Pattern: Async loop with configurable `heartbeat_interval` and `task_poll_interval`; registers handler via `set_task_handler(fn)` callback
## Entry Points
- Location: `app/main.py` - `app` variable (FastAPI instance)
- Triggers: `uvicorn app.main:app --host 0.0.0.0 --port 7788`
- Responsibilities: Router assembly, CORS setup, error handler setup, database table bootstrap in `lifespan()` context manager
- Location: `app/main.py` - `run_server()` function
- Triggers: `python -m app.main` or `uvicorn app.main:app --reload`
- Location: `scripts/run_bridge.py`
- Triggers: Direct script execution by remote agent process
- Location: `Dockerfile`, `docker-compose.yml` at project root
## Error Handling
- Routes raise `HTTPException` with appropriate status codes directly
- Services raise `ValueError` for business rule violations (e.g., duplicate names)
- `app/middleware.py` contains `RequestTimingMiddleware` (logs every request/response) and global exception handlers set via `setup_error_handlers(app)`
- Database errors propagate up from repositories with structured log entries before re-raising
- Auth failures raise `HTTPException(401)` from dependency functions; these short-circuit before routes execute
## Cross-Cutting Concerns
<!-- GSD:architecture-end -->

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd:quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd:debug` for investigation and bug fixing
- `/gsd:execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->

<!-- GSD:profile-start -->
## Developer Profile

> Profile not yet configured. Run `/gsd:profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
