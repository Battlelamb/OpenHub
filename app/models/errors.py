"""
RFC 7807 Problem Details for HTTP Problems
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict, Field


class FieldError(BaseModel):
    """Single field validation error"""
    field: str = Field(..., description="Field path (e.g., 'agent_name')")
    message: str = Field(..., description="Human-readable error message")


class ProblemDetail(BaseModel):
    """
    RFC 7807 Problem Details for HTTP Problems
    
    See: https://datatracker.ietf.org/doc/html/rfc7807
    
    Attributes:
        type: URI reference identifying the problem type
        title: Short, human-readable summary
        status: HTTP status code
        detail: Human-readable explanation specific to this occurrence
        instance: URI reference identifying the specific occurrence
        trace_id: Request ID for tracing (OpenHub extension)
        errors: Field-level validation errors (for 422 responses)
    """
    type: str = Field(
        default="about:blank",
        description="URI reference identifying the problem type"
    )
    title: str = Field(..., description="Short, human-readable summary")
    status: int = Field(..., description="HTTP status code")
    detail: str = Field(..., description="Human-readable explanation")
    instance: Optional[str] = Field(
        default=None,
        description="URI reference identifying the specific occurrence"
    )
    trace_id: Optional[str] = Field(
        default=None,
        description="Request ID for tracing"
    )
    errors: Optional[List[FieldError]] = Field(
        default=None,
        description="Field-level validation errors"
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "type": "about:blank",
                "title": "Unauthorized",
                "status": 401,
                "detail": "Invalid or missing API key",
                "instance": "/v1/agents/register",
                "trace_id": "f76aad78-d29c-45d2-9cef-b959b6a61cce"
            }
        }
    )


# Pre-built problem instances for common errors
def problem_unauthorized(detail: str = "Authentication required", instance: str = None, trace_id: str = None) -> ProblemDetail:
    """401 Unauthorized"""
    return ProblemDetail(
        type="about:blank",
        title="Unauthorized",
        status=401,
        detail=detail,
        instance=instance,
        trace_id=trace_id
    )


def problem_forbidden(detail: str = "Access denied", instance: str = None, trace_id: str = None) -> ProblemDetail:
    """403 Forbidden"""
    return ProblemDetail(
        type="about:blank",
        title="Forbidden",
        status=403,
        detail=detail,
        instance=instance,
        trace_id=trace_id
    )


def problem_not_found(detail: str = "Resource not found", instance: str = None, trace_id: str = None) -> ProblemDetail:
    """404 Not Found"""
    return ProblemDetail(
        type="about:blank",
        title="Not Found",
        status=404,
        detail=detail,
        instance=instance,
        trace_id=trace_id
    )


def problem_conflict(detail: str = "Resource conflict", instance: str = None, trace_id: str = None) -> ProblemDetail:
    """409 Conflict"""
    return ProblemDetail(
        type="about:blank",
        title="Conflict",
        status=409,
        detail=detail,
        instance=instance,
        trace_id=trace_id
    )


def problem_validation(detail: str = "Request validation failed", instance: str = None, trace_id: str = None, errors: List[FieldError] = None) -> ProblemDetail:
    """422 Unprocessable Entity"""
    return ProblemDetail(
        type="about:blank",
        title="Unprocessable Entity",
        status=422,
        detail=detail,
        instance=instance,
        trace_id=trace_id,
        errors=errors
    )


def problem_rate_limit(detail: str = "Rate limit exceeded", instance: str = None, trace_id: str = None) -> ProblemDetail:
    """429 Too Many Requests"""
    return ProblemDetail(
        type="about:blank",
        title="Too Many Requests",
        status=429,
        detail=detail,
        instance=instance,
        trace_id=trace_id
    )


def problem_internal(detail: str = "Internal server error", instance: str = None, trace_id: str = None) -> ProblemDetail:
    """500 Internal Server Error"""
    return ProblemDetail(
        type="about:blank",
        title="Internal Server Error",
        status=500,
        detail=detail,
        instance=instance,
        trace_id=trace_id
    )


def problem_bad_gateway(detail: str = "Bad gateway", instance: str = None, trace_id: str = None) -> ProblemDetail:
    """502 Bad Gateway"""
    return ProblemDetail(
        type="about:blank",
        title="Bad Gateway",
        status=502,
        detail=detail,
        instance=instance,
        trace_id=trace_id
    )


def problem_unavailable(detail: str = "Service unavailable", instance: str = None, trace_id: str = None) -> ProblemDetail:
    """503 Service Unavailable"""
    return ProblemDetail(
        type="about:blank",
        title="Service Unavailable",
        status=503,
        detail=detail,
        instance=instance,
        trace_id=trace_id
    )
