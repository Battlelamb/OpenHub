# Codebase Concerns

**Analysis Date:** 2026-04-07

---

## Security Considerations

**Hardcoded Admin Credentials in Production Auth Path:**
- Risk: The admin login endpoint has a hardcoded username/password (`admin` / `admin123`) with a TODO comment and no actual admin user store.
- Files: `app/api/routes_auth.py:244-252`
- Current mitigation: None - this is the live auth path.
- Recommendations: Implement admin user table with hashed passwords. Until then, admin login grants full `["*"]` permissions to anyone who knows the default credentials.

**`app/dependencies.py` API Key Validation is a Stub:**
- Risk: The `verify_api_key` dependency used across several endpoints accepts any string of 8+ characters as a valid API key and always returns role `"agent"`. This means role-based access control (RBAC) via `require_admin_role` / `require_agent_role` is effectively bypassed for all endpoints using the old dependency.
- Files: `app/dependencies.py:41-59`
- Current mitigation: The newer `app/auth/dependencies.py` (JWT-based) and `app/auth/api_keys.py` (hashed key store) are the real implementations. The old `app/dependencies.py` still exists and may be imported by some routes.
- Recommendations: Audit all router imports to confirm no route uses the stub `verify_api_key`. Remove or fully implement the old dependencies module.

**CORS Wildcard Default:**
- Risk: Default config sets `cors_origins = ["*"]`, `cors_methods = ["*"]`, `cors_headers = ["*"]`. The live deployment at `hub.brunhilde.cloud` inherits this unless overridden by env vars.
- Files: `app/config.py:51-53`
- Current mitigation: None in code; relies on operator to set env vars.
- Recommendations: Change default to a restrictive list and document required env var.

**ACN Admin Key Stored Only in Memory on Process Start:**
- Risk: The `_admin_key` in `routes_acn.py` is an in-memory global. If the process restarts and `AGENTHUB_ACN_ADMIN_KEY` env var is not set, `/v1/acn/admin/setup` can be called again from localhost to generate a new key, effectively rotating the admin key without audit trail.
- Files: `app/api/routes_acn.py:36-60, 124-154`
- Current mitigation: Localhost-only restriction for setup endpoint.
- Recommendations: Persist admin key to database or require it always from env var.

**ACN Invite Codes Stored Only in Memory:**
- Risk: `_invite_store` is an in-memory dict. Process restart clears all pending invites without warning agents. In multi-process or multi-worker deployments (e.g., `uvicorn --workers 4`), invite created by one worker will not be seen by another.
- Files: `app/api/routes_acn.py:32, 167-172`
- Current mitigation: Single-process assumption.
- Recommendations: Persist invite codes to the database with TTL column.

**WebSocket Token Exposed in Query Parameter:**
- Risk: `GET /v1/ws?token=oh_...` passes the API key in the URL. URLs appear in server access logs, browser history, and reverse-proxy logs in plaintext.
- Files: `app/api/routes_websocket.py:22-26`
- Current mitigation: None.
- Recommendations: Accept token via WebSocket subprotocol header or initial message frame instead of query string.

**`decode_token_without_verification` is a Public Method:**
- Risk: `JWTManager.decode_token_without_verification` skips signature validation entirely. If called by mistake instead of `verify_token`, any crafted JWT is accepted.
- Files: `app/auth/jwt_auth.py:149-155`
- Current mitigation: Method is only used internally for expiry checks.
- Recommendations: Rename to `_decode_unverified` to make private intent explicit and reduce call-site mistake risk.

**Redis Blacklist Fails Closed (Blocks All Auth):**
- Risk: `is_token_blacklisted` returns `True` on any Redis error (line 203: `return True`). If Redis goes down, all authenticated requests are rejected as if their token is blacklisted, causing a full outage even though JWT signature verification would succeed independently.
- Files: `app/auth/redis_cache.py:200-203`
- Current mitigation: Redis is optional/graceful degradation is documented, but this logic defeats that.
- Recommendations: Return `False` on connectivity errors (fail open for blacklist check), and separately log the Redis failure. Or skip blacklist check entirely when Redis is unavailable.

---

## Tech Debt

**Duplicate `_auth` / `_sender` Functions Across Route Files:**
- Issue: `_auth`, `_sender`, and `_resolve_agent_id` are copy-pasted into `routes_p1.py`, `routes_p2.py`, `routes_artifacts.py`, `routes_memory.py`, `routes_acn.py`, and `routes_websocket.py` with slight variations. Any security fix to one must be applied to all manually.
- Files: `app/api/routes_p1.py:22-36`, `app/api/routes_p2.py:29-52`, `app/api/routes_artifacts.py:21-36`, `app/api/routes_memory.py:20-40`, `app/api/routes_websocket.py:133-140`
- Impact: High maintenance burden; divergence risk on fixes.
- Fix approach: Extract a shared `app/auth/api_key_deps.py` with a single `require_api_key` FastAPI dependency and a `resolve_agent_id(key_info, db)` helper.

**`routes_auth.py` Uses `str()` Instead of `json.dumps()` for List/Dict Fields:**
- Issue: Agent registration via `/v1/auth/agent/register` stores `capabilities` as Python `str()` representation (e.g., `"['coding', 'review']"`) rather than valid JSON. This breaks any code expecting `json.loads()` on the column.
- Files: `app/api/routes_auth.py:88-90`
- Impact: Capability matching queries against agents registered via this path will silently fail or return incorrect results.
- Fix approach: Replace `str(agent_data.capabilities)` with `json.dumps(agent_data.capabilities)` and `str(agent_data.labels)` with `json.dumps(agent_data.labels or {})`.

**Pervasive Use of Deprecated `datetime.utcnow()`:**
- Issue: `datetime.utcnow()` is deprecated in Python 3.12 (the runtime version in `.venv`). The codebase uses it in 40+ locations across services, repositories, and route files.
- Files: `app/database/repositories/base.py:59`, `app/services/task_service.py` (multiple), `app/services/agent_service.py`, `app/services/heartbeat_service.py`, `app/services/remote_agent_service.py`, `app/services/hatchet_service.py`, `app/services/workflow_coordinator.py`, `app/api/routes_health.py`, `app/api/routes_auth.py`, and more.
- Impact: DeprecationWarnings in Python 3.12; will break in Python 3.14+. Comparison bugs when mixing naive `utcnow()` results with aware `datetime.now(timezone.utc)` timestamps (both patterns exist in the codebase).
- Fix approach: Replace all `datetime.utcnow()` with `datetime.now(timezone.utc)`. Ensure stored ISO strings include timezone suffix.

**`APIKeyManager.validate_api_key` Performs Full Table Scan Per Request:**
- Issue: Every API request triggers `SELECT * FROM api_keys WHERE is_active = true ...` and then iterates all rows in Python to find a hash match. This is O(n) in the number of API keys.
- Files: `app/auth/api_keys.py:230-244`
- Impact: Acceptable now with few keys, but degrades linearly as more agents register. Each request also issues an additional `UPDATE` to set `last_used_at`.
- Fix approach: Add a hash prefix column indexed in the database (first 8 chars of the hash) to narrow the scan, or cache validated keys in Redis with a short TTL.

**`requirements.txt` Lists SQLAlchemy and Alembic but Neither is Used:**
- Issue: `sqlalchemy==2.0.23` and `alembic==1.12.1` appear in `requirements.txt`. The application uses raw `sqlite3` / `libsql` directly. There is no `alembic.ini`, no `env.py`, and no migration scripts using Alembic.
- Files: `requirements.txt:9-10`
- Impact: Installs ~10 MB of unused dependencies; creates false impression that ORM migrations are in use.
- Fix approach: Remove both from `requirements.txt`. SQL migration files exist separately in `database/migrations/`.

**`zvec` Listed as a Dependency but Not Integrated:**
- Issue: `zvec==0.1.0` is in `requirements.txt` and a `zvec_path` directory is created on startup, but no code in `app/` imports or uses zvec. Phase 2.4 (Vector Database Integration) is marked as not yet started.
- Files: `requirements.txt:7`, `app/config.py:23`, `app/main.py:35`
- Impact: Installs an obscure/potentially unmaintained package; directory creation is a no-op cost.
- Fix approach: Remove from `requirements.txt` until Phase 2.4 begins.

**`HatchetService` Simulates Hatchet Instead of Integrating It:**
- Issue: The `HatchetService` stores `self._hatchet_client = None` and all workflow orchestration is simulated in-memory using `self._running_workflows` dict with `asyncio.sleep` polling. No actual Hatchet server communication occurs.
- Files: `app/services/hatchet_service.py:54-58`
- Impact: Workflow routes at `/v1/workflows/*` appear functional but provide no real durable execution or retry guarantees.
- Fix approach: Implement the actual Hatchet HTTP/gRPC client calls or clearly mark these routes as experimental/not-production.

**Schema Definition Scattered Across `main.py` Lifespan:**
- Issue: All `CREATE TABLE IF NOT EXISTS` DDL statements live inline in the `lifespan` function in `main.py` (lines 43-168). This means: no versioning, no rollback path, and schema changes require editing startup code rather than migration files. The `database/migrations/` folder contains only 3 SQL files that cover an older schema subset.
- Files: `app/main.py:43-173`, `database/migrations/001_initial.sql`, `database/migrations/002_api_keys.sql`, `database/migrations/003_acn_federation.sql`
- Impact: Schema drift between migration files and actual runtime schema makes it impossible to recreate a consistent database from migrations alone.
- Fix approach: Move DDL to versioned migration files. Run them in order on startup instead of raw `CREATE TABLE IF NOT EXISTS` strings.

**`time.sleep(1)` in Application Startup:**
- Issue: The lifespan startup calls `time.sleep(1)` between two `db.sync()` calls, blocking the event loop during server initialization.
- Files: `app/main.py:177-179`
- Impact: Adds 1+ second to every server startup. Blocks async event loop (synchronous sleep in async context).
- Fix approach: If sync is needed for Turso embedded replicas, use `await asyncio.sleep(1)`. Better: remove the double-sync pattern entirely since remote Turso mode's `sync()` is a no-op.

---

## Performance Bottlenecks

**`get_available_tasks` Fetches All Queued Tasks into Python:**
- Problem: `TaskService.get_available_tasks` retrieves all `status=queued` tasks from the database, then filters them in Python via `capability_matcher._score_agent`.
- Files: `app/services/task_service.py:568-592`
- Cause: No capability-based database filter; all matching happens in application memory.
- Improvement path: Store capabilities as a normalized join table or use SQLite JSON functions to filter at the query level.

**In-Memory Rate Limiter Not Process-Safe:**
- Problem: `_rate_limits` dict in `routes_p2.py` is an in-memory `defaultdict`. Under multiple uvicorn workers or after any restart, rate limit state is lost and not shared.
- Files: `app/api/routes_p2.py:24-43`
- Cause: Intentional simplification ("in-memory rate limiter state"), no Redis or shared store backing.
- Improvement path: Delegate to Redis using sliding window counters, or use `slowapi` (already in `requirements.txt`) with Redis storage.

**`EventDeliveryService` Shares a Single `httpx.AsyncClient`:**
- Problem: The `_client` instance is lazy-initialized but never closed during normal shutdown since `EventDeliveryService` is not registered in the lifespan.
- Files: `app/services/event_delivery_service.py:21-26, 105-108`
- Cause: No lifecycle management for the HTTP client.
- Improvement path: Register `EventDeliveryService.close()` in the lifespan shutdown sequence.

---

## Fragile Areas

**`_sender` / `_resolve_agent_id` Silent Fallback to `"unknown"`:**
- Files: `app/api/routes_p1.py:31-36`, `app/api/routes_p2.py:47-52`, `app/api/routes_artifacts.py:30-36`, `app/api/routes_websocket.py:133-140`
- Why fragile: When an API key's name does not start with `"acn-agent-"`, the sender resolves to the string `"unknown"` silently. All artifacts, tools, locks, and traces uploaded will have `registered_by = "unknown"`. Ownership queries will be incorrect.
- Safe modification: Add a fallback lookup by `key_info["key_id"]` against a `registered_by` column, or return an error if the caller cannot be identified.

**`cursor.rowcount` Unreliable with libsql (Turso):**
- Files: `app/auth/api_keys.py:301`, `app/database/repositories/base.py:130, 147`, `app/database/repositories/tasks.py:157`
- Why fragile: The libsql Python driver does not guarantee that `cursor.rowcount` returns the affected row count for all query types. In Turso remote mode, UPDATE/DELETE `rowcount` may return `-1` or `0` even on success, causing false "not found" responses.
- Safe modification: Confirm row existence with a subsequent `SELECT` or use `RETURNING` clause (SQLite 3.35+).

**`WebSocket _connections` Dict is Module-Level Global:**
- Files: `app/api/routes_websocket.py:19`
- Why fragile: `_connections: Dict[str, WebSocket]` is a module-global. If two requests race to connect with the same `agent_id`, the second silently overwrites the first with no cleanup. The overwritten WebSocket may remain open on the client side, consuming resources.
- Safe modification: Add a check-and-close step before inserting into `_connections`. Consider using an asyncio `Lock` for the connect/disconnect pair.

**Task Auto-Assignment Races on Concurrent Claims:**
- Files: `app/services/task_service.py:471-505`, `app/services/task_service.py:133-199`
- Why fragile: `_attempt_auto_assignment` reads a task status, then separately calls `claim_task`, which re-reads the status. There is no database-level atomic check-and-claim (e.g., `UPDATE ... WHERE status='queued' RETURNING id`). Two agents could both see a task as `queued` simultaneously and one claim will silently fail.
- Safe modification: Use a single `UPDATE tasks SET status='claimed', owner=:agent WHERE id=:id AND status='queued'` and check `rowcount` to determine if the claim succeeded atomically.

---

## Missing Critical Features

**No Test Suite:**
- Problem: Zero test files exist outside `.venv`. `requirements.txt` lists `pytest`, `pytest-asyncio`, and `pytest-cov`, but no tests have been written.
- Blocks: Safe refactoring of fragile areas above, confidence in auth changes, regression detection.

**No OpenAPI Docs Exposed:**
- Problem: `docs_url=None, redoc_url=None` in the FastAPI app constructor disables all auto-generated documentation.
- Files: `app/main.py:197-198`
- Blocks: Developer onboarding, client generation, API discoverability.

**Heartbeat Monitoring Not Started in Lifespan:**
- Problem: `HeartbeatService.start_monitoring()` is defined but never called from `main.py` lifespan. Agents that disconnect will never be marked offline automatically.
- Files: `app/services/heartbeat_service.py:29-53`, `app/main.py` (absent)
- Blocks: Accurate agent status, task requeue on agent failure.

---

## Scaling Limits

**SQLite Single-Writer Constraint:**
- Current capacity: WAL mode allows concurrent reads; writes are serialized.
- Limit: High-frequency task claim/complete cycles from many agents will queue behind the single write lock. At ~50+ concurrent writing agents, contention becomes noticeable.
- Scaling path: Turso (libSQL) is already supported as an alternative; the connection layer handles the switch via env vars.

**`api_keys` Full Table Scan per Request (see Tech Debt above):**
- Current capacity: Acceptable up to ~100 keys.
- Limit: Degrades O(n) per authenticated request.

---

## Dependencies at Risk

**`zvec==0.1.0`:**
- Risk: Very early version of an obscure library; no usage in codebase; unclear maintenance status.
- Impact: Dependency pulled but unused.
- Migration plan: Remove until Phase 2.4 begins; evaluate at that time.

**`passlib[bcrypt]==1.7.4`:**
- Risk: `passlib` is in maintenance-only mode as of 2023. Python 3.12 generates deprecation warnings from `passlib`'s use of `datetime.utcnow()` internally.
- Impact: Bcrypt hashing still works, but upstream security fixes are unlikely.
- Migration plan: Replace with `bcrypt` directly (`import bcrypt`) or `argon2-cffi` for new projects.

---

*Concerns audit: 2026-04-07*
