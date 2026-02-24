"""
Admin endpoints for token and cache management
"""
from typing import Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, status

from ..config import get_settings
from ..logging import get_logger
from ..auth.dependencies import CurrentAdmin
from ..auth.redis_cache import get_redis_cache

logger = get_logger(__name__)
settings = get_settings()

router = APIRouter(prefix="/v1/admin", tags=["admin"])


@router.get("/cache/stats")
async def get_cache_stats(current_admin: CurrentAdmin) -> Dict[str, Any]:
    """
    Get Redis cache statistics (admin only)
    """
    logger.info("cache_stats_requested", admin_id=current_admin.agent_id)
    
    try:
        redis_cache = await get_redis_cache()
        stats = await redis_cache.get_cache_stats()
        
        return {
            "success": True,
            "stats": stats,
            "requested_by": current_admin.agent_name
        }
    
    except Exception as e:
        logger.error("cache_stats_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve cache stats"
        )


@router.post("/cache/cleanup")
async def cleanup_cache(current_admin: CurrentAdmin) -> Dict[str, Any]:
    """
    Clean up expired tokens and cache entries (admin only)
    """
    logger.info("cache_cleanup_requested", admin_id=current_admin.agent_id)
    
    try:
        redis_cache = await get_redis_cache()
        cleaned_count = await redis_cache.cleanup_expired_tokens()
        
        return {
            "success": True,
            "cleaned_count": cleaned_count,
            "message": f"Cleaned up {cleaned_count} expired entries",
            "cleaned_by": current_admin.agent_name
        }
    
    except Exception as e:
        logger.error("cache_cleanup_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Cache cleanup failed"
        )


@router.post("/tokens/revoke-user")
async def revoke_user_tokens(
    agent_id: str,
    current_admin: CurrentAdmin
) -> Dict[str, Any]:
    """
    Revoke all tokens for a specific user (admin only)
    """
    logger.info("user_tokens_revocation_requested", 
               target_agent_id=agent_id,
               admin_id=current_admin.agent_id)
    
    try:
        redis_cache = await get_redis_cache()
        revoked_count = await redis_cache.blacklist_user_tokens(
            agent_id=agent_id,
            reason="admin_revocation",
            blacklisted_by=current_admin.agent_id
        )
        
        return {
            "success": True,
            "agent_id": agent_id,
            "revoked_count": revoked_count,
            "message": f"Revoked {revoked_count} tokens for agent {agent_id}",
            "revoked_by": current_admin.agent_name
        }
    
    except Exception as e:
        logger.error("user_tokens_revocation_failed", 
                    target_agent_id=agent_id,
                    error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token revocation failed"
        )