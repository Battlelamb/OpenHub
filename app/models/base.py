"""
Base Pydantic models for Agent Hub
"""
from pydantic import BaseModel as PydanticBaseModel, Field, ConfigDict
from datetime import datetime
from typing import Optional, Dict, Any
from uuid import uuid4


class BaseModel(PydanticBaseModel):
    """Base model with common configuration"""
    
    model_config = ConfigDict(
        # Allow population by field name and alias
        populate_by_name=True,
        # Validate assignment
        validate_assignment=True,
        # Use enum values instead of names
        use_enum_values=True,
        # Extra fields not allowed
        extra='forbid',
        # Serialize by alias
        by_alias=True,
    )


class TimestampMixin(BaseModel):
    """Mixin for models that need timestamp fields"""
    
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Creation timestamp"
    )
    
    updated_at: Optional[datetime] = Field(
        default=None,
        description="Last update timestamp"
    )


class IDMixin(BaseModel):
    """Mixin for models that need ID fields"""
    
    id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique identifier"
    )


class MetadataMixin(BaseModel):
    """Mixin for models that need metadata fields"""
    
    labels: Dict[str, str] = Field(
        default_factory=dict,
        description="Key-value labels"
    )
    
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata"
    )


class PaginationParams(BaseModel):
    """Parameters for paginated requests"""
    
    limit: int = Field(
        default=50,
        ge=1,
        le=1000,
        description="Maximum number of items to return"
    )
    
    offset: int = Field(
        default=0,
        ge=0,
        description="Number of items to skip"
    )
    
    sort_by: str = Field(
        default="created_at",
        description="Field to sort by"
    )
    
    sort_order: str = Field(
        default="desc",
        regex="^(asc|desc)$",
        description="Sort order (asc or desc)"
    )


class PaginatedResponse(BaseModel):
    """Response model for paginated data"""
    
    data: list = Field(description="List of items")
    
    pagination: Dict[str, Any] = Field(
        description="Pagination information"
    )
    
    @classmethod
    def create(
        cls,
        data: list,
        total: int,
        limit: int,
        offset: int,
        **kwargs
    ) -> "PaginatedResponse":
        """Create paginated response with calculated pagination info"""
        
        has_next = offset + limit < total
        has_previous = offset > 0
        
        pagination = {
            "total": total,
            "count": len(data),
            "limit": limit,
            "offset": offset,
            "has_next": has_next,
            "has_previous": has_previous,
            **kwargs
        }
        
        return cls(data=data, pagination=pagination)