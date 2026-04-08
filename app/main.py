"""
Agent Hub Main Application Entry Point
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
import uvicorn

from .config import get_settings
from .logging import setup_logging, get_logger
from .middleware import setup_error_handlers, setup_middleware
from .api.routes_health import router as health_router
from .api.routes_metrics import router as metrics_router

# Version info
__version__ = "0.1.0"

# Initialize settings
settings = get_settings()

# Setup logging
setup_logging()
logger = get_logger(__name__)

# Initialize slowapi rate limiter
limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    # Startup
    logger.info("agent_hub_starting", version=__version__)
    
    # Create necessary directories
    import os
    os.makedirs(settings.artifact_dir, exist_ok=True)
    os.makedirs(os.path.dirname(settings.db_path), exist_ok=True)
    os.makedirs(settings.zvec_path, exist_ok=True)

    # Run database migrations via Alembic (HARD-06)
    from alembic.config import Config as AlembicConfig
    from alembic import command as alembic_command
    import os as _lifespan_os
    alembic_ini = _lifespan_os.path.join(
        _lifespan_os.path.dirname(_lifespan_os.path.dirname(__file__)), "alembic.ini"
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

    # Wire heartbeat monitor to detect offline agents (HARD-04)
    from .services.heartbeat_service import HeartbeatService
    heartbeat_service = HeartbeatService(db)
    await heartbeat_service.start_monitoring()
    logger.info("heartbeat_monitor_started")

    logger.info("agent_hub_started", version=__version__)

    yield

    # Shutdown
    await heartbeat_service.stop_monitoring()
    logger.info("heartbeat_monitor_stopped")
    logger.info("agent_hub_shutting_down")


# Create FastAPI app with lifespan management
app = FastAPI(
    title="Agent Hub API",
    description="Multi-agent coordination system for local development",
    version=__version__,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Setup error handlers and middleware
setup_error_handlers(app)
setup_middleware(app)

# Wire slowapi rate limiter
app.state.limiter = limiter
app.add_exception_handler(429, _rate_limit_exceeded_handler)

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

# Import and include memory router
from .api.routes_memory import router as memory_router
app.include_router(memory_router)

# Import and include workflow engine router
from .api.routes_workflow import router as workflow_engine_router
app.include_router(workflow_engine_router)

# Import and include artifact router
from .api.routes_artifacts import router as artifacts_router
app.include_router(artifacts_router)

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