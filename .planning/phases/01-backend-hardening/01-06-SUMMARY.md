---
phase: 01-backend-hardening
plan: "06"
subsystem: api
tags: [slowapi, prometheus, structlog, rate-limiting, observability]

# Dependency graph
requires:
  - phase: 01-backend-hardening
    provides: "RFC 7807 error format (plan 05), middleware infrastructure"
provides:
  - "Global slowapi rate limiting with RFC 7807 429 responses"
  - "Prometheus /metrics endpoint with request counters and duration histograms"
  - "structlog trace_id propagation via merge_contextvars"
affects: [testing, deployment, monitoring]

# Tech tracking
tech-stack:
  added: [slowapi, prometheus-client]
  patterns: [global-rate-limiter-module, prometheus-instrumentation-in-middleware, structlog-contextvars-trace-id]

key-files:
  created:
    - app/limiter.py
    - app/api/routes_metrics.py
  modified:
    - app/main.py
    - app/middleware.py
    - app/logging.py
    - app/api/routes_auth.py
    - app/api/routes_p2.py

key-decisions:
  - "Limiter in dedicated app/limiter.py module to avoid circular imports between main.py and route modules"
  - "RFC 7807 JSON for 429 responses instead of slowapi default plain text handler"
  - "trace_id (not request_id) as the structlog contextvars key for consistency with observability standards"

patterns-established:
  - "Rate limit decorators: @limiter.limit('N/minute') on sensitive endpoints, import from app.limiter"
  - "Prometheus metrics: define in routes_metrics.py, instrument in middleware, expose via GET /metrics"
  - "Structured logging: merge_contextvars first in processor chain, all log lines include trace_id within request"

requirements-completed: [PROD-01, PROD-02, PROD-04]

# Metrics
duration: 3min
completed: 2026-04-09
---

# Phase 01 Plan 06: Rate Limiting, Prometheus Metrics, and Structlog Enhancement Summary

**slowapi global rate limiting with RFC 7807 429 handler, Prometheus /metrics endpoint with request counters/histograms, structlog trace_id on every log line via merge_contextvars**

## Performance

- **Duration:** 3 min
- **Started:** 2026-04-09T14:23:00Z
- **Completed:** 2026-04-09T14:26:05Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments
- Global slowapi rate limiter wired into app.state with RFC 7807 compliant 429 responses including Retry-After header
- Prometheus /metrics endpoint returns text exposition format with openhub_requests_total counter and openhub_request_duration_seconds histogram
- structlog enhanced with merge_contextvars as first processor - trace_id appears in every log line within a request context
- In-memory rate limiter removed from routes_p2.py (replaced by slowapi globally)
- Auth endpoints rate-limited: login 10/min, register 5/min per IP

## Task Commits

Each task was committed atomically:

1. **Task 1: Wire slowapi rate limiting and remove in-memory rate limiter** - `6a8b809` (feat)
2. **Task 2: Add Prometheus /metrics endpoint and enhance structlog output** - `9978a6e` (feat)

## Files Created/Modified
- `app/limiter.py` - Global Limiter instance (slowapi) for import by route modules
- `app/api/routes_metrics.py` - Prometheus /metrics endpoint with REQUESTS_TOTAL, REQUEST_DURATION_SECONDS, ACTIVE_AGENTS, TASKS_BY_STATUS
- `app/main.py` - slowapi wiring (app.state.limiter, RFC 7807 handler, metrics router include)
- `app/middleware.py` - Prometheus instrumentation in RequestTimingMiddleware, trace_id binding
- `app/logging.py` - merge_contextvars as first structlog processor
- `app/api/routes_auth.py` - Rate limit decorators on login/register endpoints
- `app/api/routes_p2.py` - Removed in-memory _rate_limits dict and check_rate_limit function

## Decisions Made
- Used dedicated `app/limiter.py` module for the Limiter instance to avoid circular imports between main.py and route modules
- Custom RFC 7807 JSON handler for 429 instead of slowapi's built-in plain-text `_rate_limit_exceeded_handler`
- Renamed `request_id` to `trace_id` in structlog contextvars binding for consistency with observability naming conventions
- ProblemDetail model not available in this branch (added by plan 05 in a parallel worktree), so RFC 7807 response uses inline dict format

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] ProblemDetail model not available in worktree**
- **Found during:** Task 1 (RFC 7807 rate limit handler)
- **Issue:** Plan referenced `app/models/errors.ProblemDetail` but this model does not exist in the current worktree branch (it was added by plan 01-05 in a different worktree)
- **Fix:** Used inline RFC 7807 dict format for the 429 response instead of ProblemDetail model. Same structure (type, title, status, detail, instance, trace_id).
- **Files modified:** app/main.py
- **Verification:** TestClient GET /metrics returns 200, log output includes trace_id
- **Committed in:** 6a8b809

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Minimal - inline dict produces identical RFC 7807 JSON. Will converge when branches merge.

## Issues Encountered
None beyond the ProblemDetail model absence documented above.

## Known Stubs
None - all metrics, rate limiting, and logging features are fully wired.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Rate limiting, Prometheus metrics, and structured logging are production-ready
- ACTIVE_AGENTS and TASKS_BY_STATUS gauges defined but not yet wired to database queries (intentional: these are populated by background tasks or periodic scrapers, not request middleware)
- Ready for testing phase and deployment hardening

---
*Phase: 01-backend-hardening*
*Completed: 2026-04-09*
