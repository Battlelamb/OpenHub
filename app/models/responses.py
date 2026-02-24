"""
Standard API response models
"""
from datetime import datetime
from typing import Optional, Any, Dict, List
from pydantic import Field

from .base import BaseModel


class SuccessResponse(BaseModel):
    """Standard success response"""
    
    success: bool = Field(
        default=True,
        description="Success indicator"
    )
    
    message: str = Field(
        description="Success message"
    )
    
    data: Optional[Any] = Field(
        default=None,
        description="Response data"
    )
    
    request_id: Optional[str] = Field(
        default=None,
        description="Request ID for tracking"
    )
    
    timestamp: datetime = Field(
        default_factory=lambda: datetime.utcnow(),
        description="Response timestamp"
    )


class ErrorResponse(BaseModel):
    """Standard error response"""
    
    success: bool = Field(
        default=False,
        description="Success indicator"
    )
    
    error: str = Field(
        description="Error message"
    )
    
    error_code: Optional[str] = Field(
        default=None,
        description="Error code"
    )
    
    error_details: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Detailed error information"
    )
    
    request_id: Optional[str] = Field(
        default=None,
        description="Request ID for tracking"
    )
    
    timestamp: datetime = Field(
        default_factory=lambda: datetime.utcnow(),
        description="Response timestamp"
    )
    
    trace_id: Optional[str] = Field(
        default=None,
        description="Trace ID for debugging"
    )


class ValidationErrorResponse(ErrorResponse):
    """Response for validation errors"""
    
    validation_errors: List[Dict[str, Any]] = Field(
        description="List of validation errors"
    )


class HealthResponse(BaseModel):
    """Health check response"""
    
    status: str = Field(
        description="Health status"
    )
    
    version: str = Field(
        description="Application version"
    )
    
    timestamp: str = Field(
        description="Check timestamp"
    )
    
    request_id: Optional[str] = Field(
        default=None,
        description="Request ID"
    )
    
    system: Optional[Dict[str, Any]] = Field(
        default=None,
        description="System information"
    )
    
    configuration: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Configuration status"
    )
    
    database: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Database status"
    )
    
    storage: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Storage status"
    )
    
    cache: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Cache status"
    )
    
    agents: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Agent status"
    )
    
    tasks: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Task status"
    )


class StatusResponse(BaseModel):
    """General status response"""
    
    status: str = Field(description="Status value")
    
    message: Optional[str] = Field(
        default=None,
        description="Status message"
    )
    
    details: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Status details"
    )


class AsyncOperationResponse(BaseModel):
    """Response for asynchronous operations"""
    
    operation_id: str = Field(
        description="Operation identifier"
    )
    
    status: str = Field(
        description="Operation status"
    )
    
    message: str = Field(
        description="Operation message"
    )
    
    estimated_completion: Optional[datetime] = Field(
        default=None,
        description="Estimated completion time"
    )
    
    progress_url: Optional[str] = Field(
        default=None,
        description="URL to check progress"
    )
    
    result_url: Optional[str] = Field(
        default=None,
        description="URL to get results when complete"
    )


class BulkOperationResponse(BaseModel):
    """Response for bulk operations"""
    
    total_items: int = Field(
        description="Total number of items processed"
    )
    
    successful: int = Field(
        description="Number of successful operations"
    )
    
    failed: int = Field(
        description="Number of failed operations"
    )
    
    errors: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="List of errors that occurred"
    )
    
    results: Optional[List[Any]] = Field(
        default=None,
        description="Results for successful operations"
    )