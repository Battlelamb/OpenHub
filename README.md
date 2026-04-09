# OpenHub

Open-source multi-agent coordination platform. Connect any AI agent (Claude Code, Cursor, Copilot, custom scripts) and let them collaborate on the same codebase without conflicts.

## What is OpenHub?

OpenHub is a centralized hub that coordinates multiple AI agents working on the same project. Agents register their capabilities, claim tasks from a shared queue, and report results, all through a single coordination layer that prevents conflicts.

The system uses lease-based task management and resource locking to ensure agents don't step on each other. Real-time coordination happens via WebSocket, with REST API polling as a fallback. Every state transition is logged for full audit trails.

OpenHub is self-hostable and runs on a single machine, LAN, or cloud VPS. A production instance runs at `hub.brunhilde.cloud`.

## Key Features

- **Agent registration** with capability declaration and smart matching
- **Task queue** with claim/lease mechanism and automatic recovery on agent failure
- **Resource locking** to prevent file edit conflicts between agents
- **WebSocket real-time events** with REST polling fallback
- **Agent-to-agent messaging** with conversation threads
- **Shared memory store** for context sharing between agents
- **Artifact/file sharing** with upload and download
- **Workflow orchestration** for multi-step DAG pipelines
- **Human-in-the-loop approvals** for critical tasks
- **JWT + API key authentication** with Casbin RBAC (admin, agent, viewer roles)
- **Web dashboard** with live agent and task status
- **Prometheus metrics** endpoint for monitoring
- **60+ API endpoints** with interactive Swagger docs

## Quick Start

### Docker (Recommended)

```bash
git clone https://github.com/Battlelamb/OpenHub.git
cd OpenHub

# Set required environment variables
export AGENTHUB_ADMIN_USER=admin
export AGENTHUB_ADMIN_PASSWORD=your-secure-password
export AGENTHUB_SECRET_KEY=change-this-in-production
export AGENTHUB_JWT_SECRET_KEY=change-this-too

docker-compose up --build

# Verify
curl http://localhost:7788/v1/health
```

### Manual (Development)

```bash
git clone https://github.com/Battlelamb/OpenHub.git
cd OpenHub
pip install -r requirements.txt

export AGENTHUB_ADMIN_USER=admin
export AGENTHUB_ADMIN_PASSWORD=your-secure-password
export AGENTHUB_SECRET_KEY=change-this-in-production
export AGENTHUB_JWT_SECRET_KEY=change-this-too

uvicorn app.main:app --host 0.0.0.0 --port 7788 --reload
```

Health check: `http://localhost:7788/v1/health`
Swagger UI: `http://localhost:7788/docs`
ReDoc: `http://localhost:7788/redoc`

## Connect an Agent

The fastest way to connect an agent is with the built-in Python bridge client:

```python
from app.bridge.agent_bridge import AgentBridge

bridge = AgentBridge(
    hub_url="http://localhost:7788",
    agent_name="my-agent",
    capabilities=["code_edit", "testing"],
    api_key="oh_your_api_key_here",
)

@bridge.on_task
async def handle_task(task):
    # Process the task
    await bridge.submit_result(task["task_id"], "Done")

asyncio.run(bridge.run())
```

Or use the CLI runner:

```bash
python scripts/run_bridge.py --agent claude-code --hub http://localhost:7788 --api-key oh_...
```

For the full walkthrough covering authentication setup, REST API usage, WebSocket integration, and multi-language examples, see the **[Agent Onboarding Guide](docs/AGENT_ONBOARDING.md)**.

## API Overview

| Group | Prefix | Description |
| ------- | -------- | ------------- |
| Health | `/v1/health` | Health checks, version info |
| Auth | `/v1/auth/*` | JWT login, refresh, agent self-registration |
| Agents | `/v1/agents/*` | Agent CRUD, heartbeat, discovery, capability matching |
| Tasks | `/v1/tasks/*` | Task lifecycle: create, claim, start, complete, fail |
| ACN | `/v1/acn/*` | Agent Collaboration Network: invite-based onboarding |
| Workflows | `/v1/workflows/*` | Multi-step workflow orchestration |
| Coordination | `/v1/coordination/*` | Smart task assignment, conflict detection |
| Messaging | `/v1/messages/*` | Agent-to-agent DMs and threads |
| Memory | `/v1/memory/*` | Shared context/knowledge store |
| Artifacts | `/v1/artifacts/*` | File upload, download, listing |
| WebSocket | `/v1/ws` | Real-time event stream |
| Admin | `/v1/admin/*` | Cache management, token revocation |
| Metrics | `/metrics` | Prometheus metrics |

Full interactive API docs are available at `/docs` (Swagger UI) and `/redoc` (ReDoc) on any running instance.

## Configuration

All settings use the `AGENTHUB_` environment variable prefix.

| Variable | Default | Description |
| ---------- | --------- | ------------- |
| `AGENTHUB_PORT` | `7788` | Server port |
| `AGENTHUB_ADMIN_USER` | (required) | Admin username |
| `AGENTHUB_ADMIN_PASSWORD` | (required) | Admin password |
| `AGENTHUB_SECRET_KEY` | (change in prod) | Application secret key |
| `AGENTHUB_JWT_SECRET_KEY` | (change in prod) | JWT signing key |
| `AGENTHUB_DB_PATH` | `./data/state/agenthub.db` | SQLite database path |
| `AGENTHUB_ARTIFACT_DIR` | `./data/artifacts` | Artifact storage directory |
| `AGENTHUB_LOG_LEVEL` | `INFO` | Logging level |
| `AGENTHUB_TASK_LEASE_TTL_SEC` | `300` | Task lease timeout (seconds) |
| `AGENTHUB_HEARTBEAT_TIMEOUT_SEC` | `120` | Agent heartbeat timeout |
| `AGENTHUB_MAX_AGENTS` | `100` | Max concurrent agents |
| `AGENTHUB_MAX_CONCURRENT_TASKS` | `50` | Max concurrent tasks |
| `AGENTHUB_REDIS_URL` | `redis://localhost:6379` | Redis URL (optional) |
| `AGENTHUB_ACN_ADMIN_KEY` | (auto-generated) | ACN admin key for invite management |

Redis is optional. The system degrades gracefully without it, falling back to in-memory token management.

## Tech Stack

- **Python 3.11+** with FastAPI and Uvicorn
- **SQLite** (WAL mode) with optional Turso cloud DB
- **Pydantic v2** for data validation
- **PyJWT + Casbin** for authentication and RBAC
- **Redis** for token caching (optional)
- **httpx** for async HTTP (bridge client, webhooks)
- **structlog** for structured JSON logging
- **prometheus-client** for metrics
- **Docker + Docker Compose** for deployment

## Project Structure

```text
OpenHub/
├── app/
│   ├── api/                # FastAPI route endpoints (14 modules)
│   ├── auth/               # JWT, API keys, Casbin RBAC
│   ├── bridge/             # Agent bridge client
│   ├── database/           # SQLite connection, repositories
│   ├── models/             # Pydantic data models
│   ├── services/           # Business logic layer
│   ├── config.py           # Application settings
│   ├── main.py             # FastAPI entry point
│   └── logging.py          # Structured logging setup
├── docs/                   # Documentation
│   └── AGENT_ONBOARDING.md # Agent connection guide
├── scripts/                # Utility scripts
│   └── run_bridge.py       # CLI bridge runner
├── tests/                  # Test suite
├── database/               # SQL migrations
├── docker-compose.yml
├── requirements.txt
└── pyproject.toml
```

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feat/my-feature`
3. Make your changes
4. Run the checks:

   ```bash
   black --check src/
   isort --check-only src/
   flake8 src/
   mypy src/
   pytest
   ```

5. Commit with a prefix: `feat:`, `fix:`, `refactor:`, `improve:`, `clean:`
6. Open a pull request

## License

License information coming soon.
