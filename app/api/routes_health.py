"""
Health check and system status endpoints
"""
from fastapi import APIRouter, Depends
from datetime import datetime
import psutil
import os
from typing import Dict, Any

from ..config import get_settings, Settings
from ..dependencies import RequestIdDep
from ..logging import get_logger

router = APIRouter(prefix="/v1", tags=["health"])
logger = get_logger(__name__)


@router.get("/health")
async def health_check(
    request_id: RequestIdDep,
    settings: Settings = Depends(get_settings)
) -> Dict[str, Any]:
    """
    Comprehensive health check endpoint
    
    Returns:
        - Basic service status
        - System information
        - Configuration status
        - Dependency status
    """
    logger.info("health_check_requested", request_id=request_id)
    
    # Basic status
    health_data = {
        "status": "healthy",
        "version": "0.1.0",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "request_id": request_id,
    }
    
    # System information
    try:
        health_data["system"] = {
            "cpu_percent": psutil.cpu_percent(interval=0.1),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage("/").percent if os.name != "nt" else psutil.disk_usage("C:\\").percent,
            "process_id": os.getpid(),
        }
    except Exception as e:
        logger.warning("system_info_failed", error=str(e), request_id=request_id)
        health_data["system"] = {"status": "unavailable", "error": str(e)}
    
    # Configuration status
    health_data["configuration"] = {
        "host": settings.host,
        "port": settings.port,
        "debug": settings.debug,
        "log_level": settings.log_level,
        "max_agents": settings.max_agents,
        "max_concurrent_tasks": settings.max_concurrent_tasks,
    }
    
    # Database status
    try:
        db_path = settings.db_path
        db_exists = os.path.exists(db_path)
        db_size = os.path.getsize(db_path) if db_exists else 0
        
        health_data["database"] = {
            "status": "ready" if db_exists else "not_initialized",
            "path": db_path,
            "size_bytes": db_size,
            "connection": "ok"  # TODO: Test actual DB connection
        }
    except Exception as e:
        logger.warning("database_check_failed", error=str(e), request_id=request_id)
        health_data["database"] = {
            "status": "error",
            "error": str(e)
        }
    
    # Storage status
    try:
        artifact_dir = settings.artifact_dir
        zvec_dir = settings.zvec_path
        
        health_data["storage"] = {
            "artifact_dir": {
                "path": artifact_dir,
                "exists": os.path.exists(artifact_dir),
                "writable": os.access(artifact_dir, os.W_OK) if os.path.exists(artifact_dir) else False
            },
            "zvec_dir": {
                "path": zvec_dir,
                "exists": os.path.exists(zvec_dir),
                "writable": os.access(zvec_dir, os.W_OK) if os.path.exists(zvec_dir) else False
            }
        }
    except Exception as e:
        logger.warning("storage_check_failed", error=str(e), request_id=request_id)
        health_data["storage"] = {
            "status": "error",
            "error": str(e)
        }
    
    # Cache status (Redis)
    try:
        # TODO: Test actual Redis connection
        health_data["cache"] = {
            "status": "not_implemented",
            "redis_url": settings.redis_url
        }
    except Exception as e:
        logger.warning("cache_check_failed", error=str(e), request_id=request_id)
        health_data["cache"] = {
            "status": "error",
            "error": str(e)
        }
    
    # Agent and task counts (placeholder)
    health_data["agents"] = {
        "connected": 0,  # TODO: Get actual count
        "max_allowed": settings.max_agents
    }
    
    health_data["tasks"] = {
        "active": 0,  # TODO: Get actual count
        "queued": 0,  # TODO: Get actual count
        "max_concurrent": settings.max_concurrent_tasks
    }
    
    logger.info("health_check_completed", request_id=request_id, status="healthy")
    return health_data


@router.get("/health/simple")
async def simple_health_check() -> Dict[str, str]:
    """
    Simple health check for load balancers and monitoring
    
    Returns minimal response for quick health verification
    """
    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }


@router.get("/version")
async def version_info() -> Dict[str, str]:
    """
    Version information endpoint
    """
    return {
        "version": "0.1.0",
        "api_version": "v1",
        "build": "development"  # TODO: Add actual build info
    }