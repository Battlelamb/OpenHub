# Phase 05-04: Graceful Shutdown

**Goal:** Stopping the server drains in-flight tasks and closes WebSocket connections cleanly — no tasks are silently dropped.

**Roadmap requirement:** Phase 5, Success Criteria #4

## Slices

### 05-04-01: Lifespan shutdown hook
- Wire shutdown logic into FastAPI lifespan (app/main.py)
- On shutdown signal:
  1. Stop accepting new connections
  2. Close all WebSocket connections with close code 1001 (going away)
  3. Drain in-flight tasks: for each task with status=running, set status=queued (return to queue)
  4. Stop heartbeat monitor
  5. Log shutdown sequence with structlog

### 05-04-02: Task drain service
- Add `drain_tasks()` to TaskService
- Query all tasks WHERE status IN ('claimed', 'running')
- Update them back to 'queued' with reason='server_shutdown'
- Return count of drained tasks for logging

### 05-04-03: WebSocket drain
- Add `drain_all()` to ConnectionManager
- Send close frame to all connected clients
- Wait for close acknowledgment (with timeout)
- Clear connection pools

### 05-04-04: Tests
- Unit test: drain_tasks() resets claimed/running tasks to queued
- Unit test: drain_tasks() with no active tasks returns 0
- Unit test: ConnectionManager.drain_all() closes all connections
- Integration test: lifespan shutdown sequence order
- Integration test: tasks survive shutdown (drain → restart → still queued)

## Success Criteria
- [ ] `drain_tasks()` resets running/claimed tasks to queued
- [ ] WebSocket connections receive close frame on shutdown
- [ ] Shutdown sequence is logged (structlog)
- [ ] All existing tests still pass
- [ ] New tests pass for drain logic
