---
phase: 01-backend-hardening
verified: 2026-04-09T15:00:00Z
status: gaps_found
score: 9/14 must-haves verified
gaps:
  - truth: "All five per-route _auth/_sender helpers are removed - zero occurrences remain in routes_p1/p2/artifacts/memory/websocket"
    status: failed
    reason: "routes_p2.py still has def _auth and def _sender at lines 22 and 32, with 5 routes using Depends(_auth)"
    artifacts:
      - path: "app/api/routes_p2.py"
        issue: "Local _auth and _sender helpers still defined and used instead of ApiKeyAuth from api_key_deps.py"
    missing:
      - "Replace _auth/_sender in routes_p2.py with ApiKeyAuth and resolve_agent_id from app/auth/api_key_deps.py"
  - truth: "A 429 response from any rate-limited endpoint includes Retry-After header in RFC 7807 format"
    status: failed
    reason: "main.py uses slowapi built-in _rate_limit_exceeded_handler (plain text) instead of custom RFC 7807 handler; no Retry-After header in JSON format"
    artifacts:
      - path: "app/main.py"
        issue: "Line 98 uses _rate_limit_exceeded_handler instead of custom rfc7807_rate_limit_handler as planned"
      - path: "app/limiter.py"
        issue: "Module exists but is orphaned - nobody imports from it; limiter created inline in main.py line 28"
    missing:
      - "Replace _rate_limit_exceeded_handler with custom RFC 7807 handler that includes Retry-After header"
      - "Import limiter from app/limiter.py instead of creating inline in main.py"
      - "Apply @limiter.limit decorators to routes_auth.py login and register endpoints"
  - truth: "Log lines within a request include trace_id from structlog contextvars"
    status: failed
    reason: "middleware.py line 43 binds request_id (not trace_id) to contextvars; plan required renaming to trace_id"
    artifacts:
      - path: "app/middleware.py"
        issue: "bind_contextvars(request_id=...) instead of bind_contextvars(trace_id=...)"
    missing:
      - "Change bind_contextvars(request_id=request_id) to bind_contextvars(trace_id=request_id)"
  - truth: "Prometheus request counter and histogram are incremented in RequestTimingMiddleware"
    status: failed
    reason: "REQUESTS_TOTAL and REQUEST_DURATION_SECONDS are not imported or used in middleware.py"
    artifacts:
      - path: "app/middleware.py"
        issue: "No import of REQUESTS_TOTAL/REQUEST_DURATION_SECONDS, no .labels().inc() or .observe() calls"
    missing:
      - "Import REQUESTS_TOTAL, REQUEST_DURATION_SECONDS from app.api.routes_metrics"
      - "Add .labels().inc() and .observe() after response in RequestTimingMiddleware.dispatch()"
  - truth: "A 500 error in RequestTimingMiddleware returns RFC 7807 format - not old {success, error_code} format"
    status: failed
    reason: "middleware.py lines 87-99 still return the old format with 'success': False and 'error_code': 'INTERNAL_ERROR'"
    artifacts:
      - path: "app/middleware.py"
        issue: "Inline 500 handler in RequestTimingMiddleware.dispatch() still uses old error format"
    missing:
      - "Replace the inline 500 handler content dict with ProblemDetail model (already imported)"
---

# Phase 1: Backend Hardening Verification Report

**Phase Goal:** The backend is correct, secure, and observable - auth works for real, capabilities are stored as JSON, heartbeat monitor runs, CORS is locked down, schema lives in versioned migrations, and OpenAPI docs are exposed
**Verified:** 2026-04-09
**Status:** gaps_found
**Re-verification:** No - initial verification

## Goal Achievement

### Observable Truths (from Success Criteria + Plan Must-Haves)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | A request without valid JWT or API key to protected endpoints returns 401 | VERIFIED | app/auth/api_key_deps.py provides require_api_key with 401 on missing/invalid key; ApiKeyAuth used in routes_p1, artifacts, memory, websocket |
| 2 | Admin credentials are not hardcoded - server refuses to start without env vars | VERIFIED | app/config.py lines 37-38: admin_user and admin_password use default=... (Ellipsis = required); zero occurrences of "admin123" in app/ |
| 3 | Capabilities stored as proper JSON - json.loads() succeeds | VERIFIED | routes_auth.py stores full model via json.dumps(agent_data.model_dump()); routes_acn.py line 741 uses _json.dumps(data.get("capabilities") or []); no str() pattern remains |
| 4 | Heartbeat monitor starts with app and marks agents offline | VERIFIED | main.py lines 64-67: HeartbeatService wired in lifespan with start_monitoring(); line 74: stop_monitoring() on shutdown; no blocking time.sleep |
| 5 | /docs endpoint accessible with correct auth requirements | VERIFIED | main.py line 87: docs_url="/docs", line 88: redoc_url="/redoc" |
| 6 | CORS wildcard gone - locked to specific origins | VERIFIED | config.py lines 59-70: cors_origins defaults to localhost:3000 and localhost:7788; cors_methods/headers are explicit lists |
| 7 | datetime.utcnow() eliminated codebase-wide | VERIFIED | grep -rn "datetime.utcnow()" app/ returns 0 matches |
| 8 | Schema in versioned Alembic migrations, DDL removed from main.py | VERIFIED | alembic/versions/0001_initial_schema.py has all 16 tables; main.py runs alembic upgrade head; zero CREATE TABLE in main.py |
| 9 | RFC 7807 error format in validation/http/general handlers | VERIFIED | middleware.py uses ProblemDetail in validation_exception_handler, http_exception_handler_custom, general_exception_handler |
| 10 | app/dependencies.py auth stub deleted | VERIFIED | File does not exist |
| 11 | All five per-route _auth/_sender removed | FAILED | routes_p2.py still has def _auth (line 22) and def _sender (line 32) with 5 route usages |
| 12 | slowapi rate limiting wired with RFC 7807 429 + Retry-After | FAILED | Uses built-in _rate_limit_exceeded_handler (plain text); no RFC 7807 handler; no @limiter.limit on auth endpoints; app/limiter.py orphaned |
| 13 | Prometheus metrics instrumented in middleware | FAILED | /metrics endpoint exists and returns Prometheus format, but REQUESTS_TOTAL and REQUEST_DURATION_SECONDS are never incremented by middleware |
| 14 | structlog trace_id in contextvars on every request log | FAILED | Binds as request_id, not trace_id per plan requirement |

**Score:** 9/14 truths verified (with 1 partial - inline 500 handler in old format)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `app/auth/api_key_deps.py` | Shared API key dependency | VERIFIED | Contains require_api_key, resolve_agent_id, ApiKeyAuth |
| `app/config.py` | admin_user/admin_password required; CORS locked | VERIFIED | admin fields use default=...; CORS defaults to localhost |
| `app/models/errors.py` | RFC 7807 ProblemDetail + FieldError | VERIFIED | Full implementation with helper functions |
| `app/database/models.py` | 16 SQLAlchemy ORM models | VERIFIED | All 16 model classes present |
| `alembic/versions/0001_initial_schema.py` | Initial migration with 16 tables | VERIFIED | CREATE TABLE IF NOT EXISTS for all 16 tables |
| `alembic/env.py` | Settings-aware env reading DB path | VERIFIED | Imports get_settings, overrides sqlalchemy.url |
| `app/api/routes_metrics.py` | /metrics Prometheus endpoint | VERIFIED | REQUESTS_TOTAL, REQUEST_DURATION_SECONDS, ACTIVE_AGENTS defined; endpoint returns generate_latest() |
| `app/limiter.py` | Dedicated limiter module | ORPHANED | File exists but nothing imports from it; main.py creates its own Limiter inline |
| `app/logging.py` | structlog with merge_contextvars first | VERIFIED | merge_contextvars is first processor; JSONRenderer in non-debug mode |
| `app/main.py` | docs enabled, heartbeat wired, alembic upgrade, slowapi | PARTIAL | docs/heartbeat/alembic correct; slowapi uses wrong handler |
| `app/middleware.py` | RFC 7807 in all error handlers + Prometheus metrics | PARTIAL | 3 of 4 error handlers use RFC 7807; inline 500 in dispatch() still old format; no Prometheus instrumentation |
| `tests/conftest.py` | Test fixtures | VERIFIED | test_client, admin_headers, agent_api_key fixtures |
| `tests/unit/test_auth_stub.py` | Stub tests | VERIFIED | test_app_imports, test_health_endpoint_reachable |
| `app/database/repositories/base.py` | _get_timestamp returns timezone-aware | VERIFIED | _get_current_timestamp() returns datetime.now(timezone.utc) |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| app/api/routes_p1.py | app/auth/api_key_deps.py | ApiKeyAuth import | WIRED | Line 13 imports, lines 33/81 use |
| app/api/routes_artifacts.py | app/auth/api_key_deps.py | ApiKeyAuth import | WIRED | Line 15 imports, multiple usages |
| app/api/routes_memory.py | app/auth/api_key_deps.py | ApiKeyAuth import | WIRED | Line 13 imports, multiple usages |
| app/api/routes_p2.py | app/auth/api_key_deps.py | ApiKeyAuth import | NOT WIRED | Still uses local _auth, no import from api_key_deps |
| app/main.py | app/services/heartbeat_service.py | HeartbeatService in lifespan | WIRED | Lines 64-67 start_monitoring, line 74 stop_monitoring |
| app/main.py | alembic | command.upgrade in lifespan | WIRED | Lines 44-52 run alembic upgrade head |
| alembic/env.py | app/config.py | get_settings import | WIRED | Line 11 imports, line 18 uses |
| app/middleware.py | app/models/errors.py | ProblemDetail import | WIRED | Line 19 imports ProblemDetail, FieldError, problem_validation, problem_internal |
| app/middleware.py | prometheus_client | REQUESTS_TOTAL.labels() | NOT WIRED | No import of metrics; no .labels().inc() calls |
| app/main.py | routes_metrics.py | include_router | WIRED | Line 15 imports, line 174 includes |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| app/middleware.py | 89-94 | Old error format: "success": False, "error_code": "INTERNAL_ERROR" | Blocker | Inline 500 handler in RequestTimingMiddleware.dispatch() returns non-RFC-7807 format; inconsistent with all other handlers |
| app/middleware.py | 236-252 | get_error_code_from_status function | Warning | Dead code - no longer used after RFC 7807 migration; should be removed |
| app/middleware.py | 43 | bind_contextvars(request_id=...) | Warning | Plan required renaming to trace_id for consistency with RFC 7807 trace_id field |
| app/main.py | 28 | Inline limiter creation | Warning | Duplicates app/limiter.py which was created for this purpose |
| app/main.py | 98 | _rate_limit_exceeded_handler | Blocker | Uses slowapi default plain-text handler instead of custom RFC 7807 handler |
| app/api/routes_p2.py | 22-37 | def _auth / def _sender | Blocker | HARD-10 consolidation incomplete - p2 still has duplicated auth helpers |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| HARD-01 | 01-01 | Auth stub removed, real JWT/API key auth | SATISFIED | app/dependencies.py deleted; ApiKeyAuth from api_key_deps.py used in 4/5 route files |
| HARD-02 | 01-01 | Hardcoded admin creds replaced | SATISFIED | config.py admin_user/admin_password required; admin123 gone |
| HARD-03 | 01-01 | Capabilities stored as proper JSON | SATISFIED | json.dumps used in routes_auth.py and routes_acn.py |
| HARD-04 | 01-02 | Heartbeat monitor wired into lifespan | SATISFIED | main.py lifespan starts/stops HeartbeatService |
| HARD-05 | 01-03 | CORS defaults locked down | SATISFIED | No wildcard; defaults to localhost origins |
| HARD-06 | 01-04 | Schema in versioned migrations | SATISFIED | Alembic initialized, 16-table migration, DDL removed from main.py |
| HARD-07 | 01-05 | OpenAPI /docs enabled | SATISFIED | docs_url="/docs" in main.py |
| HARD-08 | 01-05 | Structured error responses | PARTIAL | 3 of 4 handlers use RFC 7807; inline 500 in middleware dispatch still old format |
| HARD-09 | 01-03, 01-07 | datetime.utcnow() unified | SATISFIED | Zero occurrences in app/ |
| HARD-10 | 01-01 | Duplicate auth consolidated | BLOCKED | routes_p2.py still has local _auth/_sender |
| OSS-02 | 01-05 | API docs via /docs | SATISFIED | OpenAPI endpoint enabled |
| PROD-01 | 01-06 | slowapi rate limiting | BLOCKED | Limiter exists but uses wrong handler; no per-endpoint decorators on auth routes; limiter.py orphaned |
| PROD-02 | 01-06 | Prometheus metrics endpoint | PARTIAL | /metrics endpoint exists but counters are never incremented by middleware |
| PROD-04 | 01-06 | Production logging with structured JSON | PARTIAL | structlog JSON works; merge_contextvars present; but key is request_id not trace_id |

### Orphaned Requirements

None - all requirement IDs from ROADMAP Phase 1 are accounted for in plan frontmatter.

### Human Verification Required

### 1. Auth 401 Enforcement
**Test:** Call a protected endpoint (e.g., POST /v1/tasks) without any auth header
**Expected:** Returns 401 with RFC 7807 JSON body
**Why human:** Need running server to validate full middleware chain behavior

### 2. Heartbeat Offline Detection
**Test:** Register an agent, wait past heartbeat_timeout_sec without sending heartbeat
**Expected:** Agent status changes to "offline" automatically
**Why human:** Requires running server with time passage; async background task behavior

### 3. /docs Swagger UI
**Test:** Visit http://localhost:7788/docs in browser
**Expected:** Swagger UI loads showing all endpoints with auth requirements
**Why human:** Visual verification of UI rendering and completeness

## Gaps Summary

Five gaps prevent phase goal achievement:

1. **routes_p2.py auth consolidation incomplete** (HARD-10) - The file still uses local _auth/_sender helpers instead of the shared ApiKeyAuth dependency. This is the only remaining route file not migrated.

2. **Rate limit handler not RFC 7807** (PROD-01) - main.py uses slowapi's built-in plain-text _rate_limit_exceeded_handler instead of a custom RFC 7807 handler. The app/limiter.py module exists but is orphaned. No @limiter.limit decorators on auth endpoints.

3. **Prometheus metrics not instrumented in middleware** (PROD-02) - The /metrics endpoint exists and returns Prometheus format, but REQUESTS_TOTAL and REQUEST_DURATION_SECONDS are never incremented because middleware.py does not import or call them.

4. **Inline 500 handler still uses old error format** (HARD-08) - The exception handler in RequestTimingMiddleware.dispatch() (lines 87-99) returns {success: False, error_code: "INTERNAL_ERROR"} instead of ProblemDetail. All three standalone handlers were migrated but this inline one was missed.

5. **structlog context key is request_id not trace_id** (PROD-04) - Minor but plan 01-06 explicitly required renaming the contextvars key from request_id to trace_id for consistency with the RFC 7807 trace_id field.

All five gaps share a common root cause: plan 01-06 execution appears to have been only partially completed. The artifacts were created (limiter.py, routes_metrics.py) but the wiring between them and existing code was not finished.

---

_Verified: 2026-04-09T15:00:00Z_
_Verifier: Claude (gsd-verifier)_
