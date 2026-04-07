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
        migrations_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "database", "migrations")
        if os.path.isdir(migrations_dir):
            for sql_file in sorted(os.listdir(migrations_dir)):
                if sql_file.endswith(".sql"):
                    sql_path = os.path.join(migrations_dir, sql_file)
                    with open(sql_path) as f:
                        for stmt in f.read().split(";"):
                            stmt = stmt.strip()
                            if stmt:
                                try:
                                    db.execute(stmt)
                                except Exception:
                                    pass  # Table already exists
                    logger.info("migration_applied", file=sql_file)

        # Ensure api_keys table exists (not in migrations yet)
        db.execute("""CREATE TABLE IF NOT EXISTS api_keys (
            id TEXT PRIMARY KEY, name TEXT NOT NULL, key_type TEXT NOT NULL,
            key_hash TEXT NOT NULL, salt TEXT NOT NULL, scopes TEXT DEFAULT '[]',
            description TEXT, expires_at TIMESTAMP, created_by TEXT,
            metadata TEXT DEFAULT '{}', is_active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_used_at TIMESTAMP, revoked_at TIMESTAMP, revoked_by TEXT
        )""")

        # Sync to Turso if configured
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
    docs_url="/docs",
    redoc_url="/redoc",
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