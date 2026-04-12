---
phase: 01-backend-hardening
plan: "07"
subsystem: api
tags: [datetime, timezone, utcnow, python-stdlib]

requires:
  - phase: 01-backend-hardening
    provides: "Plan 01-03 established datetime.now(timezone.utc) pattern in 4 high-impact files"
provides:
  - "Zero datetime.utcnow() occurrences across entire app/ directory"
  - "All datetime operations use timezone-aware datetime.now(timezone.utc)"
  - "Naive/aware comparison bug in routes_memory.py TTL check fixed"
affects: [testing, deployment]

tech-stack:
  added: []
  patterns: ["datetime.now(timezone.utc) as canonical timestamp pattern across all modules"]

key-files:
  created: []
  modified:
    - app/database/repositories/acn_nodes.py
    - app/database/repositories/agents.py
    - app/database/repositories/base.py
    - app/auth/dependencies.py
    - app/api/routes_memory.py
    - app/api/routes_auth.py
    - app/api/routes_health.py
    - app/models/responses.py
    - app/services/discovery_service.py
    - app/services/hatchet_service.py
    - app/services/heartbeat_service.py
    - app/services/workflow_coordinator.py
    - app/services/event_delivery_service.py
    - app/services/agent_service.py
    - app/services/task_service.py
    - app/services/remote_agent_service.py

key-decisions:
  - "Fixed all remaining files including those listed as Plan 01-03 scope since they still had utcnow on this branch"

patterns-established:
  - "datetime.now(timezone.utc): canonical timestamp pattern for all new code in app/"
  - "from datetime import datetime, timezone: standard import pattern in all modules using timestamps"

requirements-completed: [HARD-09]

duration: 2min
completed: 2026-04-09
---

# Phase 01 Plan 07: Datetime UTC Sweep Summary

**Codebase-wide datetime.utcnow() elimination - 16 files converted to timezone-aware datetime.now(timezone.utc) with zero remaining occurrences**

## Performance

- **Duration:** 2 min
- **Started:** 2026-04-09T14:16:21Z
- **Completed:** 2026-04-09T14:18:40Z
- **Tasks:** 2
- **Files modified:** 16

## Accomplishments
- Eliminated all datetime.utcnow() calls from every file in app/ (was ~55 occurrences across 16 files)
- Fixed naive/aware datetime comparison bug in routes_memory.py TTL expiry check that would cause TypeError at runtime
- Established timezone-aware datetime as the only timestamp pattern, preventing future naive/aware mismatch crashes

## Task Commits

Each task was committed atomically:

1. **Task 1: Replace datetime.utcnow() in repository and auth files** - `1982cfe` (fix)
2. **Task 2: Replace datetime.utcnow() in service files and complete sweep** - `c4b22ba` (fix)

## Files Created/Modified
- `app/database/repositories/acn_nodes.py` - Heartbeat update uses timezone-aware datetime
- `app/database/repositories/agents.py` - Heartbeat update uses timezone-aware datetime
- `app/database/repositories/base.py` - _get_current_timestamp() returns timezone-aware datetime
- `app/auth/dependencies.py` - last_seen in AuthenticatedAgent uses timezone-aware datetime
- `app/api/routes_memory.py` - TTL expiry check uses timezone-aware comparison with proper fromisoformat handling
- `app/api/routes_auth.py` - Agent registration timestamps use timezone-aware datetime
- `app/api/routes_health.py` - Health check timestamps use timezone-aware datetime
- `app/models/responses.py` - SuccessResponse/ErrorResponse default_factory uses timezone-aware datetime
- `app/services/discovery_service.py` - Relevance scoring and health checks use timezone-aware datetime
- `app/services/hatchet_service.py` - All 13 workflow lifecycle timestamps use timezone-aware datetime
- `app/services/heartbeat_service.py` - Heartbeat timeout threshold and stats use timezone-aware datetime
- `app/services/workflow_coordinator.py` - Coordination timestamps use timezone-aware datetime
- `app/services/event_delivery_service.py` - Event payload timestamps use timezone-aware datetime
- `app/services/agent_service.py` - Agent creation timestamps use timezone-aware datetime
- `app/services/task_service.py` - All task lifecycle timestamps use timezone-aware datetime
- `app/services/remote_agent_service.py` - Remote agent timestamps use timezone-aware datetime

## Decisions Made
- Fixed all files in app/ including those originally scoped to Plan 01-03, because those files still had utcnow() on this branch and the plan requires zero remaining occurrences codebase-wide

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Fixed 6 additional files not in plan scope**
- **Found during:** Task 2 (final sweep)
- **Issue:** routes_auth.py, routes_health.py, base.py, agent_service.py, task_service.py, remote_agent_service.py still had datetime.utcnow() - likely Plan 01-03 changes not present on this branch
- **Fix:** Applied same mechanical replacement pattern to all 6 files
- **Files modified:** Listed above
- **Verification:** `grep -rn "datetime.utcnow()" app/` returns 0 matches
- **Committed in:** c4b22ba (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (Rule 2 - missing critical for correctness)
**Impact on plan:** Essential for achieving the zero-occurrence guarantee. No scope creep.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Known Stubs
None

## Next Phase Readiness
- All datetime operations across the entire codebase now use timezone-aware timestamps
- No risk of naive/aware TypeError crashes in heartbeat monitoring, task lease checks, or TTL expiry
- Ready for any phase that depends on consistent datetime handling

---
*Phase: 01-backend-hardening*
*Completed: 2026-04-09*
