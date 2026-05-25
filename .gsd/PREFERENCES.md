# OpenHub GSD Preferences

## Project Context
OpenHub is a multi-agent coordination platform enabling multiple AI agents to work together on the same codebase without conflicts.

## Technology Stack
- Language: Python 3.11+
- Framework: FastAPI 0.104.1 + Uvicorn + WebSockets
- Database: SQLite with WAL mode (optional Turso/libSQL)
- Data Validation: Pydantic v2
- Authentication: JWT + API Keys + Casbin RBAC
- Cache: Redis (optional, graceful degradation)
- Frontend: React + Vite (for Command Center UI)
- Deployment: Docker + pip install support

## Development Tools
- Test Framework: pytest + pytest-asyncio + pytest-cov
- Code Format: black (line-length 88), isort (profile = black)
- Linting: flake8, mypy (strict mode)
- Package Manager: Poetry (dev) / pip (production)

## Code Style
- Naming: snake_case for functions/variables, PascalCase for classes
- Route modules: routes_{noun}.py (e.g., routes_agents.py)
- Service modules: {noun}_service.py (e.g., agent_service.py)
- Repository modules: {noun}.py in database/repositories/
- Model modules: {noun}.py in models/
- Import style: Relative imports using .. from api/, ... from repositories/
- Logging: structlog with structured JSON format
- Error handling: Custom exceptions extending HTTPException, business logic raises ValueError

## Git Workflow
- Branch pattern: feature/{slice-name} per task
- Worktree: Enabled for isolation
- Commit style: Conventional commits with scope
- Merge strategy: Squash merge per milestone

## Verification Commands
- Run tests: pytest
- Type check: mypy app/
- Lint: flake8 app/
- Format check: black --check app/
- Import check: isort --check app/
- Start dev server: uvicorn app.main:app --host 0.0.0.0 --port 7788 --reload
- Docker deployment: docker-compose up --build

## Project Structure
- app/ - Main application (api/, auth/, database/, models/, services/)
- .gsd/ - GSD configuration
- .planning/ - Legacy planning docs
- docs/ - Specifications and plans
- scripts/ - Setup and utility scripts
- tests/ - Test suite
- data/ - Persistent data

## Current Milestone
v1.0 - Production Ready

## Active Phase
Phase 1: Backend Hardening - Fix silent correctness bugs and security holes before any test is written

## Next Phases
- Phase 2: WebSocket + Test Suite
- Phase 3: Vector Database
- Phase 4: Command Center UI
- Phase 5: Release Readiness

## GSD Workflow
- Use /gsd:quick for small fixes, doc updates, ad-hoc tasks
- Use /gsd:debug for investigation and bug fixing
- Use /gsd:execute-phase for planned phase work
- Use /gsd:transition for phase transitions
- Use /gsd:complete-milestone for milestone completion

## Authentication
Use the local Hermes/OpenAI Codex OAuth credential (`hermes auth list openai-codex`) or user-level Codex auth. Never commit credential values.

## Model Routing (Optional)
- Research: GPT 5.5 via OpenAI Codex
- Planning: GPT 5.5 via OpenAI Codex
- Implementation: GPT 5.5 via OpenAI Codex
- Verification: GPT 5.5 via OpenAI Codex
