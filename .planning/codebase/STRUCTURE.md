---
last_mapped_commit: 13fcce7400bd66c4e9b5412c9ed677cd215f019a
---
# Codebase Structure

**Analysis Date:** 2026-05-25

## Directory Layout

```text
OpenHub/
├── app/                         # FastAPI backend package
│   ├── api/                     # Route modules for /v1 APIs, websockets, webhooks
│   ├── auth/                    # JWT, API keys, RBAC, Redis token cache
│   ├── bridge/                  # Python bridge client for remote agents
│   ├── database/                # DB wrapper, repositories, migration helpers
│   ├── models/                  # Pydantic domain/request/response models
│   ├── services/                # Business logic and background workers
│   ├── static/                  # Legacy static admin page
│   ├── config.py                # AGENTHUB_ settings
│   ├── main.py                  # FastAPI app, lifespan, route mounting, dashboard serving
│   └── middleware.py            # Error/middleware setup
├── web/                         # React + Vite dashboard
│   ├── src/routes/              # TanStack Router route modules
│   ├── src/components/          # UI, Kanban, canvas, layout, forms
│   ├── src/hooks/queries/       # TanStack Query hooks
│   ├── src/stores/              # Zustand auth/UI stores
│   ├── src/mocks/               # MSW handlers/server for frontend tests
│   └── e2e/                     # Playwright E2E tests
├── tests/                       # Backend pytest suite
│   ├── unit/                    # Unit/regression tests
│   └── integration/             # API/integration/vector tests
├── alembic/                     # Alembic migration revisions
├── docs/                        # OpenHub docs/specs/onboarding
├── scripts/                     # Bridge runner and smoke/cleanup utilities
├── data/                        # Local runtime state/artifacts/logs (not a source package)
├── .planning/                   # GSD planning, codebase maps, phase evidence
├── .claude/, .hermes/, .codex/  # open-gsd/get-shit-done-redux local runtime surfaces
├── Dockerfile                   # Production API image
├── docker-compose.yml           # API + Redis composition
├── pyproject.toml               # Python package metadata and test/tool config
├── requirements.txt             # Pinned Python dependencies
└── README.md                    # Public quick start and API overview
```

## Directory Purposes

**`app/api/`:**
- Purpose: FastAPI route modules grouped by domain.
- Contains: `routes_auth.py`, `routes_agents.py`, `routes_tasks.py`, `routes_acn.py`, `routes_workflows.py`, `routes_search.py`, `routes_ws_ui.py`, `routes_twilio_webhook_proxy.py`, etc.
- Key files: `app/api/routes_tasks.py`, `app/api/routes_acn.py`, `app/api/routes_auth.py`, `app/api/routes_search.py`.

**`app/services/`:**
- Purpose: Domain/business logic outside route handlers.
- Contains: task lifecycle, heartbeat monitoring, capability matching, discovery, workflow coordination, vector search, event delivery.
- Key files: `app/services/task_service.py`, `app/services/connection_manager.py`, `app/services/heartbeat_service.py`, `app/services/vector_search_service.py`.

**`app/database/`:**
- Purpose: Persistence connection and repositories.
- Contains: `connection.py` SQLite/Turso wrapper, `models.py`, `migrations.py`, table-specific repositories.
- Key files: `app/database/connection.py`, `app/database/repositories/tasks.py`, `app/database/repositories/agents.py`, `app/database/repositories/acn_nodes.py`.

**`app/auth/`:**
- Purpose: AuthN/AuthZ implementation.
- Contains: JWT helpers, API-key validation, FastAPI dependencies, Redis cache, Casbin RBAC.
- Key files: `app/auth/jwt_auth.py`, `app/auth/api_keys.py`, `app/auth/dependencies.py`, `app/auth/rbac/enforcer.py`.

**`web/src/routes/`:**
- Purpose: Dashboard page routes.
- Contains: login, authenticated layout, agents, tasks, workflows, health, locks, memory, settings, costs, traces, DLQ.
- Key files: `web/src/routes/_authed.tsx`, `web/src/routes/login.tsx`, `web/src/routes/_authed/tasks/index.tsx`, `web/src/routes/_authed/tasks/$taskId.tsx`.

**`web/src/components/`:**
- Purpose: Reusable dashboard UI.
- Contains: Kanban board/cards/columns, workflow canvas, layout shell, forms, common renderers, shadcn/Radix-style UI atoms.
- Key files: `web/src/components/kanban/KanbanBoard.tsx`, `web/src/components/canvas/WorkflowCanvas.tsx`, `web/src/components/forms/LoginForm.tsx`, `web/src/components/common/SemanticSearchPanel.tsx`.

**`tests/`:**
- Purpose: Backend verification.
- Contains: 30 unit test files and 10 integration test files at mapping time.
- Key files: `tests/conftest.py`, `tests/unit/test_admin_dashboard_auth.py`, `tests/integration/test_task_lifecycle.py`, `tests/integration/test_search_api.py`.

## Key File Locations

**Entry Points:**
- `app/main.py`: backend app, lifespan, route registration, dashboard mount, `run_server()`.
- `web/src/main.tsx`: dashboard root, QueryClient, TanStack Router setup.
- `scripts/run_bridge.py`: CLI bridge runner for agents.
- `app/bridge/agent_bridge.py`: reusable bridge class.

**Configuration:**
- `app/config.py`: all `AGENTHUB_` application settings.
- `pyproject.toml`: Python packaging, pytest, black/isort/mypy config.
- `requirements.txt`: pinned backend dependencies.
- `web/package.json`: frontend scripts/dependencies.
- `web/vite.config.ts`: dashboard base path, proxy, aliases, build outDir.
- `web/vitest.config.ts`: frontend test environment.
- `web/playwright.config.ts`: E2E against `http://localhost:7788`.
- `.gsdrc.toml`, `.gsd/provider-config.json`: GSD operating configuration.

**Core Logic:**
- `app/services/task_service.py`: task state machine and recovery/drain behavior.
- `app/api/routes_tasks.py`: task API surface.
- `app/api/routes_acn.py`: ACN onboarding, remote agents/tasks, invites, heartbeat/status.
- `app/services/connection_manager.py`: WebSocket broadcast/state.
- `app/services/embedding_hooks.py`: semantic indexing scheduling.
- `app/services/embedding_retry_worker.py`: retry worker lifecycle.

**Testing:**
- `tests/conftest.py`: backend env defaults, TestClient, auth fixtures, Turso skip marker.
- `web/src/test/setup.ts`: Vitest setup and MSW lifecycle.
- `web/src/mocks/handlers.ts`: frontend mock API handlers.
- `web/e2e/dashboard.spec.ts`: Playwright dashboard E2E smoke.

## Naming Conventions

**Files:**
- Backend route modules: `app/api/routes_<domain>.py`.
- Backend services: `app/services/<domain>_service.py` or explicit worker/manager names.
- Backend models: `app/models/<domain>.py`.
- Backend tests: `tests/unit/test_<thing>.py`, `tests/integration/test_<flow>.py`.
- Frontend components: PascalCase `.tsx` files such as `WorkflowCanvas.tsx`, `KanbanBoard.tsx`.
- Frontend query hooks: `web/src/hooks/queries/use<Domain>.ts`.
- Frontend tests: colocated `*.test.ts` / `*.test.tsx`.

**Directories:**
- Domain grouping is preferred over generic utility dumping.
- Dashboard routes mirror URL structure under `web/src/routes/_authed/`.
- UI atoms live in `web/src/components/ui/`; domain components live in `web/src/components/<domain>/`.

## Where to Add New Code

**New backend API feature:**
- Route: `app/api/routes_<feature>.py` or an existing domain route.
- Service logic: `app/services/<feature>_service.py` if business logic exceeds route glue.
- Models: `app/models/<feature>.py` or local request models in route file for narrow P2/P1 style endpoints.
- Persistence: `app/database/repositories/<feature>.py` and migration under `alembic/versions/` or migration helper if schema changes.
- Tests: `tests/unit/test_<feature>.py` and/or `tests/integration/test_<feature>.py`.

**New dashboard page:**
- Route: `web/src/routes/_authed/<page>.tsx`.
- Query hook: `web/src/hooks/queries/use<Page>.ts`.
- Types: `web/src/types/entities.ts` if shared.
- Components: `web/src/components/<domain>/` or `web/src/components/common/`.
- Tests: colocated `*.test.tsx`, MSW additions in `web/src/mocks/handlers.ts`.

**New task/workflow UI behavior:**
- Reuse `web/src/components/kanban/` and `web/src/components/canvas/WorkflowCanvas.tsx`.
- Backend status mutation should go through `app/api/routes_tasks.py` and `app/services/task_service.py`.
- WebSocket updates should broadcast through `app/services/connection_manager.py` and be consumed in `web/src/hooks/useWebSocketSync.ts`.

**Utilities:**
- Backend shared helpers: prefer domain service modules or `app/<focused>.py`; avoid broad global helper files.
- Frontend shared helpers: `web/src/lib/` for non-React helpers, `web/src/components/common/` for reusable renderers.

## Special Directories

**`.planning/`:**
- Purpose: GSD project state, roadmap, phase plans, codebase maps, evidence.
- Generated: Yes, maintained by open-gsd/get-shit-done-redux workflows.
- Committed: Yes for project continuity artifacts.

**`.claude/`, `.hermes/`, `.codex/`:**
- Purpose: repo-local GSD runtime surfaces for Claude, Hermes, and Codex.
- Generated: Yes from `@opengsd/get-shit-done-redux`.
- Committed: Yes as local project operating surface; do not store provider credentials inside.

**`data/`:**
- Purpose: runtime SQLite state, artifacts, logs.
- Generated: Yes.
- Committed: generally no for live data; preserve `.gitkeep` patterns only if present.

**`web/dist/`:**
- Purpose: built dashboard assets for FastAPI `/dashboard` mount.
- Generated: Yes from `cd web && npm run build`.
- Committed: normally no unless release packaging intentionally includes static bundle.

**`.venv/`, `web/node_modules/`:**
- Purpose: local dependencies.
- Generated: Yes.
- Committed: no.

---

*Structure analysis: 2026-05-25*
