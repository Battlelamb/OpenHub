"""
RFC 7807 Problem Details error models.
Used by all exception handlers in middleware.py.
"""
from pydantic import BaseModel
from typing import Optional, List


class FieldError(BaseModel):
    """Single field validation error."""
    field: str
    message: str
    type: Optional[str] = None


class ProblemDetail(BaseModel):
    """
    RFC 7807 Problem Details for HTTP APIs.
    https://www.rfc-editor.org/rfc/rfc7807

    type: URI identifying the problem type. Use "about:blank" when no type URI exists.
    title: Human-readable summary of the problem type.
    status: HTTP status code.
    detail: Human-readable explanation specific to this occurrence.
    instance: URI reference identifying this specific occurrence.
    trace_id: Request trace ID for log correlation (extension field).
    errors: Field-level validation errors (422 responses only).
    """
    type: str = "about:blank"
    title: str
    status: int
    detail: str
    instance: Optional[str] = None
    trace_id: Optional[str] = None
    errors: Optional[List[FieldError]] = None

    def to_dict(self) -> dict:
        """Return dict excluding None values for clean JSON responses."""
        return self.model_dump(exclude_none=True)
