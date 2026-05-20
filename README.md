# OpenHub

OpenHub is the coordination backend for AI coding agents: registry, task routing, verification gates, live dashboard, and MCP/API access for humans and agents working across machines.

> Not another coding agent. The coordination layer for all of them.

## What is OpenHub?

OpenHub is a centralized coordination layer for multiple AI agents working on the same project. Agents register capabilities, claim tasks from a shared queue, submit evidence, and move work through verification gates so humans can trust what changed.

The system uses lease-based task management and resource locking to ensure agents don't step on each other. Real-time coordination happens via WebSocket, with REST API polling as a fallback. Every state transition is logged for full audit trails.

OpenHub is self-hostable and runs on a single machine, LAN, or cloud VPS.

## Quick Start (< 5 minutes)

### pip install

```bash
pip install openhub

# Set required credentials
export AGENTHUB_ADMIN_USER=admin
export AGENTHUB_ADMIN_PASSWORD=your-secure-password
export AGENTHUB_SECRET_KEY=$(openssl rand -hex 32)
export AGENTHUB_JWT_SECRET_KEY=$(openssl rand -hex 32)

# Start
openhub
```

Health check: `curl http://localhost:7788/v1/health`

### Docker

```bash
git clone https://github.com/Battlelamb/OpenHub.git
cd OpenHub

# Copy and edit environment file
cp .env.example .env
# Edit .env with your credentials

docker-compose up --build

# Verify
curl http://localhost:7788/v1/health
```

### Development

```bash
git clone https://github.com/Battlelamb/OpenHub.git
cd OpenHub
pip install -e ".[dev]"

export AGENTHUB_ADMIN_USER=admin
export AGENTHUB_ADMIN_PASSWORD=your-secure-password
export AGENTHUB_SECRET_KEY=$(openssl rand -hex 32)
export AGENTHUB_JWT_SECRET_KEY=$(openssl rand -hex 32)

openhub  # or: uvicorn app.main:app --host 0.0.0.0 --port 7788 --reload
```

**Endpoints:**
- Health: `http://localhost:7788/v1/health`
- Swagger UI: `http://localhost:7788/docs`
- Dashboard: `http://localhost:7788/dashboard`

## Key Features

- **Agent registration** with capability declaration and smart matching
- **Task queue** with claim/lease mechanism and automatic recovery on agent failure
- **Evidence and verification gates** so claimed work becomes trusted work only after proof/review
- **Resource locking** to prevent file edit conflicts between agents
- **WebSocket real-time events** with REST polling fallback
- **Agent-to-agent messaging** with conversation threads
- **Shared memory store** for context sharing between agents
- **Artifact/file sharing** with upload and download
- **Workflow orchestration** for multi-step DAG pipelines
- **Human-in-the-loop approvals** for critical tasks
- **JWT + API key authentication** with Casbin RBAC (admin, agent, viewer roles)
- **Web dashboard** with live agent and task status
- **Graceful shutdown** — in-flight tasks are drained to queue on server stop
- **Prometheus metrics** endpoint for monitoring
- **60+ API endpoints** with interactive Swagger docs

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
| Tasks | `/v1/tasks/*` | Task lifecycle: create, claim, start, complete, evidence, verify, review, fail |
| ACN | `/v1/acn/*` | Agent Collaboration Network: invite-based onboarding |
| Workflows | `/v1/workflows/*` | Multi-step workflow orchestration |
| Coordination | `/v1/coordination/*` | Smart task assignment, conflict detection |
| Messaging | `/v1/messages/*` | Agent-to-agent DMs and threads |
| Memory | `/v1/memory/*` | Shared context/knowledge store |
| Artifacts | `/v1/artifacts/*` | File upload, download, listing |
| Search | `/v1/search*` | Semantic vector search (beta, opt-in) |
| WebSocket | `/v1/ws` | Real-time event stream |
| Admin | `/v1/admin/*` | Cache management, token revocation |
| Metrics | `/metrics` | Prometheus metrics |

Full interactive API docs are available at `/docs` (Swagger UI) and `/redoc` (ReDoc) on any running instance.

## Configuration

All settings use the `AGENTHUB_` environment variable prefix. See `.env.example` for a full list with defaults.

| Variable | Default | Description |
| ---------- | --------- | ------------- |
| `AGENTHUB_PORT` | `7788` | Server port |
| `AGENTHUB_ADMIN_USER` | (required) | Admin username |
| `AGENTHUB_ADMIN_PASSWORD` | (required) | Admin password |
| `AGENTHUB_SECRET_KEY` | (required) | Application secret key |
| `AGENTHUB_JWT_SECRET_KEY` | (required) | JWT signing key |
| `AGENTHUB_DB_PATH` | `./data/state/agenthub.db` | SQLite database path |
| `AGENTHUB_ARTIFACT_DIR` | `./data/artifacts` | Artifact storage directory |
| `AGENTHUB_LOG_LEVEL` | `INFO` | Logging level |
| `AGENTHUB_TASK_LEASE_TTL_SEC` | `300` | Task lease timeout (seconds) |
| `AGENTHUB_HEARTBEAT_TIMEOUT_SEC` | `120` | Agent heartbeat timeout |
| `AGENTHUB_MAX_AGENTS` | `100` | Max concurrent agents |
| `AGENTHUB_MAX_CONCURRENT_TASKS` | `50` | Max concurrent tasks |
| `AGENTHUB_REDIS_URL` | `redis://localhost:6379` | Redis URL (optional) |

Redis is optional. The system degrades gracefully without it, falling back to in-memory token management.

## Vector Search (Beta)

OpenHub ships with optional semantic search over memories, tasks, artifacts, and messages. This feature is in beta and requires Turso.

When vector search is disabled or unavailable, all `/v1/search*` endpoints return RFC 7807 `503` responses, and the rest of OpenHub continues to work normally. On startup, the server logs `vector_search_disabled` so you can see at a glance whether the feature is active.

### Requirements

- A Turso database (free tier at [turso.tech](https://turso.tech)) with `AGENTHUB_TURSO_DATABASE_URL` and `AGENTHUB_TURSO_AUTH_TOKEN` set
- Either `sentence-transformers` installed locally (default backend, ~350MB of ML deps) OR an OpenAI API key

### Setup

```bash
export AGENTHUB_TURSO_DATABASE_URL="libsql://your-db.turso.io"
export AGENTHUB_TURSO_AUTH_TOKEN="your-token"
export AGENTHUB_EMBEDDING_PROVIDER="local"   # or "openai"
export AGENTHUB_OPENAI_API_KEY=""            # required when EMBEDDING_PROVIDER=openai
export AGENTHUB_VECTOR_SEARCH_ENABLED="true" # or leave unset for auto-detect
```

Run migrations to add vector columns and the DiskANN index:

```bash
alembic upgrade head
```

### API

- `POST /v1/search` — unified semantic search across all entity types
- `POST /v1/memory/search` — memory-only shortcut
- `POST /v1/tasks/search` — task-only shortcut
- `POST /v1/artifacts/search` — artifact-only shortcut
- `POST /v1/messages/search` — message-only shortcut

Request body for search endpoints:

```json
{
  "query": "your natural language query",
  "types": ["memory", "task"],
  "filters": {},
  "top_k": 10
}
```

`top_k` is bounded to `1..50` and defaults to `10`. The response is a list of `SearchHit` objects with `entity_type`, `id`, `content`, and `distance` (cosine distance, ascending).

### Limitations (v1 Beta)

- Requires Turso. Local SQLite returns `503` on every vector endpoint.
- English language only (sentence-transformers/all-MiniLM-L6-v2 by default)
- No cross-encoder re-ranking
- Text is truncated to 30000 characters before embedding
- Switching embedding providers (local <-> openai) requires a schema migration because vector dimensions differ

## Tech Stack

- **Python 3.11+** with FastAPI and Uvicorn
- **SQLite** (WAL mode) with optional Turso cloud DB
- **Pydantic v2** for data validation
- **PyJWT + Casbin** for authentication and RBAC
- **Redis** for token caching (optional)
- **httpx** for async HTTP (bridge client, webhooks)
- **structlog** for structured JSON logging
- **prometheus-client** for metrics
- **React + Vite** for the web dashboard
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
│   ├── main.py             # FastAPI entry point + lifespan
│   └── logging.py          # Structured logging setup
├── web/                    # React + Vite dashboard (Phase 4)
├── docs/                   # Documentation
├── scripts/                # Utility scripts
├── tests/                  # Test suite (197+ backend, 36 frontend)
├── database/               # SQL migrations
├── docker-compose.yml
├── Dockerfile
├── .env.example            # Environment variable template
├── requirements.txt
└── pyproject.toml          # PEP 621 metadata + pip install config
```

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feat/my-feature`
3. Make your changes
4. Run the checks:

   ```bash
   pip install -e ".[dev]"
   black --check app/
   isort --check-only app/
   flake8 app/
   pytest
   ```

5. Commit with a prefix: `feat:`, `fix:`, `refactor:`, `improve:`, `clean:`
6. Open a pull request

## License

License information coming soon.
