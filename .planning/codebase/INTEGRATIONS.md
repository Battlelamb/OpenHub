---
last_mapped_commit: 13fcce7400bd66c4e9b5412c9ed677cd215f019a
---
# External Integrations

**Analysis Date:** 2026-05-25

## APIs & External Services

**Agent Collaboration Network (ACN):**
- OpenHub exposes invite, node, agent, task, and status APIs under `app/api/routes_acn.py` with prefix `/v1/acn`.
  - SDK/Client: internal Python bridge in `app/bridge/agent_bridge.py` and REST clients through `httpx`.
  - Auth: `AGENTHUB_ACN_ADMIN_KEY` for admin invite operations; per-agent API keys use the `X-API-Key` path in `app/auth/api_key_deps.py`.

**Hatchet workflow runtime:**
- Workflow orchestration adapters live in `app/services/hatchet_service.py`, `app/services/workflow_coordinator.py`, `app/api/routes_coordination.py`, and `app/api/routes_workflows.py`.
  - SDK/Client: service code wraps outbound workflow calls rather than a separate generated client.
  - Auth/config: `AGENTHUB_HATCHET_SERVER_URL`, `AGENTHUB_HATCHET_API_KEY`, `AGENTHUB_HATCHET_TENANT_ID`.

**OpenAI-compatible embeddings:**
- Optional embeddings path for vector search is implemented in `app/services/embedding_service.py` and used by `app/api/routes_search.py`.
  - SDK/Client: `openai` package from `requirements.txt`.
  - Auth/config: `AGENTHUB_OPENAI_API_KEY`, `AGENTHUB_EMBEDDING_PROVIDER`, `AGENTHUB_EMBEDDING_BASE_URL`, `AGENTHUB_EMBEDDING_MODEL_OVERRIDE`, `AGENTHUB_EMBEDDING_DIM_OVERRIDE`.

**Twilio/Hermes webhook bridge:**
- Public webhook bridge is mounted from `app/api/routes_twilio_webhook_proxy.py` at `/webhooks/twilio`.
  - SDK/Client: HTTP forwarding; signature validation belongs to the receiving Hermes/Twilio path.
  - Auth/config: environment names should be documented only from safe config, never from `.env` values.

## Data Storage

**Databases:**
- SQLite local default.
  - Connection: `AGENTHUB_DB_PATH`.
  - Client: custom raw-SQL `Database` wrapper in `app/database/connection.py` with `sqlite3.Row` row factory.
- Turso/libSQL remote optional mode.
  - Connection: `AGENTHUB_TURSO_DATABASE_URL`, `AGENTHUB_TURSO_AUTH_TOKEN`.
  - Client: `libsql_experimental` or `libsql` imported by `app/database/connection.py`; query parameter adaptation is centralized in `_adapt_params()`.

**File Storage:**
- Local artifacts directory via `AGENTHUB_ARTIFACT_DIR`; API surface is `app/api/routes_artifacts.py`.
- Dashboard build artifacts must exist under `web/dist` for `/dashboard` to mount in `app/main.py`.

**Caching:**
- Redis is optional and used for token cache/blacklist through `app/auth/redis_cache.py`.
- If Redis is unavailable, auth code falls back to in-memory behavior; preserve graceful degradation.

## Authentication & Identity

**Auth Provider:**
- Custom JWT + API key + Casbin RBAC.
  - JWT implementation: `app/auth/jwt_auth.py`, `app/auth/dependencies.py`, `app/api/routes_auth.py`.
  - API-key implementation: `app/auth/api_keys.py`, `app/auth/api_dependencies.py`, `app/auth/api_key_deps.py`.
  - RBAC policies: `app/auth/rbac/policies/rbac_model.conf`, `app/auth/rbac/policies/rbac_policy.csv`, `app/auth/rbac/policies/role_inheritance.csv`.

**Dashboard auth:**
- React login form uses `/v1/auth/admin/login` through `web/src/components/forms/LoginForm.tsx` and `web/src/lib/api-client.ts`.
- Synthetic admin JWT subjects are supported by backend tests in `tests/unit/test_admin_dashboard_auth.py` and `tests/unit/test_dashboard_auth_alignment.py`.

## Monitoring & Observability

**Error Tracking:**
- No third-party error tracking service detected.
- RFC 7807 problem responses are centralized through middleware/error helpers in `app/middleware.py` and `app/models/errors.py`.

**Logs:**
- Structured logging with `structlog` is configured in `app/logging.py` and used across services/routes (`logger.info`, `logger.warning`, `logger.error`).

**Metrics:**
- Prometheus metrics endpoint is exposed via `app/api/routes_metrics.py` and mounted in `app/main.py`.
- Health endpoints are in `app/api/routes_health.py`; note that legacy aggregate counts may be placeholders and should not be treated as ACN/task truth without checking specific endpoints.

## CI/CD & Deployment

**Hosting:**
- Repository supports pip install (`openhub` console script), local Uvicorn, and Docker Compose.
- Dockerfile uses `python:3.11-slim`, copies backend/migration files, runs as non-root `openhub`, and exposes port 7788.

**CI Pipeline:**
- No GitHub Actions workflow files were found under `.github/workflows` during this mapping.
- Local verification commands are encoded in `pyproject.toml`, `web/package.json`, and GSD planning/config files.

## Environment Configuration

**Required env vars:**
- `AGENTHUB_ADMIN_USER`
- `AGENTHUB_ADMIN_PASSWORD`
- `AGENTHUB_SECRET_KEY`
- `AGENTHUB_JWT_SECRET_KEY`

**Common optional env vars:**
- `AGENTHUB_PORT`, `AGENTHUB_HOST`, `AGENTHUB_DB_PATH`, `AGENTHUB_ARTIFACT_DIR`
- `AGENTHUB_REDIS_URL`
- `AGENTHUB_TURSO_DATABASE_URL`, `AGENTHUB_TURSO_AUTH_TOKEN`, `AGENTHUB_VECTOR_SEARCH_ENABLED`
- `AGENTHUB_EMBEDDING_PROVIDER`, `AGENTHUB_OPENAI_API_KEY`
- `AGENTHUB_ACN_ADMIN_KEY`, `AGENTHUB_ACN_NODE_ID`, `AGENTHUB_ACN_NODE_URL`

**Secrets location:**
- `.env` may exist locally but must never be read into codebase maps or committed.
- `.env.example` is safe for variable names and placeholder guidance.

## Webhooks & Callbacks

**Incoming:**
- `/v1/ws` and `/v1/ws/ui` WebSocket connections in `app/api/routes_websocket.py` and `app/api/routes_ws_ui.py`.
- `/webhooks/twilio` GET/POST bridge in `app/api/routes_twilio_webhook_proxy.py`.
- ACN node and agent heartbeat/task endpoints in `app/api/routes_acn.py`.

**Outgoing:**
- Agent bridge polling/submission uses outbound HTTP from `app/bridge/agent_bridge.py`.
- Event delivery service uses HTTP delivery from `app/services/event_delivery_service.py`.
- Embedding backends may call local sentence-transformers or OpenAI-compatible endpoints through `app/services/embedding_service.py`.

---

*Integration audit: 2026-05-25*
