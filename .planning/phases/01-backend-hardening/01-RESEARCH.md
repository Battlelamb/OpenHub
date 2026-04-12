# Phase 1: Backend Hardening - Research

**Researched:** 2026-04-07
**Domain:** FastAPI backend security hardening, auth consolidation, schema migration, structured logging, rate limiting, observability
**Confidence:** HIGH (grounded in direct codebase audit + verified patterns)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Use RFC 7807 Problem Details as the standard error response shape across all endpoints ({type, title, status, detail, instance})
- **D-02:** Validation errors include field-level detail - an 'errors' array with field name + message per invalid field
- **D-03:** Rate-limited responses include Retry-After header plus remaining/limit in response headers
- **D-04:** Internal server errors (500) never expose stack traces in the response body - generic message in response, full trace in server logs only
- **D-05:** Structured JSON logging via structlog with {event, error_type, status, path, trace_id} - machine-parseable for monitoring
- **D-06:** Replace hardcoded admin/admin123 with AGENTHUB_ADMIN_USER + AGENTHUB_ADMIN_PASSWORD environment variables
- **D-07:** Server refuses to start if admin env vars are not set - no defaults, not even in development mode
- **D-08:** Delete app/dependencies.py entirely - all routes must use real auth from app/auth/dependencies.py
- **D-09:** Consolidate duplicate _auth/_sender helpers into FastAPI middleware - auth runs before all routes, no per-route imports needed
- **D-10:** Use Alembic for schema migrations with full SQLAlchemy ORM models - auto-generate migrations from model changes
- **D-11:** Move all 125 lines of inline DDL from main.py into Alembic initial migration revision
- **D-12:** Requires defining SQLAlchemy models for all 16 existing tables
- **D-13:** Keep current fail-closed behavior for Redis blacklist checks - when Redis is down, all auth is blocked

### Claude's Discretion

- Specific implementation of Prometheus metrics endpoint layout
- Exact structlog configuration and processors
- How to handle the decode_token_without_verification rename
- ACN admin key and invite code persistence approach (within security constraints)
- API key validation optimization (replacing full table scan)

### Deferred Ideas (OUT OF SCOPE)

None - discussion stayed within phase scope.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| HARD-01 | Auth stub in app/dependencies.py removed - all routes use real JWT/API key auth from app/auth/ | Stub confirmed at app/dependencies.py:41-59; only app/api/routes_health.py imports from it (RequestIdDep) |
| HARD-02 | Hardcoded admin credentials (admin/admin123) replaced with env-configurable | Hardcoded at routes_auth.py:246; Settings class already has env var infrastructure via pydantic-settings |
| HARD-03 | Capabilities stored as proper JSON (not Python str()) | Bug confirmed at routes_auth.py:88-90; str() not json.dumps(); two-line fix |
| HARD-04 | Heartbeat monitor wired into app lifespan and actually runs | HeartbeatService.start_monitoring() confirmed never called from main.py lifespan |
| HARD-05 | CORS defaults locked down (no wildcard in production) | Wildcard confirmed in config.py:50-52; must set safe default + env override |
| HARD-06 | Schema DDL consolidated from inline main.py into versioned migration files | 16 tables in main.py lifespan; alembic 1.12.1 + sqlalchemy 2.0.23 already installed in .venv |
| HARD-07 | OpenAPI /docs endpoint enabled and accessible | docs_url=None, redoc_url=None confirmed in main.py:197-198; one-line fix |
| HARD-08 | Structured error responses with consistent error format | Current format uses {success, error, error_code, request_id}; must migrate to RFC 7807 |
| HARD-09 | datetime.utcnow() calls unified to timezone-aware datetime handling | 61 occurrences confirmed across app/; correct pattern (timezone.utc) already used in routes_acn.py |
| HARD-10 | Duplicate auth helper modules consolidated | _auth/_sender defined in routes_p1.py, routes_p2.py, routes_artifacts.py, routes_memory.py, routes_websocket.py |
| OSS-02 | API documentation via exposed OpenAPI /docs with endpoint descriptions | Covered by HARD-07 + ensuring route docstrings exist |
| PROD-01 | slowapi rate limiting wired into middleware | slowapi 0.1.9 installed in .venv; currently unused (in-memory rate limiter in routes_p2.py only) |
| PROD-02 | prometheus-client metrics endpoint | prometheus-client 0.19.0 installed in .venv; currently undeclared in routes |
| PROD-04 | Production logging configuration with structured JSON output | structlog 23.2.0 installed; app/logging.py already outputs JSON in non-debug mode; needs field enhancement |
</phase_requirements>

---

## Summary

Phase 1 is a pure hardening pass on an existing, functionally mature FastAPI backend. There are no new features to build - only bugs to fix and gaps to fill. The backend has two parallel auth systems: the real one (`app/auth/dependencies.py`) and an abandoned stub (`app/dependencies.py`) that accepts any 8-character string as a valid API key. Only one route (`routes_health.py`) imports from the stub, and only for a utility (`RequestIdDep`), not for auth. The stub itself must be deleted and that import migrated.

The three highest-impact fixes are: (1) the auth consolidation and stub deletion which makes the auth surface coherent, (2) the capabilities JSON bug (`str()` instead of `json.dumps()`) which silently breaks all capability-based task routing, and (3) the heartbeat monitor never being started in the lifespan, which means agents never go offline automatically. These three are interdependent correctness bugs that must land before any test is written.

The schema migration work is substantial: 16 tables defined inline in `main.py` lifespan must become SQLAlchemy ORM models and Alembic migration revisions. The tools are already installed (`alembic 1.12.1`, `sqlalchemy 2.0.23` confirmed present in `.venv`). Error response format migration from the current `{success, error, error_code, request_id}` envelope to RFC 7807 `{type, title, status, detail, instance}` touches every exception handler in `app/middleware.py` plus all custom `HTTPException` subclasses.

**Primary recommendation:** Execute in correctness order - auth stub + credentials first, capabilities fix + heartbeat second, then the structural work (migrations, error format, logging, rate limiting, metrics). This order ensures each fix is testable as it lands.

---

## Standard Stack

### Already Installed (confirmed in .venv)

| Library | Version | Purpose | Status |
|---------|---------|---------|--------|
| alembic | 1.12.1 | Schema migration framework | Installed, not used |
| sqlalchemy | 2.0.23 | ORM models for Alembic autogenerate | Installed, not used |
| slowapi | 0.1.9 | Rate limiting middleware | Installed, not wired |
| prometheus-client | 0.19.0 | Metrics endpoint | Installed, not routed |
| structlog | 23.2.0 | Structured JSON logging | Installed, partially configured |
| pytest | 7.4.3 | Test runner | Installed, no tests/ dir yet |
| pytest-asyncio | 0.21.1 | Async test support | Installed |

**No new packages required for this phase.** All tools are already declared in `requirements.txt` and present in `.venv`. The phase is configuration and code changes only.

### Verification

```bash
# All confirmed importable from .venv:
/home/omer/projects/OpenHub/.venv/bin/python -c "import alembic, sqlalchemy, slowapi, prometheus_client, structlog, pytest"
```

---

## Architecture Patterns

### Current State (what must change)

**Auth layer today:**
- Real auth: `app/auth/dependencies.py` - JWT + API key validation, used by routes_agents, routes_tasks, routes_workflows, routes_coordination, routes_admin, routes_auth
- Stub: `app/dependencies.py:41-59` - accepts any 8-char string, imported ONLY by `routes_health.py` for `RequestIdDep`
- Per-route _auth: `routes_p1.py`, `routes_p2.py`, `routes_artifacts.py`, `routes_memory.py`, `routes_websocket.py` each define local `_auth(x_api_key)` + `_sender(key_info, db)` helpers calling `APIKeyManager.validate_api_key()`

**The _auth pattern (all five files use this identical structure):**
```python
# app/api/routes_p1.py:22-36 (representative - same in p2, artifacts, memory, websocket)
def _auth(x_api_key: str = Header(None, alias="X-API-Key"),
          database: Database = Depends(get_database)) -> Dict:
    info = APIKeyManager(database).validate_api_key(x_api_key)
    if not info:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return info

def _sender(ki: Dict, db: Database) -> str:
    name = ki.get("name", "")
    if name.startswith("acn-agent-"):
        row = db.fetch_one("SELECT local_agent_id FROM remote_agent_mappings ...")
        return row["local_agent_id"] if row else "unknown"
    return "unknown"
```

**Target state (D-09): shared dependency in app/auth/api_key_deps.py:**
```python
# New file: app/auth/api_key_deps.py
from fastapi import Header, Depends, HTTPException, status
from ..database.connection import get_database, Database
from .api_keys import APIKeyManager

def require_api_key(
    x_api_key: str = Header(None, alias="X-API-Key"),
    database: Database = Depends(get_database)
) -> Dict:
    info = APIKeyManager(database).validate_api_key(x_api_key)
    if not info:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                           detail="Invalid or missing API key")
    return info

def resolve_agent_id(key_info: Dict, db: Database) -> str:
    """Resolve agent ID from API key info."""
    name = key_info.get("name", "")
    if name.startswith("acn-agent-"):
        row = db.fetch_one(
            "SELECT local_agent_id FROM remote_agent_mappings WHERE local_agent_id = :id",
            {"id": key_info.get("key_id")}
        )
        return row["local_agent_id"] if row else key_info.get("key_id", "unknown")
    return key_info.get("key_id", "unknown")

# Type alias for dependency injection
ApiKeyAuth = Annotated[Dict, Depends(require_api_key)]
```

### RequestIdDep Migration (HARD-01 prerequisite)

`routes_health.py:11` imports `RequestIdDep` from the stub. This utility has nothing to do with auth. The fix is to move `get_request_id` from `app/dependencies.py` into `app/middleware.py` (it already uses request IDs there) or into a dedicated `app/utils/request_id.py`. After that, `app/dependencies.py` can be deleted.

### RFC 7807 Error Format (D-01)

Current error envelope in `app/middleware.py`:
```json
{"success": false, "error": "...", "error_code": "CONFLICT", "request_id": "..."}
```

Target RFC 7807 envelope:
```json
{
  "type": "https://openhub.dev/errors/conflict",
  "title": "Conflict",
  "status": 409,
  "detail": "Agent name already exists",
  "instance": "/v1/agents/register",
  "trace_id": "request-uuid-here"
}
```

**Key implementation points:**
- The `type` field should be a URI. For an open source self-hosted tool, use a relative path like `/errors/{slug}` or a documentation URL. Using `about:blank` is valid per RFC 7807 when no specific type URI exists.
- Validation errors (D-02) extend the base with an `errors` array:
  ```json
  {
    "type": "about:blank",
    "title": "Unprocessable Entity",
    "status": 422,
    "detail": "Request validation failed",
    "instance": "/v1/agents/register",
    "errors": [
      {"field": "agent_name", "message": "String should have at least 3 characters"}
    ]
  }
  ```
- `app/middleware.py` contains ALL exception handlers: `validation_exception_handler`, `http_exception_handler_custom`, `general_exception_handler`. All three must be updated.
- `RequestTimingMiddleware.dispatch` also has an inline 500 handler - this must also be updated.

### Alembic + SQLAlchemy ORM Migration (D-10, D-11, D-12, HARD-06)

**The 16 tables in main.py lifespan:**
agents, tasks, acn_nodes, remote_agent_mappings, api_keys, pending_applications, messages, threads, shared_memory, workflows, artifacts, resource_locks, trace_events, cost_tracking, shared_tools, agent_templates.

**Alembic setup steps:**
```bash
cd /home/omer/projects/OpenHub
.venv/bin/alembic init alembic
```

This creates: `alembic.ini`, `alembic/env.py`, `alembic/versions/`.

**alembic.ini key config:**
```ini
sqlalchemy.url = sqlite:///%(here)s/data/state/agenthub.db
```

However, since the DB path comes from `AGENTHUB_DB_PATH` env var, `env.py` must read from `Settings`:
```python
# alembic/env.py
from app.config import get_settings
settings = get_settings()
config.set_main_option("sqlalchemy.url", f"sqlite:///{settings.db_path}")
```

**SQLAlchemy ORM models (new file: app/database/models.py):**
```python
from sqlalchemy import Column, String, Integer, Float, Boolean, Text, DateTime
from sqlalchemy.orm import DeclarativeBase
from datetime import datetime, timezone

class Base(DeclarativeBase):
    pass

class AgentModel(Base):
    __tablename__ = "agents"
    id = Column(String, primary_key=True)
    agent_name = Column(String, nullable=False, unique=True)
    description = Column(Text)
    capabilities = Column(Text, default="[]")   # JSON string
    status = Column(String, default="offline")
    last_heartbeat = Column(DateTime)
    current_task = Column(String)
    labels = Column(Text, default="{}")
    metadata = Column(Text, default="{}")
    tasks_completed = Column(Integer, default=0)
    tasks_failed = Column(Integer, default=0)
    average_task_duration = Column(Float)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
```

**CRITICAL pitfall:** The existing database already exists with data. The Alembic initial migration must use `CREATE TABLE IF NOT EXISTS` (or check for table existence) so it does not fail on a database that already has tables. Use `op.execute("CREATE TABLE IF NOT EXISTS ...")` in the initial migration, OR use `include_object` in env.py to skip existing tables on first run.

**Recommended approach:** Generate the initial migration as a "baseline" that matches the current schema, then mark it as already applied against the existing database:
```bash
.venv/bin/alembic stamp head   # mark existing DB as at latest revision without running DDL
```

**Migration runner in main.py lifespan (replaces inline CREATE TABLE block):**
```python
from alembic.config import Config
from alembic import command

alembic_cfg = Config("alembic.ini")
command.upgrade(alembic_cfg, "head")
```

Remove the `time.sleep(1)` and double-sync pattern from main.py:178-179 (synchronous sleep in async context). Replace with `await asyncio.sleep(0)` if any Turso sync is needed, or remove entirely.

### Admin Credential Validation (D-06, D-07, HARD-02)

**Current (routes_auth.py:244-252):**
```python
if form_data.username != "admin" or form_data.password != "admin123":
    raise HTTPException(401, "Invalid admin credentials")
```

**Target - add to Settings class in app/config.py:**
```python
admin_user: str = Field(default=..., description="Admin username (required)")
admin_password: str = Field(default=..., description="Admin password (required)")
```

Using `default=...` (Ellipsis) with pydantic-settings makes the field required - pydantic raises `ValidationError` on startup if not set. This satisfies D-07 (fail to start if not set) without any custom validation code.

**In routes_auth.py:**
```python
if form_data.username != settings.admin_user or not verify_password(form_data.password, settings.admin_password):
    raise HTTPException(401, ...)
```

Note: `admin_password` should be stored as a bcrypt hash or compared using `verify_password`. If stored as plaintext in env var, use direct comparison. Given passlib is already present, hash-based comparison is cleaner.

### CORS Lockdown (HARD-05)

**Current (app/config.py:50-52):**
```python
cors_origins: List[str] = Field(default=["*"], ...)
cors_methods: List[str] = Field(default=["*"], ...)
cors_headers: List[str] = Field(default=["*"], ...)
```

**Target:**
```python
cors_origins: List[str] = Field(default=["http://localhost:3000", "http://localhost:7788"], ...)
cors_methods: List[str] = Field(default=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"], ...)
cors_headers: List[str] = Field(default=["Authorization", "Content-Type", "X-API-Key", "X-Request-ID"], ...)
```

The live VPS deployment (`hub.brunhilde.cloud`) must set `AGENTHUB_CORS_ORIGINS='["https://hub.brunhilde.cloud"]'` via environment. The default safe list covers local development only.

### slowapi Rate Limiting (PROD-01, D-03)

**Standard slowapi pattern with FastAPI:**
```python
# app/main.py additions
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# In route handlers:
@router.post("/v1/auth/login")
@limiter.limit("10/minute")
async def login(request: Request, ...):
    ...
```

**Retry-After header (D-03):** slowapi automatically adds `Retry-After` to 429 responses when using the built-in exception handler. The custom RFC 7807 exception handler must also include it:
```python
async def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    retry_after = exc.retry_after  # seconds until reset
    return JSONResponse(
        status_code=429,
        content={
            "type": "about:blank",
            "title": "Too Many Requests",
            "status": 429,
            "detail": f"Rate limit exceeded. Try again in {retry_after} seconds.",
            "instance": str(request.url.path)
        },
        headers={
            "Retry-After": str(retry_after),
            "X-RateLimit-Limit": str(exc.limit.limit),
            "X-RateLimit-Remaining": "0"
        }
    )
```

**Remove the in-memory rate limiter in routes_p2.py:23-43** (`_rate_limits` defaultdict) - this is replaced by slowapi globally.

### Prometheus Metrics (PROD-02)

**Standard pattern:**
```python
# app/api/routes_metrics.py (new file)
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from fastapi import APIRouter, Response

router = APIRouter()

# Metrics
REQUESTS_TOTAL = Counter("openhub_requests_total", "Total requests", ["method", "endpoint", "status"])
REQUEST_DURATION = Histogram("openhub_request_duration_seconds", "Request duration", ["endpoint"])
ACTIVE_AGENTS = Gauge("openhub_active_agents", "Currently active agents")
TASKS_QUEUED = Gauge("openhub_tasks_queued", "Tasks in queued state")

@router.get("/metrics", include_in_schema=False)
async def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
```

**Metrics to instrument (Claude's discretion - recommended minimal set):**
- `openhub_requests_total` - labeled by method, path, status code (in RequestTimingMiddleware)
- `openhub_request_duration_seconds` - histogram in RequestTimingMiddleware
- `openhub_active_agents` - Gauge, updated in heartbeat monitor on status change
- `openhub_tasks_total` - labeled by status (queued/running/completed/failed)

### structlog Enhancement (D-05, PROD-04)

**Current app/logging.py already outputs JSON in production** (`structlog.processors.JSONRenderer()` when `not settings.debug`). What needs to change is the field set to match D-05 requirements (`event, error_type, status, path, trace_id`).

The `trace_id` must be consistently populated. `RequestTimingMiddleware` already binds `request_id` via `structlog.contextvars.bind_contextvars(request_id=request_id)`. Rename or alias this to `trace_id` for consistency with D-05.

**Enhanced processor chain:**
```python
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,   # pulls trace_id from context
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,       # formats exceptions cleanly
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer() if not settings.debug else structlog.dev.ConsoleRenderer()
    ],
    wrapper_class=structlog.make_filtering_bound_logger(logging.getLevelName(level.upper())),
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)
```

**Key change:** Add `structlog.contextvars.merge_contextvars` as FIRST processor so `trace_id` bound by middleware appears in all log lines within a request.

### datetime.utcnow() Fix (HARD-09)

61 occurrences of `datetime.utcnow()` across the codebase. The correct replacement is:

```python
# Replace:
from datetime import datetime
datetime.utcnow()

# With:
from datetime import datetime, timezone
datetime.now(timezone.utc)
```

**Key files with most occurrences:**
- `app/database/repositories/base.py:59` - `_get_timestamp()` method; fix once, fixes all subclasses
- `app/services/task_service.py` - multiple calls
- `app/services/agent_service.py` - multiple calls
- `app/api/routes_auth.py:91-93` - registration timestamps
- `app/api/routes_health.py:38, 146` - health response timestamps

**Pattern already in use correctly:** `routes_acn.py` already uses `datetime.now(timezone.utc)` - this is the canonical reference for the correct pattern.

### OpenAPI Docs (HARD-07, OSS-02)

**Current (main.py:197-198):**
```python
docs_url=None,
redoc_url=None,
```

**Fix:**
```python
docs_url="/docs",
redoc_url="/redoc",
```

For a security-hardened production deployment, consider restricting `/docs` to localhost or behind auth. For open source developer friendliness, leaving it public is standard. This is Claude's discretion.

### decode_token_without_verification Rename (Claude's Discretion)

`app/auth/jwt_auth.py:149` has a public method `decode_token_without_verification` that skips signature validation. It is only called internally by `is_token_expired` and `get_token_remaining_time` in the same class.

Rename to `_decode_unverified` (private by convention). No external callers confirmed by grep.

### Heartbeat Monitor Wiring (HARD-04)

`HeartbeatService.start_monitoring()` exists and is correct but never called. It must be wired into the FastAPI `lifespan` context manager in `main.py`:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # ... existing startup code ...

    # Wire heartbeat monitor
    from .database.connection import get_database
    from .services.heartbeat_service import HeartbeatService
    db = get_database()
    heartbeat_service = HeartbeatService(db)
    await heartbeat_service.start_monitoring()

    yield

    # Shutdown
    await heartbeat_service.stop_monitoring()
    logger.info("agent_hub_shutting_down")
```

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Rate limiting | In-memory sliding window dict | slowapi 0.1.9 (already installed) | Per-IP tracking, Redis backend option, Retry-After headers, standard limiter |
| Schema migrations | Custom migration runner | Alembic 1.12.1 (already installed) | Rollback, autogenerate from ORM, upgrade path for self-hosters |
| Prometheus metrics | Custom counters dict | prometheus-client 0.19.0 (already installed) | OTLP scrape format, histogram bucketing, Grafana compatibility |
| JSON logging fields | Manual dict formatting | structlog contextvars.merge_contextvars | Automatic request_id binding to all log lines in request scope |
| Admin credential validation | Custom startup validator | pydantic-settings `Field(default=...)` | Pydantic raises ValidationError on startup automatically |
| RFC 7807 response model | Free-form dict | Pydantic model with type, title, status, detail, instance | Validation, serialization, OpenAPI schema generation |

**Key insight:** Every tool this phase needs is already in requirements.txt and installed in .venv. The phase is wiring and configuration, not package research.

---

## Common Pitfalls

### Pitfall 1: Alembic Initial Migration on Existing Database

**What goes wrong:** Running `alembic upgrade head` against the existing `.db` file fails because all 16 tables already exist from the inline DDL in `main.py`.

**Why it happens:** Alembic's initial migration generates `CREATE TABLE` statements, not `CREATE TABLE IF NOT EXISTS`. Running against an existing database raises `OperationalError: table already exists`.

**How to avoid:** Two valid approaches:
1. **Stamp the baseline:** After creating the initial migration, run `alembic stamp head` against the existing database. This records the revision in `alembic_version` without executing DDL. Future migrations run normally.
2. **Use IF NOT EXISTS in the initial revision:** Manually write `op.execute("CREATE TABLE IF NOT EXISTS ...")` instead of using the autogenerated `op.create_table()`. Less elegant but foolproof.

**Recommended:** Approach 1 (stamp) for the existing database. Approach 2 (IF NOT EXISTS) for the Dockerfile fresh-start path.

**Warning signs:** Any `OperationalError: table already exists` during startup after enabling Alembic.

### Pitfall 2: RequestIdDep Import Blocks app/dependencies.py Deletion

**What goes wrong:** Deleting `app/dependencies.py` (D-08) breaks `app/api/routes_health.py:11` which imports `RequestIdDep`.

**Why it happens:** `RequestIdDep` is a utility type alias unrelated to auth, but it lives in the stub file. The stub file must be emptied of all useful utilities before it can be deleted.

**How to avoid:** Before deleting, extract `get_request_id` and `RequestIdDep` to `app/middleware.py` or `app/utils/request_id.py`. Update `routes_health.py` import. Then delete.

**Warning signs:** `ImportError: cannot import name 'RequestIdDep'` after deletion.

### Pitfall 3: pydantic-settings Required Field with Ellipsis Breaks Docker Compose

**What goes wrong:** Adding `admin_user: str = Field(default=...)` breaks startup unless `AGENTHUB_ADMIN_USER` and `AGENTHUB_ADMIN_PASSWORD` are set in the environment. The existing `docker-compose.yml` does not set these.

**Why it happens:** D-07 is intentional - but the Docker Compose file must be updated simultaneously or the Docker path breaks.

**How to avoid:** Update `docker-compose.yml` to include `AGENTHUB_ADMIN_USER` and `AGENTHUB_ADMIN_PASSWORD` with placeholder values OR document in README that these must be set. The live VPS systemd service must also be updated before the change is deployed.

**Warning signs:** `pydantic_core._pydantic_core.ValidationError: 1 validation error ... admin_user: Field required` on startup.

### Pitfall 4: RFC 7807 Migration Breaks Existing Clients

**What goes wrong:** The current error format `{success, error, error_code, request_id}` is what the live agents at `hub.brunhilde.cloud` may be parsing. Switching to RFC 7807 `{type, title, status, detail, instance}` removes `success`, `error`, and `error_code` fields.

**Why it happens:** The live VPS has 4 active agents. Their error-handling code may check `response.json()["error"]` or `response.json()["success"]`.

**How to avoid:** Check the bridge client (`app/bridge/agent_bridge.py`) for error field references. If it parses specific error fields, update it in the same task as the middleware change. Since there's no test suite yet, this is a code-grep risk.

**Warning signs:** Agents entering error loops after middleware update because `response["error"]` throws KeyError.

### Pitfall 5: slowapi with Custom RFC 7807 Exception Handler

**What goes wrong:** slowapi's default `_rate_limit_exceeded_handler` returns a plain string response, not the RFC 7807 format (D-01, D-03).

**Why it happens:** slowapi provides its own exception handler that overrides the custom one if registered in the wrong order.

**How to avoid:** Register a custom `RateLimitExceeded` handler instead of slowapi's default:
```python
# Do NOT use: app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
# Use custom handler:
app.add_exception_handler(RateLimitExceeded, custom_rfc7807_rate_limit_handler)
```
The custom handler must include `Retry-After` header (D-03).

### Pitfall 6: structlog contextvars Binding Order

**What goes wrong:** If `merge_contextvars` is not the FIRST processor in the chain, the `trace_id` bound by `RequestTimingMiddleware` does not appear in log lines.

**Why it happens:** structlog processors run in order. If `merge_contextvars` is in the middle, earlier processors format the event without the context vars.

**How to avoid:** Always put `structlog.contextvars.merge_contextvars` first in the processors list.

### Pitfall 7: datetime.utcnow Fix Must Include SQLite Storage Format

**What goes wrong:** `datetime.now(timezone.utc)` produces timezone-aware datetimes. SQLite stores datetimes as strings. The existing schema uses `TIMESTAMP DEFAULT CURRENT_TIMESTAMP` which produces naive UTC strings. Mixing aware and naive datetimes in comparison operations raises `TypeError: can't compare offset-naive and offset-aware datetimes`.

**Why it happens:** The codebase has both patterns: `routes_acn.py` already uses `datetime.now(timezone.utc)` while most other files use `datetime.utcnow()`. Mixing them in the same comparison crashes.

**How to avoid:** When fixing `datetime.utcnow()` calls, ensure any datetime retrieved from SQLite is also made timezone-aware via `dt.replace(tzinfo=timezone.utc)` in `_row_to_model` converters. The `base.py:59` `_get_timestamp()` method change propagates to all repository subclasses automatically.

---

## Code Examples

### RFC 7807 ProblemDetail Pydantic Model

```python
# app/models/errors.py (new file)
from pydantic import BaseModel
from typing import Optional, List, Any

class FieldError(BaseModel):
    field: str
    message: str
    type: Optional[str] = None

class ProblemDetail(BaseModel):
    """RFC 7807 Problem Details for HTTP APIs"""
    type: str = "about:blank"
    title: str
    status: int
    detail: str
    instance: Optional[str] = None
    trace_id: Optional[str] = None
    errors: Optional[List[FieldError]] = None  # D-02: validation errors
```

### Updated middleware.py error handlers

```python
# app/middleware.py - replace existing handlers

async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    request_id = getattr(request.state, "request_id", str(uuid4()))
    errors = [
        FieldError(
            field=".".join(str(loc) for loc in error["loc"] if loc != "body"),
            message=error["msg"],
            type=error["type"]
        )
        for error in exc.errors()
    ]
    problem = ProblemDetail(
        type="about:blank",
        title="Unprocessable Entity",
        status=422,
        detail="Request validation failed",
        instance=str(request.url.path),
        trace_id=request_id,
        errors=errors
    )
    logger.warning("validation_error", path=request.url.path, error_count=len(errors), trace_id=request_id)
    return JSONResponse(status_code=422, content=problem.model_dump(exclude_none=True),
                       headers={"X-Request-ID": request_id})

async def http_exception_handler_custom(request: Request, exc: HTTPException) -> JSONResponse:
    request_id = getattr(request.state, "request_id", str(uuid4()))
    problem = ProblemDetail(
        type="about:blank",
        title=STATUS_TITLES.get(exc.status_code, "Error"),
        status=exc.status_code,
        detail=exc.detail if isinstance(exc.detail, str) else str(exc.detail),
        instance=str(request.url.path),
        trace_id=request_id
    )
    # Log 500s at error, 4xx at warning (D-04: no stack traces in response)
    if exc.status_code >= 500:
        logger.error("http_exception", status=exc.status_code, path=request.url.path, trace_id=request_id)
    else:
        logger.warning("http_exception", status=exc.status_code, path=request.url.path, trace_id=request_id)
    return JSONResponse(status_code=exc.status_code, content=problem.model_dump(exclude_none=True),
                       headers={"X-Request-ID": request_id})

async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    request_id = getattr(request.state, "request_id", str(uuid4()))
    # Log with full traceback - trace stays in logs, not response (D-04)
    logger.error("unhandled_exception", error_type=type(exc).__name__,
                error=str(exc), trace_id=request_id, exc_info=True)
    problem = ProblemDetail(
        type="about:blank",
        title="Internal Server Error",
        status=500,
        detail="An unexpected error occurred",  # Never expose exc details (D-04)
        instance=str(request.url.path),
        trace_id=request_id
    )
    return JSONResponse(status_code=500, content=problem.model_dump(exclude_none=True),
                       headers={"X-Request-ID": request_id})
```

### Alembic env.py for dynamic DB path

```python
# alembic/env.py (key sections)
from app.config import get_settings

def get_url():
    settings = get_settings()
    return f"sqlite:///{settings.db_path}"

def run_migrations_online():
    connectable = create_engine(get_url())
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata,
                         render_as_batch=True)  # render_as_batch required for SQLite ALTER support
        with context.begin_transaction():
            context.run_migrations()
```

### slowapi middleware wiring

```python
# app/main.py additions
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])
app.state.limiter = limiter
# Register custom RFC 7807 handler instead of slowapi default
app.add_exception_handler(RateLimitExceeded, rfc7807_rate_limit_handler)

# In setup_middleware:
from slowapi.middleware import SlowAPIMiddleware
app.add_middleware(SlowAPIMiddleware)
```

---

## State of the Art

| Old Approach | Current Approach | Impact |
|--------------|------------------|--------|
| `datetime.utcnow()` | `datetime.now(timezone.utc)` | deprecated since Python 3.12, removed in 3.14 |
| Inline DDL in app startup | Alembic versioned migrations | enables safe upgrades for self-hosters |
| Per-route `_auth()` helper | Shared FastAPI dependency | single fix point for auth bugs |
| `str(list)` for JSON fields | `json.dumps(list)` | enables json.loads() by downstream code |
| Custom error envelope | RFC 7807 Problem Details | standard format, client library compatibility |
| `docs_url=None` | `docs_url="/docs"` | open source discoverability |

**Deprecated:**
- `passlib[bcrypt]==1.7.4`: passlib is maintenance-only since 2023. Not in scope for this phase (don't expand scope). Flag for Phase 2 or post-v1.0.
- `zvec==0.1.0`: installed but unused. Remove from requirements.txt in this phase to reduce install size. The `zvec_path` directory creation in `main.py:35` should also be removed.

---

## Environment Availability

All dependencies are already installed in `.venv`. No external services are required for this phase.

| Dependency | Required By | Available | Version | Notes |
|------------|------------|-----------|---------|-------|
| alembic | HARD-06 schema migrations | Yes | 1.12.1 | in .venv |
| sqlalchemy | HARD-06 ORM models | Yes | 2.0.23 | in .venv |
| slowapi | PROD-01 rate limiting | Yes | 0.1.9 | in .venv, not wired |
| prometheus-client | PROD-02 metrics | Yes | 0.19.0 | in .venv, not routed |
| structlog | PROD-04 logging | Yes | 23.2.0 | in .venv, partially configured |
| pytest | Test validation | Yes | 7.4.3 | in .venv, no tests/ dir |
| pytest-asyncio | Async tests | Yes | 0.21.1 | in .venv |
| Redis | HARD-13 blacklist | Optional | 5.0.1 client | Server may not be running; fail-closed behavior kept per D-13 |

**Missing dependencies with no fallback:** None.

**Run command (using project venv):**
```bash
cd /home/omer/projects/OpenHub
.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 7788 --reload
```

---

## Validation Architecture

nyquist_validation is `true` in `.planning/config.json` - this section is required.

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 7.4.3 + pytest-asyncio 0.21.1 |
| Config file | pyproject.toml [tool.pytest.ini_options] - EXISTS |
| Quick run command | `.venv/bin/pytest tests/ -x -q --no-cov` |
| Full suite command | `.venv/bin/pytest tests/ --cov=app --cov-report=term` |
| Async mode | `asyncio_mode = "auto"` (already set in pyproject.toml) |

### Phase Requirements to Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| HARD-01 | app/dependencies.py is deleted; no route imports from it | unit | `pytest tests/test_auth_stub_removed.py -x` | No - Wave 0 |
| HARD-02 | Missing admin env vars fail startup; correct creds authenticate | unit | `pytest tests/test_admin_credentials.py -x` | No - Wave 0 |
| HARD-03 | Capabilities stored as valid JSON; json.loads() succeeds | unit | `pytest tests/test_capabilities_json.py -x` | No - Wave 0 |
| HARD-04 | Heartbeat monitor runs; agent goes offline after timeout | integration | `pytest tests/test_heartbeat.py -x` | No - Wave 0 |
| HARD-05 | CORS headers absent for non-allowed origins | unit | `pytest tests/test_cors.py -x` | No - Wave 0 |
| HARD-06 | Alembic migration creates all 16 tables from scratch | integration | `pytest tests/test_migrations.py -x` | No - Wave 0 |
| HARD-07 | GET /docs returns 200 with OpenAPI JSON | smoke | `pytest tests/test_openapi.py -x` | No - Wave 0 |
| HARD-08 | Error responses match RFC 7807 shape | unit | `pytest tests/test_error_format.py -x` | No - Wave 0 |
| HARD-09 | No datetime.utcnow() calls remain in app/ | static | `pytest tests/test_datetime_usage.py -x` | No - Wave 0 |
| HARD-10 | No _auth/_sender definitions in route files | static | `pytest tests/test_auth_consolidation.py -x` | No - Wave 0 |
| PROD-01 | POST /v1/auth/login rate-limited at 10/minute | integration | `pytest tests/test_rate_limiting.py -x` | No - Wave 0 |
| PROD-02 | GET /metrics returns prometheus text/plain | smoke | `pytest tests/test_metrics.py -x` | No - Wave 0 |
| PROD-04 | Log output is valid JSON in non-debug mode | unit | `pytest tests/test_logging.py -x` | No - Wave 0 |

### Sampling Rate

- **Per task commit:** `.venv/bin/pytest tests/ -x -q --no-cov` (fast, no coverage overhead)
- **Per wave merge:** `.venv/bin/pytest tests/ --cov=app --cov-report=term`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

All test files are missing - `tests/` directory does not exist. Wave 0 must create:

- [ ] `tests/__init__.py`
- [ ] `tests/conftest.py` - shared fixtures: `test_app`, `test_client` (httpx AsyncClient), `test_db` (in-memory SQLite), `mock_settings` with admin credentials set
- [ ] `tests/test_auth_stub_removed.py` - covers HARD-01
- [ ] `tests/test_admin_credentials.py` - covers HARD-02
- [ ] `tests/test_capabilities_json.py` - covers HARD-03
- [ ] `tests/test_heartbeat.py` - covers HARD-04
- [ ] `tests/test_cors.py` - covers HARD-05
- [ ] `tests/test_migrations.py` - covers HARD-06
- [ ] `tests/test_openapi.py` - covers HARD-07
- [ ] `tests/test_error_format.py` - covers HARD-08
- [ ] `tests/test_datetime_usage.py` - covers HARD-09 (static analysis test: grep app/ for utcnow)
- [ ] `tests/test_auth_consolidation.py` - covers HARD-10 (static analysis: grep for def _auth)
- [ ] `tests/test_rate_limiting.py` - covers PROD-01
- [ ] `tests/test_metrics.py` - covers PROD-02
- [ ] `tests/test_logging.py` - covers PROD-04

**conftest.py key fixtures:**
```python
import pytest
import os
from httpx import AsyncClient, ASGITransport

@pytest.fixture(autouse=True)
def set_admin_env(monkeypatch):
    monkeypatch.setenv("AGENTHUB_ADMIN_USER", "testadmin")
    monkeypatch.setenv("AGENTHUB_ADMIN_PASSWORD", "testpass123!")
    monkeypatch.setenv("AGENTHUB_DB_PATH", ":memory:")

@pytest.fixture
async def client():
    from app.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
```

---

## Open Questions

1. **ACN invite code persistence (Claude's Discretion)**
   - What we know: `_invite_store` is in-memory dict in `routes_acn.py:32`; confirmed single-process assumption
   - What's unclear: Add a `pending_invites` table (Alembic migration) or keep in-memory for now?
   - Recommendation: Persist to SQLite via a new `invite_codes` table with `expires_at` TTL. Natural fit since Alembic is being set up anyway. Small effort, removes the "process restart clears invites" concern.

2. **API key prefix optimization (Claude's Discretion)**
   - What we know: `APIKeyManager.validate_api_key` does full table scan (O(n) per request)
   - What's unclear: How many API keys exist in production today?
   - Recommendation: Add `key_prefix` column (first 8 chars of hash) to `api_keys` table, index it, and filter by prefix before iterating. Include as a migration alongside the initial Alembic baseline.

3. **Alembic fresh-install vs. upgrade path**
   - What we know: Existing database has data; fresh Docker installs start empty
   - What's unclear: Does the initial migration use `CREATE TABLE IF NOT EXISTS` or regular `CREATE TABLE`?
   - Recommendation: Regular `CREATE TABLE` (Alembic standard). Use `alembic stamp head` for the existing database only. The Dockerfile should run `alembic upgrade head` which works on fresh databases automatically.

4. **OSS-02 requires endpoint docstrings**
   - What we know: `/docs` will be enabled (HARD-07)
   - What's unclear: Many route handlers lack docstrings that produce useful OpenAPI descriptions
   - Recommendation: Add one-line docstrings to all route handlers as part of the HARD-07 task. Low effort, high documentation value.

---

## Project Constraints (from CLAUDE.md)

From `/home/omer/projects/OpenHub/CLAUDE.md`:

| Constraint | Implication for this phase |
|------------|---------------------------|
| Python 3.11+ / FastAPI + Uvicorn + SQLite + Pydantic v2 | Stack is fixed; no framework changes |
| AGENTHUB_ prefix for all env vars | New `AGENTHUB_ADMIN_USER` and `AGENTHUB_ADMIN_PASSWORD` must use this prefix |
| Repository pattern: routes -> services -> repos -> DB | New `api_key_deps.py` lives in `app/auth/`; metrics route in `app/api/` |
| Relative imports only (no absolute `app.*`) | All new imports must use `..config`, `..auth.dependencies`, etc. |
| `snake_case` functions, `PascalCase` classes | `ProblemDetail`, `FieldError` models follow this convention |
| Commit prefixes: `feat:`, `refactor:`, `improve:`, `clean:` | This phase is `refactor:` (auth) and `feat:` (Alembic, metrics, rate limiting) |
| Never push without asking user first | Research only; no push |
| No AI tool names in commits | Comply |
| Development style: slow, clean, small steps | Plan should wave small changes; don't bundle auth + migrations in one task |
| Live system at hub.brunhilde.cloud, systemd services | Admin credential env vars must be coordinated with VPS deployment before push |

---

## Sources

### Primary (HIGH confidence)

- Direct code audit: `app/dependencies.py`, `app/auth/dependencies.py`, `app/main.py`, `app/config.py`, `app/middleware.py`, `app/logging.py`, `app/api/routes_auth.py`, `app/api/routes_p1.py`, `app/api/routes_p2.py`
- `.planning/codebase/CONCERNS.md` - security audit with file:line references
- `.planning/codebase/CONVENTIONS.md` - naming and style patterns
- `.planning/codebase/ARCHITECTURE.md` - layered architecture
- `.planning/codebase/STACK.md` - confirmed dependencies
- `.planning/research/PITFALLS.md` - pre-existing pitfall analysis
- `.planning/research/SUMMARY.md` - prior research synthesis
- `.venv/bin/python` import verification: alembic 1.12.1, sqlalchemy 2.0.23, slowapi 0.1.9, prometheus-client 0.19.0, structlog 23.2.0 all importable
- `grep` audit: 61 `datetime.utcnow()` occurrences; 1 stub import (`routes_health.py`); 5 `_auth` definitions in route files

### Secondary (MEDIUM confidence)

- RFC 7807 Problem Details spec (known standard, implementation pattern from training + verification against official RFC)
- Alembic SQLite `render_as_batch=True` requirement for ALTER TABLE support in SQLite (well-documented Alembic limitation)
- slowapi + FastAPI integration pattern (verified against requirements.txt version 0.1.9)

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All packages verified importable in .venv; no new packages needed
- Architecture patterns: HIGH - Based on direct code reading of all affected files
- Pitfalls: HIGH - Pitfalls 1-4 grounded in specific file:line references; pitfall 5-7 from structlog/slowapi/datetime API knowledge verified against installed versions
- Test architecture: HIGH - pyproject.toml pytest config exists; framework verified importable

**Research date:** 2026-04-07
**Valid until:** 2026-05-07 (stable stack, no fast-moving dependencies)
