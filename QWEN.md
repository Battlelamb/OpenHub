# OpenHub - QWEN.md

## Project Overview

**OpenHub** is a multi-agent coordination platform that enables multiple AI agents (Claude Code, Cursor, Copilot, Qwen Code, etc.) to work together on the same codebase without conflicts. It provides a centralized hub for agent registration, task management, workflow orchestration, and real-time coordination.

### Key Features

- **Agent Management**: Registration, heartbeat monitoring, capability matching, and discovery
- **Task Lifecycle**: Create, claim, start, complete, fail, and retry tasks with lease-based assignment
- **Workflow Orchestration**: Hatchet integration for multi-step AI agent pipelines
- **Authentication**: JWT tokens, API keys, and Casbin RBAC (roles: admin, agent, viewer)
- **Real-time Communication**: WebSocket support for live updates
- **Observability**: Prometheus metrics, structured logging with structlog, request tracing
- **Database**: SQLite with WAL mode + Turso (libSQL) cloud sync for remote mode

### Production Status

- **Live Deployment**: https://hub.brunhilde.cloud (Hostinger VPS via Cloudflare tunnel)
- **Port**: 7788
- **Admin Dashboard**: https://hub.brunhilde.cloud/admin
- **API Docs**: https://hub.brunhilde.cloud/docs

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| **Runtime** | Python 3.11+ |
| **Web Framework** | FastAPI 0.104.1 + Uvicorn |
| **Database** | SQLite (WAL) + Turso (libSQL) + Alembic migrations |
| **Cache** | Redis 5.0.1 (optional, graceful degradation) |
| **Validation** | Pydantic v2 + pydantic-settings |
| **Auth** | PyJWT + passlib (bcrypt) + Casbin RBAC |
| **Rate Limiting** | slowapi |
| **Monitoring** | Prometheus client + structlog |
| **Workflow** | Hatchet orchestration |
| **Vector Search** | zvec (local) |
| **Deployment** | Docker + Docker Compose |

---

## Project Structure

```
OpenHub/
├── app/                          # Main application
│   ├── api/                      # FastAPI route endpoints
│   │   ├── routes_agents.py      # Agent management + discovery
│   │   ├── routes_tasks.py       # Task lifecycle management
│   │   ├── routes_workflows.py   # Hatchet workflow orchestration
│   │   ├── routes_auth.py        # JWT authentication
│   │   ├── routes_admin.py       # Administrative functions
│   │   ├── routes_health.py      # Health check endpoints
│   │   ├── routes_metrics.py     # Prometheus metrics
│   │   ├── routes_acn.py         # Agent Collaboration Network
│   │   ├── routes_memory.py      # Shared memory/context store
│   │   ├── routes_artifacts.py   # File/artifact storage
│   │   ├── routes_p1.py          # Locks, tracing, cost tracking
│   │   └── routes_p2.py          # Tools, templates, DLQ
│   ├── auth/                     # Authentication & Security
│   │   ├── jwt_auth.py           # JWT token management
│   │   ├── api_keys.py           # API key system
│   │   ├── api_key_deps.py       # Shared API key dependencies
│   │   └── rbac/                 # Casbin RBAC policies
│   ├── database/                 # Database layer
│   │   ├── connection.py         # SQLite/Turso connection
│   │   ├── migrations.py         # Migration system
│   │   └── repositories/         # Data access layer (repository pattern)
│   ├── models/                   # Pydantic data models
│   │   ├── agents.py             # Agent models
│   │   ├── tasks.py              # Task models
│   │   ├── events.py             # Event models
│   │   └── errors.py             # RFC 7807 error models
│   ├── services/                 # Business logic
│   │   ├── agent_service.py      # Agent registration & management
│   │   ├── heartbeat_service.py  # Agent heartbeat monitoring
│   │   ├── task_service.py       # Task lifecycle management
│   │   ├── hatchet_service.py    # Hatchet workflow integration
│   │   └── capability_matcher.py # Agent-task capability matching
│   ├── static/                   # Static files (admin dashboard)
│   ├── config.py                 # Application settings
│   ├── main.py                   # FastAPI app entry point
│   ├── middleware.py             # Error handling, timing, security
│   └── logging.py                # Structured logging setup
├── alembic/                      # Database migrations
├── tests/                        # Test suite
│   ├── unit/                     # Unit tests
│   ├── integration/              # Integration tests
│   └── conftest.py               # Shared fixtures
├── docs/                         # Documentation
│   ├── CLAUDE.md                 # Project documentation
│   ├── PROJECT_ROADMAP.md        # Development roadmap
│   └── DEVELOPMENT_RULES.md      # Development guidelines
├── .planning/                    # GSD planning artifacts
├── .gsd/                         # GSD-2 configuration
├── data/                         # Persistent data (gitignored)
│   ├── state/                    # SQLite database
│   ├── artifacts/                # File storage
│   └── zvec/                     # Vector database
├── scripts/                      # Utility scripts
├── docker-compose.yml            # Docker orchestration
├── Dockerfile                    # Container build
├── pyproject.toml                # Poetry configuration
├── requirements.txt              # Pip requirements
└── .gsdrc.toml                   # GSD-2 project config
```

---

## Building and Running

### Local Development

```bash
# Clone and enter directory
git clone https://github.com/Battlelamb/OpenHub.git
cd OpenHub

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Set environment variables (or copy .env.example to .env)
export AGENTHUB_ADMIN_USER=admin
export AGENTHUB_ADMIN_PASSWORD=your-secure-password
export AGENTHUB_SECRET_KEY=your-secret-key-here
export AGENTHUB_JWT_SECRET_KEY=your-jwt-secret-key

# Run development server with hot reload
uvicorn app.main:app --host 0.0.0.0 --port 7788 --reload

# Test health endpoint
curl http://localhost:7788/v1/health/simple
```

### Docker Deployment

```bash
# Build and start all services
docker-compose up --build

# Or run in background
docker-compose up -d

# Check logs
docker-compose logs -f agenthub

# Stop all services
docker-compose down
```

### Production (VPS)

```bash
# SSH to VPS
ssh brunhilde@hub.brunhilde.cloud  # or via IPv4: ssh brunhilde@76.13.135.40 -p 443

# Navigate to project
cd ~/OpenHub

# Pull latest changes
git pull origin gsd/phase-01-backend-hardening

# Restart server (screen session)
screen -r openhub  # Attach to running session
# Ctrl+C to stop, then restart:
.venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 7788
# Detach: Ctrl+A, D
```

---

## Testing

```bash
# Run all tests with coverage
pytest

# Run specific test file
pytest tests/unit/test_auth_stub.py -v

# Run with coverage report
pytest --cov=app --cov-report=html --cov-report=term

# View coverage report
open htmlcov/index.html  # Mac/Linux
# or open htmlcov/index.html in browser
```

### Test Structure

- **Unit Tests** (`tests/unit/`): Isolated component tests
- **Integration Tests** (`tests/integration/`): End-to-end API tests
- **Fixtures** (`conftest.py`): Shared test fixtures (TestClient, admin_headers, agent_api_key)

---

## Linting and Type Checking

```bash
# Format code
black app/ tests/
isort app/ tests/

# Check formatting
black --check app/
isort --check app/

# Lint
flake8 app/

# Type check
mypy app/
```

---

## API Endpoints

### Health & Monitoring

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/v1/health` | Full health check with system info |
| `GET` | `/v1/health/simple` | Simple health check |
| `GET` | `/metrics` | Prometheus metrics endpoint |
| `GET` | `/docs` | Swagger UI (OpenAPI docs) |
| `GET` | `/redoc` | ReDoc documentation |

### Authentication

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/v1/auth/agent/register` | Register new agent |
| `POST` | `/v1/auth/agent/login` | Agent login |
| `POST` | `/v1/auth/admin/login` | Admin login |
| `POST` | `/v1/auth/refresh` | Refresh access token |
| `POST` | `/v1/auth/logout` | Logout current session |

### Agents

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/v1/agents/register` | Register agent |
| `POST` | `/v1/agents/heartbeat` | Send heartbeat |
| `GET` | `/v1/agents` | List all agents |
| `GET` | `/v1/agents/{id}` | Get agent details |
| `DELETE` | `/v1/agents/{id}` | Deregister agent |

### Tasks

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/v1/tasks` | Create new task |
| `POST` | `/v1/tasks/claim` | Claim available task |
| `POST` | `/v1/tasks/{id}/start` | Start task execution |
| `POST` | `/v1/tasks/{id}/complete` | Mark task complete |
| `POST` | `/v1/tasks/{id}/fail` | Mark task failed |
| `GET` | `/v1/tasks` | List tasks |
| `GET` | `/v1/tasks/{id}` | Get task details |

### Workflows

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/v1/workflows` | Create workflow |
| `GET` | `/v1/workflows` | List workflows |
| `GET` | `/v1/workflows/{id}` | Get workflow status |
| `POST` | `/v1/workflows/{id}/cancel` | Cancel workflow |

---

## Configuration

### Environment Variables

All configuration uses `AGENTHUB_` prefix via pydantic-settings.

| Variable | Default | Description |
|----------|---------|-------------|
| `AGENTHUB_HOST` | `0.0.0.0` | Server host |
| `AGENTHUB_PORT` | `7788` | Server port |
| `AGENTHUB_DB_PATH` | `./data/state/agenthub.db` | SQLite database path |
| `AGENTHUB_TURSO_DATABASE_URL` | `None` | Turso libSQL URL (optional) |
| `AGENTHUB_TURSO_AUTH_TOKEN` | `None` | Turso auth token |
| `AGENTHUB_ADMIN_USER` | *(required)* | Admin username |
| `AGENTHUB_ADMIN_PASSWORD` | *(required)* | Admin password |
| `AGENTHUB_SECRET_KEY` | *(change in prod)* | Secret key for tokens |
| `AGENTHUB_JWT_SECRET_KEY` | *(change in prod)* | JWT signing key |
| `AGENTHUB_REDIS_URL` | `redis://localhost:6379` | Redis connection URL |
| `AGENTHUB_LOG_LEVEL` | `INFO` | Logging level |
| `AGENTHUB_CORS_ORIGINS` | `["http://localhost:3000", "http://localhost:7788"]` | CORS allowed origins |

### Config File

See `app/config.py` for full Settings class with all configuration options.

---

## Development Conventions

### Code Style

- **Formatting**: Black (line-length 88), isort (profile = black)
- **Type Hints**: Required for all functions (mypy strict mode)
- **Naming**: 
  - `snake_case` for functions/variables
  - `PascalCase` for classes
  - `routes_{noun}.py` for route modules
  - `{noun}_service.py` for service modules

### Architecture Patterns

- **Repository Pattern**: Database access via repositories (`app/database/repositories/`)
- **Service Layer**: Business logic in services (`app/services/`)
- **Dependency Injection**: FastAPI `Depends()` for service injection
- **Structured Logging**: structlog with JSON output in production
- **Error Handling**: RFC 7807 Problem Details format (`app/models/errors.py`)

### Git Workflow

- **Branch Pattern**: `feature/{slice-name}` per task
- **Commits**: Conventional commits with scope
- **Merge Strategy**: Squash merge per milestone

---

## Key Design Decisions

### Database

- **SQLite with WAL mode** for local development
- **Turso (libSQL)** for cloud sync with embedded replicas
- **Alembic migrations** for schema versioning
- **Repository pattern** for data access abstraction

### Authentication

- **JWT tokens** for interactive sessions (access + refresh)
- **API keys** for service-to-service communication
- **Casbin RBAC** for fine-grained authorization
- **Redis caching** for token blacklisting (optional)

### Task Assignment

- **Lease-based claiming**: Tasks have TTL, auto-release if not completed
- **Capability matching**: Agents matched to tasks by capabilities
- **Retry logic**: Failed tasks can retry up to `max_retries` times
- **Dead Letter Queue**: Tasks that exhaust retries go to DLQ

---

## Troubleshooting

### Server Won't Start

```bash
# Check if port 7788 is in use
lsof -i :7788

# Kill existing process
kill -9 <PID>

# Check .env file exists and has required vars
cat .env | grep AGENTHUB_ADMIN
```

### Database Issues

```bash
# Reset database (development only!)
rm data/state/agenthub.db

# Run migrations manually
alembic upgrade head
```

### Test Failures

```bash
# Clean pytest cache
rm -rf .pytest_cache __pycache__

# Run tests with verbose output
pytest -v -s
```

---

## Live Deployment Info

### VPS Details

- **Provider**: Hostinger
- **Hostname**: srv1315198.hstgr.cloud
- **IPv4**: 76.13.135.40
- **SSH**: `ssh brunhilde@76.13.135.40 -p 443`
- **Cloudflare Tunnel**: Active (hub.brunhilde.cloud)

### Current Status

```bash
# SSH to VPS and check
ssh brunhilde "ps aux | grep uvicorn && curl -s http://localhost:7788/v1/health"
```

### Screen Sessions

```bash
# List screen sessions
screen -ls

# Attach to OpenHub session
screen -r openhub

# Detach: Ctrl+A, D
```

---

## Resources

- **GitHub**: https://github.com/Battlelamb/OpenHub
- **Live API**: https://hub.brunhilde.cloud
- **Swagger UI**: https://hub.brunhilde.cloud/docs
- **Admin Dashboard**: https://hub.brunhilde.cloud/admin
