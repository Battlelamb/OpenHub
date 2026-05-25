---
last_mapped_commit: 13fcce7400bd66c4e9b5412c9ed677cd215f019a
---
# Coding Conventions

**Analysis Date:** 2026-05-25

## Naming Patterns

**Files:**
- Backend API files use `routes_<domain>.py` in `app/api/`; keep new route modules consistent with `app/api/routes_tasks.py` and `app/api/routes_acn.py`.
- Backend services use `<domain>_service.py` or focused manager/worker names such as `connection_manager.py`, `embedding_retry_worker.py`.
- Backend repositories use plural domain files under `app/database/repositories/`, e.g. `tasks.py`, `agents.py`, `acn_nodes.py`.
- Frontend components use PascalCase filenames under `web/src/components/`, e.g. `WorkflowCanvas.tsx`, `KanbanBoard.tsx`.
- Frontend hooks use `useX.ts` naming, especially under `web/src/hooks/queries/`.

**Functions:**
- Python functions and methods use snake_case: `create_task()`, `claim_task()`, `get_database()`.
- FastAPI handlers use action-oriented snake_case names: `admin_dashboard()`, `post_search()`, `acquire_lock()`.
- React functions/components use PascalCase for components and camelCase for helpers/callbacks: `WorkflowCanvas`, `handleDragEnd`, `buildWsUrl`.

**Variables:**
- Python locals use snake_case; constants and enum values use uppercase where appropriate.
- TypeScript locals use camelCase; constants can be uppercase arrays/records like `COLUMNS` in `web/src/components/kanban/KanbanBoard.tsx`.
- Environment variables use `AGENTHUB_` prefix and uppercase names in `app/config.py`.

**Types:**
- Python models are Pydantic classes in PascalCase (`Task`, `TaskCreate`, `SearchRequest`).
- TypeScript interfaces/types are PascalCase in `web/src/types/entities.ts` and route/component files.

## Code Style

**Formatting:**
- Python formatting target is Black with line length 88 and Python 3.11 target in `pyproject.toml`.
- isort uses Black profile in `pyproject.toml`.
- TypeScript formatting is standard project style: single quotes, trailing commas where existing code has them, semicolon-free style in `web/src/`.

**Linting:**
- Python lint/type tools declared: flake8 and mypy in `pyproject.toml` (`disallow_untyped_defs = true`).
- Frontend lint command is `npm run lint` from `web/package.json`, backed by `web/eslint.config.js`.
- Do not mass-format unrelated files in feature slices; keep diffs small and GSD-plan scoped.

## Import Organization

**Order:**
1. Python stdlib imports first (`datetime`, `typing`, `uuid`, etc.).
2. Third-party imports next (`fastapi`, `pydantic`, `structlog`).
3. Relative app imports last (`from ..database.connection import get_database`).

**Path Aliases:**
- Frontend uses `@/` alias to `web/src` via `web/vite.config.ts` and `web/tsconfig.json`.
- Prefer `@/hooks/...`, `@/lib/...`, `@/components/...` over deep relative imports in dashboard code.

## Error Handling

**Patterns:**
- Use FastAPI `HTTPException` for explicit HTTP failure paths in route files, with status codes that match route semantics.
- Prefer RFC 7807 helpers for cross-cutting/problem responses in `app/models/errors.py` and `app/middleware.py`.
- Log structured events before raising or swallowing errors; see `TaskService` logging in `app/services/task_service.py`.
- For dashboard API failures, let `api()` in `web/src/lib/api-client.ts` throw `ApiError` and handle user copy at component/hook boundaries.

## Logging

**Framework:** structlog.

**Patterns:**
- Use `logger = get_logger(__name__)` in backend modules.
- Event names are machine-readable snake_case strings: `task_created_successfully`, `database_migrations_applied`, `vector_search_disabled`.
- Include context fields (`task_id`, `agent_id`, `error`) instead of interpolating free-form strings.
- Never log secret values; log only boolean availability, env var names, or redacted prefixes if required.

## Comments

**When to Comment:**
- Comment lifecycle ordering, feature gates, compatibility shims, and non-obvious operational invariants.
- Good examples: shutdown ordering in `app/main.py`, vector feature-gate comments in `app/api/routes_search.py`, dashboard SPA fallback comments in `app/main.py`.
- Avoid comments that restate obvious assignments.

**JSDoc/TSDoc:**
- Frontend currently uses minimal inline comments rather than full TSDoc.
- Prefer clear TypeScript names and explicit interface types over long component comments.

## Function Design

**Size:**
- Route handlers may be moderately long in legacy modules, but new work should push business logic into services when it crosses validation + persistence + side effects.
- Keep frontend components focused; extract reusable display logic to `web/src/components/common/` or domain component folders.

**Parameters:**
- FastAPI route dependencies should be explicit (`Depends(get_database)`, auth dependencies, `Query`, `Header`).
- Service constructors accept dependencies directly, e.g. `TaskService(database)`.
- React hooks should not be called inside nested submit helpers or conditionals; route/search hooks belong at component top level.

**Return Values:**
- Backend routes return Pydantic models or plain dictionaries aligned to frontend types.
- Service methods return domain models, booleans for state transition success, or `None` for not-found/invalid cases; document/cover ambiguous states with tests.
- Frontend hooks return typed query/mutation results from TanStack Query.

## Module Design

**Exports:**
- Backend modules usually export concrete routers/services/classes, not broad barrels.
- Frontend files export named components and hooks; keep default exports rare and consistent with existing code.

**Barrel Files:**
- `app/models/__init__.py`, `app/services/__init__.py`, `app/database/repositories/__init__.py` exist but most code imports direct modules.
- Dashboard uses direct `@/path/file` imports; do not add broad index barrels without project-wide decision.

## Security Conventions

- Never read `.env` or secret/key files for documentation; use `.env.example` only for safe variable names.
- Keep admin `ak_...` keys server-side; dashboard wrappers should use JWTs and backend-side admin key access.
- Preserve known-good tokens and environment files; do not rewrite credentials during unrelated slices.
- Secret scanning is mandatory before committing generated docs or config changes.

---

*Convention analysis: 2026-05-25*
