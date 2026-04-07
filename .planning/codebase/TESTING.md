# Testing Patterns

**Analysis Date:** 2026-04-07

## Current State

**There are no test files in this codebase.** The `tests/` directory referenced in `pyproject.toml` does not exist. All testing infrastructure is declared but unused.

## Test Framework (Declared, Not Yet Used)

**Runner:**
- `pytest` 7.4.3
- Config in `pyproject.toml`: `[tool.pytest.ini_options]`
- `testpaths = ["tests"]` - directory does not currently exist

**Async support:**
- `pytest-asyncio` 0.21.1
- `asyncio_mode = "auto"` configured - all async test functions run automatically without `@pytest.mark.asyncio`

**Coverage:**
- `pytest-cov` 4.1.0
- Default addopts: `--cov=app --cov-report=html --cov-report=term`
- No minimum coverage threshold enforced

**Assertion Library:**
- Standard `pytest` assertions (no separate library)

**Run Commands (when tests exist):**
```bash
# Run all tests (from project root)
pytest

# Run with verbose output
pytest -v

# Run specific file
pytest tests/unit/test_agents.py -v --tb=short

# Run specific test by name
pytest -k "test_register_agent" -v

# Coverage report
pytest --cov=app --cov-report=html
```

## Recommended Test Structure

Based on `pyproject.toml` `testpaths = ["tests"]` and the project's layered architecture, tests should be organized as:

```
tests/
├── conftest.py              # Shared fixtures (DB, app client, auth)
├── unit/
│   ├── test_agent_service.py
│   ├── test_task_service.py
│   ├── test_capability_matcher.py
│   ├── test_heartbeat_service.py
│   └── test_models.py
├── integration/
│   ├── test_routes_agents.py
│   ├── test_routes_tasks.py
│   ├── test_routes_auth.py
│   └── test_routes_p1.py
└── e2e/
    └── test_multi_agent_workflow.py
```

## What Needs to Be Tested

### High Priority (Core Business Logic)

**`app/services/agent_service.py`:**
- `register_agent` - duplicate name rejection, valid registration, ID generation
- `get_agents_by_capability` - capability filtering, empty results
- `update_heartbeat` - success/failure paths

**`app/services/task_service.py`:**
- `create_task` - auto-assignment attempt, DB persistence, state transitions
- Task state machine: QUEUED -> CLAIMED -> RUNNING -> COMPLETED/FAILED

**`app/database/repositories/base.py`:**
- `create`, `get_by_id`, `update`, `delete` - standard CRUD operations
- `find_by`, `find_one_by` - filter correctness
- `bulk_create` - count returned, all rows inserted

**`app/models/agents.py` + `app/models/tasks.py`:**
- `AgentCreate.validate_agent_name` - rejects special chars, accepts valid chars
- `AgentCreate.validate_capabilities` - rejects empty names, invalid chars
- `TaskCreate` field constraints - min/max lengths, enum values

### Medium Priority (Routes / Integration)

**Route integration tests** use FastAPI's `TestClient` (via `httpx`):
```python
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
```

Key routes to cover:
- `POST /v1/agents/register` - 200 success, 409 duplicate
- `POST /v1/tasks/` - 200 creation, 500 error path
- `POST /v1/auth/login` - 200 token return, 401 bad credentials
- `GET /v1/health` - 200 with status fields

### Lower Priority

**`app/services/capability_matcher.py`** - scoring algorithm correctness

**`app/middleware.py`** - error envelope format, status code mapping

## Recommended conftest.py Pattern

```python
# tests/conftest.py
import pytest
import tempfile
import os
from fastapi.testclient import TestClient
from app.main import app
from app.database.connection import Database, get_database


@pytest.fixture
def test_db():
    """In-memory SQLite database for tests"""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    
    db = Database(db_path)
    # Run DDL from app/main.py lifespan startup here
    yield db
    
    db.close()
    os.unlink(db_path)


@pytest.fixture
def test_client(test_db):
    """FastAPI test client with overridden database"""
    app.dependency_overrides[get_database] = lambda: test_db
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


@pytest.fixture
def agent_api_key(test_db):
    """Create a test API key with agent role"""
    from app.auth.api_keys import APIKeyManager
    mgr = APIKeyManager(test_db)
    result = mgr.create_api_key(name="test-agent", key_type="agent", scopes=["*"])
    return result["key_value"]
```

## Recommended Unit Test Pattern

```python
# tests/unit/test_agent_service.py
import pytest
from unittest.mock import MagicMock, patch
from app.services.agent_service import AgentService
from app.models.agents import AgentCreate


@pytest.fixture
def mock_db():
    return MagicMock()


@pytest.fixture
def agent_service(mock_db):
    return AgentService(mock_db)


def test_register_agent_success(agent_service):
    agent_data = AgentCreate(
        agent_name="test-agent",
        capabilities=["code_edit"],
        description="A test agent"
    )
    agent = agent_service.register_agent(agent_data)
    
    assert agent.agent_name == "test-agent"
    assert "code_edit" in agent.capabilities
    assert agent.id is not None


def test_register_agent_duplicate_raises(agent_service):
    # Arrange - pre-populate repo to return existing agent
    agent_service.agent_repo.find_by_name = MagicMock(return_value=MagicMock())
    
    agent_data = AgentCreate(
        agent_name="existing-agent",
        capabilities=["code_edit"]
    )
    
    with pytest.raises(ValueError, match="already exists"):
        agent_service.register_agent(agent_data)
```

## Recommended Integration Test Pattern

```python
# tests/integration/test_routes_agents.py
import pytest
from fastapi.testclient import TestClient


def test_register_agent(test_client, agent_api_key):
    response = test_client.post(
        "/v1/agents/register",
        json={
            "agent_name": "test-agent-001",
            "capabilities": ["code_edit", "testing"],
            "description": "Test agent"
        },
        headers={"X-API-Key": agent_api_key}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["agent_name"] == "test-agent-001"
    assert "id" in data


def test_register_agent_duplicate(test_client, agent_api_key):
    payload = {
        "agent_name": "duplicate-agent",
        "capabilities": ["code_edit"]
    }
    test_client.post("/v1/agents/register", json=payload, headers={"X-API-Key": agent_api_key})
    
    response = test_client.post(
        "/v1/agents/register",
        json=payload,
        headers={"X-API-Key": agent_api_key}
    )
    
    assert response.status_code == 409
    assert response.json()["error_code"] == "CONFLICT"
```

## Mocking

**Framework:** `unittest.mock` (standard library) + `pytest` fixtures

**What to mock:**
- `AgentRepository`, `TaskRepository` in unit tests of services
- `get_database()` dependency in integration tests via `app.dependency_overrides`
- External services (Redis, Hatchet) using `unittest.mock.patch`

**What NOT to mock:**
- Pydantic model validation (test it directly)
- `BaseRepository` logic in repository unit tests (use real in-memory SQLite)
- Error handler behavior (test via TestClient, not mocked)

**Dependency override pattern (FastAPI):**
```python
app.dependency_overrides[get_database] = lambda: test_db
# After test:
app.dependency_overrides.clear()
```

## Async Testing

Since `asyncio_mode = "auto"` is set in `pyproject.toml`, async test functions run without decoration:
```python
async def test_heartbeat_monitoring():
    # No @pytest.mark.asyncio needed
    service = HeartbeatService(mock_db)
    await service.start_monitoring()
    await service.stop_monitoring()
```

## Model Validation Testing

Pydantic models with validators should be tested directly:
```python
def test_agent_name_rejects_special_chars():
    with pytest.raises(ValidationError):
        AgentCreate(agent_name="bad name!", capabilities=["code_edit"])


def test_capability_name_rejects_spaces():
    with pytest.raises(ValidationError):
        AgentCreate(agent_name="valid-agent", capabilities=["bad cap"])
```

## Coverage

**Requirements:** None enforced (no `--cov-fail-under` set)

**Report output:**
- HTML: `htmlcov/` directory (gitignored)
- Terminal: inline after test run

**Priority areas for first coverage pass:**
1. `app/models/` - Pydantic validators (pure Python, easy to test)
2. `app/services/agent_service.py` - core registration logic
3. `app/services/task_service.py` - state machine transitions
4. `app/database/repositories/base.py` - generic CRUD methods
5. `app/middleware.py` - error handler envelope format

## Test Types

**Unit Tests:**
- Scope: single class or function, all dependencies mocked
- Location: `tests/unit/`
- Speed: fast, no I/O

**Integration Tests:**
- Scope: full HTTP request through FastAPI to real SQLite (in-memory or temp file)
- Location: `tests/integration/`
- Speed: medium, real DB operations

**E2E Tests:**
- Scope: multi-agent workflow scenarios against running server
- Not yet planned/implemented
- Would use `httpx.AsyncClient` against `uvicorn` test server

---

*Testing analysis: 2026-04-07*
