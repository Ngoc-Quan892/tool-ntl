"""
Redis caching service with decorators and invalidation strategies.

Features:
- Connection pooling
- Cache decorators for functions
- Invalidation strategies
- TTL management
- Cache statistics
"""
from __future__ import annotations

import asyncio
import functools
import hashlib
import json
import logging
from typing import Any, Callable, Dict, Optional, TypeVar, Union

import redis.asyncio as aioredis
from redis.exceptions import ConnectionError, RedisError

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Type variable for function return types
F = TypeVar("F", bound=Callable[..., Any])


class CacheManager:
    """
    Redis cache manager with connection pooling and utilities.
    """

    def __init__(self, redis_url: Optional[str] = None):
        """
        Initialize cache manager.

        Args:
            redis_url: Redis connection URL. If None, uses settings.REDIS_URL
        """
        self.redis_url = redis_url or settings.REDIS_URL
        self.client: Optional[aioredis.Redis] = None
        self._connection_pool: Optional[aioredis.ConnectionPool] = None
        self._is_connected = False

    async def connect(self) -> None:
        """Connect to Redis."""
        try:
            self._connection_pool = aioredis.ConnectionPool.from_url(
                self.redis_url,
                max_connections=settings.REDIS_MAX_CONNECTIONS,
                decode_responses=True,
            )
            self.client = aioredis.Redis(connection_pool=self._connection_pool)
            
            # Test connection
            await self.client.ping()
            self._is_connected = True
            logger.info(f"Redis connected: {self.redis_url.split('@')[-1] if '@' in self.redis_url else self.redis_url}")
        except (ConnectionError, RedisError) as e:
            logger.warning(f"Redis connection failed: {e}. Cache will be disabled.")
            self._is_connected = False
            self.client = None

    async def disconnect(self) -> None:
        """Disconnect from Redis."""
        if self.client:
            await self.client.close()
            self.client = None
        if self._connection_pool:
            await self._connection_pool.disconnect()
            self._connection_pool = None
        self._is_connected = False
        logger.info("Redis disconnected")

    async def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found
        """
        if not self._is_connected or not self.client:
            return None

        try:
            value = await self.client.get(key)
            if value is None:
                return None
            
            # Try to deserialize JSON
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value
        except (ConnectionError, RedisError) as e:
            logger.warning(f"Redis get error for key {key}: {e}")
            return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
    ) -> bool:
        """
        Set value in cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds (uses default if None)

        Returns:
            True if successful, False otherwise
        """
        if not self._is_connected or not self.client:
            return False

        try:
            # Serialize value
            if isinstance(value, (dict, list)):
                serialized = json.dumps(value)
            else:
                serialized = str(value)

            ttl = ttl or settings.REDIS_CACHE_TTL
            await self.client.setex(key, ttl, serialized)
            return True
        except (ConnectionError, RedisError) as e:
            logger.warning(f"Redis set error for key {key}: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """
        Delete key from cache.

        Args:
            key: Cache key

        Returns:
            True if successful, False otherwise
        """
        if not self._is_connected or not self.client:
            return False

        try:
            await self.client.delete(key)
            return True
        except (ConnectionError, RedisError) as e:
            logger.warning(f"Redis delete error for key {key}: {e}")
            return False

    async def delete_pattern(self, pattern: str) -> int:
        """
        Delete all keys matching pattern.

        Args:
            pattern: Key pattern (e.g., "user:*")

        Returns:
            Number of keys deleted
        """
        if not self._is_connected or not self.client:
            return 0

        try:
            keys = []
            async for key in self.client.scan_iter(match=pattern):
                keys.append(key)
            
            if keys:
                return await self.client.delete(*keys)
            return 0
        except (ConnectionError, RedisError) as e:
            logger.warning(f"Redis delete_pattern error for pattern {pattern}: {e}")
            return 0

    async def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        if not self._is_connected or not self.client:
            return False

        try:
            return await self.client.exists(key) > 0
        except (ConnectionError, RedisError):
            return False

    async def get_or_set(
        self,
        key: str,
        callable: Callable[[], Any],
        ttl: Optional[int] = None,
    ) -> Any:
        """
        Get value from cache or compute and set it.

        Args:
            key: Cache key
            callable: Function to compute value if not cached
            ttl: Time to live in seconds

        Returns:
            Cached or computed value
        """
        value = await self.get(key)
        if value is not None:
            return value

        # Compute value
        if asyncio.iscoroutinefunction(callable):
            value = await callable()
        else:
            value = callable()

        # Cache it
        await self.set(key, value, ttl)
        return value

    async def invalidate(self, pattern: str) -> int:
        """
        Invalidate cache by pattern.

        Args:
            pattern: Key pattern to invalidate

        Returns:
            Number of keys invalidated
        """
        return await self.delete_pattern(pattern)

    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        if not self._is_connected or not self.client:
            return {
                "connected": False,
                "keys": 0,
                "memory_usage": 0,
            }

        try:
            info = await self.client.info("stats")
            memory = await self.client.info("memory")
            
            return {
                "connected": True,
                "keys": await self.client.dbsize(),
                "memory_usage": memory.get("used_memory_human", "0B"),
                "hits": info.get("keyspace_hits", 0),
                "misses": info.get("keyspace_misses", 0),
            }
        except (ConnectionError, RedisError) as e:
            logger.warning(f"Redis stats error: {e}")
            return {"connected": False, "error": str(e)}


# Global cache manager instance
cache_manager = CacheManager()


def cache_key(*args, **kwargs) -> str:
    """
    Generate cache key from function arguments.

    Args:
        *args: Positional arguments
        **kwargs: Keyword arguments

    Returns:
        Cache key string
    """
    # Create a hash from arguments
    key_data = json.dumps({"args": args, "kwargs": kwargs}, sort_keys=True)
    return hashlib.md5(key_data.encode()).hexdigest()


def cached(
    ttl: Optional[int] = None,
    key_prefix: str = "",
    invalidate_on: Optional[list] = None,
) -> Callable[[F], F]:
    """
    Decorator to cache function results.

    Args:
        ttl: Time to live in seconds (uses default if None)
        key_prefix: Prefix for cache keys
        invalidate_on: List of patterns to invalidate when function is called

    Example:
        @cached(ttl=300, key_prefix="predictions")
        async def get_prediction():
            return compute_prediction()
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Generate cache key
            cache_key_str = f"{key_prefix}:{func.__name__}:{cache_key(*args, **kwargs)}"
            
            # Try to get from cache
            cached_value = await cache_manager.get(cache_key_str)
            if cached_value is not None:
                logger.debug(f"Cache hit: {cache_key_str}")
                return cached_value
            
            # Compute value
            logger.debug(f"Cache miss: {cache_key_str}")
            result = await func(*args, **kwargs)
            
            # Cache result
            await cache_manager.set(cache_key_str, result, ttl)
            
            # Invalidate related caches if specified
            if invalidate_on:
                for pattern in invalidate_on:
                    await cache_manager.invalidate(pattern)
            
            return result

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            # For sync functions, we need to run in event loop
            import asyncio
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            cache_key_str = f"{key_prefix}:{func.__name__}:{cache_key(*args, **kwargs)}"
            
            # Try to get from cache (sync)
            if loop.is_running():
                # If loop is running, we can't use sync get
                # Just call function directly
                return func(*args, **kwargs)
            else:
                cached_value = loop.run_until_complete(cache_manager.get(cache_key_str))
                if cached_value is not None:
                    return cached_value
                
                result = func(*args, **kwargs)
                loop.run_until_complete(cache_manager.set(cache_key_str, result, ttl))
                return result

        if asyncio.iscoroutinefunction(func):
            return async_wrapper  # type: ignore
        else:
            return sync_wrapper  # type: ignore

    return decorator



