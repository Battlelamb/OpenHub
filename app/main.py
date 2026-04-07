"""
Agent Hub Main Application Entry Point
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from .config import get_settings
from .logging import setup_logging, get_logger
from .middleware import setup_error_handlers, setup_middleware
from .api.routes_health import router as health_router

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
    os.makedirs(settings.zvec_path, exist_ok=True)

    # Auto-create database tables on startup
    from .database.connection import get_database
    try:
        db = get_database()
        # Sync from Turso first to get existing tables
        db.sync()
        tables = [
            """CREATE TABLE IF NOT EXISTS agents (
                id TEXT PRIMARY KEY, agent_name TEXT NOT NULL UNIQUE, description TEXT,
                capabilities TEXT DEFAULT '[]', status TEXT DEFAULT 'offline',
                last_heartbeat TIMESTAMP, current_task TEXT,
                labels TEXT DEFAULT '{}', metadata TEXT DEFAULT '{}',
                tasks_completed INTEGER DEFAULT 0, tasks_failed INTEGER DEFAULT 0,
                average_task_duration REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""",
            """CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY, title TEXT NOT NULL, description TEXT,
                task_type TEXT NOT NULL DEFAULT 'feature', priority INTEGER DEFAULT 50,
                status TEXT NOT NULL DEFAULT 'queued',
                required_capabilities TEXT DEFAULT '[]', owner_agent_id TEXT,
                claimed_at TIMESTAMP, started_at TIMESTAMP, completed_at TIMESTAMP,
                lease_until TIMESTAMP, retry_count INTEGER DEFAULT 0,
                max_retries INTEGER DEFAULT 3, last_error TEXT,
                deadline_at TIMESTAMP, idempotency_key TEXT,
                labels TEXT DEFAULT '{}', metadata TEXT DEFAULT '{}',
                payload TEXT DEFAULT '{}', result_summary TEXT,
                output TEXT DEFAULT '{}', artifact_ids TEXT DEFAULT '[]',
                duration_seconds REAL, created_by TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""",
            """CREATE TABLE IF NOT EXISTS acn_nodes (
                id TEXT PRIMARY KEY, node_name TEXT NOT NULL UNIQUE, node_url TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'offline', capabilities TEXT DEFAULT '[]',
                metadata TEXT DEFAULT '{}', labels TEXT DEFAULT '{}',
                last_heartbeat TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""",
            """CREATE TABLE IF NOT EXISTS remote_agent_mappings (
                id TEXT PRIMARY KEY, local_agent_id TEXT NOT NULL UNIQUE,
                node_id TEXT NOT NULL, remote_agent_name TEXT NOT NULL,
                callback_url TEXT, connection_metadata TEXT DEFAULT '{}',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""",
            """CREATE TABLE IF NOT EXISTS api_keys (
                id TEXT PRIMARY KEY, name TEXT NOT NULL, key_type TEXT NOT NULL,
                key_hash TEXT NOT NULL, salt TEXT NOT NULL, scopes TEXT DEFAULT '[]',
                description TEXT, expires_at TIMESTAMP, created_by TEXT,
                metadata TEXT DEFAULT '{}', is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_used_at TIMESTAMP, revoked_at TIMESTAMP, revoked_by TEXT)""",
            """CREATE TABLE IF NOT EXISTS pending_applications (
                id TEXT PRIMARY KEY, agent_name TEXT NOT NULL,
                data TEXT NOT NULL, client_ip TEXT,
                status TEXT DEFAULT 'pending',
                api_key_value TEXT,
                reviewed_by TEXT, reviewed_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""",
            """CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                from_agent_id TEXT NOT NULL,
                to_agent_id TEXT,
                thread_id TEXT,
                message_type TEXT DEFAULT 'text',
                content TEXT NOT NULL,
                metadata TEXT DEFAULT '{}',
                read_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""",
            """CREATE TABLE IF NOT EXISTS threads (
                id TEXT PRIMARY KEY,
                title TEXT,
                thread_type TEXT DEFAULT 'conversation',
                task_id TEXT,
                participants TEXT DEFAULT '[]',
                status TEXT DEFAULT 'open',
                created_by TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""",
        ]
        for ddl in tables:
            try:
                db.execute(ddl)
            except Exception:
                pass
        # Force sync to pull tables into local replica
        db.sync()
        # Re-sync to ensure local has all tables
        import time
        time.sleep(1)
        db.sync()
        logger.info("database_tables_ready")
    except Exception as e:
        logger.error("database_init_failed", error=str(e))

    logger.info("agent_hub_started", version=__version__)
    
    yield
    
    # Shutdown
    logger.info("agent_hub_shutting_down")


# Create FastAPI app with lifespan management
app = FastAPI(
    title="Agent Hub API",
    description="Multi-agent coordination system for local development",
    version=__version__,
    docs_url=None,
    redoc_url=None,
    lifespan=lifespan,
)

# Setup error handlers and middleware
setup_error_handlers(app)
setup_middleware(app)

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