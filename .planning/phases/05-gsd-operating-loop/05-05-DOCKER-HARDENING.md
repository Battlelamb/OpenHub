# Phase 05-05: Docker Compose Hardening

**Goal:** Docker Compose starts with health checks and restart policies — a container that crashes restarts automatically.

**Roadmap requirement:** Phase 5, Success Criteria #3

## Changes

### docker-compose.yml
- ✅ Added `healthcheck` to agenthub service (curl /v1/health)
- ✅ Added `healthcheck` to redis service (redis-cli ping)
- ✅ Added `depends_on` with `condition: service_healthy` for Redis
- ✅ Used `${VAR:?error}` for required secrets (fails fast if missing)
- ✅ Removed hardcoded passwords — requires .env or env vars
- ✅ `restart: unless-stopped` already present (kept)

### Dockerfile
- ✅ Removed `--reload` from CMD (production mode)
- ✅ Added non-root user (`openhub`)
- ✅ Copy alembic.ini and alembic/ for migration support
- ✅ Added `.dockerignore` for leaner images

### .env.example
- ✅ Created with all required + optional variables documented

## Success Criteria
- [x] Health checks on both services
- [x] Restart policies on both services
- [x] Required secrets fail fast if not set
- [x] Non-root user in container
- [x] .dockerignore for lean builds
