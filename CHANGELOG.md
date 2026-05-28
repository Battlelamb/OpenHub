# Changelog

All notable changes to OpenHub will be documented in this file. Release tags are created only after an explicit operator decision.

## Unreleased

### Added

- Manual **OpenHub Release Verification** GitHub Actions workflow (`workflow_dispatch`) that validates an explicitly chosen version, builds Python artifacts, runs release-focused checks, builds the dashboard, builds the Docker image, and uploads local workflow artifacts without publishing to any registry.
- Dependency drift guard (`scripts/check_dependency_drift.py`) for backend Python manifests and frontend `package.json` / `package-lock.json` root specs.
- CI dependency drift job so manifest drift is caught before packaging/release work.

### Guardrails

- No automatic tag creation from CI or the release verification workflow.
- No PyPI, Docker Hub, GHCR, or other registry publishing in the default workflow path.
- The release workflow requires `confirm_no_publish=true` and refuses existing tags or versions that do not match `pyproject.toml`.

## [0.1.0] — 2026-05-20

### 🚀 Highlights

First public release of OpenHub — a self-hosted coordination backend for AI coding agents.

### ✨ Added

**Backend (Phase 1–3)**
- Real JWT + API key authentication with Casbin RBAC (admin, agent, viewer)
- Agent registration with capability declaration and smart matching
- Task queue with claim/lease mechanism and automatic recovery on agent failure
- WebSocket real-time events with first-frame JWT auth
- Heartbeat-based offline agent detection
- RFC 7807 Problem Details error format across all endpoints
- SlowAPI rate limiting with Prometheus metrics
- Alembic migration system for schema versioning
- Vector semantic search (opt-in beta) via Turso/libSQL native F32_BLOB columns
- Local + OpenAI embedding backends with auto-indexing hooks
- Agent-to-agent messaging with conversation threads
- Shared memory store, artifact/file sharing, resource locking
- Workflow orchestration for multi-step DAG pipelines
- 60+ REST API endpoints with interactive Swagger docs

**Command Center UI (Phase 4)**
- React + Vite dashboard with live agent/task/workflow control
- DLQ panel, cost tracking, distributed trace viewer
- Shared memory viewer, resource lock panel
- Mobile-responsive layout (tables → cards at small widths)
- i18n support (English + Turkish)
- Dark/light theme

**Release Readiness (Phase 5)**
- `pip install openhub` — PEP 621 metadata with hatchling build backend
- `openhub` console command starts the server
- Docker Compose with health checks, restart policies, non-root user
- Graceful shutdown — in-flight tasks drained to queue on server stop
- Stuck work recovery — stale task detection + admin recovery endpoint
- Playwright E2E tests (login, navigation, validation)
- `.env.example` with all required/optional variables

### 🔒 Security

- Auth stub removed — all protected endpoints require valid JWT or API key
- Admin credentials via environment variables (no hardcoded defaults in production)
- CORS lockdown with configurable origins
- Non-root user in Docker container
- Secrets fail-fast in Docker Compose (`${VAR:?error}`)

### 📦 Infrastructure

- Python 3.11+ / FastAPI / SQLite (WAL mode)
- React 19 + Vite + Tailwind v4 + shadcn/ui
- Pydantic v2 data validation
- structlog structured JSON logging
- Prometheus metrics endpoint

### 📝 Known Limitations

- Vector search requires Turso (local SQLite returns 503)
- Vector search is English-only (sentence-transformers/all-MiniLM-L6-v2)
- No cross-encoder re-ranking in vector search
- Redis optional (graceful degradation to in-memory)
