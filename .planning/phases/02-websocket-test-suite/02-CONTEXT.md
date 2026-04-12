# Phase 2: WebSocket + Test Suite - Context

**Gathered:** 2026-04-11
**Status:** Ready for planning

<domain>
## Phase Boundary

Dashboard clients connect to a stable WebSocket endpoint and receive live events for agent status changes, task lifecycle transitions, and workflow progress. The backend also gets a comprehensive test suite covering auth, capability matching, and the task/agent lifecycle. No new REST endpoints or features beyond WebSocket broadcasting and test coverage.

</domain>

<decisions>
## Implementation Decisions

### WebSocket Protocol
- **D-01:** Reuse the same JSON event format as the existing agent endpoint: `{event, agent_id, timestamp, data}` - same format for both agent and UI clients
- **D-02:** New `/v1/ws/ui` endpoint for dashboard clients, separate from existing `/v1/ws` for agents
- **D-03:** JWT authentication via initial-message frame (WS-01) - no token in URL query string or server logs

### Reconnection Strategy (Claude's Discretion)
- **D-04:** Claude decides reconnection approach - likely fresh state via REST on reconnect (no server-side event buffering)

### Event Model - Tiered Broadcasting
- **D-05:** Critical events push immediately: agent status changes (online/offline/idle), task status transitions (queued/claimed/running/completed/failed)
- **D-06:** Non-critical events batch every 5 seconds: heartbeat timestamp updates, metadata changes
- **D-07:** Task progress is a separate event type (`task_progress` with percentage field) - agents report progress, enables progress bars in UI
- **D-08:** Workflow step progress events broadcast to UI (WS-06)

### ConnectionManager
- **D-09:** Separate connection pools for agents vs UI clients - `Dict[str, WebSocket]` each. `broadcast_to_ui()` only hits UI pool
- **D-10:** Replace current module-level `_connections` dict with a ConnectionManager class (WS-02) with explicit connect/disconnect lifecycle
- **D-11:** JWT expiry handling: send `token_expiring` warning event 60s before expiry. If no refresh within grace period, disconnect with close frame

### Connection Limits and Backpressure
- **D-12:** Configurable soft limits via env vars: `AGENTHUB_MAX_WS_AGENTS=100`, `AGENTHUB_MAX_WS_UI=10`. Log warning at 80%, reject at limit with 4002 close code
- **D-13:** Slow UI clients: drop oldest non-critical events when send buffer exceeds threshold. Send `events_dropped` notification to affected client

### Error Handling
- **D-14:** Dual error communication: recoverable errors as event messages (`{event: 'error', data: {code, message, detail}}`), fatal errors as WebSocket close frames (4001=auth_expired, 4002=limit_reached, 4003=server_error)

### Monitoring
- **D-15:** WebSocket-specific Prometheus metrics: `ws_connections_active` (gauge by type: agent/ui), `ws_events_sent_total` (counter by event type), `ws_errors_total` (counter). Extends Phase 1 Prometheus setup

### Test Strategy
- **D-16:** Integration tests use real in-memory SQLite (conftest.py already sets `:memory:` path). No mocked DB layer - Phase 1 context explicitly rejected mocks
- **D-17:** Coverage target is requirement-driven, not percentage-driven: cover TEST-01 through TEST-05 requirements. Claude determines appropriate scope

### Claude's Discretion
- Reconnection strategy (D-04) - fresh state vs replay buffer
- Test coverage depth beyond required TEST-01 through TEST-05
- Specific WebSocket close frame code values beyond the three specified
- Event batching implementation details (timer-based vs threshold-based)
- WebSocket test fixtures design (real or mock WS connections)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### WebSocket Implementation
- `app/api/routes_websocket.py` - Existing /v1/ws agent endpoint with connection tracking, event format, and broadcast helpers
- `app/services/event_delivery_service.py` - Broadcast pattern (iterate mappings, deliver to callbacks) - model for broadcast_to_ui()

### Auth System (for WS JWT auth)
- `app/auth/jwt_auth.py` - JWTManager with token lifecycle (create, verify, refresh, blacklist)
- `app/auth/api_key_deps.py` - ApiKeyAuth dependency pattern to follow for WS auth
- `app/auth/dependencies.py` - Real auth implementation

### Services (event sources for broadcasts)
- `app/services/agent_service.py` - Agent lifecycle operations (status changes trigger WS-04)
- `app/services/task_service.py` - Task lifecycle operations (status changes trigger WS-05)
- `app/services/heartbeat_service.py` - Heartbeat monitoring (offline detection triggers WS-04)
- `app/services/workflow_coordinator.py` - Workflow coordination (step progress triggers WS-06)
- `app/services/capability_matcher.py` - Capability matching logic (test target for TEST-02)

### Test Infrastructure
- `tests/conftest.py` - Session-scoped fixtures (test_client, admin_headers, agent_api_key)
- `tests/unit/test_auth_stub.py` - Existing stub tests (pattern to follow)

### Observability (Phase 1 foundation to extend)
- `app/api/routes_metrics.py` - Prometheus endpoint with REQUESTS_TOTAL, REQUEST_DURATION_SECONDS
- `app/middleware.py` - Prometheus instrumentation in RequestTimingMiddleware
- `app/logging.py` - structlog setup with trace_id binding

### Architecture
- `.planning/codebase/ARCHITECTURE.md` - Layered architecture patterns
- `.planning/codebase/CONVENTIONS.md` - Code style, naming patterns

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `routes_websocket.py`: push_event(), broadcast_event(), get_connected_count() - can be refactored into ConnectionManager
- `event_delivery_service.py`: broadcast pattern iterates webhook mappings - same pattern for broadcast_to_ui()
- `conftest.py`: test_client, admin_headers, agent_api_key fixtures ready for expansion
- `app/limiter.py`: Global limiter instance pattern - ConnectionManager can follow same singleton approach

### Established Patterns
- Service layer: routes delegate to services, services to repositories
- FastAPI Depends() for dependency injection
- Pydantic models for request/response validation
- structlog with trace_id for all logging

### Integration Points
- ConnectionManager replaces module-level _connections dict in routes_websocket.py
- Task service operations need to call broadcast_to_ui() after status transitions
- Agent service operations need to call broadcast_to_ui() after status changes
- Heartbeat monitor offline detection triggers broadcast_to_ui()
- Prometheus metrics endpoint extends with WS gauges and counters

</code_context>

<specifics>
## Specific Ideas

- Agent bridge (agent_bridge.py) uses HTTP polling (10s interval) for remote agents - WebSocket is for dashboard UI only, not a replacement for agent communication
- The tiered event model (immediate critical + 5s batched non-critical) requires a background timer task similar to the heartbeat monitor
- Token expiry grace period (60s warning) requires tracking JWT expiry times per connection in ConnectionManager

</specifics>

<deferred>
## Deferred Ideas

None - discussion stayed within phase scope

</deferred>

---

*Phase: 02-websocket-test-suite*
*Context gathered: 2026-04-11*
