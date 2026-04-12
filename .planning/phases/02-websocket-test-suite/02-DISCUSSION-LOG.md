# Phase 2: WebSocket + Test Suite - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md - this log preserves the alternatives considered.

**Date:** 2026-04-11
**Phase:** 02-websocket-test-suite
**Areas discussed:** WebSocket protocol design, Event granularity, Test scope and strategy, ConnectionManager design, Max connections + backpressure, Error handling over WebSocket, Monitoring + observability

---

## WebSocket Protocol Design

### Message Format

| Option | Description | Selected |
|--------|-------------|----------|
| Same JSON format | Reuse {event, agent_id, timestamp, data} for UI clients too | yes |
| Typed envelope with sequence | Add {type, seq, payload} wrapper with sequence numbers | |
| You decide | Claude picks | |

**User's choice:** Same JSON format
**Notes:** Consistency with existing agent endpoint, simple to implement and debug

### Reconnection Strategy

| Option | Description | Selected |
|--------|-------------|----------|
| No replay - fresh state only | Client fetches current state via REST on reconnect | |
| Short replay buffer | Server keeps last N events per client | |
| You decide | Claude picks | yes |

**User's choice:** You decide
**Notes:** Delegated to Claude's discretion

---

## Event Granularity

### Push Model

| Option | Description | Selected |
|--------|-------------|----------|
| Key lifecycle only | Only broadcast on state transitions | |
| All mutations | Broadcast on every DB write | |
| Tiered events | Critical push immediately, non-critical batch every 5s | yes |

**User's choice:** Tiered events
**Notes:** Critical events (status changes) immediate, non-critical (heartbeat, metadata) batched at 5-second intervals

### Task Progress

| Option | Description | Selected |
|--------|-------------|----------|
| No progress events | Tasks have status but no percentage | |
| Progress as separate event | New task_progress event with percentage field | yes |
| You decide | Claude picks | |

**User's choice:** Progress as separate event
**Notes:** Enables progress bars in dashboard UI

### Batch Interval

| Option | Description | Selected |
|--------|-------------|----------|
| 5 seconds | Good balance of responsiveness and efficiency | yes |
| 2 seconds | More responsive but higher volume | |
| 10 seconds | Lower overhead but may feel stale | |

**User's choice:** 5 seconds

---

## Test Scope and Strategy

### Database Approach

| Option | Description | Selected |
|--------|-------------|----------|
| Real in-memory SQLite | conftest.py already sets :memory: path | yes |
| Mock repositories | Mock repository layer, test service logic | |
| Both layers | Unit mocks + integration real DB | |

**User's choice:** Real in-memory SQLite
**Notes:** Phase 1 context explicitly rejected mocks (learned from prior incident)

### Coverage Target

| Option | Description | Selected |
|--------|-------------|----------|
| Critical paths only | Cover TEST-01 through TEST-05 requirements | |
| 80% line coverage | Enforce 80% across touched modules | |
| You decide | Claude determines | yes |

**User's choice:** You decide

---

## ConnectionManager Design

### Pool Architecture

| Option | Description | Selected |
|--------|-------------|----------|
| Separate pools | Dict for agents, Dict for UI clients | yes |
| Single pool with tags | One dict with connection type tags | |
| You decide | Claude picks | |

**User's choice:** Separate pools
**Notes:** Matches the two-endpoint design (/v1/ws for agents, /v1/ws/ui for dashboard)

### Token Expiry Behavior

| Option | Description | Selected |
|--------|-------------|----------|
| Disconnect with close frame | Send close frame with 4001 code | |
| Grace period + warning | Send token_expiring event 60s before, then disconnect | yes |
| Ignore until next message | Only check on incoming messages | |

**User's choice:** Grace period + warning
**Notes:** Smoother UX - client gets time to refresh token before disconnection

---

## Max Connections + Backpressure

### Connection Limits

| Option | Description | Selected |
|--------|-------------|----------|
| Soft limits in config | AGENTHUB_MAX_WS_AGENTS=100, AGENTHUB_MAX_WS_UI=10 | yes |
| No limits | Accept all connections | |
| You decide | Claude picks | |

**User's choice:** Soft limits in config
**Notes:** Log warning at 80%, reject at limit with 4002 close code

### Slow Client Handling

| Option | Description | Selected |
|--------|-------------|----------|
| Drop events for slow clients | Drop oldest non-critical, send events_dropped notification | yes |
| Disconnect slow clients | Close connection after timeout | |
| You decide | Claude picks | |

**User's choice:** Drop events for slow clients

---

## Error Handling over WebSocket

| Option | Description | Selected |
|--------|-------------|----------|
| Error event type | Send error as regular event message | |
| Close frame codes | Use WebSocket close frames for all errors | |
| Both - errors vs fatal | Recoverable as events, fatal as close frames | yes |

**User's choice:** Both - errors vs fatal
**Notes:** 4001=auth_expired, 4002=limit_reached, 4003=server_error for fatal; event messages for recoverable

---

## Monitoring + Observability

| Option | Description | Selected |
|--------|-------------|----------|
| Connection gauges + event counters | ws_connections_active, ws_events_sent_total, ws_errors_total | yes |
| Minimal - just connection count | Single gauge | |
| You decide | Claude determines | |

**User's choice:** Full metrics suite

---

## Claude's Discretion

- Reconnection strategy (fresh state vs replay buffer)
- Test coverage depth beyond TEST-01 through TEST-05
- Event batching implementation details
- WebSocket test fixture design

## Deferred Ideas

None - discussion stayed within phase scope
