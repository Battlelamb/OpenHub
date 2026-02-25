# CLAUDE.md - OpenHub

This file provides guidance to Claude Code when working with the OpenHub project.

## Project Overview

**OpenHub** is a multi-agent coordination platform that enables multiple AI agents (Claude Code, Cursor, Copilot, etc.) to work together on the same codebase without conflicts.

**GitHub**: https://github.com/Battlelamb/OpenHub.git
**Location**: `D:\OneDrive\OLD\Documents\OpenHub`

## Repository Structure

```
OpenHub/
├── app/                          # Main application
│   ├── api/                      # FastAPI route endpoints
│   │   ├── routes_agents.py      # Agent management + discovery + monitoring
│   │   ├── routes_tasks.py       # Task lifecycle management
│   │   ├── routes_workflows.py   # Hatchet workflow orchestration
│   │   ├── routes_coordination.py # Smart agent-workflow coordination
│   │   ├── routes_auth.py        # JWT authentication endpoints
│   │   ├── routes_admin.py       # Administrative functions
│   │   └── routes_health.py      # Health check
│   ├── auth/                     # Authentication & Security
│   │   ├── jwt_auth.py           # JWT token management
│   │   ├── api_keys.py           # API key system
│   │   ├── dependencies.py       # FastAPI auth dependencies
│   │   ├── redis_cache.py        # Redis token caching
│   │   └── rbac/                 # Casbin role-based access control
│   ├── database/                 # Database layer
│   │   ├── connection.py         # SQLite connection management
│   │   ├── migrations.py         # Migration system
│   │   └── repositories/         # Data access layer
│   ├── models/                   # Pydantic data models
│   │   ├── agents.py             # Agent models
│   │   ├── tasks.py              # Task models
│   │   └── events.py             # Event models
│   ├── services/                 # Business logic
│   │   ├── agent_service.py      # Agent registration & management
│   │   ├── heartbeat_service.py  # Agent health monitoring
│   │   ├── capability_matcher.py # Smart agent-capability matching
│   │   ├── discovery_service.py  # Agent discovery & monitoring
│   │   ├── task_service.py       # Task lifecycle management
│   │   ├── hatchet_service.py    # Hatchet workflow integration
│   │   └── workflow_coordinator.py # Agent-workflow coordination
│   ├── config.py                 # Application settings
│   ├── main.py                   # FastAPI app entry point
│   └── logging.py                # Structured logging
├── docs/                         # Specifications & plans
│   ├── CODEX_PLAN.md
│   ├── MULTI_AGENT_HUB_SPEC.md
│   ├── PROJECT_ROADMAP.md
│   ├── ARCHITECTURE_EVALUATION.md
│   └── DEVELOPMENT_RULES.md
├── database/                     # SQL migrations
├── scripts/                      # Setup & utility scripts
├── tests/                        # Test suite
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── pyproject.toml
```

## Technical Stack

- **Python 3.11+** with FastAPI + Uvicorn + WebSockets
- **SQLite** with WAL mode and migration system
- **Pydantic v2** for data validation
- **Hatchet** for workflow orchestration (AI agent pipelines)
- **JWT + API Keys + Casbin RBAC** for authentication
- **Redis** for token caching (optional, graceful degradation)
- **Docker** for deployment

## Development Commands

```bash
# Run development server
uvicorn app.main:app --host 0.0.0.0 --port 7788 --reload

# Docker deployment
docker-compose up --build

# Health check
curl http://localhost:7788/v1/health
```

## API Architecture

### Authentication
- **JWT tokens**: Interactive sessions (login/refresh)
- **API Keys**: Service-to-service communication (permanent)
- **RBAC**: Casbin policy-based role authorization
- Roles: `admin`, `agent`, `viewer`

### Core Endpoints
- **Health**: `GET /v1/health`
- **Agents**: `/v1/agents/*` (register, heartbeat, discover, monitor)
- **Tasks**: `/v1/tasks/*` (create, claim, start, complete, fail, search)
- **Workflows**: `/v1/workflows/*` (create, templates, status, cancel)
- **Coordination**: `/v1/coordination/*` (plan, execute, status)
- **Auth**: `/v1/auth/*` (login, refresh, API keys)
- **Admin**: `/v1/admin/*` (stats, cleanup)

### Task State Flow
```
QUEUED → CLAIMED → RUNNING → COMPLETED/FAILED
          ↓                      ↓
     (lease expires)        (retry if retryable)
          ↓                      ↓
        QUEUED ←─────────────── QUEUED
```

## Implementation Progress

### Completed Phases:
- ✅ **Phase 1**: Foundation & Security (FastAPI, database, JWT, API keys, RBAC, Redis)
- ✅ **Phase 2.1**: Agent Management (registration, heartbeat, capability matching, discovery)
- ✅ **Phase 2.2.1**: Basic Task Management (CRUD, assignment, tracking, search)
- ✅ **Phase 2.2.2**: Hatchet Integration (workflow orchestration, templates)
- ✅ **Phase 2.2.3**: Agent-Workflow Coordination (smart assignment, planning, monitoring)

### Next Phases:
- 🔄 **Phase 2.3**: Real-time Communication (WebSocket)
- 🔄 **Phase 2.4**: Vector Database Integration

## Configuration

Environment variables (prefix: `AGENTHUB_`):
- `AGENTHUB_HOST=0.0.0.0`
- `AGENTHUB_PORT=7788`
- `AGENTHUB_DB_PATH=./data/state/agenthub.db`
- `AGENTHUB_ARTIFACT_DIR=./data/artifacts`
- `AGENTHUB_TASK_LEASE_TTL_SEC=60`
- `AGENTHUB_LOG_LEVEL=INFO`
- `AGENTHUB_HATCHET_SERVER_URL=http://localhost:8080`

## Development Style

- **Slow, clean, and small steps** (yavaş, temiz ve küçük adımlar)
- Production-grade code quality with fine detail
- Structured logging throughout
- Repository pattern with service layer architecture
- Clean separation of concerns