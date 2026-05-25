---
last_mapped_commit: 13fcce7400bd66c4e9b5412c9ed677cd215f019a
---
# Technology Stack

**Analysis Date:** 2026-05-25

## Languages

**Primary:**
- Python 3.11+ - backend API, services, models, database, bridge, scripts; package metadata in `pyproject.toml` requires `>=3.11`.
- TypeScript 5.7+ - dashboard application under `web/src/`, configured by `web/tsconfig.json`, `web/tsconfig.app.json`, and `web/tsconfig.node.json`.

**Secondary:**
- SQL / SQLite DDL - persistence schema and migrations under `app/database/migrations.py`, `alembic/`, and raw SQL repositories under `app/database/repositories/`.
- Bash - developer smoke and startup scripts such as `scripts/dev_start.sh`.
- CSS - dashboard styling via Tailwind CSS v4 and custom global CSS in `web/src/index.css`.

## Runtime

**Environment:**
- Backend: ASGI application served by Uvicorn from `app/main.py`.
- Local runtime observed during mapping: `python3 --version` reports Python 3.13.5; repository supports Python 3.11+ via `pyproject.toml`.
- Frontend: Vite dev/build runtime on Node.js; local mapping host reports Node v22.22.0 and npm 10.9.4.

**Package Manager:**
- Python: pip / PEP 621 metadata via `pyproject.toml`; pinned production dependency set in `requirements.txt`.
- Frontend: npm with `web/package-lock.json` committed.
- Lockfile: frontend lockfile present; no Python lockfile detected.

## Frameworks

**Core:**
- FastAPI 0.104.1 - primary REST and WebSocket API in `app/main.py` and `app/api/routes_*.py`.
- Uvicorn 0.24.0 - ASGI server, Docker command, and `openhub = app.main:run_server` console entry point.
- React 19 - dashboard UI under `web/src/`.
- Vite 6 - dashboard build/dev server configured by `web/vite.config.ts`.
- TanStack Router 1.87 - route tree generated in `web/src/routeTree.gen.ts`; route modules live in `web/src/routes/`.
- TanStack Query 5.59 - dashboard server-state cache, query keys in `web/src/lib/query-keys.ts`, query hooks in `web/src/hooks/queries/`.

**Testing:**
- pytest 7.4.3, pytest-asyncio 0.21.1, pytest-cov 4.1.0 - backend tests configured in `pyproject.toml` and `tests/conftest.py`.
- Vitest 4.1.7 + jsdom - frontend unit/component tests configured by `web/vitest.config.ts` and `web/src/test/setup.ts`.
- Playwright 1.60 - dashboard E2E under `web/e2e/dashboard.spec.ts`, configured by `web/playwright.config.ts`.

**Build/Dev:**
- hatchling - Python build backend in `pyproject.toml`.
- Alembic 1.12.1 - migrations run during application lifespan from `app/main.py` using `alembic.ini`.
- Tailwind CSS v4 via `@tailwindcss/vite` - dashboard styling through `web/vite.config.ts`.
- ESLint 10 + typescript-eslint 8.59 - frontend lint command in `web/package.json` and config in `web/eslint.config.js`.

## Key Dependencies

**Critical:**
- `fastapi` - all API routers; adding endpoints should follow existing route modules in `app/api/`.
- `pydantic` / `pydantic-settings` - request/response models and settings class in `app/config.py`.
- `pyjwt[crypto]` + `bcrypt` - JWT sessions and password hashing in `app/auth/jwt_auth.py` and `app/api/routes_auth.py`.
- `casbin` - RBAC model/policies in `app/auth/rbac/policies/`.
- `redis` - optional token/cache backend in `app/auth/redis_cache.py`; system degrades without Redis.
- `sqlalchemy-libsql` and libSQL support - Turso remote mode for vector/search runtime in `app/database/connection.py`.

**Infrastructure:**
- SQLite / Turso - local default DB path is `./data/state/agenthub.db`; Turso enabled by `AGENTHUB_TURSO_DATABASE_URL` and `AGENTHUB_TURSO_AUTH_TOKEN`.
- Redis - optional cache URL configured by `AGENTHUB_REDIS_URL`.
- Docker Compose - `docker-compose.yml` builds `agenthub` and provides a Redis service.
- Cloud/public serving is outside repository code; the app itself exposes `/dashboard` only when `web/dist/index.html` exists beside the backend.

**Dashboard UI:**
- `@hello-pangea/dnd` - Kanban drag/drop in `web/src/components/kanban/KanbanBoard.tsx`.
- `@xyflow/react` - Workflow Canvas in `web/src/components/canvas/WorkflowCanvas.tsx`.
- Radix UI primitives - dialog/select/tooltip/form building blocks in `web/src/components/ui/`.
- Zustand - auth/UI stores in `web/src/stores/auth-store.ts` and `web/src/stores/ui-store.ts`.
- MSW - frontend test request mocking in `web/src/mocks/server.ts` and `web/src/mocks/handlers.ts`.

## Configuration

**Environment:**
- Configuration uses Pydantic Settings with `AGENTHUB_` prefix in `app/config.py`.
- Required production/admin settings: `AGENTHUB_ADMIN_USER`, `AGENTHUB_ADMIN_PASSWORD`, `AGENTHUB_SECRET_KEY`, `AGENTHUB_JWT_SECRET_KEY`.
- Runtime paths: `AGENTHUB_DB_PATH`, `AGENTHUB_ARTIFACT_DIR`.
- Optional integrations: `AGENTHUB_REDIS_URL`, `AGENTHUB_TURSO_DATABASE_URL`, `AGENTHUB_TURSO_AUTH_TOKEN`, `AGENTHUB_OPENAI_API_KEY`, `AGENTHUB_HATCHET_SERVER_URL`, `AGENTHUB_HATCHET_API_KEY`.
- `.env.example` documents variables; `.env` must not be read or committed.

**Build:**
- Backend package/build: `pyproject.toml`, `requirements.txt`, `hatchling`, `openhub = app.main:run_server`.
- API container: `Dockerfile`, `docker-compose.yml`.
- Dashboard: `web/package.json`, `web/vite.config.ts`, `web/tsconfig*.json`, `web/eslint.config.js`, `web/vitest.config.ts`, `web/playwright.config.ts`.

## Platform Requirements

**Development:**
- Python 3.11+ with pip; a virtualenv is normally used under `.venv/`.
- Node.js 22+ and npm 10+ for dashboard build/test in `web/`.
- Optional Redis for production-like auth cache; tests can run without Redis.
- Turso credentials only for vector-search live tests marked `turso`.

**Production:**
- API listens on port 7788 by default.
- Docker image is Python 3.11 slim, non-root `openhub` user, and no reload flag.
- `web/dist` must be built and present for `/dashboard` static SPA serving.
- Persistent volumes should preserve `data/state` and `data/artifacts`.

---

*Stack analysis: 2026-05-25*
