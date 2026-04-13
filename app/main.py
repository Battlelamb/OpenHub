"""
Agent Hub Main Application Entry Point
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
import uvicorn

from .config import get_settings
from .logging import setup_logging, get_logger
from .middleware import setup_error_handlers, setup_middleware
from .limiter import limiter
from .services.connection_manager import ConnectionManager
from .api.routes_health import router as health_router
from .api.routes_metrics import router as metrics_router
from .api.routes_ws_ui import router as ws_ui_router

# Version info
__version__ = "0.1.0"

# Initialize settings
settings = get_settings()

# Setup logging
setup_logging()
logger = get_logger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    # Startup
    logger.info("agent_hub_starting", version=__version__)
    
    # Create necessary directories
    import os
    os.makedirs(settings.artifact_dir, exist_ok=True)
    os.makedirs(os.path.dirname(settings.db_path), exist_ok=True)

    # Run database migrations via Alembic (HARD-06)
    from alembic.config import Config as AlembicConfig
    from alembic import command as alembic_command
    import os as _lifespan_os
    alembic_ini = _lifespan_os.path.join(
        _lifespan_os.path.dirname(_lifespan_os.path.dirname(_lifespan_os.path.abspath(__file__))),
        "alembic.ini",
    )
    alembic_cfg = AlembicConfig(alembic_ini)
    alembic_command.upgrade(alembic_cfg, "head")
    logger.info("database_migrations_applied")

    # Sync for Turso remote mode compatibility
    from .database.connection import get_database
    try:
        db = get_database()
        db.sync()
    except Exception as e:
        logger.warning("database_sync_skipped", reason=str(e))

    # Wire ConnectionManager for WebSocket management (WS-02)
    # Must be created BEFORE HeartbeatService so the broadcast callback can be
    # injected into heartbeat monitoring (WS-04 offline detection events).
    connection_manager = ConnectionManager()
    await connection_manager.start()
    app.state.connection_manager = connection_manager
    logger.info("connection_manager_started")

    # Wire heartbeat monitor to detect offline agents (HARD-04).
    # Pass broadcast callback so offline detection emits agent_status_changed
    # events to UI clients (WS-04).
    from .services.heartbeat_service import HeartbeatService
    heartbeat_service = HeartbeatService(db, on_event=connection_manager.broadcast_to_ui)
    await heartbeat_service.start_monitoring()
    logger.info("heartbeat_monitor_started")

    # Start embedding retry worker (Plan 03-04 / VEC-04). No-op on local SQLite.
    from .services.embedding_retry_worker import (
        start_retry_worker,
        stop_retry_worker,
    )
    try:
        await start_retry_worker()
        logger.info("embedding_retry_worker_lifespan_started")
    except Exception as e:
        logger.warning("embedding_retry_worker_start_failed", error=str(e))

    # Vector search availability advisory (Plan 03-06 / VEC-06).
    # Emit a clear warning so OSS users running on local SQLite without Turso
    # understand why /v1/search returns 503. Also logs on auto-detect failures.
    from .database.vector_availability import is_vector_enabled
    if not is_vector_enabled():
        logger.warning(
            "vector_search_disabled",
            reason="Turso not configured or AGENTHUB_VECTOR_SEARCH_ENABLED=false",
            hint=(
                "Set AGENTHUB_TURSO_DATABASE_URL + AGENTHUB_TURSO_AUTH_TOKEN "
                "and AGENTHUB_VECTOR_SEARCH_ENABLED=true to enable BETA vector search. "
                "See README Vector Search (Beta) section for setup."
            ),
        )
    else:
        logger.info("vector_search_enabled")

    logger.info("agent_hub_started", version=__version__)

    yield

    # Shutdown - stop the embedding retry worker first so its in-flight DB
    # operations finish before the connection layer is torn down.
    try:
        await stop_retry_worker()
        logger.info("embedding_retry_worker_lifespan_stopped")
    except Exception as e:
        logger.warning("embedding_retry_worker_stop_failed", error=str(e))

    # Stop WebSocket manager before heartbeat so open sockets are closed
    # cleanly while the rest of the runtime is still live.
    await connection_manager.stop()
    logger.info("connection_manager_stopped")

    await heartbeat_service.stop_monitoring()
    logger.info("heartbeat_monitor_stopped")
    logger.info("agent_hub_shutting_down")


# OpenAPI tag metadata. The "search [experimental]" tag matches the prefix used
# by app/api/routes_search.py and the per-entity shortcut routes (Plan 03-06 /
# VEC-06). Marking it BETA in OpenAPI surfaces the opt-in status to /docs users.
openapi_tags = [
    {
        "name": "search [experimental]",
        "description": (
            "Semantic vector search over memories, tasks, artifacts, and messages. "
            "BETA: opt-in feature that requires Turso configuration. "
            "Set AGENTHUB_VECTOR_SEARCH_ENABLED=true and provide "
            "AGENTHUB_TURSO_DATABASE_URL + AGENTHUB_TURSO_AUTH_TOKEN. "
            "See README Vector Search (Beta) section for full setup."
        ),
    },
]

# Create FastAPI app with lifespan management
app = FastAPI(
    title="OpenHub API",
    description=(
        "Multi-agent coordination platform. "
        "All endpoints require JWT Bearer token or X-API-Key header unless marked public."
    ),
    version=__version__,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
    openapi_tags=openapi_tags,
)

# Setup error handlers and middleware
setup_error_handlers(app)
setup_middleware(app)

# Wire slowapi rate limiter with RFC 7807 handler
app.state.limiter = limiter


async def rfc7807_rate_limit_handler(request, exc):
    from .models.errors import problem_rate_limit
    request_id = getattr(request.state, "request_id", str(__import__("uuid").uuid4()))
    retry_after = getattr(exc, "retry_after", "60")
    problem = problem_rate_limit(
        detail=str(exc.detail) if hasattr(exc, "detail") else "Rate limit exceeded",
        instance=request.url.path,
        trace_id=request_id,
    )
    from starlette.responses import JSONResponse
    return JSONResponse(
        status_code=429,
        content=problem.model_dump(exclude_none=True),
        headers={"Retry-After": str(retry_after), "X-Request-ID": request_id},
    )


app.add_exception_handler(RateLimitExceeded, rfc7807_rate_limit_handler)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=settings.cors_methods,
    allow_headers=settings.cors_headers,
)

# Include routers
app.include_router(health_router)

# Import and include auth router
from .api.routes_auth import router as auth_router
app.include_router(auth_router)

# Import and include admin router
from .api.routes_admin import router as admin_router
app.include_router(admin_router)

# Import and include agents router
from .api.routes_agents import router as agents_router
app.include_router(agents_router)

# Import and include tasks router
from .api.routes_tasks import router as tasks_router
app.include_router(tasks_router)

# Import and include workflows router
from .api.routes_workflows import router as workflows_router
app.include_router(workflows_router)

# Import and include coordination router
from .api.routes_coordination import router as coordination_router
app.include_router(coordination_router)

# Import and include ACN router
from .api.routes_acn import router as acn_router
app.include_router(acn_router)

# Import and include messaging routers
from .api.routes_messaging import router as messaging_router, thread_router
app.include_router(messaging_router)
app.include_router(thread_router)

# Import and include WebSocket router
from .api.routes_websocket import router as ws_router
app.include_router(ws_router)

# Include WebSocket UI router (WS-01) - module-level import at top of file
app.include_router(ws_ui_router)

# Import and include memory router
from .api.routes_memory import router as memory_router
app.include_router(memory_router)

# Import and include workflow engine router
from .api.routes_workflow import router as workflow_engine_router
app.include_router(workflow_engine_router)

# Import and include artifact router
from .api.routes_artifacts import router as artifacts_router
app.include_router(artifacts_router)

# Import and include vector search router (Phase 03 / VEC-05, experimental)
from .api.routes_search import router as search_router
app.include_router(search_router)

# Import and include P1 routers (locks, tracing, costs)
from .api.routes_p1 import lock_router, trace_router, cost_router
app.include_router(lock_router)
app.include_router(trace_router)
app.include_router(cost_router)

# Import and include P2 routers (tools, templates, DLQ)
from .api.routes_p2 import tools_router, templates_router, dlq_router
app.include_router(tools_router)
app.include_router(templates_router)
app.include_router(dlq_router)

# Import and include metrics router (Prometheus)
app.include_router(metrics_router)

# Admin dashboard (static HTML)
from fastapi.responses import FileResponse
import os as _os
_static_dir = _os.path.join(_os.path.dirname(__file__), "static")

@app.get("/admin")
async def admin_dashboard():
    """Admin dashboard UI"""
    return FileResponse(_os.path.join(_static_dir, "admin.html"))

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with basic info"""
    return {
        "name": "Agent Hub",
        "version": __version__,
        "description": "Multi-agent coordination system for local development",
        "docs_url": "/docs",
        "health_url": "/v1/health",
        "api_version": "v1"
    }


def create_app() -> FastAPI:
    """Factory function to create FastAPI application"""
    return app


def run_server():
    """Run the development server with hot reload"""
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=True,
        reload_dirs=["app"],
        log_level=settings.log_level.lower(),
        access_log=True,
        use_colors=True,
    )


if __name__ == "__main__":
    run_server()