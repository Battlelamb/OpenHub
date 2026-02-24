"""
Structured logging configuration for Agent Hub
"""
import logging
import logging.config
import structlog
import sys
from pathlib import Path
from typing import Any, Dict, Optional

from .config import get_settings


def setup_logging(log_level: Optional[str] = None, log_file: Optional[str] = None) -> None:
    """Configure structured logging for the application"""
    
    settings = get_settings()
    level = log_level or settings.log_level
    
    # Create log directory if file logging is enabled
    if log_file or settings.log_file:
        log_path = Path(log_file or settings.log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Configure structlog
    structlog.configure(
        processors=[
            # Add timestamp
            structlog.processors.TimeStamper(fmt="iso"),
            # Add log level
            structlog.processors.add_log_level,
            # Add logger name
            structlog.processors.add_logger_name,
            # Stack info for exceptions
            structlog.processors.StackInfoRenderer(),
            # Format exceptions
            structlog.dev.set_exc_info,
            # JSON formatting for production, pretty for development
            structlog.processors.JSONRenderer() if not settings.debug else structlog.dev.ConsoleRenderer()
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.getLevelName(level.upper())),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    # Configure standard library logging
    logging_config: Dict[str, Any] = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "json": {
                "format": "%(message)s",
            },
            "standard": {
                "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "stream": sys.stdout,
                "formatter": "json" if not settings.debug else "standard",
                "level": level.upper(),
            },
        },
        "loggers": {
            "": {  # Root logger
                "handlers": ["console"],
                "level": level.upper(),
                "propagate": False,
            },
            "uvicorn": {
                "handlers": ["console"],
                "level": "INFO",
                "propagate": False,
            },
            "uvicorn.access": {
                "handlers": ["console"],
                "level": "INFO",
                "propagate": False,
            },
            "fastapi": {
                "handlers": ["console"], 
                "level": "INFO",
                "propagate": False,
            },
        },
    }
    
    # Add file handler if configured
    if log_file or settings.log_file:
        logging_config["handlers"]["file"] = {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": log_file or settings.log_file,
            "maxBytes": 10 * 1024 * 1024,  # 10MB
            "backupCount": 5,
            "formatter": "json",
            "level": level.upper(),
        }
        
        # Add file handler to all loggers
        for logger_config in logging_config["loggers"].values():
            logger_config["handlers"].append("file")
    
    logging.config.dictConfig(logging_config)


def get_logger(name: str = __name__) -> structlog.BoundLogger:
    """Get a structured logger instance"""
    return structlog.get_logger(name)


# Application logger
logger = get_logger("agenthub")


def log_request(request_id: str, method: str, path: str, **kwargs) -> None:
    """Log HTTP request with context"""
    logger.info(
        "http_request",
        request_id=request_id,
        method=method,
        path=path,
        **kwargs
    )


def log_response(request_id: str, status_code: int, duration_ms: float, **kwargs) -> None:
    """Log HTTP response with context"""
    logger.info(
        "http_response",
        request_id=request_id,
        status_code=status_code,
        duration_ms=duration_ms,
        **kwargs
    )


def log_task_event(event_type: str, task_id: str, agent_id: Optional[str] = None, **kwargs) -> None:
    """Log task-related event"""
    logger.info(
        "task_event",
        event_type=event_type,
        task_id=task_id,
        agent_id=agent_id,
        **kwargs
    )


def log_agent_event(event_type: str, agent_id: str, **kwargs) -> None:
    """Log agent-related event"""
    logger.info(
        "agent_event",
        event_type=event_type,
        agent_id=agent_id,
        **kwargs
    )