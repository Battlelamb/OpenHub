# Technology Stack

**Analysis Date:** 2026-04-07

## Languages

**Primary:**
- Python 3.11+ - All application code (runtime is 3.12.3 in local WSL env)

## Runtime

**Environment:**
- CPython 3.12.3 (local WSL2), pinned to ^3.11 in `pyproject.toml`

**Package Manager:**
- pip via `requirements.txt` (production installs)
- Poetry via `pyproject.toml` (dev tooling and dependency declarations)
- Lockfile: Not detected (no `poetry.lock` or `requirements.lock` committed)

## Frameworks

**Core:**
- FastAPI 0.104.1 - Web framework, all REST and WebSocket endpoints
- Uvicorn 0.24.0 (with `[standard]` extras) - ASGI server, hot reload in dev
- Starlette - Underlying ASGI toolkit (bundled with FastAPI), used directly for `BaseHTTPMiddleware`

**Data Validation:**
- Pydantic v2 2.4.2 - All request/response models in `app/models/`
- pydantic-settings 2.0.3 - `app/config.py` `Settings` class with `AGENTHUB_` env prefix

**Database ORM:**
- SQLAlchemy 2.0.23 - Declared as dependency; actual DB operations use raw SQL via custom `Database` class in `app/database/connection.py`
- Alembic 1.12.1 - Migration framework declared; runtime DDL is executed inline in `app/main.py` lifespan

**Authentication:**
- PyJWT 2.8.0 (with `[crypto]`) - JWT access and refresh token creation/verification (`app/auth/jwt_auth.py`)
- passlib 1.7.4 (with `[bcrypt]`) - Password hashing for admin users (`bcrypt` scheme)
- Casbin 1.25.0 - RBAC policy enforcement via file-based `rbac_model.conf` + `rbac_policy.csv` (`app/auth/rbac/enforcer.py`)
- slowapi 0.1.9 - Rate limiting (declared in `requirements.txt`; not yet wired into middleware)

**HTTP Client:**
- httpx 0.25.2 (async) - Outgoing HTTP: webhook delivery (`app/services/event_delivery_service.py`), agent bridge polling (`app/bridge/agent_bridge.py`)

**WebSocket:**
- websockets 12.0 - WebSocket support; endpoint at `GET /v1/ws` (`app/api/routes_websocket.py`)

**Structured Logging:**
- structlog 23.2.0 - JSON logging in production, console renderer in debug; configured in `app/logging.py`

**Monitoring:**
- prometheus-client 0.19.0 - Declared dependency; not yet actively instrumented in route handlers

**Vector Database:**
- zvec 0.1.0 - Local vector storage at `./data/zvec` path; configured via `Settings.zvec_path` and `Settings.embedding_model`

**Caching:**
- redis 5.0.1 - Async Redis client (`redis.asyncio`) for token caching and blacklisting (`app/auth/redis_cache.py`)

**Testing:**
- pytest 7.4.3
- pytest-asyncio 0.21.1
- pytest-cov 4.1.0

**Build/Dev:**
- black 23.11.0 - Code formatting, line length 88, target Python 3.11
- isort 5.12.0 - Import sorting (`profile = "black"`)
- flake8 6.1.0 - Linting
- mypy 1.7.1 - Static type checking (`disallow_untyped_defs = true`)

## Key Dependencies

**Critical:**
- `fastapi==0.104.1` - Entire API surface lives here; version pinned hard
- `pydantic==2.4.2` - v2 API (not v1 compatible); all models use v2 patterns
- `pyjwt[crypto]==2.8.0` - Auth token signing; `jwt_secret_key` must be set in production
- `casbin==1.25.0` - RBAC policies live in `app/auth/rbac/policies/` as `.conf`/`.csv` files

**Infrastructure:**
- `sqlalchemy==2.0.23` - Declared but DB layer uses a custom raw-SQL `Database` wrapper, not SQLAlchemy ORM sessions
- `alembic==1.12.1` - Declared; migrations not actively used - tables created via DDL in `app/main.py` lifespan startup
- `redis==5.0.1` - Optional: Redis is gracefully degraded if unavailable
- `zvec==0.1.0` - Local vector store; path created at startup (`./data/zvec`)
- `python-multipart==0.0.6` - Required for FastAPI file upload support (`routes_artifacts.py`)
- `python-dotenv==1.0.0` - `.env` file loading for local dev
- `click==8.1.7` - CLI entrypoints in `scripts/`
- `httpx==0.25.2` - Used in `AgentBridge` client and webhook delivery

## Configuration

**Environment:**
- All config in `app/config.py` via `pydantic-settings` `Settings` class
- Environment variable prefix: `AGENTHUB_`
- Key variables required for production:
  - `AGENTHUB_SECRET_KEY` - General secret key
  - `AGENTHUB_JWT_SECRET_KEY` - JWT signing secret
  - `AGENTHUB_DB_PATH` - SQLite file path (default: `./data/state/agenthub.db`)
  - `AGENTHUB_REDIS_URL` - Redis connection string (default: `redis://localhost:6379`)
  - `AGENTHUB_ACN_ADMIN_KEY` - Admin key for ACN invite management
  - `AGENTHUB_TURSO_DATABASE_URL` + `AGENTHUB_TURSO_AUTH_TOKEN` - Turso cloud DB (optional)
  - `AGENTHUB_HATCHET_API_KEY` + `AGENTHUB_HATCHET_SERVER_URL` - Hatchet workflow (optional)

**Build:**
- `pyproject.toml` - Poetry build config, black/isort/mypy/pytest settings
- `Dockerfile` - `python:3.11-slim` base, installs `requirements.txt`, exposes 7788
- `docker-compose.yml` - Two services: `agenthub` (port 7788) + `redis:7-alpine` (port 6379)

## Platform Requirements

**Development:**
- Python 3.11+
- Redis (optional, graceful degradation)
- Docker + Docker Compose (for containerized dev)
- Run command: `uvicorn app.main:app --host 0.0.0.0 --port 7788 --reload`

**Production:**
- Deployed as systemd service on VPS at `hub.brunhilde.cloud`
- Docker image via `docker-compose.yml`
- Health check endpoint: `GET /v1/health`
- Optional cloud DB via Turso (libSQL) - falls back to local SQLite if not configured
- Port: 7788

---

*Stack analysis: 2026-04-07*
