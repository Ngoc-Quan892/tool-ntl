"""
Performance optimization utilities: query tuning, caching, batching, and monitoring.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import pickle
import re
import time
from contextlib import asynccontextmanager
from functools import wraps
from typing import Any, Callable, Dict, List, Optional

try:  # Optional Redis dependency
    import redis  # type: ignore
except ImportError:  # pragma: no cover
    redis = None  # type: ignore

import numpy as np
from sqlalchemy import event, text
from sqlalchemy.orm import Session
from sqlalchemy.pool import Pool

from app.core.config import get_settings
from app.models.database import db_manager

settings = get_settings()
logger = logging.getLogger(__name__)


class QueryOptimizer:
    """Database query optimization helpers."""

    def __init__(self, db: Session):
        self.db = db
        self.slow_query_threshold = 0.1  # 100ms
        self.query_cache: Dict[str, Any] = {}
        self.query_stats: Dict[str, Dict[str, float]] = {}

    def optimize_shoe_query(self, shoe_number: int) -> Optional[Dict[str, Any]]:
        """Fetch aggregated shoe statistics in a single query."""
        query = text(
            """
            SELECT
                shoe_number,
                COUNT(id) AS total_hands,
                SUM(CASE WHEN result = 'B' THEN 1 ELSE 0 END) AS banker_wins,
                SUM(CASE WHEN result = 'P' THEN 1 ELSE 0 END) AS player_wins,
                SUM(CASE WHEN result = 'T' THEN 1 ELSE 0 END) AS ties,
                MAX(hand_number) AS last_hand_number,
                AVG(true_count) AS avg_true_count,
                MAX(ABS(true_count)) AS max_true_count
            FROM game_results
            WHERE shoe_number = :shoe_number
            GROUP BY shoe_number
            """
        )
        start = time.time()
        row = self.db.execute(query, {"shoe_number": shoe_number}).first()
        elapsed = time.time() - start
        self._track_query_stats("optimize_shoe_query", elapsed)
        if elapsed > self.slow_query_threshold:
            logger.warning("Slow shoe query for %s (%.2fms)", shoe_number, elapsed * 1000)
        return row._asdict() if row else None

    def batch_fetch_hands(self, shoe_number: int, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """Efficiently fetch batched hands to avoid loading the full shoe."""
        query = text(
            """
            SELECT id, hand_number, result, prediction, true_count, edge, timestamp
            FROM game_results
            WHERE shoe_number = :shoe_number
            ORDER BY hand_number
            LIMIT :limit OFFSET :offset
            """
        )
        start = time.time()
        rows = self.db.execute(
            query, {"shoe_number": shoe_number, "limit": limit, "offset": offset}
        ).fetchall()
        elapsed = time.time() - start
        self._track_query_stats("batch_fetch_hands", elapsed)
        return [row._asdict() for row in rows]

    def get_game_results(self, game_id: int, limit: int = 100) -> List[Dict[str, Any]]:
        """Get game results for a specific game/shoe with optimized query."""
        query = text(
            """
            SELECT 
                id, 
                shoe_number, 
                hand_number, 
                result, 
                prediction, 
                true_count, 
                edge, 
                timestamp
            FROM game_results
            WHERE shoe_number = :game_id
            ORDER BY hand_number ASC
            LIMIT :limit
            """
        )
        start = time.time()
        rows = self.db.execute(query, {"game_id": game_id, "limit": limit}).fetchall()
        elapsed = time.time() - start
        self._track_query_stats("get_game_results", elapsed)
        if elapsed > self.slow_query_threshold:
            logger.warning("Slow game results query for game_id %s (%.2fms)", game_id, elapsed * 1000)
        return [row._asdict() for row in rows]

    def get_pattern_statistics(self, pattern_type: str, days: int = 7, limit: int = 1000, use_cache: bool = True) -> List[Dict[str, Any]]:
        """Calculate pattern statistics by pattern type for specified days."""
        cache_key = f"pattern_stats:{pattern_type}:{days}:{limit}"
        if use_cache and cache_key in self.query_cache:
            return self.query_cache[cache_key]

        # Base query for pattern statistics
        # Use PostgreSQL-compatible date arithmetic
        query = text(
            """
            WITH recent AS (
                SELECT id, shoe_number, hand_number, result
                FROM game_results
                WHERE timestamp >= CURRENT_DATE - :days
                ORDER BY timestamp DESC
                LIMIT :limit
            ), patterns AS (
                SELECT
                    shoe_number,
                    result,
                    LAG(result, 1) OVER (PARTITION BY shoe_number ORDER BY hand_number) AS prev_1,
                    LAG(result, 2) OVER (PARTITION BY shoe_number ORDER BY hand_number) AS prev_2,
                    LEAD(result, 1) OVER (PARTITION BY shoe_number ORDER BY hand_number) AS next_1
                FROM recent
            )
            SELECT
                COALESCE(prev_2, '') || '-' || COALESCE(prev_1, '') || '-' || result || '-' || COALESCE(next_1, '') AS pattern,
                COUNT(*) AS frequency
            FROM patterns
            WHERE prev_2 IS NOT NULL AND next_1 IS NOT NULL
            GROUP BY pattern
            ORDER BY frequency DESC
            LIMIT 50
            """
        )
        start = time.time()
        # PostgreSQL uses integer days for date arithmetic
        rows = self.db.execute(query, {"days": days, "limit": limit}).fetchall()
        elapsed = time.time() - start
        self._track_query_stats("get_pattern_statistics", elapsed)
        data = [row._asdict() for row in rows]
        
        # Filter by pattern_type if specified
        if pattern_type and pattern_type.lower() != "all":
            data = [p for p in data if pattern_type.lower() in p.get("pattern", "").lower()]
        
        if use_cache:
            self.query_cache[cache_key] = data
        return data

    def get_aggregated_statistics(self, days: int = 30) -> Dict[str, Any]:
        """Aggregate statistics for a rolling window."""
        query = text(
            """
            SELECT
                COUNT(*) AS total_hands,
                COUNT(DISTINCT shoe_number) AS total_shoes,
                SUM(CASE WHEN result = 'B' THEN 1 ELSE 0 END) AS banker_wins,
                SUM(CASE WHEN result = 'P' THEN 1 ELSE 0 END) AS player_wins,
                SUM(CASE WHEN result = 'T' THEN 1 ELSE 0 END) AS ties,
                AVG(true_count) AS avg_true_count,
                STDDEV(true_count) AS std_true_count
            FROM game_results
            WHERE timestamp >= CURRENT_DATE - :days
            """
        )
        start = time.time()
        row = self.db.execute(query, {"days": days}).first()
        elapsed = time.time() - start
        self._track_query_stats("get_aggregated_statistics", elapsed)
        return row._asdict() if row else {}

    def _track_query_stats(self, name: str, duration: float) -> None:
        stats = self.query_stats.setdefault(
            name,
            {"count": 0, "total": 0.0, "min": float("inf"), "max": 0.0, "slow": 0},
        )
        stats["count"] += 1
        stats["total"] += duration
        stats["min"] = min(stats["min"], duration)
        stats["max"] = max(stats["max"], duration)
        if duration > self.slow_query_threshold:
            stats["slow"] += 1

    def get_query_statistics(self) -> Dict[str, Any]:
        summary = {}
        for name, stats in self.query_stats.items():
            count = max(stats["count"], 1)
            summary[name] = {
                "count": stats["count"],
                "avg_time_ms": round(stats["total"] / count * 1000, 2),
                "min_time_ms": round(stats["min"] * 1000, 2),
                "max_time_ms": round(stats["max"] * 1000, 2),
                "slow_queries": stats["slow"],
                "slow_rate_pct": round(stats["slow"] / count * 100, 2),
            }
        return summary

    def explain_query(self, sql: str) -> str:
        """Return execution plan for a raw SQL statement."""
        plan = self.db.execute(text(f"EXPLAIN ANALYZE {sql}")).fetchall()
        return "\n".join(row[0] for row in plan)


class CacheManager:
    """Multi-layer caching (local + Redis)."""

    def __init__(self, redis_client: Optional["redis.Redis"]):
        self.redis_client = redis_client
        self.local_cache: Dict[str, Any] = {}
        self.local_cache_max_size = 1000
        self.default_ttl = 300
        self.stats = {
            "redis_hits": 0,
            "redis_misses": 0,
            "local_hits": 0,
            "local_misses": 0,
            "sets": 0,
            "deletes": 0,
        }

    def _generate_key(self, prefix: str, *args, **kwargs) -> str:
        key_parts = [prefix]
        key_parts.extend(str(arg) for arg in args)
        key_parts.extend(f"{k}:{v}" for k, v in sorted(kwargs.items()))
        raw_key = "|".join(key_parts)
        if len(raw_key) > 200:
            return f"{prefix}:{hashlib.md5(raw_key.encode()).hexdigest()}"
        return raw_key

    def _set_local(self, key: str, value: Any) -> None:
        if len(self.local_cache) >= self.local_cache_max_size:
            for k in list(self.local_cache.keys())[:100]:
                self.local_cache.pop(k, None)
        self.local_cache[key] = value

    def get(self, key: str, level: str = "l1_l2") -> Optional[Any]:
        """
        Get value from cache with tiered strategy.
        
        Args:
            key: Cache key
            level: Cache level - "l1" (memory only), "l2" (Redis only), "l1_l2" (both)
            
        Returns:
            Cached value or None
        """
        # Try L1 (memory) first if level includes L1
        if level in ("l1", "l1_l2"):
            if key in self.local_cache:
                self.stats["local_hits"] += 1
                return self.local_cache[key]
            self.stats["local_misses"] += 1
        
        # Try L2 (Redis) if level includes L2
        if level in ("l2", "l1_l2"):
            if self.redis_client is None:
                return None
            try:
                cached = self.redis_client.get(key)
                if cached:
                    self.stats["redis_hits"] += 1
                    value = pickle.loads(cached)
                    # Promote to L1 if using l1_l2 strategy
                    if level == "l1_l2":
                        self._set_local(key, value)
                    return value
            except Exception as exc:  # pragma: no cover
                logger.warning("Redis get failed: %s", exc)
            self.stats["redis_misses"] += 1
        
        return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None, level: str = "l1_l2") -> None:
        """
        Set value in cache with tiered strategy.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds
            level: Cache level - "l1" (memory only), "l2" (Redis only), "l1_l2" (both)
        """
        ttl = ttl or self.default_ttl
        
        # Set in L1 (memory) if level includes L1
        if level in ("l1", "l1_l2"):
            self._set_local(key, value)
        
        # Set in L2 (Redis) if level includes L2
        if level in ("l2", "l1_l2"):
            if self.redis_client is None:
                return
            try:
                self.redis_client.setex(key, ttl, pickle.dumps(value))
                self.stats["sets"] += 1
            except Exception as exc:  # pragma: no cover
                logger.warning("Redis set failed: %s", exc)

    def delete(self, key: str) -> None:
        self.local_cache.pop(key, None)
        if self.redis_client is None:
            return
        try:
            self.redis_client.delete(key)
            self.stats["deletes"] += 1
        except Exception as exc:
            logger.warning("Redis delete failed: %s", exc)

    def delete_pattern(self, pattern: str) -> None:
        """
        Delete all keys matching a pattern from both L1 and L2.
        
        Args:
            pattern: Pattern to match (supports wildcards for Redis)
        """
        # Delete from L1 (memory)
        deleted_l1 = 0
        for key in list(self.local_cache.keys()):
            if self._match_pattern(key, pattern):
                self.local_cache.pop(key, None)
                deleted_l1 += 1
        
        # Delete from L2 (Redis)
        if self.redis_client is not None:
            try:
                # Redis supports wildcards with scan_iter
                keys = list(self.redis_client.scan_iter(match=pattern))
                if keys:
                    self.redis_client.delete(*keys)
                    logger.debug(f"Deleted {len(keys)} keys from Redis matching pattern: {pattern}")
            except Exception as exc:
                logger.warning("Redis delete pattern failed: %s", exc)
        
        if deleted_l1 > 0:
            logger.debug(f"Deleted {deleted_l1} keys from local cache matching pattern: {pattern}")
    
    def delete_patterns(self, patterns: List[str]) -> None:
        """
        Delete all keys matching multiple patterns.
        
        Args:
            patterns: List of patterns to match
        """
        for pattern in patterns:
            self.delete_pattern(pattern)
    
    def _match_pattern(self, key: str, pattern: str) -> bool:
        """
        Simple pattern matching for local cache (supports * wildcard).
        
        Args:
            key: Cache key
            pattern: Pattern to match
            
        Returns:
            True if key matches pattern
        """
        if "*" not in pattern:
            return key == pattern
        
        # Convert pattern to regex-like matching
        regex_pattern = pattern.replace("*", ".*")
        return bool(re.match(regex_pattern, key))

    def clear_all(self) -> None:
        self.local_cache.clear()
        if self.redis_client is None:
            return
        try:
            keys = list(self.redis_client.scan_iter(match="*"))
            if keys:
                self.redis_client.delete(*keys)
        except Exception as exc:
            logger.warning("Redis clear failed: %s", exc)

    def get_stats(self) -> Dict[str, Any]:
        total_local = self.stats["local_hits"] + self.stats["local_misses"]
        total_redis = self.stats["redis_hits"] + self.stats["redis_misses"]
        return {
            "local_cache_size": len(self.local_cache),
            "local_hit_rate": round(
                (self.stats["local_hits"] / total_local * 100) if total_local else 0, 2
            ),
            "redis_hit_rate": round(
                (self.stats["redis_hits"] / total_redis * 100) if total_redis else 0, 2
            ),
            "stats": self.stats,
        }


def cached(
    ttl: int = 300,
    key_prefix: str = "cache",
    prefix: str = "cache",
    level: str = "l1_l2",
):
    """
    Decorator to cache sync/async function results via CacheManager with tiered caching.
    
    Tiered caching strategy:
    - l1: Hot data (memory only, <1 min TTL) - Very frequent access
    - l1_l2: Warm data (memory + Redis, 5-15 min TTL) - Frequent access
    - l2: Cold data (Redis only, 1+ hour TTL) - Infrequent access
    
    Args:
        ttl: Time to live in seconds
        key_prefix: Prefix for cache key (preferred parameter name)
        prefix: Alias for key_prefix (for backward compatibility)
        level: Cache level - "l1" (memory only), "l2" (Redis only), "l1_l2" (both)
    """
    # Use key_prefix if provided, otherwise fall back to prefix
    actual_prefix = key_prefix if key_prefix != "cache" else prefix

    def decorator(func: Callable):
        if asyncio.iscoroutinefunction(func):

            @wraps(func)
            async def async_wrapper(*args, cache_manager: Optional[CacheManager] = None, **kwargs):
                if cache_manager is None:
                    return await func(*args, **kwargs)
                key = cache_manager._generate_key(actual_prefix, func.__name__, *args, **kwargs)
                cached_value = cache_manager.get(key, level=level)
                if cached_value is not None:
                    return cached_value
                result = await func(*args, **kwargs)
                cache_manager.set(key, result, ttl=ttl, level=level)
                return result

            return async_wrapper

        @wraps(func)
        def sync_wrapper(*args, cache_manager: Optional[CacheManager] = None, **kwargs):
            if cache_manager is None:
                return func(*args, **kwargs)
            key = cache_manager._generate_key(actual_prefix, func.__name__, *args, **kwargs)
            cached_value = cache_manager.get(key, level=level)
            if cached_value is not None:
                return cached_value
            result = func(*args, **kwargs)
            cache_manager.set(key, result, ttl=ttl, level=level)
            return result

        return sync_wrapper

    return decorator


class ConnectionPoolManager:
    """Connection pool configuration helpers."""

    @staticmethod
    def configure_pool(engine) -> None:
        if engine is None:
            return

        @event.listens_for(Pool, "connect")
        def _(dbapi_conn, connection_record):  # pragma: no cover
            logger.debug("DB connection established (id=%s)", id(dbapi_conn))

        @event.listens_for(Pool, "checkout")
        def _(dbapi_conn, connection_record, connection_proxy):  # pragma: no cover
            cursor = dbapi_conn.cursor()
            try:
                cursor.execute("SET statement_timeout = 30000")
            finally:
                cursor.close()

    @staticmethod
    def get_pool_status(engine) -> Dict[str, Any]:
        if engine is None:
            return {}
        pool = engine.pool
        return {
            "pool_size": pool.size(),
            "checked_in": pool.checkedin(),
            "checked_out": pool.checkedout(),
            "overflow": pool.overflow(),
            "total_connections": pool.size() + pool.overflow(),
        }


class BatchProcessor:
    """Batch helpers for async workloads."""

    def __init__(self, batch_size: int = 100):
        self.batch_size = batch_size

    async def process_batch(
        self, items: List[Any], processor: Callable[[Any], Any], max_concurrency: int = 10
    ) -> List[Any]:
        semaphore = asyncio.Semaphore(max_concurrency)
        results: List[Any] = []

        async def process_item(item):
            async with semaphore:
                return await processor(item)

        for index in range(0, len(items), self.batch_size):
            batch = items[index : index + self.batch_size]
            batch_results = await asyncio.gather(
                *[process_item(item) for item in batch], return_exceptions=True
            )
            for result in batch_results:
                if isinstance(result, Exception):
                    logger.error("Batch processing error: %s", result)
                else:
                    results.append(result)
        return results

    def batch_insert(self, db: Session, model_class, rows: List[Dict[str, Any]]) -> None:
        if not rows:
            return
        try:
            db.bulk_insert_mappings(model_class, rows)
            db.commit()
        except Exception:
            db.rollback()
            raise

    def batch_update(self, db: Session, model_class, rows: List[Dict[str, Any]]) -> None:
        if not rows:
            return
        try:
            db.bulk_update_mappings(model_class, rows)
            db.commit()
        except Exception:
            db.rollback()
            raise


class PerformanceMonitor:
    """Light-weight performance metric recorder with context manager support."""

    def __init__(self, operation_name: Optional[str] = None):
        self.operation_name = operation_name
        self.start_time: Optional[float] = None
        self.metrics = {
            "request_count": 0,
            "total_response_time": 0.0,
            "slow_requests": 0,
            "errors": 0,
        }
        self.slow_request_threshold = 1.0
        self._operation_metrics: Dict[str, List[float]] = {}

    def __enter__(self):
        """Context manager entry - start timing."""
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - record timing."""
        if self.start_time is not None:
            elapsed = time.time() - self.start_time
            self.record_request(elapsed, is_error=(exc_type is not None))
            if self.operation_name:
                if self.operation_name not in self._operation_metrics:
                    self._operation_metrics[self.operation_name] = []
                self._operation_metrics[self.operation_name].append(elapsed)
                if elapsed > self.slow_request_threshold:
                    logger.warning(
                        "Slow operation '%s' took %.2fms",
                        self.operation_name,
                        elapsed * 1000,
                    )
        return False  # Don't suppress exceptions

    def record_request(self, response_time: float, is_error: bool = False) -> None:
        self.metrics["request_count"] += 1
        self.metrics["total_response_time"] += response_time
        if response_time > self.slow_request_threshold:
            self.metrics["slow_requests"] += 1
        if is_error:
            self.metrics["errors"] += 1

    def get_metrics(self) -> Dict[str, Any]:
        count = self.metrics["request_count"]
        avg = (self.metrics["total_response_time"] / count) if count else 0
        error_rate = (self.metrics["errors"] / count * 100) if count else 0
        slow_rate = (self.metrics["slow_requests"] / count * 100) if count else 0
        
        # Add operation-specific metrics
        operation_stats = {}
        for op_name, times in self._operation_metrics.items():
            if times:
                operation_stats[op_name] = {
                    "count": len(times),
                    "avg_ms": round(sum(times) / len(times) * 1000, 2),
                    "min_ms": round(min(times) * 1000, 2),
                    "max_ms": round(max(times) * 1000, 2),
                }
        
        return {
            "total_requests": count,
            "avg_response_time_ms": round(avg * 1000, 2),
            "error_rate": round(error_rate, 2),
            "slow_request_rate": round(slow_rate, 2),
            "slow_requests": self.metrics["slow_requests"],
            "operations": operation_stats,
        }

    def reset(self) -> None:
        self.metrics = {
            "request_count": 0,
            "total_response_time": 0.0,
            "slow_requests": 0,
            "errors": 0,
        }
        self._operation_metrics.clear()


_cache_manager: Optional[CacheManager] = None
_performance_monitor = PerformanceMonitor()


def _new_redis_client() -> Optional["redis.Redis"]:
    """Create a new Redis client from settings. Internal function."""
    if redis is None:
        return None
    try:
        return redis.from_url(settings.REDIS_URL, decode_responses=False)
    except Exception as exc:  # pragma: no cover
        logger.warning("Redis unavailable: %s", exc)
        return None


def new_redis_client() -> Optional["redis.Redis"]:
    """
    Create a new Redis client from settings.
    
    Public function for creating Redis clients.
    """
    return _new_redis_client()


def get_cache_manager(redis_client: Optional["redis.Redis"] = None) -> CacheManager:
    global _cache_manager
    if _cache_manager is None:
        client = redis_client or _new_redis_client()
        _cache_manager = CacheManager(client)
    return _cache_manager


def get_performance_monitor() -> PerformanceMonitor:
    return _performance_monitor


class OptimizationStack:
    """
    Centralized optimization stack combining query optimization, caching, and monitoring.
    
    This class provides a unified interface for:
    - Query optimization with QueryOptimizer
    - Multi-layer caching (L1 memory + L2 Redis)
    - Performance monitoring
    - Batch processing
    """

    def __init__(
        self,
        db_connection: Any,
        redis_client: Optional["redis.Redis"] = None,
        cache_ttl: int = 300,
    ):
        """
        Initialize OptimizationStack.
        
        Args:
            db_connection: Database connection pool or session factory (db_manager)
            redis_client: Optional Redis client for L2 cache
            cache_ttl: Default cache TTL in seconds
        """
        self.db_connection = db_connection
        self.redis_client = redis_client
        self.cache_ttl = cache_ttl
        
        # Initialize components
        self.cache_manager = CacheManager(redis_client)
        self.performance_monitor = PerformanceMonitor()
        self.batch_processor = BatchProcessor()

    def get_query_optimizer(self, session: Session) -> QueryOptimizer:
        """
        Get QueryOptimizer with a specific session.
        
        Args:
            session: SQLAlchemy session (typically from dependency injection)
            
        Returns:
            QueryOptimizer instance configured with the session
        """
        return QueryOptimizer(session)

    def get_cache_manager(self) -> CacheManager:
        """Get CacheManager instance."""
        return self.cache_manager

    def get_performance_monitor(self) -> PerformanceMonitor:
        """Get PerformanceMonitor instance."""
        return self.performance_monitor

    def get_batch_processor(self) -> BatchProcessor:
        """Get BatchProcessor instance."""
        return self.batch_processor

