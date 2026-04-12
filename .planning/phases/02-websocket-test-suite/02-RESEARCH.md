# Phase 2: WebSocket + Test Suite - Research

**Researched:** 2026-04-11
**Domain:** WebSocket real-time events, FastAPI testing, Prometheus metrics
**Confidence:** HIGH

## Summary

Phase 2 adds a dashboard-facing WebSocket endpoint (`/v1/ws/ui`) with JWT auth, a ConnectionManager class, tiered event broadcasting, and Prometheus metrics. It also builds out the test suite covering auth, capability matching, and task/agent lifecycle. The existing codebase has a working agent WebSocket at `/v1/ws` using module-level `_connections` dict and API key auth via query param - the new endpoint uses a different auth model (JWT via initial message frame) and separate connection pool.

The testing infrastructure is minimal: `conftest.py` with session-scoped `test_client`, `admin_headers`, and `agent_api_key` fixtures, plus two stub tests. The `asyncio_mode = "auto"` config in pyproject.toml means async tests work out of the box. Starlette's TestClient supports `websocket_connect()` for in-memory WebSocket testing - no need for a real server or external WS client library.

**Primary recommendation:** Build ConnectionManager as a standalone service class (not tied to routes), wire it as a singleton via lifespan, and inject it into routes/services. Test WebSocket endpoints using Starlette's built-in `TestClient.websocket_connect()` context manager.

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions
- D-01: Reuse same JSON event format as existing agent endpoint: `{event, agent_id, timestamp, data}`
- D-02: New `/v1/ws/ui` endpoint for dashboard clients, separate from existing `/v1/ws` for agents
- D-03: JWT authentication via initial-message frame (WS-01) - no token in URL query string
- D-05: Critical events push immediately: agent status changes (online/offline/idle), task status transitions (queued/claimed/running/completed/failed)
- D-06: Non-critical events batch every 5 seconds: heartbeat timestamp updates, metadata changes
- D-07: Task progress is a separate event type (`task_progress` with percentage field)
- D-08: Workflow step progress events broadcast to UI (WS-06)
- D-09: Separate connection pools for agents vs UI clients - `Dict[str, WebSocket]` each. `broadcast_to_ui()` only hits UI pool
- D-10: Replace current module-level `_connections` dict with ConnectionManager class with explicit connect/disconnect lifecycle
- D-11: JWT expiry handling: send `token_expiring` warning event 60s before expiry. If no refresh within grace period, disconnect with close frame
- D-12: Configurable soft limits via env vars: `AGENTHUB_MAX_WS_AGENTS=100`, `AGENTHUB_MAX_WS_UI=10`. Log warning at 80%, reject at limit with 4002 close code
- D-13: Slow UI clients: drop oldest non-critical events when send buffer exceeds threshold. Send `events_dropped` notification
- D-14: Dual error communication: recoverable errors as event messages, fatal errors as WebSocket close frames (4001=auth_expired, 4002=limit_reached, 4003=server_error)
- D-15: WebSocket-specific Prometheus metrics: `ws_connections_active` (gauge by type), `ws_events_sent_total` (counter by event type), `ws_errors_total` (counter)
- D-16: Integration tests use real in-memory SQLite (`:memory:` path). No mocked DB layer
- D-17: Coverage target is requirement-driven, not percentage-driven

### Claude's Discretion
- Reconnection strategy (D-04) - fresh state vs replay buffer
- Test coverage depth beyond required TEST-01 through TEST-05
- Specific WebSocket close frame code values beyond the three specified (4001, 4002, 4003)
- Event batching implementation details (timer-based vs threshold-based)
- WebSocket test fixtures design (real or mock WS connections)

### Deferred Ideas (OUT OF SCOPE)
None - discussion stayed within phase scope

</user_constraints>

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| WS-01 | /v1/ws/ui endpoint with JWT auth via initial-message frame | ConnectionManager class + JWT verify_token integration; Starlette WebSocket accept/receive flow |
| WS-02 | ConnectionManager class replacing module-level _connections dict | Singleton service pattern per app/limiter.py; dual pools (agent/ui) |
| WS-03 | broadcast_to_ui() helper for pushing events to all dashboard clients | ConnectionManager method iterating UI pool; tiered batching with asyncio.create_task timer |
| WS-04 | Agent status change events broadcast to UI | Hook into AgentService status transitions + HeartbeatService offline detection |
| WS-05 | Task lifecycle events broadcast to UI | Hook into TaskService create/claim/start/complete/fail methods |
| WS-06 | Workflow step progress events broadcast to UI | Hook into WorkflowCoordinator step transitions |
| TEST-01 | Unit tests for auth system (JWT, API key, RBAC) | Direct JWTManager/APIKeyManager/Casbin calls with in-memory DB |
| TEST-02 | Unit tests for capability matching | Direct CapabilityMatcher calls with in-memory DB + seeded agents |
| TEST-03 | Integration tests for task lifecycle | TestClient HTTP calls through full create/claim/start/complete/fail/retry cycle |
| TEST-04 | Integration tests for agent registration and heartbeat/offline | TestClient registration + heartbeat polling + offline detection |
| TEST-05 | Integration tests for WebSocket connections | TestClient.websocket_connect() for auth, event broadcast, disconnect cleanup |

</phase_requirements>

## Standard Stack

### Core (Already Installed)
| Library | Installed Version | Purpose | Why Standard |
|---------|-------------------|---------|--------------|
| FastAPI | 0.135.3 | WebSocket endpoints via `@router.websocket()` | Already the app framework |
| Starlette | 1.0.0 | WebSocket class, TestClient with `websocket_connect()` | Bundled with FastAPI |
| PyJWT | 2.7.0 | JWT verification for WS auth | Already used in `app/auth/jwt_auth.py` |
| websockets | 16.0 | ASGI WebSocket protocol support | Already installed |
| prometheus-client | (declared in requirements.txt) | Gauge/Counter for WS metrics | Already used in `routes_metrics.py` |
| pytest | 9.0.2 | Test runner | Already installed and configured |

### Supporting (Already Installed)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| structlog | (installed) | Structured logging for ConnectionManager | All WS lifecycle events |
| httpx | (installed) | TestClient backend for HTTP + WS testing | All integration tests |

### No New Dependencies Needed
The entire phase can be implemented with existing installed packages. No `pip install` required.

## Architecture Patterns

### Recommended New Files
```
app/
  services/
    connection_manager.py    # ConnectionManager class (WS-02)
  api/
    routes_ws_ui.py          # /v1/ws/ui endpoint (WS-01)
tests/
  unit/
    test_auth.py             # TEST-01: JWT, API key, RBAC
    test_capability_matcher.py # TEST-02: capability matching
  integration/
    test_task_lifecycle.py   # TEST-03: task CRUD cycle
    test_agent_lifecycle.py  # TEST-04: agent registration + heartbeat
    test_websocket.py        # TEST-05: WS auth, events, cleanup
```

### Pattern 1: ConnectionManager as Singleton Service

**What:** A class that manages both agent and UI WebSocket pools, handles broadcast, batching, and metrics.
**When to use:** All WebSocket operations go through this single instance.

```python
# app/services/connection_manager.py
import asyncio
from typing import Dict, Optional
from fastapi import WebSocket
from prometheus_client import Gauge, Counter

from ..logging import get_logger
from ..config import get_settings

logger = get_logger(__name__)
settings = get_settings()

# Prometheus metrics (D-15)
WS_CONNECTIONS_ACTIVE = Gauge(
    "openhub_ws_connections_active",
    "Active WebSocket connections",
    ["type"],  # "agent" or "ui"
)
WS_EVENTS_SENT_TOTAL = Counter(
    "openhub_ws_events_sent_total",
    "Total WebSocket events sent",
    ["event_type"],
)
WS_ERRORS_TOTAL = Counter(
    "openhub_ws_errors_total",
    "Total WebSocket errors",
)


class ConnectionManager:
    """Manages agent and UI WebSocket connections with tiered broadcasting."""

    def __init__(self) -> None:
        self._agents: Dict[str, WebSocket] = {}
        self._ui_clients: Dict[str, WebSocket] = {}
        self._batch_buffer: list = []
        self._batch_task: Optional[asyncio.Task] = None

    async def connect_agent(self, agent_id: str, ws: WebSocket) -> bool:
        """Register agent WS connection. Returns False if limit reached."""
        max_agents = getattr(settings, "max_ws_agents", 100)
        if len(self._agents) >= max_agents:
            return False
        self._agents[agent_id] = ws
        WS_CONNECTIONS_ACTIVE.labels(type="agent").inc()
        return True

    async def connect_ui(self, client_id: str, ws: WebSocket) -> bool:
        """Register UI client WS connection. Returns False if limit reached."""
        max_ui = getattr(settings, "max_ws_ui", 10)
        if len(self._ui_clients) >= max_ui:
            return False
        self._ui_clients[client_id] = ws
        WS_CONNECTIONS_ACTIVE.labels(type="ui").inc()
        return True

    async def disconnect_agent(self, agent_id: str) -> None:
        if agent_id in self._agents:
            del self._agents[agent_id]
            WS_CONNECTIONS_ACTIVE.labels(type="agent").dec()

    async def disconnect_ui(self, client_id: str) -> None:
        if client_id in self._ui_clients:
            del self._ui_clients[client_id]
            WS_CONNECTIONS_ACTIVE.labels(type="ui").dec()

    async def broadcast_to_ui(self, event_type: str, data: dict) -> int:
        """Broadcast event to all UI clients. Returns count sent."""
        # ... iterate self._ui_clients, send_json, handle failures
        pass
```

**Lifecycle:** Create in `main.py` lifespan, store on `app.state.connection_manager`. Access in routes via `request.app.state.connection_manager`.

### Pattern 2: JWT Auth via Initial Message Frame (D-03)

**What:** Client connects to WS, server accepts, client sends JWT in first message, server validates and either keeps connection or closes.
**Why:** Prevents token exposure in URL/query params and server logs.

```python
@router.websocket("/v1/ws/ui")
async def ws_ui_endpoint(websocket: WebSocket):
    await websocket.accept()

    # Wait for auth message (timeout after 10s)
    try:
        raw = await asyncio.wait_for(websocket.receive_text(), timeout=10.0)
        msg = json.loads(raw)
    except (asyncio.TimeoutError, json.JSONDecodeError):
        await websocket.close(code=4001, reason="auth timeout or invalid format")
        return

    token = msg.get("token")
    if not token:
        await websocket.close(code=4001, reason="token required in first message")
        return

    try:
        payload = verify_token(token, expected_type="access")
    except Exception:
        await websocket.close(code=4001, reason="invalid or expired token")
        return

    client_id = payload["sub"]
    # Register with ConnectionManager ...
```

### Pattern 3: Tiered Event Broadcasting (D-05, D-06)

**What:** Critical events (status changes, task transitions) push immediately. Non-critical events (heartbeat updates, metadata) batch every 5 seconds.
**Implementation:** Use `asyncio.create_task` for a background timer loop that flushes the batch buffer.

```python
async def _start_batch_loop(self) -> None:
    """Background task: flush non-critical event buffer every 5s."""
    while True:
        await asyncio.sleep(5.0)
        if self._batch_buffer:
            events = self._batch_buffer[:]
            self._batch_buffer.clear()
            for event in events:
                await self.broadcast_to_ui(event["event_type"], event["data"])
```

### Pattern 4: Service Hook Points for Broadcasting

**What:** After status transitions in services, call `connection_manager.broadcast_to_ui()`.
**How:** Pass ConnectionManager reference to services, or use a simple event bus pattern.

The cleanest approach: services accept an optional `on_event` callback, set during initialization from lifespan. This avoids circular imports and keeps services testable.

```python
# In TaskService
class TaskService:
    def __init__(self, database: Database, on_event=None):
        self._on_event = on_event

    async def complete_task(self, task_id, result):
        # ... business logic ...
        if self._on_event:
            await self._on_event("task_completed", {"task_id": task_id, ...})
```

### Anti-Patterns to Avoid
- **Importing ConnectionManager in services:** Creates circular imports. Use callback injection instead.
- **Sharing one connection pool for agents and UI:** D-09 explicitly requires separate pools.
- **Storing JWT token text in ConnectionManager:** Store only the decoded payload (sub, exp) to track expiry. Never store raw tokens.
- **Using `asyncio.sleep` in tests:** Use deterministic approaches. For batch timer tests, call the flush method directly rather than waiting.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| WebSocket test client | Custom WS client | `TestClient.websocket_connect()` | Starlette's implementation handles ASGI lifecycle correctly |
| JWT creation for tests | Manual token string construction | `JWTManager.create_access_token()` | Ensures tokens match production format, handles claims correctly |
| In-memory DB for tests | SQLite file with cleanup | `AGENTHUB_DB_PATH=":memory:"` (already set in conftest.py) | Automatic cleanup, no file I/O, already configured |
| Prometheus metric types | Custom counters/gauges | `prometheus_client.Gauge`, `Counter` | Thread-safe, compatible with existing `/metrics` endpoint |
| WebSocket keepalive | Custom ping/pong | Starlette built-in ping/pong | Protocol-level, handled by ASGI server |

## Common Pitfalls

### Pitfall 1: TestClient WebSocket requires context manager
**What goes wrong:** Using `client.websocket_connect()` without `with` block causes connection to not clean up, tests hang.
**Why it happens:** Starlette runs ASGI app in a background thread; context manager ensures proper shutdown.
**How to avoid:** Always use `with client.websocket_connect("/v1/ws/ui") as ws:` pattern.
**Warning signs:** Tests hanging indefinitely, unclosed connection warnings.

### Pitfall 2: Session-scoped test_client with in-memory SQLite
**What goes wrong:** Session-scoped `test_client` means all tests share one DB instance. State leaks between tests.
**Why it happens:** In-memory SQLite lives as long as the connection is open; session scope keeps it alive.
**How to avoid:** For integration tests that need clean state, use function-scoped fixtures that reset tables, or use a separate function-scoped client for isolation-critical tests. The existing session-scope is fine for read-heavy tests.
**Warning signs:** Tests pass individually but fail when run together; order-dependent failures.

### Pitfall 3: asyncio event loop conflicts in pytest
**What goes wrong:** `pytest-asyncio` auto mode can conflict with Starlette's synchronous TestClient.
**Why it happens:** TestClient is synchronous (runs ASGI in background thread). Mixing async test functions with sync TestClient causes event loop issues.
**How to avoid:** Use synchronous test functions with TestClient. Only use `async def test_*` when testing async service methods directly (not through TestClient HTTP/WS calls).
**Warning signs:** `RuntimeError: This event loop is already running`, `no running event loop`.

### Pitfall 4: WebSocket close frame not received in tests
**What goes wrong:** Server sends close frame but test client doesn't receive it, or receives it as an exception instead of clean close.
**Why it happens:** Starlette TestClient WebSocket raises `WebSocketDisconnect` on server-initiated close, not a clean close message.
**How to avoid:** Wrap `ws.receive_json()` in try/except for `WebSocketDisconnect` when testing server-initiated disconnects. Check the close code via the exception.
**Warning signs:** Unexpected exceptions in tests expecting clean close.

### Pitfall 5: Prometheus metric state leaking between tests
**What goes wrong:** Gauge/Counter values accumulate across test runs because prometheus_client uses process-global registries.
**Why it happens:** Prometheus metrics are module-level singletons.
**How to avoid:** Don't assert exact metric values. Assert relative changes (read before and after). Or use `prometheus_client.REGISTRY.unregister()` in fixtures, but this is fragile.
**Warning signs:** Metric assertions pass in isolation but fail in full suite.

### Pitfall 6: Alembic migrations in test startup
**What goes wrong:** The lifespan runs `alembic upgrade head` which looks for `alembic.ini` file. With `:memory:` DB this may fail or be slow.
**Why it happens:** `main.py` lifespan unconditionally runs Alembic on startup.
**How to avoid:** The existing conftest.py already works (session-scoped TestClient triggers lifespan once). If Alembic fails with `:memory:`, the migration DDL may need to handle in-memory path specially. Verify this works before writing tests.
**Warning signs:** `FileNotFoundError` for alembic.ini, migration errors on test startup.

## Code Examples

### WebSocket Testing with TestClient

```python
# Source: Starlette docs + FastAPI testing docs
from fastapi.testclient import TestClient
from app.main import app
from app.auth.jwt_auth import create_access_token

def test_ws_ui_auth_success(test_client: TestClient):
    """TEST-05: WebSocket connects with valid JWT."""
    token = create_access_token(subject="admin", claims={"role": "admin"})

    with test_client.websocket_connect("/v1/ws/ui") as ws:
        # Send auth message (D-03: JWT via initial frame)
        ws.send_json({"token": token})
        # Should receive welcome event
        data = ws.receive_json()
        assert data["event"] == "connected"

def test_ws_ui_auth_failure(test_client: TestClient):
    """TEST-05: WebSocket rejects invalid JWT."""
    with test_client.websocket_connect("/v1/ws/ui") as ws:
        ws.send_json({"token": "invalid-token"})
        # Server should close with 4001
        # In Starlette TestClient, this raises WebSocketDisconnect
        try:
            ws.receive_json()
            assert False, "Should have been disconnected"
        except Exception:
            pass  # Expected disconnect
```

### Unit Testing JWT (TEST-01)

```python
import pytest
from datetime import timedelta
from app.auth.jwt_auth import JWTManager

def test_jwt_create_and_verify():
    mgr = JWTManager()
    token = mgr.create_access_token(subject="test-agent", claims={"role": "agent"})
    payload = mgr.verify_token(token)
    assert payload["sub"] == "test-agent"
    assert payload["role"] == "agent"

def test_jwt_expired_token():
    mgr = JWTManager()
    token = mgr.create_access_token(
        subject="test-agent",
        expires_delta=timedelta(seconds=-1)  # Already expired
    )
    with pytest.raises(Exception):  # jwt.ExpiredSignatureError
        mgr.verify_token(token)
```

### Unit Testing Capability Matcher (TEST-02)

```python
from app.services.capability_matcher import CapabilityMatcher
from app.database.connection import get_database

def test_capability_exact_match(test_client):
    """TEST-02: Agent with matching capabilities scores 1.0."""
    db = get_database()
    matcher = CapabilityMatcher(db)
    # Seed an agent with capabilities via DB or service
    # Then call matcher.find_best_agent(["python", "testing"])
    # Assert match_score, matched_capabilities, etc.
```

### Integration Test for Task Lifecycle (TEST-03)

```python
def test_task_full_lifecycle(test_client, admin_headers):
    """TEST-03: create -> claim -> start -> complete."""
    # Create task
    resp = test_client.post("/v1/tasks", json={
        "title": "Test task",
        "task_type": "code_generation",
        "required_capabilities": ["python"],
    }, headers=admin_headers)
    assert resp.status_code == 201
    task_id = resp.json()["id"]

    # Claim task (as agent)
    # Start task
    # Complete task
    # Verify final status
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Module-level `_connections` dict | ConnectionManager class | This phase | Proper lifecycle management, testability |
| WS auth via query param `?token=` | JWT via initial message frame | This phase (D-03) | Token not in URL/logs |
| Single connection pool | Separate agent/UI pools | This phase (D-09) | UI broadcasts don't hit agents |
| No WebSocket metrics | Prometheus gauges/counters | This phase (D-15) | Observability |
| 2 stub tests | Full auth + lifecycle + WS test suite | This phase | Real test coverage |

## Open Questions

1. **conftest.py `admin_headers` fixture returns placeholder token**
   - What we know: Current fixture has `"Bearer test-admin-token-placeholder"` - this is not a real JWT
   - What's unclear: Whether Phase 1 updated this to generate a real admin JWT via login flow
   - Recommendation: Phase 2 conftest updates should create a real admin JWT via `create_access_token()` and a real agent API key via the auth endpoints. This is likely a Wave 0 task.

2. **Alembic + in-memory SQLite interaction**
   - What we know: Lifespan runs `alembic upgrade head` on startup. conftest.py sets `AGENTHUB_DB_PATH=":memory:"`
   - What's unclear: Whether Alembic migrations work cleanly with `:memory:` SQLite (connection lifecycle)
   - Recommendation: Verify this works in Wave 0. If it doesn't, the test lifespan may need to bypass Alembic and use direct DDL.

3. **Background batch timer in tests**
   - What we know: D-06 requires 5s batching for non-critical events
   - What's unclear: How to test time-dependent batching without `asyncio.sleep` delays
   - Recommendation: Expose a `flush_batch()` method on ConnectionManager for deterministic testing. Tests call flush directly instead of waiting for timer.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 + pytest-asyncio |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `python3 -m pytest tests/ -x -q` |
| Full suite command | `python3 -m pytest tests/ --tb=short -q` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| WS-01 | /v1/ws/ui auth via initial frame | integration | `python3 -m pytest tests/integration/test_websocket.py -x -q` | No - Wave 0 |
| WS-02 | ConnectionManager connect/disconnect | unit | `python3 -m pytest tests/unit/test_connection_manager.py -x -q` | No - Wave 0 |
| WS-03 | broadcast_to_ui delivery | integration | `python3 -m pytest tests/integration/test_websocket.py -x -q` | No - Wave 0 |
| WS-04 | Agent status events broadcast | integration | `python3 -m pytest tests/integration/test_websocket.py -x -q` | No - Wave 0 |
| WS-05 | Task lifecycle events broadcast | integration | `python3 -m pytest tests/integration/test_websocket.py -x -q` | No - Wave 0 |
| WS-06 | Workflow progress events broadcast | integration | `python3 -m pytest tests/integration/test_websocket.py -x -q` | No - Wave 0 |
| TEST-01 | Auth unit tests (JWT, API key, RBAC) | unit | `python3 -m pytest tests/unit/test_auth.py -x -q` | No - Wave 0 |
| TEST-02 | Capability matching unit tests | unit | `python3 -m pytest tests/unit/test_capability_matcher.py -x -q` | No - Wave 0 |
| TEST-03 | Task lifecycle integration | integration | `python3 -m pytest tests/integration/test_task_lifecycle.py -x -q` | No - Wave 0 |
| TEST-04 | Agent registration + heartbeat | integration | `python3 -m pytest tests/integration/test_agent_lifecycle.py -x -q` | No - Wave 0 |
| TEST-05 | WebSocket integration tests | integration | `python3 -m pytest tests/integration/test_websocket.py -x -q` | No - Wave 0 |

### Sampling Rate
- **Per task commit:** `python3 -m pytest tests/ -x -q`
- **Per wave merge:** `python3 -m pytest tests/ --tb=short -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/conftest.py` - Update `admin_headers` to generate real JWT; add `auth_token` fixture
- [ ] `tests/unit/test_auth.py` - TEST-01 test file
- [ ] `tests/unit/test_capability_matcher.py` - TEST-02 test file
- [ ] `tests/unit/test_connection_manager.py` - WS-02 unit tests
- [ ] `tests/integration/test_task_lifecycle.py` - TEST-03 test file
- [ ] `tests/integration/test_agent_lifecycle.py` - TEST-04 test file
- [ ] `tests/integration/test_websocket.py` - TEST-05 + WS-01 through WS-06 test file

## Sources

### Primary (HIGH confidence)
- Existing codebase: `app/api/routes_websocket.py`, `app/auth/jwt_auth.py`, `app/services/capability_matcher.py`, `app/config.py`, `tests/conftest.py`
- Starlette TestClient docs: https://www.starlette.io/testclient/
- FastAPI WebSocket testing docs: https://fastapi.tiangolo.com/advanced/testing-websockets/

### Secondary (MEDIUM confidence)
- WebSearch for FastAPI WS testing patterns - verified against official docs

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - all libraries already installed, versions verified via runtime import
- Architecture: HIGH - patterns derived from existing codebase conventions (limiter singleton, service layer)
- Pitfalls: HIGH - based on known Starlette TestClient behavior and pytest-asyncio interaction patterns
- WebSocket protocol: HIGH - existing `/v1/ws` endpoint provides working reference

**Research date:** 2026-04-11
**Valid until:** 2026-05-11 (stable - no library upgrades needed)
