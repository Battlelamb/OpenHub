"""
Error handling and middleware for Agent Hub
"""
import time
import traceback
from typing import Dict, Any, Callable, Optional
from uuid import uuid4

from fastapi import FastAPI, Request, Response, HTTPException, status
from fastapi.exception_handlers import http_exception_handler, request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import structlog

from .config import get_settings
from .logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


class RequestTimingMiddleware(BaseHTTPMiddleware):
    """Middleware to track request timing and add request IDs"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate request ID
        request_id = str(uuid4())
        request.state.request_id = request_id
        
        # Start timing
        start_time = time.time()
        
        # Add request ID to logs context
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)
        
        # Log request start
        logger.info(
            "request_started",
            method=request.method,
            path=request.url.path,
            query=str(request.url.query) if request.url.query else None,
            user_agent=request.headers.get("user-agent"),
            client_ip=request.client.host if request.client else None
        )
        
        try:
            # Process request
            response = await call_next(request)
            
            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000
            
            # Log response
            logger.info(
                "request_completed",
                status_code=response.status_code,
                duration_ms=round(duration_ms, 2)
            )
            
            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Response-Time"] = f"{duration_ms:.2f}ms"
            
            return response
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            
            logger.error(
                "request_failed",
                error=str(e),
                error_type=type(e).__name__,
                duration_ms=round(duration_ms, 2),
                traceback=traceback.format_exc()
            )
            
            # Return generic error response
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "success": False,
                    "error": "Internal server error",
                    "request_id": request_id,
                    "error_code": "INTERNAL_ERROR"
                },
                headers={
                    "X-Request-ID": request_id,
                    "X-Response-Time": f"{duration_ms:.2f}ms"
                }
            )


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to add security headers"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        
        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        return response


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handle validation errors with structured response"""
    
    request_id = getattr(request.state, "request_id", str(uuid4()))
    
    logger.warning(
        "validation_error",
        errors=[{
            "field": ".".join(str(loc) for loc in error["loc"]),
            "message": error["msg"],
            "type": error["type"]
        } for error in exc.errors()],
        request_id=request_id
    )
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "error": "Validation error",
            "error_code": "VALIDATION_ERROR",
            "validation_errors": [{
                "field": ".".join(str(loc) for loc in error["loc"]),
                "message": error["msg"],
                "type": error["type"]
            } for error in exc.errors()],
            "request_id": request_id
        },
        headers={"X-Request-ID": request_id}
    )


async def http_exception_handler_custom(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle HTTP exceptions with structured response"""
    
    request_id = getattr(request.state, "request_id", str(uuid4()))
    
    # Log error if status code >= 500
    if exc.status_code >= 500:
        logger.error(
            "http_exception",
            status_code=exc.status_code,
            detail=exc.detail,
            request_id=request_id
        )
    else:
        logger.warning(
            "http_exception",
            status_code=exc.status_code,
            detail=exc.detail,
            request_id=request_id
        )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": exc.detail,
            "error_code": get_error_code_from_status(exc.status_code),
            "request_id": request_id
        },
        headers={"X-Request-ID": request_id}
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle general exceptions with structured response"""
    
    request_id = getattr(request.state, "request_id", str(uuid4()))
    
    logger.error(
        "unhandled_exception",
        error=str(exc),
        error_type=type(exc).__name__,
        traceback=traceback.format_exc(),
        request_id=request_id
    )
    
    # Don't expose internal error details in production
    error_message = str(exc) if settings.debug else "Internal server error"
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": error_message,
            "error_code": "INTERNAL_ERROR",
            "request_id": request_id,
            "trace_id": request_id if settings.debug else None
        },
        headers={"X-Request-ID": request_id}
    )


def get_error_code_from_status(status_code: int) -> str:
    """Get error code from HTTP status code"""
    error_codes = {
        400: "BAD_REQUEST",
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        405: "METHOD_NOT_ALLOWED",
        409: "CONFLICT",
        422: "VALIDATION_ERROR",
        429: "RATE_LIMITED",
        500: "INTERNAL_ERROR",
        502: "BAD_GATEWAY",
        503: "SERVICE_UNAVAILABLE",
        504: "GATEWAY_TIMEOUT"
    }
    return error_codes.get(status_code, "UNKNOWN_ERROR")


class APIKeyValidationError(HTTPException):
    """Custom exception for API key validation errors"""
    
    def __init__(self, detail: str = "Invalid or missing API key"):
        super().__init__(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)


class TaskNotFoundError(HTTPException):
    """Custom exception for task not found errors"""
    
    def __init__(self, task_id: str):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task '{task_id}' not found"
        )


class AgentNotFoundError(HTTPException):
    """Custom exception for agent not found errors"""
    
    def __init__(self, agent_id: str):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent '{agent_id}' not found"
        )


class TaskConflictError(HTTPException):
    """Custom exception for task conflict errors"""
    
    def __init__(self, detail: str):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=detail
        )


class AgentBusyError(HTTPException):
    """Custom exception for agent busy errors"""
    
    def __init__(self, agent_id: str):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Agent '{agent_id}' is busy with another task"
        )


class RateLimitError(HTTPException):
    """Custom exception for rate limit errors"""
    
    def __init__(self, detail: str = "Rate limit exceeded"):
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=detail
        )


def setup_error_handlers(app: FastAPI) -> None:
    """Setup all error handlers for the application"""
    
    # Custom exception handlers
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler_custom)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler_custom)
    app.add_exception_handler(Exception, general_exception_handler)


def setup_middleware(app: FastAPI) -> None:
    """Setup all middleware for the application"""
    
    # Add middleware in reverse order (last added = first executed)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RequestTimingMiddleware)