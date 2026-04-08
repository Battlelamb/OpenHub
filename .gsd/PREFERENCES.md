# OpenHub GSD Preferences

## Project Context
OpenHub is a multi-agent coordination platform enabling multiple AI agents (Claude Code, Cursor, Copilot, etc.) to work together on the same codebase without conflicts.

## Technology Stack
- **Language**: Python 3.11+
- **Framework**: FastAPI 0.104.1 + Uvicorn + WebSockets
- **Database**: SQLite with WAL mode (optional Turso/libSQL)
- **Data Validation**: Pydantic v2
- **Authentication**: JWT + API Keys + Casbin RBAC
- **Cache**: Redis (optional, graceful degradation)
- **Frontend**: React + Vite (for Command Center UI)
- **Deployment**: Docker + pip install support

## Development Tools
- **Test Framework**: pytest + pytest-asyncio + pytest-cov
- **Code Format**: black (line-length 88), isort (profile = "black")
- **Linting**: flake8, mypy (strict mode)
- **Package Manager**: Poetry (dev) / pip (production)

## Code Style
- **Naming**: `snake_case` for functions/variables, `PascalCase` for classes
- **Route modules**: `routes_{noun}.py` (e.g., `routes_agents.py`)
- **Service modules**: `{noun}_service.py` (e.g., `agent_service.py`)
- **Repository modules**: `{noun}.py` in `database/repositories/`
- **Model modules**: `{noun}.py` in `models/`
- **Import style**: Relative imports using `..` from api/, `...` from repositories/
- **Logging**: structlog with structured JSON format
- **Error handling**: Custom exceptions extending `HTTPException`, business logic raises `ValueError`

## Git Workflow
- **Branch pattern**: `feature/{slice-name}` per task
- **Worktree**: Enabled for isolation
- **Commit style**: Conventional commits with scope
- **Merge strategy**: Squash merge per milestone

## Verification Commands
```bash
# Run tests
pytest

# Type check
mypy app/

# Lint
flake8 app/
black --check app/
isort --check app/

# Start dev server
uvicorn app.main:app --host 0.0.0.0 --port 7788 --reload

# Docker deployment
docker-compose up --build
```

## Project Structure
```
OpenHub/
├── app/                    # Main application
│   ├── api/               # FastAPI routes
│   ├── auth/              # Authentication & Security
│   ├── database/          # Database layer
│   ├── models/            # Pydantic data models
│   ├── services/          # Business logic
│   └── bridge/            # Remote agent bridge
├── .gsd/                  # GSD configuration (you are here)
├── .planning/             # Legacy planning docs
├── docs/                  # Specifications & plans
├── scripts/               # Setup & utility scripts
├── tests/                 # Test suite
└── data/                  # Persistent data
```

## Current Milestone
**v1.0 - Production Ready**

### Active Phase
**Phase 1: Backend Hardening** - Fix silent correctness bugs and security holes before any test is written

### Next Phases
- Phase 2: WebSocket + Test Suite
- Phase 3: Vector Database
- Phase 4: Command Center UI
- Phase 5: Release Readiness

## GSD Workflow
- Use `/gsd:quick` for small fixes, doc updates, ad-hoc tasks
- Use `/gsd:debug` for investigation and bug fixing
- Use `/gsd:execute-phase` for planned phase work
- Use `/gsd:transition` for phase transitions
- Use `/gsd:complete-milestone` for milestone completion

## Authentication
Run `gsd auth login` to authenticate with GSD-2 CLI (uses same login as claude.ai)

## Model Routing (Optional)
- **Research**: Cheaper models for code search, documentation
- **Planning**: Premium models for architecture decisions
- **Implementation**: Premium models for code generation
- **Verification**: Any model for test execution, lint checks
