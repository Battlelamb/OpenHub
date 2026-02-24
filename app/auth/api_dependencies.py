"""
Clean API Key dependency injection for FastAPI
"""
from typing import Optional, Annotated
from fastapi import Depends, HTTPException, status, Request, Header

from ..config import get_settings
from ..logging import get_logger
from .api_keys import get_api_key_manager, APIKeyScope

logger = get_logger(__name__)
settings = get_settings()


async def get_api_key_from_header(
    request: Request,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key")
) -> Optional[str]:
    """
    Extract API key from X-API-Key header
    
    Returns None if no key provided (for optional auth)
    """
    if not x_api_key:
        # Check alternative header names
        api_key = (
            request.headers.get("X-API-Key") or
            request.headers.get("X-Api-Key") or  
            request.headers.get("Authorization", "").replace("ApiKey ", "") or
            None
        )
        return api_key
    
    return x_api_key


async def validate_api_key(
    request: Request,
    api_key: Optional[str] = Depends(get_api_key_from_header)
) -> dict:
    """
    Validate API key and return key information
    
    Raises HTTPException if key is invalid
    """
    if not api_key:
        logger.warning("missing_api_key", 
                      path=request.url.path,
                      client_ip=request.client.host if request.client else None)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required"
        )
    
    # Validate key
    api_key_manager = get_api_key_manager()
    key_info = api_key_manager.validate_api_key(api_key)
    
    if not key_info:
        logger.warning("invalid_api_key", 
                      key_prefix=api_key[:10] + "..." if len(api_key) > 10 else api_key,
                      path=request.url.path,
                      client_ip=request.client.host if request.client else None)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )
    
    logger.debug("api_key_validated", 
                key_id=key_info["key_id"],
                key_name=key_info["name"],
                key_type=key_info["key_type"])
    
    return key_info


async def validate_optional_api_key(
    request: Request,
    api_key: Optional[str] = Depends(get_api_key_from_header)
) -> Optional[dict]:
    """
    Validate API key if provided, return None if not provided
    
    Does not raise exception for missing key
    """
    if not api_key:
        return None
    
    try:
        return await validate_api_key(request, api_key)
    except HTTPException:
        # Invalid key provided - return None instead of raising
        return None


def require_api_key_scope(*required_scopes: str):
    """
    Dependency factory for scope-based API key validation
    
    Usage:
        @app.get("/tasks")
        async def get_tasks(
            key_info = Depends(require_api_key_scope("task:read"))
        ):
            return {"tasks": []}
    """
    
    async def scope_checker(
        request: Request,
        api_key: Optional[str] = Depends(get_api_key_from_header)
    ) -> dict:
        """Check if API key has required scopes"""
        
        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="API key required"
            )
        
        api_key_manager = get_api_key_manager()
        
        # Check each required scope
        for scope in required_scopes:
            key_info = api_key_manager.validate_api_key(api_key, required_scope=scope)
            if not key_info:
                logger.warning("api_key_insufficient_scope", 
                             key_prefix=api_key[:10] + "...",
                             required_scopes=list(required_scopes),
                             path=request.url.path)
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"API key missing required scopes: {', '.join(required_scopes)}"
                )
        
        # If we get here, all scopes are valid
        return key_info
    
    return scope_checker


def require_api_key_type(*allowed_types: str):
    """
    Dependency factory for API key type validation
    
    Usage:
        @app.post("/admin/action") 
        async def admin_action(
            key_info = Depends(require_api_key_type("admin"))
        ):
            return {"success": True}
    """
    
    async def type_checker(
        key_info: dict = Depends(validate_api_key)
    ) -> dict:
        """Check if API key is of allowed type"""
        
        if key_info["key_type"] not in allowed_types:
            logger.warning("api_key_wrong_type", 
                         key_id=key_info["key_id"],
                         actual_type=key_info["key_type"],
                         allowed_types=list(allowed_types))
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"API key type '{key_info['key_type']}' not allowed. Required: {', '.join(allowed_types)}"
            )
        
        return key_info
    
    return type_checker


# Common API key dependency combinations
ValidAPIKey = Annotated[dict, Depends(validate_api_key)]
OptionalAPIKey = Annotated[Optional[dict], Depends(validate_optional_api_key)]

# Scope-specific dependencies
RequireTaskRead = Depends(require_api_key_scope(APIKeyScope.TASK_READ.value))
RequireTaskCreate = Depends(require_api_key_scope(APIKeyScope.TASK_CREATE.value))
RequireAgentRegister = Depends(require_api_key_scope(APIKeyScope.AGENT_REGISTER.value))
RequireSystemMonitor = Depends(require_api_key_scope(APIKeyScope.SYSTEM_MONITOR.value))

# Type-specific dependencies  
RequireAdminKey = Depends(require_api_key_type("admin"))
RequireServiceKey = Depends(require_api_key_type("service", "admin"))
RequireAgentKey = Depends(require_api_key_type("agent", "admin"))


class APIKeyChecker:
    """Utility class for checking API key permissions in business logic"""
    
    @staticmethod
    def has_scope(key_info: dict, scope: str) -> bool:
        """Check if API key has specific scope"""
        return scope in key_info.get("scopes", [])
    
    @staticmethod
    def has_any_scope(key_info: dict, scopes: list[str]) -> bool:
        """Check if API key has any of the specified scopes"""
        key_scopes = set(key_info.get("scopes", []))
        return bool(key_scopes.intersection(set(scopes)))
    
    @staticmethod
    def has_all_scopes(key_info: dict, scopes: list[str]) -> bool:
        """Check if API key has all specified scopes"""
        key_scopes = set(key_info.get("scopes", []))
        return set(scopes).issubset(key_scopes)
    
    @staticmethod
    def is_type(key_info: dict, key_type: str) -> bool:
        """Check if API key is of specific type"""
        return key_info.get("key_type") == key_type
    
    @staticmethod
    def require_scope_or_raise(key_info: dict, scope: str) -> None:
        """Raise HTTPException if API key doesn't have scope"""
        if not APIKeyChecker.has_scope(key_info, scope):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"API key missing required scope: {scope}"
            )