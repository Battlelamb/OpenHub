---
last_mapped_commit: 13fcce7400bd66c4e9b5412c9ed677cd215f019a
---
# Testing Patterns

**Analysis Date:** 2026-05-25

## Test Framework

**Runner:**
- Backend: pytest 7.4.3 with pytest-asyncio and pytest-cov, configured in `pyproject.toml`.
- Frontend: Vitest 4.1.7 with jsdom and Testing Library, configured in `web/vitest.config.ts`.
- E2E: Playwright 1.60, configured in `web/playwright.config.ts`.

**Assertion Library:**
- Backend: standard pytest `assert` statements and FastAPI `TestClient` responses.
- Frontend: Vitest `expect` plus `@testing-library/jest-dom/vitest` from `web/src/test/setup.ts`.

**Run Commands:**
```bash
. .venv/bin/activate && pytest                         # Backend test suite with coverage options from pyproject.toml
. .venv/bin/activate && pytest tests/unit/test_auth.py  # Focused backend test file
cd web && npm run test                                  # Frontend Vitest suite
cd web && npm run typecheck                             # TypeScript typecheck
cd web && npm run build                                 # Typecheck + Vite production build
cd web && npx playwright test --reporter=list           # Dashboard E2E against localhost:7788
```

## Test File Organization

**Location:**
- Backend unit tests: `tests/unit/test_*.py` (30 files at mapping time).
- Backend integration tests: `tests/integration/test_*.py` (10 files at mapping time).
- Frontend component/hook/store tests: colocated under `web/src/**` as `*.test.ts` or `*.test.tsx` (16 files at mapping time).
- E2E tests: `web/e2e/dashboard.spec.ts`.

**Naming:**
- Backend test files use `test_<domain>.py`, e.g. `tests/unit/test_admin_dashboard_auth.py`.
- Frontend tests use `<Subject>.test.tsx` or `<hook>.test.ts`, e.g. `web/src/components/kanban/KanbanBoard.test.tsx`.

**Structure:**
```text
tests/
├── conftest.py
├── unit/test_*.py
└── integration/test_*.py
web/src/**/**.test.ts(x)
web/e2e/*.spec.ts
```

## Test Structure

**Suite Organization:**
```python
def test_admin_login_token_can_read_me_without_agent_row(test_client: TestClient) -> None:
    tokens = _synthetic_admin_tokens()
    response = test_client.get(
        "/v1/auth/me",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["role"] == "admin"
```

**Patterns:**
- Backend tests import `TestClient` and app fixtures from `tests/conftest.py`.
- `tests/conftest.py` sets required `AGENTHUB_` env vars before importing `app.main`; follow this pattern to avoid Pydantic settings failures.
- Use temporary DB path fixture defaults rather than `:memory:` because lifespan startup creates parent directories.
- Mark live Turso tests with `@pytest.mark.turso`; `pytest_collection_modifyitems` skips them when Turso env vars are absent.
- Frontend tests use MSW lifecycle from `web/src/test/setup.ts` and handlers in `web/src/mocks/handlers.ts`.

## Mocking

**Framework:**
- Backend: pytest monkeypatch/fakes and deterministic in-process fixtures.
- Frontend: MSW for network mocking, Vitest spies/mocks for local units.

**Patterns:**
```typescript
import { server } from '@/mocks/server'
import { http, HttpResponse } from 'msw'

server.use(
  http.get('/v1/tasks/search', () => HttpResponse.json({ tasks: [], total: 0 })),
)
```

**What to Mock:**
- Embedding backend calls in unit tests; `tests/conftest.py` includes `_MockEmbeddingBackend`.
- Browser/API responses in frontend component tests through MSW.
- Redis/Turso/network-only dependencies unless the test is explicitly marked as live integration.

**What NOT to Mock:**
- Task state transitions when testing `TaskService` invariants.
- Auth dependency behavior for dashboard-login regressions; use signed JWT helpers from `app/auth/jwt_auth.py`.
- Public API serialization contracts that the dashboard consumes.

## Fixtures and Factories

**Test Data:**
```python
@pytest.fixture(scope="session")
def admin_headers():
    token = create_access_token(
        subject="test-admin",
        claims={"role": "admin", "agent_name": "test-admin"},
    )
    return {"Authorization": f"Bearer {token}"}
```

**Location:**
- Shared backend fixtures: `tests/conftest.py`.
- Frontend test setup: `web/src/test/setup.ts`.
- Frontend mock API payloads: `web/src/mocks/handlers.ts`.

## Coverage

**Requirements:**
- `pyproject.toml` sets pytest addopts: `-ra -q --cov=app --cov-report=html --cov-report=term`.
- No strict coverage fail-under is configured in the observed `pyproject.toml`.

**View Coverage:**
```bash
. .venv/bin/activate && pytest --cov=app --cov-report=term --cov-report=html
open htmlcov/index.html  # local desktop only, if available
```

## Test Types

**Unit Tests:**
- Auth/session behavior: `tests/unit/test_auth.py`, `tests/unit/test_admin_dashboard_auth.py`, `tests/unit/test_dashboard_auth_alignment.py`.
- ACN invariants: `tests/unit/test_acn_node_heartbeat.py`, `tests/unit/test_acn_task_identity.py`, `tests/unit/test_acn_capabilities.py`, `tests/unit/test_acn_redaction.py`.
- Vector/search internals: `tests/unit/test_embedding_service.py`, `tests/unit/test_vector_search_service.py`, `tests/unit/test_vector_feature_flag.py`.
- Dashboard hooks/components: `web/src/hooks/useWebSocketSync.test.ts`, `web/src/components/common/ResponsiveList.test.tsx`, `web/src/components/kanban/KanbanBoard.test.tsx`.

**Integration Tests:**
- Lifecycle APIs: `tests/integration/test_task_lifecycle.py`, `tests/integration/test_agent_lifecycle.py`, `tests/integration/test_websocket.py`.
- Search/vector APIs: `tests/integration/test_search_api.py`, `tests/integration/test_vector_search.py`, `tests/integration/test_vector_storage.py`.
- Dashboard static paths: `tests/integration/test_dashboard_paths_live.py`.

**E2E Tests:**
- Playwright dashboard smoke in `web/e2e/dashboard.spec.ts`, single Chromium project, base URL `http://localhost:7788`.
- API must already be running before executing Playwright tests.

## Common Patterns

**Async Testing:**
```python
@pytest.mark.asyncio
async def test_async_behavior(...):
    result = await service_method()
    assert result is not None
```

**Error Testing:**
```python
response = test_client.get('/v1/protected', headers={})
assert response.status_code in {401, 403}
assert response.text
```

**Frontend Behavior Testing:**
```typescript
render(<Component />)
expect(await screen.findByText(/expected/i)).toBeInTheDocument()
```

## Verification Guidance

- For backend-only slices, run the smallest targeted pytest first, then a broader relevant suite.
- For dashboard slices, run `npm run typecheck`, targeted Vitest tests, then `npm run build`.
- For Kanban/workflow UX, verify backend transition tests and frontend drag/drop/API-refetch behavior; visual scaffold alone is not complete.
- For public/live claims, verify the built bundle or live route after deploy; do not infer live status from local build alone.

---

*Testing analysis: 2026-05-25*
