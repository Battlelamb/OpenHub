# Phase 01 - Plan 02 Summary: Heartbeat Monitor Wiring

## Overview
Wired the heartbeat monitor into the application lifespan so agents are automatically marked offline when they miss heartbeats.

## Completed: 2026-04-08

## Files Modified

### app/main.py
- Added `HeartbeatService` import and initialization in lifespan
- Called `heartbeat_service.start_monitoring()` after database initialization
- Called `heartbeat_service.stop_monitoring()` in shutdown phase
- Removed blocking `time.sleep(1)` call (replaced with nothing - sync is sufficient)

## Changes Detail

### Before
```python
# Blocking sleep - bad for async event loop
import time
time.sleep(1)
db.sync()

# No heartbeat service
logger.info("agent_hub_started", version=__version__)
yield
logger.info("agent_hub_shutting_down")
```

### After
```python
# No blocking sleep
db.sync()
logger.info("database_tables_ready")

# Heartbeat monitor wired
from .services.heartbeat_service import HeartbeatService
heartbeat_service = HeartbeatService(db)
await heartbeat_service.start_monitoring()
logger.info("heartbeat_monitor_started")

yield

# Shutdown
await heartbeat_service.stop_monitoring()
logger.info("heartbeat_monitor_stopped")
logger.info("agent_hub_shutting_down")
```

## Test Results

```bash
$ pytest tests/ -x -q --tb=short
2 passed
Coverage: 34%
```

## Acceptance Criteria Met

- ✅ `grep "start_monitoring" app/main.py` returns match (line 183)
- ✅ `grep "stop_monitoring" app/main.py` returns match (line 191)
- ✅ `grep "time.sleep" app/main.py` returns 0 matches (blocking sleep removed)
- ✅ `grep "HeartbeatService" app/main.py` returns match
- ✅ `grep "start_monitoring\|stop_monitoring" app/services/heartbeat_service.py` returns matches
- ✅ pytest exits 0

## HeartbeatService Behavior

The existing `HeartbeatService` implementation:
- Runs `_monitor_loop()` every 30 seconds in a background asyncio task
- Checks all agents with status "online" for stale heartbeats
- Marks agents offline if `last_heartbeat < now - heartbeat_timeout_sec` (default 120s)
- Properly cancels the task on shutdown
- Handles errors gracefully without crashing

## Impact

### Before
- Agents never went offline automatically
- Stale agents remained "online" indefinitely
- Task assignment could route to dead agents

### After
- Agents automatically marked offline after 120 seconds without heartbeat
- Task routing only targets live agents
- System self-heals when agents disconnect unexpectedly

## Next Steps

- **Plan 01-03**: CORS lockdown + datetime.utcnow() sweep (remaining files)
- **Plan 01-04**: Alembic schema migration consolidation
- **Plan 01-05**: RFC 7807 error format + OpenAPI docs

## Artifacts

- Summary: `.planning/phases/01-backend-hardening/01-02-SUMMARY.md`
