# Codebase Structure

**Analysis Date:** 2026-04-07

## Directory Layout

```
OpenHub/
├── app/                          # Main application package
│   ├── api/                      # FastAPI route modules (one file per domain)
│   │   ├── routes_agents.py      # Agent registration, heartbeat, discovery
│   │   ├── routes_tasks.py       # Task lifecycle (create, claim, start, complete, fail)
│   │   ├── routes_workflows.py   # Hatchet workflow orchestration (legacy)
│   │   ├── routes_workflow.py    # Workflow engine - multi-step DAG (active)
│   │   ├── routes_coordination.py # Smart agent-workflow coordination
│   │   ├── routes_acn.py         # ACN federation - node join, invite, remote agents
│   │   ├── routes_messaging.py   # Agent-to-agent DMs and thread conversations
│   │   ├── routes_memory.py      # Shared memory / context store
│   │   ├── routes_artifacts.py   # File artifact upload and retrieval
│   │   ├── routes_websocket.py   # WebSocket real-time event push
│   │   ├── routes_p1.py          # Locks, tracing, cost tracking (3 routers in 1 file)
│   │   ├── routes_p2.py          # MCP tools, agent templates, DLQ (3 routers in 1 file)
│   │   ├── routes_auth.py        # JWT login, refresh, API key management
│   │   ├── routes_admin.py       # Admin stats, cleanup
│   │   └── routes_health.py      # Health check endpoint
│   ├── auth/                     # Authentication and authorization
│   │   ├── jwt_auth.py           # JWT token creation and verification
│   │   ├── api_keys.py           # API key generation, hashing, validation
│   │   ├── dependencies.py       # FastAPI auth dependency functions (CurrentAgent, CurrentAdmin)
│   │   ├── api_dependencies.py   # Additional API auth dependencies
│   │   ├── redis_cache.py        # Redis token blacklist cache (optional)
│   │   ├── models.py             # Auth Pydantic models (TokenData, AuthenticatedAgent)
│   │   └── rbac/                 # Casbin role-based access control
│   │       ├── enforcer.py       # Casbin enforcer setup
│   │       ├── policies.py       # Policy definitions
│   │       └── models.py         # RBAC model definitions
│   ├── bridge/                   # Agent bridge client SDK
│   │   └── agent_bridge.py       # AgentBridge class - remote agent HTTP client
│   ├── database/                 # Database layer
│   │   ├── connection.py         # Database class, get_database() singleton
│   │   ├── migrations.py         # Migration system
│   │   └── repositories/         # Data access objects (one per table group)
│   │       ├── base.py           # BaseRepository[T] abstract class
│   │       ├── agents.py         # AgentRepository
│   │       ├── tasks.py          # TaskRepository
│   │       ├── acn_nodes.py      # ACNNodeRepository
│   │       └── remote_agent_mappings.py  # RemoteAgentMappingRepository
│   ├── models/                   # Pydantic domain models
│   │   ├── base.py               # BaseModel, IDMixin, TimestampMixin, MetadataMixin
│   │   ├── agents.py             # Agent, AgentCreate, AgentUpdate, AgentHeartbeat, AgentStatus
│   │   ├── tasks.py              # Task, TaskCreate, TaskStatus, TaskPriority, TaskType
│   │   ├── acn.py                # ACNNode, RemoteAgentRegister, RemoteAgentMapping
│   │   ├── events.py             # Event models
│   │   ├── responses.py          # Generic response wrappers
│   │   └── __init__.py           # Re-exports of all models
│   ├── services/                 # Business logic services
│   │   ├── agent_service.py      # Agent registration and management
│   │   ├── task_service.py       # Task lifecycle + auto-assignment orchestration
│   │   ├── capability_matcher.py # Agent-capability scoring (CapabilityMatch dataclass)
│   │   ├── heartbeat_service.py  # Heartbeat monitoring (HeartbeatService, AgentStatusManager)
│   │   ├── discovery_service.py  # Agent discovery and monitoring (DiscoveryService)
│   │   ├── remote_agent_service.py # ACN federation logic (RemoteAgentService)
│   │   ├── hatchet_service.py    # Hatchet workflow integration
│   │   ├── workflow_coordinator.py # Agent-workflow coordination
│   │   └── event_delivery_service.py # Event delivery to agents
│   ├── static/                   # Static assets served by FastAPI
│   │   └── admin.html            # Admin dashboard SPA (single HTML file)
│   ├── config.py                 # Settings (pydantic_settings, AGENTHUB_ prefix)
│   ├── logging.py                # structlog setup, get_logger()
│   ├── middleware.py             # RequestTimingMiddleware, setup_error_handlers()
│   ├── dependencies.py           # App-level FastAPI dependencies
│   └── main.py                   # FastAPI app, lifespan, router assembly
├── database/                     # SQL migration files (not the Python package)
│   └── migrations/               # Raw SQL: 001_initial.sql, 002_api_keys.sql, 003_acn_federation.sql
├── data/                         # Runtime data (not committed)
│   ├── state/                    # SQLite database file (agenthub.db)
│   ├── artifacts/                # Uploaded agent artifacts
│   └── zvec/                     # Vector store data
├── docs/                         # Specification and planning documents
├── AGENTS_HUB/                   # Agent prompt templates and generic AI instructions
│   ├── Promt/                    # Agent-specific prompt files
│   └── ai_generic_instructions/  # Reusable instruction documents
├── scripts/                      # Utility scripts
│   ├── run_bridge.py             # Launch script for AgentBridge client
│   └── dev_start.sh              # Development server startup script
├── logs/                         # Application log files (runtime)
├── .planning/                    # GSD planning directory
│   └── codebase/                 # Codebase analysis documents
├── Dockerfile                    # Container build
├── docker-compose.yml            # Docker Compose config
├── pyproject.toml                # Python project metadata and tool config
├── requirements.txt              # Python dependencies
├── .env                          # Local environment variables (not committed)
└── .env.example                  # Environment variable template
```

## Directory Purposes

**`app/api/`:**
- Purpose: FastAPI route handlers - one file per domain/feature area
- Contains: `APIRouter` instances, inline Pydantic models for request bodies (some newer modules define models inline rather than in `app/models/`)
- Key files: `routes_agents.py` (agent lifecycle), `routes_tasks.py` (task lifecycle), `routes_acn.py` (federation)

**`app/auth/`:**
- Purpose: All authentication and authorization - JWT, API keys, RBAC
- Contains: FastAPI dependency functions consumed by route handlers
- Key pattern: `CurrentAgent = Annotated[AuthenticatedAgent, Depends(get_current_agent)]` in `dependencies.py`

**`app/bridge/`:**
- Purpose: Client SDK for remote agents that need to connect to the hub from another machine/process
- Contains: Single `AgentBridge` class used by external agent processes
- Not a server-side concern - no routes or services import from here

**`app/database/repositories/`:**
- Purpose: One repository class per primary table or table group
- Contains: All SQL queries for that table; business logic stays in services
- Key file: `base.py` - provides generic CRUD, all concrete repos inherit from it

**`app/models/`:**
- Purpose: Shared Pydantic models for database entities and API contracts
- Contains: Domain models with enums, create/update variants, response wrappers
- Key file: `base.py` - mixins composed into domain models

**`app/services/`:**
- Purpose: Business logic, cross-entity orchestration, external integrations
- Contains: Classes that receive `Database` in constructor and use repositories internally
- Key file: `task_service.py` - most complex service; coordinates task creation, auto-assignment, lease management, retry logic

**`app/static/`:**
- Purpose: Served at `GET /admin` - single-file admin dashboard
- Contains: `admin.html` - self-contained HTML/CSS/JS SPA

**`data/`:**
- Purpose: Runtime-generated data; not part of the codebase
- Generated: Yes - created at startup by `lifespan()` in `app/main.py`
- Committed: No (in `.gitignore`)

**`database/migrations/`:**
- Purpose: Reference SQL scripts documenting the schema evolution; actual tables are created inline in `app/main.py` lifespan via `CREATE TABLE IF NOT EXISTS`
- Not executed automatically at runtime - the inline DDL in `main.py` is the authoritative schema bootstrap

**`AGENTS_HUB/`:**
- Purpose: System prompt templates and instruction documents for AI agents using the hub
- Not imported by application code

## Key File Locations

**Entry Points:**
- `app/main.py`: ASGI application object (`app`), lifespan startup, all router includes
- `scripts/run_bridge.py`: AgentBridge launcher for remote agent processes
- `scripts/dev_start.sh`: Development startup helper

**Configuration:**
- `app/config.py`: All settings with `AGENTHUB_` env prefix
- `.env.example`: Canonical list of required environment variables
- `pyproject.toml`: Tool configuration (linting, formatting, etc.)

**Core Business Logic:**
- `app/services/task_service.py`: Task lifecycle including auto-assignment, lease management, retry
- `app/services/capability_matcher.py`: Agent scoring algorithm
- `app/services/remote_agent_service.py`: ACN federation node and agent management
- `app/database/repositories/base.py`: Generic repository base (all CRUD patterns)
- `app/database/connection.py`: `Database` class and `get_database()` factory

**Auth:**
- `app/auth/dependencies.py`: `CurrentAgent`, `CurrentAdmin` FastAPI dependency annotations
- `app/auth/api_keys.py`: `APIKeyManager` - used directly in routes that don't use JWT
- `app/auth/jwt_auth.py`: `create_access_token`, `verify_token`

**Real-time:**
- `app/api/routes_websocket.py`: WebSocket endpoint + `push_event()` / `broadcast_event()` helpers used by other route modules

## Naming Conventions

**Files:**
- Route modules: `routes_{domain}.py` (e.g., `routes_agents.py`, `routes_tasks.py`)
- Services: `{domain}_service.py` (e.g., `task_service.py`, `agent_service.py`)
- Repositories: `{table_name_plural}.py` (e.g., `agents.py`, `tasks.py`, `acn_nodes.py`)
- Models: `{domain}.py` matching the primary entity (e.g., `agents.py`, `tasks.py`)

**Classes:**
- Services: `{Domain}Service` (e.g., `TaskService`, `AgentService`)
- Repositories: `{Entity}Repository` (e.g., `AgentRepository`, `TaskRepository`)
- Models: Entity name as-is (e.g., `Agent`, `Task`); create variants: `{Entity}Create`; update variants: `{Entity}Update`

**Logging events:** `snake_case` string literals as first positional arg to logger calls (e.g., `logger.info("task_created_successfully", task_id=...)`)

**Database tables:** `snake_case` plurals matching entity names (e.g., `agents`, `tasks`, `acn_nodes`, `shared_memory`, `resource_locks`)

**Environment variables:** `AGENTHUB_{SETTING_NAME}` in UPPER_SNAKE_CASE (e.g., `AGENTHUB_DB_PATH`, `AGENTHUB_JWT_SECRET_KEY`)

**API key prefix:** `oh_` for agent API keys issued by ACN join flow

## Where to Add New Code

**New API endpoint group (new domain):**
- Add `app/api/routes_{domain}.py` with `router = APIRouter(prefix="/v1/{domain}", tags=["{domain}"])`
- Import and include in `app/main.py`: `app.include_router(router)`
- Add `CREATE TABLE IF NOT EXISTS {domain}` DDL in the `tables` list in `app/main.py` lifespan

**New service:**
- Add `app/services/{domain}_service.py`
- Class accepts `database: Database` in `__init__`; creates repository instances internally
- Instantiate in route module via a `get_{domain}_service()` factory function returning `{Domain}Service(get_database())`

**New repository:**
- Add `app/database/repositories/{table_name}.py`
- Inherit from `BaseRepository[ModelType]`
- Implement `_row_to_model(row)` and `_model_to_dict(model)` abstractmethods
- Add JSON field handling via `_serialize_json_field()` / `_deserialize_json_field()` for dict/list columns

**New Pydantic model:**
- Add to `app/models/{domain}.py` or create new file if domain is new
- Inherit from `BaseModel` for request/response models
- Compose `IDMixin + TimestampMixin + MetadataMixin` for database-backed entities
- Export from `app/models/__init__.py`

**New auth-protected endpoint:**
- Use `X-API-Key` pattern for agent-facing endpoints (most common):
  ```python
  def _require_api_key(x_api_key: str = Header(None, alias="X-API-Key"), database: Database = Depends(get_database)) -> Dict:
      info = APIKeyManager(database).validate_api_key(x_api_key)
      if not info: raise HTTPException(status_code=401, detail="Invalid API key")
      return info
  ```
- Use `CurrentAgent`/`CurrentAdmin` from `app/auth/dependencies.py` for JWT-protected routes

**Utilities:**
- Shared helpers: `app/logging.py` (get_logger), `app/config.py` (get_settings)
- No general-purpose utils module exists - keep helpers close to their domain

## Special Directories

**`.planning/`:**
- Purpose: GSD planning documents for orchestrated development
- Generated: Yes (by GSD tooling)
- Committed: Yes

**`data/`:**
- Purpose: Runtime state - SQLite DB, uploaded artifacts, vector data
- Generated: Yes (created at startup)
- Committed: No

**`AGENTS_HUB/`:**
- Purpose: Agent system prompts and AI instruction documents for humans configuring agents
- Committed: Yes (reference material)

---

*Structure analysis: 2026-04-07*
