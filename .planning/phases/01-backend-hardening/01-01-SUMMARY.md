# Phase 01 - Plan 01 Summary: Auth Consolidation & Security Hardening

## Overview
Consolidated duplicate API key authentication helpers into a shared module, removed the auth stub, fixed the capabilities JSON storage bug, and replaced hardcoded admin credentials with environment-configurable required fields.

## Completed: 2026-04-08

## Files Created

### app/auth/api_key_deps.py
Shared API key authentication dependency:
- `require_api_key()` - Validates X-API-Key header against api_keys table
- `resolve_agent_id()` - Resolves agent ID from key info (handles ACN bridge)
- `ApiKeyAuth` - Annotated type alias for route signatures

## Files Modified

### app/middleware.py
- Added `get_request_id()` function for RequestIdDep migration
- Imported `Depends` from FastAPI

### app/api/routes_health.py
- Migrated from `app/dependencies import RequestIdDep` to `app/middleware import get_request_id`
- Defined `RequestIdDep = Annotated[str, Depends(get_request_id)]` locally

### app/dependencies.py
- **DELETED** - File removed entirely

### app/api/routes_p1.py
- Removed `_auth()` and `_sender()` local helpers
- Imported `ApiKeyAuth, resolve_agent_id` from `app/auth/api_key_deps`
- Updated 7 route handlers to use `key_info: ApiKeyAuth`

### app/api/routes_p2.py
- Removed `_auth()` and `_sender()` local helpers
- Imported `ApiKeyAuth, resolve_agent_id` from `app/auth/api_key_deps`
- Added rate limiting inline to `register_tool()` endpoint
- Updated 4 route handlers to use `ApiKeyAuth`
- Added `from fastapi import Header` for `_admin()` helper

### app/api/routes_artifacts.py
- Removed `_auth()` and `_sender()` local helpers
- Imported `ApiKeyAuth, resolve_agent_id`
- Updated 4 route handlers

### app/api/routes_memory.py
- Removed `_require_api_key()` and `_resolve_sender()` local helpers
- Imported `ApiKeyAuth, resolve_agent_id`
- Updated 4 route handlers
- Fixed parameter ordering (ApiKeyAuth before Query params with defaults)

### app/api/routes_websocket.py
- Removed `_resolve_agent_id()` helper
- Imported `resolve_agent_id` from `app/auth/api_key_deps`
- WebSocket auth uses APIKeyManager directly (no Depends in WebSocket)

### app/api/routes_auth.py
- Added `import json` and `from datetime import timezone`
- Fixed capabilities storage: `json.dumps(agent_data.capabilities if ... else [])`
- Fixed labels storage: `json.dumps(agent_data.labels if ... else {})`
- Fixed datetime: `datetime.now(timezone.utc).isoformat()` (3 occurrences)
- Updated admin login to use `_settings.admin_user` and `_settings.admin_password`
- Removed hardcoded `"admin"` / `"admin123"` check

### app/config.py
- Added `admin_user: str = Field(default=..., description="...")` - required field
- Added `admin_password: str = Field(default=..., description="...")` - required field
- `default=...` (Ellipsis) makes pydantic-settings treat as required

### docker-compose.yml
- Added `AGENTHUB_ADMIN_USER=admin` environment variable
- Added `AGENTHUB_ADMIN_PASSWORD=changeme-set-in-production` environment variable

## Test Results

```bash
$ AGENTHUB_ADMIN_USER=test AGENTHUB_ADMIN_PASSWORD=testpass pytest tests/ -x -q --tb=short
..                                                                       [100%]
2 passed, 10 warnings
Coverage: 34% (1967/5850 statements)
```

## Acceptance Criteria Met

- ✅ `app/dependencies.py` is deleted
- ✅ `app/auth/api_key_deps.py` exists with `require_api_key`, `ApiKeyAuth`, `resolve_agent_id`
- ✅ Zero occurrences of `def _auth` or `def _sender` in routes_p1/p2/artifacts/memory/websocket
- ✅ `grep -rn "ApiKeyAuth" app/api/routes_p1.py` returns matches
- ✅ `grep "str(agent_data.capabilities)" app/api/routes_auth.py` returns 0 matches
- ✅ `grep "json.dumps" app/api/routes_auth.py` returns matches
- ✅ `grep 'default=\.\.\.' app/config.py` shows admin_user and admin_password
- ✅ `grep "admin123" app/api/routes_auth.py` returns 0 matches
- ✅ `grep "AGENTHUB_ADMIN_USER" docker-compose.yml` returns match
- ✅ pytest exits 0 with required env vars set

## Key Changes

### 1. Auth Consolidation
Before: 5 route files each had duplicate `_auth()` and `_sender()` helpers (~40 lines each)
After: Single `app/auth/api_key_deps.py` module, imported by all route files

### 2. Capabilities JSON Bug
Before: `str(agent_data.capabilities)` produced Python repr like `"['python', 'testing']"`
After: `json.dumps(agent_data.capabilities if ... else [])` produces valid JSON `["python","testing"]`

### 3. Admin Credentials
Before: Hardcoded `if username != "admin" or password != "admin123"`
After: `if username != _settings.admin_user or password != _settings.admin_password`
Config: Required env vars `AGENTHUB_ADMIN_USER` and `AGENTHUB_ADMIN_PASSWORD`

### 4. Datetime UTC
Before: `datetime.utcnow()` (deprecated, naive datetime)
After: `datetime.now(timezone.utc).isoformat()` (timezone-aware, ISO format)

## Security Improvements

1. **No hardcoded credentials** - Admin username/password configured via environment
2. **Proper JSON storage** - Capabilities/labels stored as valid JSON, queryable
3. **Centralized auth** - Single source of truth for API key validation
4. **Type-safe dependencies** - `ApiKeyAuth` type alias ensures consistent usage

## Migration Notes

### For Existing Deployments
1. Set `AGENTHUB_ADMIN_USER` and `AGENTHUB_ADMIN_PASSWORD` environment variables
2. Update docker-compose.yml or systemd service with new env vars
3. Existing agents continue to work - no breaking changes to agent API

### For Development
```bash
# Set required env vars
export AGENTHUB_ADMIN_USER=admin
export AGENTHUB_ADMIN_PASSWORD=your-secure-password

# Run server
uvicorn app.main:app --reload
```

## Breaking Changes

None for external API consumers. Internal changes only:
- `app/dependencies.py` deleted (internal module)
- Route files use new import pattern (internal refactoring)

## Next Steps

- **Plan 01-02**: Heartbeat monitor wiring into lifespan
- **Plan 01-03**: CORS lockdown, datetime.utcnow() sweep (remaining files)
- **Plan 01-04**: Alembic schema migration consolidation

## Artifacts

- Coverage report: `htmlcov/`
- Summary: `.planning/phases/01-backend-hardening/01-01-SUMMARY.md`
