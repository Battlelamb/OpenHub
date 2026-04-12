---
phase: 01-backend-hardening
plan: 08
subsystem: api, observability, auth
tags: [prometheus, structlog, rfc7807, slowapi, rate-limiting]

requires:
  - phase: 01-backend-hardening (plans 01-06)
    provides: "routes_metrics.py metrics definitions, limiter.py module, api_key_deps.py shared auth, errors.py ProblemDetail model"
provides:
  - "Prometheus REQUESTS_TOTAL and REQUEST_DURATION_SECONDS incremented on every request via middleware"
  - "RFC 7807 format for all error responses including inline 500 and 429"
  - "Shared ApiKeyAuth used in all route files (no more per-route _auth helpers)"
  - "Rate limiting on auth endpoints (register 10/min, login 20/min)"
  - "structlog trace_id in contextvars on every request"
affects: [02-frontend-dashboard]

tech-stack:
  added: []
  patterns: ["Prometheus metrics in middleware dispatch loop", "RFC 7807 rate limit handler with Retry-After header"]

key-files:
  created: []
  modified:
    - app/middleware.py
    - app/main.py
    - app/api/routes_p2.py
    - app/api/routes_auth.py

key-decisions:
  - "request parameter reordered to first position in auth routes for slowapi compatibility"

patterns-established:
  - "All route files use ApiKeyAuth type alias from api_key_deps.py - no per-route _auth helpers"
  - "Prometheus counters/histograms recorded in middleware, not in individual routes"

requirements-completed: [HARD-08, HARD-10, PROD-01, PROD-02, PROD-04]

duration: 3min
completed: 2026-04-09
---

# Phase 1 Plan 08: Gap Closure Summary

**Wired Prometheus metrics in middleware, RFC 7807 for 500/429 handlers, consolidated routes_p2 auth to ApiKeyAuth, rate-limited auth endpoints**

## Performance

- **Duration:** 3 min
- **Started:** 2026-04-09T15:34:00Z
- **Completed:** 2026-04-09T15:37:47Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- All 5 verification gaps from 01-VERIFICATION.md closed (HARD-08, HARD-10, PROD-01, PROD-02, PROD-04)
- Prometheus REQUESTS_TOTAL and REQUEST_DURATION_SECONDS now increment on every request (success + error paths)
- routes_p2.py migrated from local _auth/_sender to shared ApiKeyAuth/resolve_agent_id - all route files now use the same auth dependency
- main.py uses limiter from app/limiter.py (no longer orphaned) with RFC 7807 429 handler including Retry-After header
- structlog binds trace_id (not request_id) in contextvars for RFC 7807 consistency

## Task Commits

Each task was committed atomically:

1. **Task 1: Fix middleware.py - Prometheus instrumentation, RFC 7807 500 handler, trace_id contextvars** - `6f92c1a` (fix)
2. **Task 2: Fix main.py rate limiter and routes_p2.py auth consolidation** - `f471177` (fix)

## Files Created/Modified
- `app/middleware.py` - Added Prometheus metric recording, RFC 7807 inline 500 handler, trace_id contextvars, removed dead get_error_code_from_status
- `app/main.py` - Import limiter from app/limiter.py, RFC 7807 429 handler with Retry-After header
- `app/api/routes_p2.py` - Replaced _auth/_sender with ApiKeyAuth/resolve_agent_id from api_key_deps
- `app/api/routes_auth.py` - Added @limiter.limit to register (10/min) and login (20/min) endpoints

## Decisions Made
- Reordered `request: Request` to first parameter in auth routes for slowapi compatibility (slowapi requires Request as first arg)

## Deviations from Plan
None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Phase 1 backend hardening is complete (14/14 verification truths should now pass)
- Ready for Phase 2 (frontend dashboard) or Phase 3 (vector DB)

---
*Phase: 01-backend-hardening*
*Completed: 2026-04-09*
