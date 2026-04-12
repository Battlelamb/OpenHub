# Domain Pitfalls

**Domain:** Multi-agent coordination platform (FastAPI backend hardening, React+Vite dashboard, WebSocket real-time, vector DB, open source release)
**Researched:** 2026-04-07
**Project context:** Existing mature backend, zero tests, no frontend, live production at hub.brunhilde.cloud

---

## Critical Pitfalls

Mistakes that cause rewrites, security incidents, or broken production systems.

---

### Pitfall 1: Testing Against a Broken Auth Baseline

**What goes wrong:** The test suite is written assuming the authentication layer works correctly, but OpenHub has two security holes that invalidate auth assumptions: the hardcoded `admin`/`admin123` credentials with full `["*"]` permissions (routes_auth.py:244-252), and the stub `verify_api_key` in `app/dependencies.py` that accepts any 8-character string. Tests written before these are fixed will pass locally against the stub, then fail or produce false positives when the real auth is wired in. Worse - tests that mock the auth dependency will mask that the stub is still being imported by some routes.

**Why it happens:** Zero tests means nobody discovered the divergence between the old dependency stub and the new auth implementation. The codebase grew two parallel auth paths without a regression gate.

**Consequences:** Tests green-light code that is actually unprotected. The open source release ships with an admin backdoor. Audit of which routes use the old stub vs. new auth cannot be verified without coverage.

**Prevention:** Audit all router imports (grep for `from ..dependencies import` vs. `from ..auth.dependencies import`) as the first test task. Fix the stub and hardcoded credentials before writing a single test. The test baseline must be the correct implementation, not the broken one.

**Detection:** Run `grep -r "from.*dependencies import verify_api_key" app/` - any match outside `app/auth/` is the stub. The stub file (`app/dependencies.py`) returning role `"agent"` for any 8+ char string is the tell.

**Phase:** Address in the backend hardening phase before any test writing begins.

---

### Pitfall 2: WebSocket Token in Query String Survives Open Source Release

**What goes wrong:** `GET /v1/ws?token=oh_...` passes the API key in the URL query string. This is documented in the existing code with the exact format. When an open source project publishes this as the connection pattern, every self-hoster's agent tokens appear in: Nginx/Caddy access logs, browser history, reverse-proxy logs, server-side request logs, and any monitoring tool that logs URLs. An attacker with log read access gets all agent keys.

**Why it happens:** WebSocket authentication is harder than HTTP - browsers cannot send custom headers on WebSocket connections from JavaScript, so query parameters feel like the natural workaround. The code comment even documents the token-in-URL pattern as correct usage.

**Consequences:** For a self-hosted open source tool, leaked agent keys mean full agent impersonation. This becomes a CVE-class issue after public release because it will affect every deployment.

**Prevention:** Accept the token as the first message frame after connection is established (the "initial message auth" pattern). The WebSocket handshake completes, then the client immediately sends `{"type": "auth", "token": "oh_..."}` before any other messages are processed. The server rejects and closes if auth does not arrive within 5 seconds. This keeps credentials out of URLs.

**Detection:** Any WebSocket test that connects via `?token=` URL parameter. The existing routes_websocket.py line 25-26 is the current implementation.

**Phase:** Must be fixed before the WebSocket phase ships, ideally as part of backend security hardening.

---

### Pitfall 3: Schema Defined Inline in main.py Lifespan Blocks the Migration Strategy

**What goes wrong:** All `CREATE TABLE IF NOT EXISTS` DDL is inline in the `lifespan` function in `main.py` (lines 43-168). The `database/migrations/` folder has 3 SQL files covering an old schema subset. When the frontend, vector DB, or any new feature needs a schema change, there are two paths: add another `CREATE TABLE IF NOT EXISTS` to `main.py` (continuing the pattern), or write a migration file (but the migration runner does not cover the inline tables). A self-hoster who upgrades from v1.0 will have a database with old schema but no migration path to the new one.

**Why it happens:** Inline schema creation is the fastest path during rapid prototyping. It works fine when you always start fresh. It breaks production upgrades.

**Consequences:** Open source users cannot upgrade without wiping their database. Schema drift between what migrations create and what main.py creates is undetectable until something breaks. Adding vector DB tables via the same pattern makes it worse.

**Prevention:** Before adding any new tables (vector DB, dashboard config, etc.), consolidate all existing DDL into versioned migration files and replace the inline block with a migration runner call on startup. This is a one-time cleanup that unlocks safe upgrades for all future phases.

**Detection:** Count `CREATE TABLE` statements in `main.py` lifespan vs. SQL files in `database/migrations/`. If they diverge, the migration path is broken.

**Phase:** Backend hardening phase - resolve before vector DB or any schema-changing features are added.

---

### Pitfall 4: Module-Level WebSocket `_connections` Dict Breaks Under Any Multi-Process Setup

**What goes wrong:** `_connections: Dict[str, WebSocket] = {}` is a module-level global in routes_websocket.py. This means:
(a) Two agents connecting with the same `agent_id` - the second silently overwrites the first, leaving the first WebSocket open on the client side consuming resources with no cleanup.
(b) Any future move to `uvicorn --workers N` (common for production hardening) means agents connected to different workers cannot receive cross-agent broadcasts.
(c) Process restart loses all connection state with no notification to clients.

**Why it happens:** Module-level dicts are the simplest way to track connections and work correctly in a single process. The problem only appears under load or multi-worker setups.

**Consequences:** Silent connection overwrites cause agents to miss events. Any attempt to scale beyond one process requires a full rewrite of the connection manager. The open source documentation promising "production-ready" will be wrong.

**Prevention:** Replace with a `ConnectionManager` class with `connect`/`disconnect` methods that include check-and-close logic before insertion. For multi-worker scenarios, add Redis pub/sub as the broadcast backbone - each worker publishes to a Redis channel, all workers relay to their local connections. The single-instance path works without Redis; add Redis as opt-in for scale.

**Detection:** Warning sign: `_connections` referenced directly in module scope in routes files. Any `uvicorn --workers 2` flag in deployment docs should trigger a review.

**Phase:** WebSocket implementation phase - build the ConnectionManager class correctly from the start, do not retrofit.

---

### Pitfall 5: Capability Matching Breaks Silently Due to `str()` Instead of `json.dumps()`

**What goes wrong:** Agent registration via `/v1/auth/agent/register` stores `capabilities` as Python `str()` representation (e.g., `"['coding', 'review']"`) instead of valid JSON. Any capability-based matching that uses `json.loads()` will fail silently or raise a parse error. Agents registered through this path will never be correctly matched to tasks - tasks will go unassigned while the API reports the agent as online with correct capabilities.

**Why it happens:** `str(list)` and `json.dumps(list)` look identical for simple cases in Python debug output. The bug is invisible until you try to deserialize.

**Consequences:** Task assignment is silently broken for agents registered via the auth registration path. This only manifests under load when you notice tasks queuing but no agents claiming them. For an open source project, this is a "works in demo, breaks in real use" trap.

**Prevention:** Fix the two-line bug in routes_auth.py:88-90 (`str(agent_data.capabilities)` -> `json.dumps(agent_data.capabilities)`). Add a test that registers an agent, retrieves it, and verifies capabilities can be JSON-parsed. Add a test that assigns a task to an agent registered via the auth path.

**Detection:** `SELECT capabilities FROM agents` in SQLite - if values look like `"['coding', 'review']"` with single quotes, they are Python reprs, not JSON.

**Phase:** Backend hardening / test suite phase. Fix before any capability-matching tests are written.

---

## Moderate Pitfalls

Mistakes that cause significant friction, bugs under load, or poor developer experience.

---

### Pitfall 6: Heartbeat Monitoring Never Started - Agents Never Go Offline

**What goes wrong:** `HeartbeatService.start_monitoring()` is defined but never called in the main.py lifespan. Agents that disconnect, crash, or go silent will stay permanently `online` in the database. Tasks assigned to dead agents will never be requeued. The dashboard will show all agents as healthy when they are not.

**Why it happens:** The service was built but the wiring step was skipped. With no tests, nothing caught it.

**Consequences:** The entire "agent health" and "auto-requeue on agent failure" feature is non-functional despite the code existing. This is immediately visible in the dashboard UI when an agent is stopped and stays online.

**Prevention:** Add `heartbeat_service.start_monitoring()` to the lifespan startup sequence. Write an integration test that starts an agent, stops sending heartbeats, waits past the TTL, and verifies the agent is marked offline.

**Detection:** Run the server, register an agent, then kill the agent process. Wait 60 seconds. Query `GET /v1/agents/{id}` - if status is still `online`, the monitor is not running.

**Phase:** Backend hardening phase, first items to fix.

---

### Pitfall 7: React WebSocket Reconnection Not Handled - Dashboard Goes Stale Silently

**What goes wrong:** A naive WebSocket connection in React created with `useEffect` will not reconnect after the server restarts or the connection drops. The dashboard shows the last known state indefinitely, with no indication that real-time updates have stopped. The user sees a stale dashboard and assumes the system is quiet - not that their connection is dead.

**Why it happens:** The `WebSocket` API does not auto-reconnect. A simple `useEffect` that opens a connection and registers `onmessage` has no retry logic.

**Consequences:** After any server restart (including deployments), all dashboard clients go stale without knowing it. This is especially bad for a self-hosted tool where operators are also watching the dashboard.

**Prevention:** Implement exponential backoff reconnection in the WebSocket hook: close event triggers a retry after 1s, 2s, 4s, 8s, cap at 30s. Show a "reconnecting..." banner on the dashboard when the connection is closed. On reconnect, fetch a full state snapshot via REST before resuming WebSocket for incremental updates.

**Detection:** Start dashboard, restart the FastAPI server, observe whether the dashboard shows a connection lost indicator.

**Phase:** Frontend implementation phase - build reconnection logic from the start, not as a fix.

---

### Pitfall 8: API Keys Full Table Scan Degrades Every Authenticated Request

**What goes wrong:** `APIKeyManager.validate_api_key` does `SELECT * FROM api_keys WHERE is_active = true` and then iterates all rows in Python to find a hash match (O(n) per request). Additionally, every validated request issues an `UPDATE` to set `last_used_at`. At 10 agents making frequent API calls, this is fine. At 100 agents running workflows, every single request is a full table scan plus a write.

**Why it happens:** Correct but unoptimized - hash comparison must be done in application code because the full hash cannot be stored indexed in a way that enables prefix lookup without the hash itself.

**Consequences:** Latency creeps up with every new agent registered. Under any load test, auth becomes the bottleneck. This affects every single API call.

**Prevention:** Add a deterministic hash prefix column (first 8 chars of the stored hash) as an indexed column. The query becomes `WHERE hash_prefix = :prefix AND is_active = true` which narrows the Python scan from all rows to typically 1. Cache validated keys in Redis with a short TTL (30-60s) to skip the DB entirely for active agents.

**Detection:** Run `EXPLAIN QUERY PLAN SELECT * FROM api_keys WHERE is_active = true` in SQLite. If it shows a full scan, confirm the issue.

**Phase:** Backend hardening phase alongside auth fixes.

---

### Pitfall 9: React State Update on Every WebSocket Message Causes Render Churn

**What goes wrong:** A naive WebSocket handler calls `setState` on every message. In an agent coordination platform, agents send heartbeats, task updates, and status changes continuously. Each `setState` triggers a React re-render. At 10 agents sending 1 heartbeat/second each, the dashboard is doing 10 re-renders per second. Complex dashboard components (charts, agent grids) re-render fully on each, causing visible jank and CPU usage.

**Why it happens:** `onmessage -> setState` is the example pattern in all tutorials. It works for low-frequency events. It breaks for high-frequency agent systems.

**Consequences:** Dashboard feels sluggish under real load. CPU usage spikes. Charts flicker. The experience does not match the "command center" positioning.

**Prevention:** Buffer incoming WebSocket messages in a `useRef` accumulator. Flush to state at a fixed interval (e.g., 100ms via `requestAnimationFrame` or `setInterval`). Memoize expensive components with `React.memo`. Use Zustand (not React Context) for WebSocket state - Context re-renders all consumers on every update, Zustand only re-renders components subscribed to the changed slice.

**Detection:** Open browser DevTools -> Performance tab -> record 10 seconds with agents running. If renders fire more than 2-3 times per second per component, the flush buffering is missing.

**Phase:** Frontend implementation phase - architecture decision before component building begins.

---

### Pitfall 10: Vector DB Added as Another In-Memory Singleton - Same Pattern as Hatchet

**What goes wrong:** `HatchetService` stores `self._hatchet_client = None` and simulates all workflow orchestration in-memory. The vector DB integration risks following the same pattern: create a `VectorService` that stores embeddings in an in-memory list, mark the feature as complete, and ship. The live deployment then restarts and loses all vectors.

**Why it happens:** The codebase already has `zvec==0.1.0` in requirements.txt with directory creation on startup but zero integration. The pattern of "wired for the feature, not actually implementing it" is established.

**Consequences:** Vector search appears to work in demos (same process, same memory), fails after any restart, and is invisible in the dashboard. The open source documentation describes a feature that does not persist.

**Prevention:** Choose the vector DB (ChromaDB for local file persistence, or Qdrant for a self-hostable server option) before writing any code. Verify the persistence model is file-based or server-based, not in-memory. Write a test that adds embeddings, restarts the service, and confirms retrieval. Remove `zvec` from requirements.txt immediately - it has no usage and unclear maintenance status.

**Detection:** After vector search is "implemented," restart the server and check if previously embedded content is still searchable.

**Phase:** Vector DB integration phase - decision on persistence layer must come before any embedding code.

---

### Pitfall 11: CORS Wildcard Ships as Default in Open Source Release

**What goes wrong:** The default config is `cors_origins = ["*"]`, `cors_methods = ["*"]`, `cors_headers = ["*"]`. This means every self-hoster who does `docker run openhub` gets an instance that accepts cross-origin requests from any domain. For a hub that manages AI agents with API keys, this means any malicious website can make requests to the hub using the user's browser session.

**Why it happens:** Wildcard CORS is the path of least resistance during development - no browser errors, easy to test. It stays as the default because there is no test that enforces a restrictive default.

**Consequences:** Security advisory for the open source release. Every default deployment is vulnerable to CSRF-style attacks against the agent management endpoints.

**Prevention:** Change the default to `cors_origins = []` (no cross-origin allowed) before release. Document the `AGENTHUB_CORS_ORIGINS` environment variable prominently in the setup guide. The React dashboard served from the same origin does not need CORS.

**Detection:** `curl http://localhost:7788/v1/health -H "Origin: https://evil.com" -v` - if the response includes `Access-Control-Allow-Origin: *`, the wildcard is active.

**Phase:** Backend hardening phase - fix before open source documentation is written.

---

### Pitfall 12: Open Source README Describes Features That Are Simulated

**What goes wrong:** Routes_workflows.py and routes_hatchet.py expose `/v1/workflows/*` endpoints that look functional but operate against an in-memory simulation (HatchetService stores `self._hatchet_client = None`, all orchestration is asyncio.sleep-based). If the README or API docs describe these as "durable workflow orchestration," users will deploy expecting real retry guarantees and get none.

**Why it happens:** The code path is real - endpoints exist, responses look correct, the abstraction hides the null backend. Without a real Hatchet server in the test environment, it is hard to notice.

**Consequences:** Users raise GitHub issues reporting that workflows do not retry after crashes. The maintainer has to either implement real Hatchet integration or retract the feature claim. Either way, trust is damaged.

**Prevention:** Before open source release, every feature described in documentation must either: (a) have a test proving it works with persistence, or (b) be clearly marked as "experimental" in both docs and the API response. Add a `simulated: true` field to workflow responses when the Hatchet client is None.

**Detection:** Check if `HatchetService._hatchet_client` is None at runtime. If None, all workflow endpoints are simulated.

**Phase:** Open source preparation phase - documentation accuracy audit against actual implementation.

---

## Minor Pitfalls

Friction that slows development or creates minor issues but is not blocking.

---

### Pitfall 13: `datetime.utcnow()` in 40+ Locations - Technical Debt Compounds During Test Writing

**What goes wrong:** 40+ uses of the deprecated `datetime.utcnow()` exist alongside some `datetime.now(timezone.utc)` calls. When writing tests that compare timestamps, mixed-aware and naive datetimes throw `TypeError: can't compare offset-naive and offset-aware datetimes` in unpredictable places. Tests will fail with confusing errors until all callsites are unified.

**Prevention:** Run a project-wide replace before writing timestamp-sensitive tests: `datetime.utcnow()` -> `datetime.now(timezone.utc)`. Single PR, no logic changes.

**Phase:** Backend hardening, as part of initial cleanup sweep.

---

### Pitfall 14: Duplicate `_auth`/`_sender` Helpers Cause Security Fix Drift

**What goes wrong:** `_auth`, `_sender`, and `_resolve_agent_id` are copy-pasted across 5+ route files. A security fix to auth logic in one file silently leaves the others broken. When the WebSocket auth token-in-URL fix is applied, it will need to touch every copy independently, and one will be missed.

**Prevention:** Extract a single `app/auth/api_key_deps.py` with a `require_api_key` FastAPI dependency before writing the WebSocket auth fix. All routes import from one place.

**Phase:** Backend hardening phase, before any auth changes are made.

---

### Pitfall 15: `passlib` Maintenance-Only Status Creates Upgrade Risk

**What goes wrong:** `passlib[bcrypt]==1.7.4` is in maintenance-only mode as of 2023. Python 3.12 already generates deprecation warnings from its internal `datetime.utcnow()` usage. If a bcrypt vulnerability is found, there will be no upstream patch.

**Prevention:** Replace with the `bcrypt` package directly (`import bcrypt`) or `argon2-cffi`. Low-effort migration with no behavior change for users.

**Phase:** Backend hardening - small cleanup alongside the utcnow() sweep.

---

### Pitfall 16: OpenAPI Docs Disabled Blocks Contributor and Client Discovery

**What goes wrong:** `docs_url=None, redoc_url=None` in the FastAPI app constructor means `localhost:7788/docs` returns 404. For an open source project, this is the first thing a new contributor or API consumer tries. No Swagger UI = no discoverability = high contribution friction.

**Prevention:** Enable docs behind an environment variable: `docs_url="/docs" if settings.debug else None`. Or enable always for open source and let self-hosters opt-out via env var.

**Detection:** `curl http://localhost:7788/docs` -> 404.

**Phase:** Backend hardening phase - one-line fix.

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| Test suite bootstrap | Writing tests against broken auth stub, masking real issues | Fix auth stub and hardcoded creds before any test writing |
| Auth hardening | Missing the stub `app/dependencies.py` still imported by some routes | Audit all imports, delete stub only after confirmed clean |
| Schema migration | Adding vector DB tables inline in main.py lifespan | Consolidate all DDL into migrations before any new tables |
| WebSocket implementation | Token in query string, module-level global dict, no reconnect | Build ConnectionManager class and initial-message auth from day one |
| Frontend WebSocket | setState on every message causing render churn | Zustand + message buffering, decide architecture before first component |
| React dashboard | No reconnection logic, stale state after server restart | Implement exponential backoff reconnect in WebSocket hook |
| Vector DB integration | Repeating the Hatchet pattern (in-memory fake) | Verify persistence model with a restart test before claiming feature done |
| Open source docs | Documenting simulated features as real | Audit each feature: test proves it works, or mark experimental |
| Default config | CORS wildcard and admin backdoor shipped as defaults | Fix defaults before any public release, add config validation test |
| Deployment | Dual Docker/pip paths diverge without shared test | Test both paths in CI before tagging v1.0 |

---

## Sources

- FastAPI WebSocket production patterns: https://websocket.org/guides/frameworks/fastapi/
- FastAPI WebSocket scaling with Redis: https://betterstack.com/community/guides/scaling-python/fastapi-websockets/
- React WebSocket state management pitfalls: https://medium.com/@connect.hashblock/i-built-a-real-time-dashboard-in-react-using-websockets-and-recoil-076d69b4eeff
- FastAPI performance mistakes: https://medium.com/@ThinkingLoop/10-fastapi-scaling-mistakes-that-break-performance-39a426e360e3
- Multi-agent coordination failure taxonomy: https://galileo.ai/blog/multi-agent-coordination-strategies
- Open source project pitfalls: https://www.daytona.io/dotfiles/building-a-successful-open-source-project
- WebSocket reconnection and observability: https://blog.greeden.me/en/2025/10/28/weaponizing-real-time-websocket-sse-notifications-with-fastapi-connection-management-rooms-reconnection-scale-out-and-observability/
- Codebase-specific issues: /home/omer/projects/OpenHub/.planning/codebase/CONCERNS.md (audited 2026-04-07)
