---
phase: 01-backend-hardening
verified: 2026-04-09T15:42:00Z
status: gaps_found
score: 13/14 must-haves verified
re_verification:
  previous_status: gaps_found
  previous_score: 9/14
  gaps_closed:
    - "routes_p2.py _auth/_sender removed - all routes use ApiKeyAuth from api_key_deps.py"
    - "429 response returns RFC 7807 JSON with Retry-After header"
    - "Prometheus REQUESTS_TOTAL and REQUEST_DURATION_SECONDS incremented in middleware"
    - "Inline 500 handler in RequestTimingMiddleware.dispatch() returns ProblemDetail format"
    - "structlog contextvars binds trace_id (not request_id)"
  gaps_remaining:
    - "routes_p2.py discover_tools has SyntaxError - ApiKeyAuth parameter after defaulted parameters"
  regressions:
    - "Plan 01-08 introduced SyntaxError in routes_p2.py discover_tools - app cannot import"
gaps:
  - truth: "All five per-route _auth/_sender helpers are removed - zero occurrences remain and app loads"
    status: partial
    reason: "The _auth/_sender helpers were correctly removed and ApiKeyAuth adopted, but discover_tools() has a Python SyntaxError: key_info: ApiKeyAuth follows tag: Optional[str] = None. The app cannot start."
    artifacts:
      - path: "app/api/routes_p2.py"
        issue: "Line 68-72: discover_tools() places key_info: ApiKeyAuth after optional query params (tag, tool_type) with defaults. Python parser rejects this as 'parameter without a default follows parameter with a default'. Must reorder so ApiKeyAuth comes before the optional params, or move optional params to keyword-only after *."
    missing:
      - "Reorder discover_tools parameters: put key_info: ApiKeyAuth before tag and tool_type, or use * to make tag/tool_type keyword-only"
---

# Phase 1: Backend Hardening Verification Report

**Phase Goal:** The backend is correct, secure, and observable - auth works for real, capabilities are stored as JSON, heartbeat monitor runs, CORS is locked down, schema lives in versioned migrations, and OpenAPI docs are exposed
**Verified:** 2026-04-09T15:42:00Z
**Status:** gaps_found
**Re-verification:** Yes - after gap closure plan 01-08

## Goal Achievement

### Observable Truths (from Success Criteria + Plan Must-Haves)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | A request without valid JWT or API key to protected endpoints returns 401 | VERIFIED | app/auth/api_key_deps.py provides require_api_key with 401 on missing/invalid key; ApiKeyAuth used in all route files |
| 2 | Admin credentials are not hardcoded - server refuses to start without env vars | VERIFIED | config.py lines 37-38: admin_user/admin_password use default=... (Ellipsis = required); import without env vars raises ValidationError for missing fields |
| 3 | Capabilities stored as proper JSON - json.loads() succeeds | VERIFIED | routes_auth.py stores full model via json.dumps(agent_data.model_dump()); routes_acn.py uses _json.dumps for capabilities |
| 4 | Heartbeat monitor starts with app and marks agents offline | VERIFIED | main.py lines 62/70: HeartbeatService wired with start_monitoring()/stop_monitoring() in lifespan |
| 5 | /docs endpoint accessible with correct auth requirements | VERIFIED | main.py line 83: docs_url="/docs", line 84: redoc_url="/redoc" |
| 6 | CORS wildcard gone - locked to specific origins | VERIFIED | config.py line 59: cors_origins defaults to localhost:3000 and localhost:7788 |
| 7 | datetime.utcnow() eliminated codebase-wide | VERIFIED | grep returns 0 matches across entire app/ directory |
| 8 | Schema in versioned Alembic migrations, DDL removed from main.py | VERIFIED | alembic/versions/0001_initial_schema.py exists; main.py runs alembic upgrade head |
| 9 | RFC 7807 error format in all error handlers (validation, HTTP, general, inline 500) | VERIFIED | middleware.py uses ProblemDetail in all 4 handlers; inline 500 at line 102 calls problem_internal() |
| 10 | app/dependencies.py auth stub deleted | VERIFIED | File does not exist (ls returns "No such file or directory") |
| 11 | All per-route _auth/_sender removed, app loads successfully | PARTIAL | _auth/_sender deleted (grep returns 0), ApiKeyAuth imported and used in 5 routes, BUT discover_tools() has SyntaxError preventing app import |
| 12 | slowapi rate limiting wired with RFC 7807 429 + Retry-After | VERIFIED | main.py line 13: from .limiter import limiter; line 96-113: rfc7807_rate_limit_handler with problem_rate_limit() and Retry-After header; routes_auth.py lines 42/180: @limiter.limit decorators |
| 13 | Prometheus metrics instrumented in middleware | VERIFIED | middleware.py line 20: imports REQUESTS_TOTAL, REQUEST_DURATION_SECONDS; lines 64-71: .labels().inc() and .observe() on success path; lines 98-99: same on error path |
| 14 | structlog trace_id in contextvars on every request log | VERIFIED | middleware.py line 44: bind_contextvars(trace_id=request_id); grep confirms zero occurrences of bind_contextvars(request_id=) |

**Score:** 13/14 truths verified (1 partial due to SyntaxError regression)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `app/auth/api_key_deps.py` | Shared API key dependency | VERIFIED | Contains require_api_key, resolve_agent_id, ApiKeyAuth |
| `app/config.py` | admin_user/admin_password required; CORS locked | VERIFIED | admin fields use default=...; CORS defaults to localhost |
| `app/models/errors.py` | RFC 7807 ProblemDetail + helpers | VERIFIED | Full implementation with problem_rate_limit, problem_internal, etc. |
| `alembic/versions/0001_initial_schema.py` | Initial migration with tables | VERIFIED | File exists |
| `app/api/routes_metrics.py` | /metrics Prometheus endpoint | VERIFIED | REQUESTS_TOTAL, REQUEST_DURATION_SECONDS, ACTIVE_AGENTS defined; endpoint returns generate_latest() |
| `app/limiter.py` | Dedicated limiter module | WIRED | main.py imports from it (line 13); routes_auth.py imports from it (line 33) |
| `app/logging.py` | structlog with merge_contextvars | VERIFIED | merge_contextvars present (grep count = 1) |
| `app/main.py` | docs enabled, heartbeat wired, alembic, slowapi RFC 7807 | VERIFIED | All wiring correct; rfc7807_rate_limit_handler with Retry-After |
| `app/middleware.py` | RFC 7807 all handlers + Prometheus metrics + trace_id | VERIFIED | All 4 error handlers use ProblemDetail; REQUESTS_TOTAL.labels x2; trace_id bound |
| `app/api/routes_p2.py` | P2 routes using shared ApiKeyAuth | BROKEN | SyntaxError at line 71: discover_tools() has parameter ordering issue |
| `app/api/routes_auth.py` | Rate limiting on register/login | VERIFIED | @limiter.limit("10/minute") on register, @limiter.limit("20/minute") on login |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| app/api/routes_p2.py | app/auth/api_key_deps.py | ApiKeyAuth import | WIRED | Line 14 imports ApiKeyAuth, resolve_agent_id; used in 5 routes (but SyntaxError blocks import) |
| app/middleware.py | app/api/routes_metrics.py | Prometheus metric imports | WIRED | Line 20 imports REQUESTS_TOTAL, REQUEST_DURATION_SECONDS; .labels().inc() x2, .observe() x2 |
| app/main.py | app/limiter.py | limiter import | WIRED | Line 13: from .limiter import limiter |
| app/main.py | RateLimitExceeded handler | rfc7807_rate_limit_handler | WIRED | Line 113: app.add_exception_handler(RateLimitExceeded, rfc7807_rate_limit_handler) |
| app/api/routes_auth.py | app/limiter.py | limiter import + decorators | WIRED | Line 33 imports; lines 42, 180 apply @limiter.limit |
| app/middleware.py | structlog.contextvars | trace_id binding | WIRED | Line 44: bind_contextvars(trace_id=request_id) |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| App imports without error | AGENTHUB_ADMIN_USER/PASSWORD set, python3 -c "from app.main import app" | SyntaxError in routes_p2.py line 71 | FAIL |
| Admin credentials required | python3 -c "from app.main import app" (no env vars) | ValidationError: admin_user/admin_password required | PASS (correct rejection) |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| HARD-01 | 01-00, 01-01 | Auth stub removed, real JWT/API key auth | SATISFIED | app/dependencies.py deleted; ApiKeyAuth used across all route files |
| HARD-02 | 01-00, 01-01 | Hardcoded admin creds replaced | SATISFIED | config.py admin_user/admin_password required; app refuses start without them |
| HARD-03 | 01-01 | Capabilities stored as proper JSON | SATISFIED | json.dumps used in routes_auth.py and routes_acn.py |
| HARD-04 | 01-02 | Heartbeat monitor wired into lifespan | SATISFIED | main.py lifespan starts/stops HeartbeatService |
| HARD-05 | 01-03 | CORS defaults locked down | SATISFIED | No wildcard; defaults to localhost origins |
| HARD-06 | 01-04 | Schema in versioned migrations | SATISFIED | Alembic initialized, migration file present, main.py runs upgrade head |
| HARD-07 | 01-05 | OpenAPI /docs enabled | SATISFIED | docs_url="/docs" in main.py |
| HARD-08 | 01-05, 01-08 | Structured error responses (RFC 7807) | SATISFIED | All 4 error handlers use ProblemDetail including inline 500 |
| HARD-09 | 01-03, 01-07 | datetime.utcnow() eliminated | SATISFIED | Zero occurrences in app/ |
| HARD-10 | 01-01, 01-08 | Duplicate auth consolidated | BLOCKED | _auth/_sender removed from routes_p2.py, ApiKeyAuth adopted, but SyntaxError blocks import |
| OSS-02 | 01-05 | API docs via /docs | SATISFIED | OpenAPI endpoint enabled |
| PROD-01 | 01-06, 01-08 | slowapi rate limiting | SATISFIED | limiter.py wired, RFC 7807 429 handler with Retry-After, auth routes decorated |
| PROD-02 | 01-06, 01-08 | Prometheus metrics endpoint | SATISFIED | /metrics endpoint exists; REQUESTS_TOTAL and REQUEST_DURATION_SECONDS incremented in middleware |
| PROD-04 | 01-06, 01-08 | Production logging with structured JSON | SATISFIED | structlog JSON configured; merge_contextvars first; trace_id bound in contextvars |

### Orphaned Requirements

None - all 14 requirement IDs from ROADMAP Phase 1 are accounted for across plan frontmatter.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| app/api/routes_p2.py | 68-72 | SyntaxError: key_info: ApiKeyAuth after defaulted params | Blocker | App cannot import routes_p2.py - prevents server startup entirely |

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

### 4. Rate Limit 429 Response
**Test:** Hit POST /v1/auth/agent/register more than 10 times in one minute
**Expected:** 429 response with RFC 7807 JSON body and Retry-After header
**Why human:** Requires sending real HTTP requests and observing rate limit behavior

## Gaps Summary

One gap remains, introduced as a regression by plan 01-08:

1. **routes_p2.py SyntaxError** (HARD-10) - The discover_tools() function at line 68 places `key_info: ApiKeyAuth` (no default) after `tag: Optional[str] = None` and `tool_type: Optional[str] = None` (with defaults). Python's parser rejects this as "parameter without a default follows parameter with a default". The entire app cannot start because routes_p2.py fails to import. The fix is to reorder parameters so `key_info: ApiKeyAuth` comes first, or make the optional query params keyword-only by adding `*` before them.

All 5 original gaps from the initial verification have been successfully closed at the code level. This single regression is the only remaining blocker.

---

_Verified: 2026-04-09T15:42:00Z_
_Verifier: Claude (gsd-verifier)_
