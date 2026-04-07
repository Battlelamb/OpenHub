# Coding Conventions

**Analysis Date:** 2026-04-07

## Naming Patterns

**Files:**
- Route modules: `routes_{noun}.py` - e.g., `routes_agents.py`, `routes_tasks.py`, `routes_p1.py`
- Service modules: `{noun}_service.py` - e.g., `agent_service.py`, `task_service.py`
- Repository modules: `{noun}.py` inside `database/repositories/` - e.g., `agents.py`, `tasks.py`
- Model modules: `{noun}.py` inside `models/` - e.g., `agents.py`, `tasks.py`, `base.py`

**Functions:**
- `snake_case` throughout - both sync and async functions
- Route handler names match their HTTP semantic: `create_task`, `get_agent`, `send_heartbeat`, `go_offline`
- Private/internal helpers prefixed with underscore: `_row_to_model`, `_model_to_dict`, `_monitor_loop`, `_auth`, `_sender`
- Service-level dependency factories named `get_{noun}_service()` in route files

**Classes:**
- `PascalCase` for all classes
- Service classes: `{Noun}Service` - e.g., `AgentService`, `TaskService`, `HeartbeatService`
- Repository classes: `{Noun}Repository` - e.g., `AgentRepository`, `TaskRepository`
- Model classes: descriptive noun or noun+verb: `AgentCreate`, `AgentUpdate`, `AgentHeartbeat`, `TaskClaim`, `TaskComplete`
- Response models: `{Noun}Response` or `{Noun}ListResponse` - e.g., `AgentRegistrationResponse`, `TaskResponse`
- Mixin classes: `{Noun}Mixin` - e.g., `TimestampMixin`, `IDMixin`, `MetadataMixin`
- Exception classes: `{Noun}Error` extending `HTTPException` - e.g., `AgentNotFoundError`, `TaskConflictError`

**Variables:**
- `snake_case` throughout
- Boolean variables: prefixed with `_running`, `_use_turso`, `is_active`
- Private module-level state uses underscore prefix: `_rate_limits`, `_RATE_LIMIT_WINDOW`, `_RATE_LIMIT_MAX`

**Constants:**
- `SCREAMING_SNAKE_CASE` for module-level constants: `TURSO_AVAILABLE`, `_RATE_LIMIT_WINDOW`, `_RATE_LIMIT_MAX`

**Enums:**
- Class name in `PascalCase`, values in `SCREAMING_SNAKE_CASE`
- String enums inherit `(str, Enum)` so values serialize as strings automatically
- Int enums inherit `(IntEnum)` for priority levels
- Examples: `AgentStatus`, `TaskStatus`, `TaskPriority`, `TaskType`

## Code Style

**Formatting:**
- Tool: `black` with `line-length = 88`
- Target: Python 3.11
- Config in `pyproject.toml`: `[tool.black]`

**Import sorting:**
- Tool: `isort` with `profile = "black"`, `line_length = 88`
- Config in `pyproject.toml`: `[tool.isort]`

**Type checking:**
- Tool: `mypy` targeting Python 3.11
- `warn_return_any = true`, `warn_unused_configs = true`, `disallow_untyped_defs = true`
- All functions have type annotations on parameters and return values

**Linting:**
- Tool: `flake8` (declared in dev deps, no custom config file found)

## Import Organization

**Order (per isort "black" profile):**
1. Standard library: `from datetime import datetime`, `from typing import List, Optional, Dict, Any`
2. Third-party: `from fastapi import APIRouter, Depends, HTTPException, status`
3. Local - relative imports only (never absolute `app.*`):
   - Config: `from ..config import get_settings`
   - Logging: `from ..logging import get_logger`
   - Database: `from ..database.connection import get_database`
   - Services: `from ..services.agent_service import AgentService`
   - Models: `from ..models.agents import Agent, AgentCreate, AgentStatus`
   - Auth: `from ..auth.dependencies import CurrentAgent, CurrentAdmin`

**Relative import depth convention:**
- Route files use `..` (two levels up from `api/`)
- Repository files use `...` (three levels up from `database/repositories/`)

**Deferred imports inside functions:** Used in `main.py` startup to avoid circular imports. Acceptable but rare - keep to lifespan context only.

## Module-Level Logger Pattern

Every module declares a module-level logger immediately after imports:
```python
from ..logging import get_logger
logger = get_logger(__name__)
```

Route files also declare settings at module level:
```python
from ..config import get_settings
logger = get_logger(__name__)
settings = get_settings()
```

## Error Handling

**Strategy:** Layered - repositories surface raw exceptions, services catch and re-raise or return booleans, routes convert everything to `HTTPException`.

**Repository layer:** Try/except wrapping every DB call. Log error with structured key-value pairs, then re-raise:
```python
except Exception as e:
    self.logger.error("entity_create_failed", error=str(e), data=data)
    raise
```

**Service layer:** Two patterns depending on operation type:
- Validation errors: `raise ValueError(f"...")` for business rule violations
- Boolean returns for update/delete operations that can legitimately fail: `return False` on failure after logging

**Route layer:** Always converts to `HTTPException`:
```python
except ValueError as e:
    raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
except Exception as e:
    logger.error("agent_registration_error", agent_name=..., error=str(e))
    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Agent registration failed")
```

**Global exception handlers** registered in `app/middleware.py`:
- `RequestValidationError` - returns 422 with structured field errors
- `HTTPException` / `StarletteHTTPException` - returns structured JSON with `error_code`
- `Exception` (catch-all) - returns 500, hides details in production (`settings.debug` gate)

**Custom HTTPException subclasses** in `app/middleware.py`:
- `AgentNotFoundError(agent_id)`, `TaskNotFoundError(task_id)` - 404
- `AgentBusyError(agent_id)`, `TaskConflictError(detail)` - 409
- `APIKeyValidationError(detail)` - 401
- `RateLimitError(detail)` - 429

**Error response envelope** (all errors):
```json
{
  "success": false,
  "error": "<message>",
  "error_code": "CONFLICT",
  "request_id": "<uuid>"
}
```

**HTTP status code to error_code mapping** lives in `get_error_code_from_status()` in `app/middleware.py`.

## Logging

**Framework:** `structlog` with `get_logger(__name__)` from `app/logging.py`

**Format:** Key-value pairs as positional event name + keyword arguments - never f-string interpolation in log calls:
```python
logger.info("agent_registered_successfully",
            agent_id=created_agent.id,
            agent_name=created_agent.agent_name)
```

**Event naming convention:** `snake_case` descriptive verb phrases:
- `agent_registration_started`, `agent_registered_successfully`
- `task_creation_failed`, `entity_created`, `entity_updated`
- `request_started`, `request_completed`, `request_failed`

**Log levels:**
- `debug` - low-frequency reads, stat queries, verification passes
- `info` - state transitions, registration, startup/shutdown events
- `warning` - not-found lookups, auth failures, duplicate attempts, degraded state
- `error` - unexpected exceptions, DB failures, auth errors

**Production vs development:** JSON renderer in production (`settings.debug == False`), `ConsoleRenderer` in debug mode. Controlled in `app/logging.py`.

**Middleware context:** `RequestTimingMiddleware` binds `request_id` via `structlog.contextvars` so all log lines within a request carry the ID automatically.

## Pydantic Model Design

**Base class:** All models inherit from `app/models/base.py::BaseModel` (wraps `PydanticBaseModel`) with:
- `populate_by_name=True`
- `validate_assignment=True`
- `use_enum_values=True`
- `extra='forbid'` - no extra fields allowed
- `by_alias=True` for serialization

**Mixins composition** (use multiple inheritance):
- `IDMixin` - adds `id: str` with UUID factory
- `TimestampMixin` - adds `created_at`, `updated_at`
- `MetadataMixin` - adds `labels: Dict[str, str]`, `metadata: Dict[str, Any]`
- Domain model example: `class Agent(IDMixin, TimestampMixin, MetadataMixin)`

**Validators:** `@field_validator` with `@classmethod` decorator. Validate character sets, length, and format. Return the value if valid, raise `ValueError` if not.

**Field declarations:** Always use `Field(description=..., ...)` with constraints declared inline (`min_length`, `max_length`, `ge`, `le`, `min_items`, `max_items`, `pattern`).

**Separate Create/Update models:** Never reuse the domain model for input. Pattern:
- `AgentCreate` - required fields only, strict validation
- `AgentUpdate` - all fields `Optional`, same validators
- `Agent` - full domain model with ID + timestamps

## Service Layer Design

**Constructor injection:** Services receive `Database` in `__init__`, instantiate repositories internally:
```python
def __init__(self, database: Database):
    self.db = database
    self.agent_repo = AgentRepository(database)
```

**Dependency factories in routes:** Each route file defines local `get_{noun}_service()` functions returning service instances via `Depends()`. No global singletons.

**No async in services:** Service methods are synchronous. Async is confined to route handlers and infrastructure (Redis, monitoring loops).

## Repository Layer Design

**Generic base:** `BaseRepository[T]` in `app/database/repositories/base.py` provides `create`, `get_by_id`, `update`, `delete`, `list_all`, `find_by`, `find_one_by`, `count`, `exists`, `bulk_create`, `bulk_update`, `execute_custom_query`.

**Mandatory overrides in subclasses:**
- `_row_to_model(row: Dict[str, Any]) -> T` - DB row to Pydantic model
- `_model_to_dict(model: T) -> Dict[str, Any]` - Pydantic model to DB dict

**JSON serialization:** All dict/list fields stored as JSON strings in SQLite. `json.loads` / `json.dumps` in `_row_to_model` / `_model_to_dict` respectively.

**Named parameters:** All SQL uses `:param_name` style (SQLite named params), never `%s` or `?`.

## Authentication Type Aliases

Dependency injection uses `Annotated` type aliases defined in `app/auth/dependencies.py`:
```python
CurrentAgent = Annotated[AuthenticatedAgent, Depends(get_current_agent)]
CurrentAdmin = Annotated[AuthenticatedAgent, Depends(get_current_admin)]
OptionalAgent = Annotated[Optional[AuthenticatedAgent], Depends(get_optional_current_agent)]
```
Use these in route signatures directly - do not repeat `Depends(...)` inline.

## Comments

**Module docstrings:** Every `.py` file has a one-line triple-quote docstring at the top describing the module's purpose.

**Function docstrings:** Short, present-tense, one-liners for most functions. Route handlers have docstrings that appear in the API docs.

**Inline comments:** Used sparingly for non-obvious logic (JSON field parsing, SQL parameter construction, rate-limit window math).

**No type-comment style:** All types expressed via annotations, not `# type: ...` comments.

---

*Convention analysis: 2026-04-07*
