"""
Redis-based token caching and blacklist system for OpenHub
"""
import json
import asyncio
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List, Set
import redis.asyncio as redis
from redis.exceptions import RedisError, ConnectionError

from ..config import get_settings
from ..logging import get_logger
from .jwt_auth import jwt_manager

logger = get_logger(__name__)
settings = get_settings()


class RedisTokenCache:
    """Clean and efficient Redis-based token management"""
    
    def __init__(self, redis_url: Optional[str] = None):
        self.redis_url = redis_url or settings.redis_url
        self.token_prefix = settings.redis_token_prefix
        self.blacklist_prefix = settings.redis_blacklist_prefix
        self._redis: Optional[redis.Redis] = None
        
        # Cache TTL settings
        self.access_token_ttl = settings.jwt_access_token_expire_minutes * 60
        self.refresh_token_ttl = settings.jwt_refresh_token_expire_days * 24 * 60 * 60
        self.blacklist_ttl = self.refresh_token_ttl  # Keep blacklist longer than longest token
        
        logger.info("redis_token_cache_initialized", redis_url=self.redis_url)
    
    async def _get_redis(self) -> redis.Redis:
        """Get or create Redis connection (async)"""
        
        if self._redis is None:
            try:
                self._redis = redis.from_url(
                    self.redis_url,
                    encoding="utf-8",
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_timeout=5,
                    retry_on_timeout=True,
                    health_check_interval=30
                )
                
                # Test connection
                await self._redis.ping()
                
                logger.info("redis_connection_established")
                
            except Exception as e:
                logger.error("redis_connection_failed", error=str(e))
                raise
        
        return self._redis
    
    def _get_token_key(self, token_id: str) -> str:
        """Generate Redis key for token storage"""
        return f"{self.token_prefix}{token_id}"
    
    def _get_blacklist_key(self, token_id: str) -> str:
        """Generate Redis key for blacklist storage"""
        return f"{self.blacklist_prefix}{token_id}"
    
    def _get_user_tokens_key(self, agent_id: str) -> str:
        """Generate Redis key for user's token list"""
        return f"{self.token_prefix}user:{agent_id}"
    
    def _extract_token_id(self, token: str) -> Optional[str]:
        """Extract unique identifier from token"""
        try:
            payload = jwt_manager.decode_token_without_verification(token)
            # Use combination of sub + iat for uniqueness
            sub = payload.get("sub")
            iat = payload.get("iat")
            if sub and iat:
                return f"{sub}:{iat}"
            return None
        except Exception:
            return None
    
    async def cache_token(
        self,
        token: str,
        token_type: str,
        agent_id: str,
        additional_data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Cache token in Redis with metadata
        
        Args:
            token: JWT token string
            token_type: "access" or "refresh"
            agent_id: Agent ID who owns the token
            additional_data: Extra metadata to store
            
        Returns:
            True if cached successfully
        """
        
        try:
            redis_client = await self._get_redis()
            token_id = self._extract_token_id(token)
            
            if not token_id:
                logger.warning("token_cache_failed_invalid_id", token_preview=token[:20] + "...")
                return False
            
            # Prepare token metadata
            token_data = {
                "token_type": token_type,
                "agent_id": agent_id,
                "cached_at": datetime.now(timezone.utc).isoformat(),
                "token_hash": self._hash_token(token),  # Store hash, not full token
                **(additional_data or {})
            }
            
            # Determine TTL
            ttl = self.access_token_ttl if token_type == "access" else self.refresh_token_ttl
            
            # Cache token data
            token_key = self._get_token_key(token_id)
            await redis_client.setex(token_key, ttl, json.dumps(token_data))
            
            # Add to user's token set
            user_tokens_key = self._get_user_tokens_key(agent_id)
            await redis_client.sadd(user_tokens_key, token_id)
            await redis_client.expire(user_tokens_key, ttl)
            
            logger.debug("token_cached", 
                        token_id=token_id,
                        token_type=token_type,
                        agent_id=agent_id,
                        ttl=ttl)
            
            return True
        
        except Exception as e:
            logger.error("token_cache_failed", 
                        token_type=token_type,
                        agent_id=agent_id,
                        error=str(e))
            return False
    
    async def get_token_data(self, token: str) -> Optional[Dict[str, Any]]:
        """Get cached token data"""
        
        try:
            redis_client = await self._get_redis()
            token_id = self._extract_token_id(token)
            
            if not token_id:
                return None
            
            token_key = self._get_token_key(token_id)
            cached_data = await redis_client.get(token_key)
            
            if cached_data:
                token_data = json.loads(cached_data)
                
                # Verify token hash matches (security check)
                if self._verify_token_hash(token, token_data.get("token_hash")):
                    logger.debug("token_data_retrieved", token_id=token_id)
                    return token_data
                else:
                    logger.warning("token_hash_mismatch", token_id=token_id)
                    await self._invalidate_token(token_id)
                    return None
            
            return None
        
        except Exception as e:
            logger.error("token_data_retrieval_failed", error=str(e))
            return None
    
    async def is_token_blacklisted(self, token: str) -> bool:
        """Check if token is in blacklist"""
        
        try:
            redis_client = await self._get_redis()
            token_id = self._extract_token_id(token)
            
            if not token_id:
                return False
            
            blacklist_key = self._get_blacklist_key(token_id)
            exists = await redis_client.exists(blacklist_key)
            
            if exists:
                logger.debug("token_blacklist_hit", token_id=token_id)
                return True
            
            return False
        
        except Exception as e:
            logger.error("blacklist_check_failed", error=str(e))
            # Fail closed - consider token blacklisted on error
            return True
    
    async def blacklist_token(
        self,
        token: str,
        reason: str = "logout",
        blacklisted_by: Optional[str] = None
    ) -> bool:
        """Add token to blacklist"""
        
        try:
            redis_client = await self._get_redis()
            token_id = self._extract_token_id(token)
            
            if not token_id:
                logger.warning("token_blacklist_failed_invalid_id")
                return False
            
            # Prepare blacklist entry
            blacklist_data = {
                "reason": reason,
                "blacklisted_at": datetime.now(timezone.utc).isoformat(),
                "blacklisted_by": blacklisted_by,
                "token_hash": self._hash_token(token)
            }
            
            # Add to blacklist
            blacklist_key = self._get_blacklist_key(token_id)
            await redis_client.setex(blacklist_key, self.blacklist_ttl, json.dumps(blacklist_data))
            
            # Remove from token cache
            await self._invalidate_token(token_id)
            
            logger.info("token_blacklisted", 
                       token_id=token_id,
                       reason=reason,
                       blacklisted_by=blacklisted_by)
            
            return True
        
        except Exception as e:
            logger.error("token_blacklist_failed", 
                        reason=reason,
                        error=str(e))
            return False
    
    async def blacklist_user_tokens(
        self,
        agent_id: str,
        reason: str = "force_logout",
        blacklisted_by: Optional[str] = None
    ) -> int:
        """Blacklist all tokens for a specific user"""
        
        try:
            redis_client = await self._get_redis()
            user_tokens_key = self._get_user_tokens_key(agent_id)
            
            # Get all token IDs for user
            token_ids = await redis_client.smembers(user_tokens_key)
            
            if not token_ids:
                logger.info("no_tokens_found_for_user", agent_id=agent_id)
                return 0
            
            blacklisted_count = 0
            
            # Blacklist each token
            for token_id in token_ids:
                blacklist_data = {
                    "reason": reason,
                    "blacklisted_at": datetime.now(timezone.utc).isoformat(),
                    "blacklisted_by": blacklisted_by,
                    "agent_id": agent_id
                }
                
                blacklist_key = self._get_blacklist_key(token_id)
                await redis_client.setex(blacklist_key, self.blacklist_ttl, json.dumps(blacklist_data))
                
                # Remove from token cache
                await self._invalidate_token(token_id)
                blacklisted_count += 1
            
            # Clear user's token set
            await redis_client.delete(user_tokens_key)
            
            logger.info("user_tokens_blacklisted", 
                       agent_id=agent_id,
                       count=blacklisted_count,
                       reason=reason)
            
            return blacklisted_count
        
        except Exception as e:
            logger.error("user_tokens_blacklist_failed", 
                        agent_id=agent_id,
                        error=str(e))
            return 0
    
    async def _invalidate_token(self, token_id: str) -> None:
        """Remove token from cache"""
        
        try:
            redis_client = await self._get_redis()
            token_key = self._get_token_key(token_id)
            await redis_client.delete(token_key)
            
            logger.debug("token_invalidated", token_id=token_id)
        
        except Exception as e:
            logger.error("token_invalidation_failed", 
                        token_id=token_id,
                        error=str(e))
    
    def _hash_token(self, token: str) -> str:
        """Hash token for secure storage"""
        import hashlib
        return hashlib.sha256((token + settings.jwt_secret_key).encode()).hexdigest()
    
    def _verify_token_hash(self, token: str, stored_hash: Optional[str]) -> bool:
        """Verify token against stored hash"""
        if not stored_hash:
            return False
        return self._hash_token(token) == stored_hash
    
    async def cleanup_expired_tokens(self) -> int:
        """Clean up expired tokens and blacklist entries"""
        
        try:
            redis_client = await self._get_redis()
            cleaned_count = 0
            
            # Redis automatically handles TTL cleanup, but we can manually clean
            # any orphaned entries or perform additional cleanup
            
            # Get all token keys
            token_pattern = f"{self.token_prefix}*"
            token_keys = []
            
            async for key in redis_client.scan_iter(match=token_pattern, count=100):
                token_keys.append(key)
            
            # Check each key and remove if expired
            for key in token_keys:
                ttl = await redis_client.ttl(key)
                if ttl == -2:  # Key doesn't exist
                    cleaned_count += 1
                elif ttl == -1:  # Key exists but no TTL set
                    # Set appropriate TTL
                    await redis_client.expire(key, self.access_token_ttl)
            
            if cleaned_count > 0:
                logger.info("token_cleanup_completed", cleaned_count=cleaned_count)
            
            return cleaned_count
        
        except Exception as e:
            logger.error("token_cleanup_failed", error=str(e))
            return 0
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get Redis cache statistics"""
        
        try:
            redis_client = await self._get_redis()
            
            # Count tokens and blacklist entries
            token_pattern = f"{self.token_prefix}*"
            blacklist_pattern = f"{self.blacklist_prefix}*"
            
            token_count = 0
            blacklist_count = 0
            
            async for _ in redis_client.scan_iter(match=token_pattern, count=100):
                token_count += 1
            
            async for _ in redis_client.scan_iter(match=blacklist_pattern, count=100):
                blacklist_count += 1
            
            # Redis info
            info = await redis_client.info()
            
            stats = {
                "connected": True,
                "cached_tokens": token_count,
                "blacklisted_tokens": blacklist_count,
                "redis_memory_used": info.get("used_memory_human", "unknown"),
                "redis_connected_clients": info.get("connected_clients", 0),
                "redis_uptime": info.get("uptime_in_seconds", 0),
                "cache_hit_rate": "N/A"  # Would need separate tracking
            }
            
            return stats
        
        except Exception as e:
            logger.error("cache_stats_failed", error=str(e))
            return {"connected": False, "error": str(e)}
    
    async def close(self) -> None:
        """Close Redis connection"""
        
        if self._redis:
            await self._redis.close()
            self._redis = None
            logger.info("redis_connection_closed")


# Global Redis cache instance
_redis_cache: Optional[RedisTokenCache] = None


async def get_redis_cache() -> RedisTokenCache:
    """Get global Redis cache instance"""
    
    global _redis_cache
    
    if _redis_cache is None:
        _redis_cache = RedisTokenCache()
        logger.info("global_redis_cache_initialized")
    
    return _redis_cache


async def close_redis_cache() -> None:
    """Close global Redis cache"""
    
    global _redis_cache
    
    if _redis_cache:
        await _redis_cache.close()
        _redis_cache = None
        logger.info("global_redis_cache_closed")