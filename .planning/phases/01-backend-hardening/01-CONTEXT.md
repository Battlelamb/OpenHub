# Phase 1: Backend Hardening - Context

**Gathered:** 2026-04-07
**Status:** Ready for planning

<domain>
## Phase Boundary

Fix silent correctness bugs and security holes in the existing FastAPI backend so it is correct, secure, and observable. No new features - pure hardening of what exists. Covers: auth stub removal, admin credential replacement, capabilities JSON fix, heartbeat wiring, CORS lockdown, schema migration consolidation, OpenAPI exposure, structured error responses, datetime unification, auth helper consolidation, rate limiting, Prometheus metrics, and structured logging.

</domain>

<decisions>
## Implementation Decisions

### Error Response Format
- **D-01:** Use RFC 7807 Problem Details as the standard error response shape across all endpoints ({type, title, status, detail, instance})
- **D-02:** Validation errors include field-level detail - an 'errors' array with field name + message per invalid field
- **D-03:** Rate-limited responses include Retry-After header plus remaining/limit in response headers
- **D-04:** Internal server errors (500) never expose stack traces in the response body - generic message in response, full trace in server logs only

### Logging
- **D-05:** Structured JSON logging via structlog with {event, error_type, status, path, trace_id} - machine-parseable for monitoring

### Admin Credentials
- **D-06:** Replace hardcoded admin/admin123 with AGENTHUB_ADMIN_USER + AGENTHUB_ADMIN_PASSWORD environment variables
- **D-07:** Server refuses to start if admin env vars are not set - no defaults, not even in development mode

### Auth Stub Cleanup
- **D-08:** Delete app/dependencies.py entirely - all routes must use real auth from app/auth/dependencies.py
- **D-09:** Consolidate duplicate _auth/_sender helpers into FastAPI middleware - auth runs before all routes, no per-route imports needed

### Migration Strategy
- **D-10:** Use Alembic for schema migrations with full SQLAlchemy ORM models - auto-generate migrations from model changes
- **D-11:** Move all 125 lines of inline DDL from main.py into Alembic initial migration revision
- **D-12:** This is a significant shift from current raw SQL approach - requires defining SQLAlchemy models for all 16 existing tables

### Redis Behavior
- **D-13:** Keep current fail-closed behavior for Redis blacklist checks - when Redis is down, all auth is blocked (strictest security posture)

### Claude's Discretion
- Specific implementation of Prometheus metrics endpoint layout
- Exact structlog configuration and processors
- How to handle the decode_token_without_verification rename
- ACN admin key and invite code persistence approach (within security constraints)
- API key validation optimization (replacing full table scan)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Security Concerns
- `.planning/codebase/CONCERNS.md` - All security issues with file:line references (auth stub, hardcoded creds, CORS, WebSocket token, Redis blacklist)

### Architecture
- `.planning/codebase/ARCHITECTURE.md` - Layered architecture (routes -> services -> repos -> DB)
- `.planning/codebase/CONVENTIONS.md` - Code style, naming patterns, error handling chain
- `.planning/codebase/STACK.md` - Current dependencies and versions

### Auth Implementation
- `app/dependencies.py` - The stub to be deleted (lines 41-59)
- `app/auth/dependencies.py` - The real auth implementation
- `app/auth/api_keys.py` - Hashed key store
- `app/api/routes_auth.py:244-252` - Hardcoded admin credentials
- `app/api/routes_auth.py:88-90` - Capabilities str() bug

### Database
- `app/main.py` - Inline DDL to be migrated (lifespan function)
- `app/database/connection.py` - Current raw SQL Database class

### Research
- `.planning/research/PITFALLS.md` - Phase 1 pitfalls with prevention strategies
- `.planning/research/SUMMARY.md` - Overall research synthesis

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `app/auth/jwt_auth.py` - JWTManager with full token lifecycle (create, verify, refresh, blacklist)
- `app/auth/rbac/enforcer.py` - Casbin RBAC enforcer with file-based policy
- `app/auth/redis_cache.py` - Redis async client with graceful degradation pattern
- `app/logging.py` - Existing structured logging setup (needs enhancement for JSON output)

### Established Patterns
- Service layer pattern: routes delegate to services, services to repositories
- Repository base class: BaseRepository[T] with _row_to_model/_model_to_dict
- Config via pydantic-settings: Settings class with AGENTHUB_ prefix
- Dependency injection via FastAPI Depends()

### Integration Points
- Auth middleware replaces per-route _auth imports across routes_p1.py, routes_p2.py, routes_artifacts.py, routes_memory.py, routes_acn.py, routes_websocket.py
- SQLAlchemy models will live alongside existing raw SQL Database class initially
- Alembic env.py connects to same DB path from AGENTHUB_DB_PATH config
- Prometheus metrics endpoint added as new route in app/api/

</code_context>

<specifics>
## Specific Ideas

No specific requirements beyond the decisions captured above - open to standard approaches for implementation details.

</specifics>

<deferred>
## Deferred Ideas

None - discussion stayed within phase scope

</deferred>

---

*Phase: 01-backend-hardening*
*Context gathered: 2026-04-07*
