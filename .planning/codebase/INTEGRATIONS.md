# External Integrations

**Analysis Date:** 2026-04-07

## APIs & External Services

**Workflow Orchestration:**
- Hatchet - AI agent pipeline orchestration
  - SDK/Client: Direct HTTP calls (no official Python SDK imported); client simulated in `app/services/hatchet_service.py`
  - Auth: `AGENTHUB_HATCHET_API_KEY` env var
  - Server URL: `AGENTHUB_HATCHET_SERVER_URL` (default: `http://localhost:8080`)
  - Tenant: `AGENTHUB_HATCHET_TENANT_ID` (default: `"default"`)
  - Status: Integration scaffolded but workflows are simulated in-process (`_running_workflows` dict); not yet making live calls to Hatchet server

**Vector Embeddings:**
- sentence-transformers model `all-MiniLM-L6-v2` - Used for vector search via zvec
  - Configured via `AGENTHUB_EMBEDDING_MODEL` setting in `app/config.py`
  - No external API call; model runs locally via zvec

## Data Storage

**Databases:**
- SQLite (primary, local)
  - Connection: File path via `AGENTHUB_DB_PATH` (default: `./data/state/agenthub.db`)
  - Client: Custom raw-SQL `Database` class in `app/database/connection.py`
  - WAL mode enabled, foreign keys on, thread-local connections
  - 16 tables created via inline DDL in `app/main.py` lifespan: `agents`, `tasks`, `acn_nodes`, `remote_agent_mappings`, `api_keys`, `pending_applications`, `messages`, `threads`, `shared_memory`, `workflows`, `artifacts`, `resource_locks`, `trace_events`, `cost_tracking`, `shared_tools`, `agent_templates`

- Turso / libSQL (optional cloud DB)
  - Connection: `AGENTHUB_TURSO_DATABASE_URL` (format: `libsql://...`) + `AGENTHUB_TURSO_AUTH_TOKEN`
  - Client: `libsql_experimental` or `libsql` Python package (optional import with fallback)
  - Mode: Remote-only (no embedded replica sync); named params converted to positional `?` for libsql compatibility
  - Falls back to SQLite if env vars not set or package not installed
  - Detection logic: `app/database/connection.py` lines 19-29

**File Storage:**
- Local filesystem only
  - Artifacts: `AGENTHUB_ARTIFACT_DIR` (default: `./data/artifacts`)
  - Vector data: `AGENTHUB_ZVEC_PATH` (default: `./data/zvec`)
  - No S3/GCS/Azure Blob integration present

**Caching:**
- Redis 7 (optional)
  - Connection: `AGENTHUB_REDIS_URL` (default: `redis://localhost:6379`)
  - Client: `redis.asyncio` (async client) in `app/auth/redis_cache.py`
  - Purpose: JWT token caching and blacklist enforcement
  - Key prefixes: `openhub:tokens:` and `openhub:blacklist:` (configurable via settings)
  - Graceful degradation: Redis failure fails closed for blacklist checks (`is_token_blacklisted` returns `True` on error)
  - Docker Compose: `redis:7-alpine` with persistence (`--save 60 1`)

**Vector Storage:**
- zvec 0.1.0 (local)
  - Data path: `./data/zvec`
  - Used for agent/task semantic search (Phase 2.4)

## Authentication & Identity

**Auth Provider:**
- Custom (no third-party OAuth/SSO)
  - JWT: `app/auth/jwt_auth.py` - `JWTManager` class, HS256 algorithm, access (30 min) + refresh (7 day) tokens
  - API Keys: `app/auth/api_keys.py` - `APIKeyManager`, SHA-256 hashed keys stored in `api_keys` DB table, prefix `oh_`, scoped permissions
  - RBAC: `app/auth/rbac/enforcer.py` - Casbin enforcer with file-based policies at `app/auth/rbac/policies/rbac_model.conf` + `rbac_policy.csv`
  - Roles: `agent`, `admin`, `readonly`
  - Dual auth paths: JWT Bearer tokens for interactive sessions; API keys (`X-API-Key` header) for agent-to-hub communication
  - FastAPI dependencies wired in `app/dependencies.py`

**ACN (Agent Collaboration Network):**
- Self-hosted multi-node federation
  - Invite flow: admin creates single-use invite code via `POST /v1/acn/admin/invite`
  - New agents join via `POST /v1/acn/join` with invite code, receive permanent API key
  - In-memory invite store (short-lived, non-persistent across restarts)
  - Admin key: `AGENTHUB_ACN_ADMIN_KEY` env var; auto-generated on first request if not set
  - Endpoints: `app/api/routes_acn.py`

## Monitoring & Observability

**Error Tracking:**
- None (no Sentry or equivalent integrated)

**Metrics:**
- prometheus-client 0.19.0 declared in `requirements.txt` but not actively instrumented in route handlers as of current codebase state

**Logs:**
- structlog 23.2.0 (`app/logging.py`)
  - JSON format in production, console renderer in debug mode
  - RotatingFileHandler: 10MB max, 5 backups if `AGENTHUB_LOG_FILE` is set
  - Request ID (`X-Request-ID`) injected via `RequestTimingMiddleware` in `app/middleware.py`
  - Response time header: `X-Response-Time`
  - Log files: `./logs/` directory (present at repo root)

## CI/CD & Deployment

**Hosting:**
- VPS at `hub.brunhilde.cloud` (live production system)
- Systemd service management

**Container:**
- Docker (`Dockerfile`) - `python:3.11-slim` base
- Docker Compose (`docker-compose.yml`) - `agenthub` + `redis` services, bridge network
- Health check: `curl -f http://localhost:7788/v1/health` every 30s

**CI Pipeline:**
- None detected (no `.github/workflows/`, no CI config files)

## Environment Configuration

**Required env vars for production:**
- `AGENTHUB_JWT_SECRET_KEY` - Must be changed from default
- `AGENTHUB_SECRET_KEY` - Must be changed from default
- `AGENTHUB_ACN_ADMIN_KEY` - Admin key for invite management
- `AGENTHUB_REDIS_URL` - Redis connection (or omit for no token caching)

**Optional env vars:**
- `AGENTHUB_TURSO_DATABASE_URL` + `AGENTHUB_TURSO_AUTH_TOKEN` - Enable Turso cloud DB
- `AGENTHUB_HATCHET_API_KEY` + `AGENTHUB_HATCHET_SERVER_URL` - Enable live Hatchet workflows
- `AGENTHUB_LOG_FILE` - Enable file logging
- `AGENTHUB_EMBEDDING_MODEL` - Override embedding model for vector search

**Secrets location:**
- Environment variables only (no secrets files committed)
- Docker Compose environment section for containerized deployment

## Webhooks & Callbacks

**Incoming:**
- None - No dedicated webhook ingestion endpoint

**Outgoing:**
- Agent event callbacks via `app/services/event_delivery_service.py`
  - Uses `httpx.AsyncClient` with 15s timeout
  - Events: `task_assigned`, `task_updated`
  - Callback URL stored per-agent in `remote_agent_mappings` table (`callback_url` column)
  - Fire-and-forget pattern (errors logged, not retried)

## Real-Time Communication

**WebSocket:**
- Endpoint: `ws://host/v1/ws?token=oh_...` (`app/api/routes_websocket.py`)
- Auth: API key passed as `token` query parameter
- Push events: `task_assigned`, `message_received`, `agent_status_changed`, `task_completed`
- In-memory connection store (`_connections` dict, not distributed - single-instance only)

**Agent Bridge:**
- `app/bridge/agent_bridge.py` - `AgentBridge` client class
- Remote agents poll for tasks via HTTP (`httpx.AsyncClient`)
- Heartbeat interval: configurable (default 60s)
- Task poll interval: configurable (default 10s)
- Connects to hub via API key (`oh_...` prefix)

---

*Integration audit: 2026-04-07*
