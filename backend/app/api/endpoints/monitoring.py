"""
Monitoring API endpoints for real-time performance metrics and health checks.

This module provides:
- Real-time performance metrics endpoint
- Comprehensive health check endpoint
- System resource monitoring
- Cache and query statistics
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.v2.base import get_database_session
from app.models.database import db_manager
from app.services.performance_optimizer import (
    OptimizationStack,
    ConnectionPoolManager,
)
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(prefix="/monitoring", tags=["monitoring"])

# Global optimizer instance (will be set from app.state)
_optimizer: Optional[OptimizationStack] = None


def get_optimizer(request: Request) -> OptimizationStack:
    """
    Get OptimizationStack instance from app state or create fallback.
    
    Prefers optimizer from app.state (initialized at startup),
    falls back to lazy initialization if not available.
    """
    global _optimizer
    
    # Try to get from app state first (preferred)
    if hasattr(request.app.state, "optimizer"):
        return request.app.state.optimizer
    
    # Fallback to lazy initialization
    if _optimizer is None:
        from app.services.performance_optimizer import OptimizationStack, new_redis_client
        
        redis_client = new_redis_client()
        _optimizer = OptimizationStack(
            db_connection=db_manager,
            redis_client=redis_client,
            cache_ttl=settings.REDIS_CACHE_TTL or 300,
        )
        logger.info("OptimizationStack initialized (lazy initialization)")
    return _optimizer


def get_system_resources() -> Dict[str, Any]:
    """
    Get system resource usage (CPU, memory).
    
    Returns:
        Dictionary with CPU and memory information
    """
    try:
        import psutil
        
        process = psutil.Process()
        memory_info = process.memory_info()
        
        return {
            "cpu_percent": process.cpu_percent(interval=0.1),
            "memory_mb": round(memory_info.rss / 1024 / 1024, 2),
            "memory_percent": round(process.memory_percent(), 2),
            "threads": process.num_threads(),
            "open_files": len(process.open_files()),
        }
    except ImportError:
        # psutil not available, return basic info
        try:
            import resource
            memory_usage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            return {
                "cpu_percent": None,
                "memory_mb": round(memory_usage / 1024, 2) if hasattr(resource, "RUSAGE_SELF") else None,
                "memory_percent": None,
                "threads": None,
                "open_files": None,
                "note": "psutil not installed, limited metrics available",
            }
        except Exception:
            return {
                "cpu_percent": None,
                "memory_mb": None,
                "memory_percent": None,
                "threads": None,
                "open_files": None,
                "note": "System resource monitoring unavailable",
            }
    except Exception as exc:
        logger.warning(f"Failed to get system resources: {exc}")
        return {
            "error": str(exc),
        }


@router.get("/metrics")
async def get_performance_metrics(
    request: Request,
    db: Session = Depends(get_database_session),
) -> Dict[str, Any]:
    """
    Return comprehensive performance metrics.
    
    Real-time metrics endpoint that exposes all performance data.
    Updates every request (real-time data, not cached).
    Use for debugging and performance monitoring.
    
    Returns:
        {
            "cache": {
                "hit_rate": 0.85,
                "size_mb": 120.5,
                "evictions": 42
            },
            "queries": {
                "avg_time_ms": 45.2,
                "slow_queries": 3,
                "total_queries": 10000
            },
            "connections": {
                "active": 8,
                "idle": 12,
                "max_wait_ms": 15
            },
            "system": {
                "cpu_percent": 25.5,
                "memory_mb": 256.8
            }
        }
    """
    optimizer = get_optimizer(request)
    
    try:
        # Get cache statistics
        cache_manager = optimizer.get_cache_manager()
        cache_stats = cache_manager.get_stats()
        
        # Calculate cache hit rate
        local_hits = cache_stats.get("stats", {}).get("local_hits", 0)
        local_misses = cache_stats.get("stats", {}).get("local_misses", 0)
        redis_hits = cache_stats.get("stats", {}).get("redis_hits", 0)
        redis_misses = cache_stats.get("stats", {}).get("redis_misses", 0)
        
        total_hits = local_hits + redis_hits
        total_misses = local_misses + redis_misses
        total_requests = total_hits + total_misses
        
        # Calculate hit rate (derived metric)
        cache_hit_rate = (total_hits / total_requests * 100) if total_requests > 0 else 0.0
        
        # Estimate cache size (rough calculation in MB)
        local_cache_size = cache_stats.get("local_cache_size", 0)
        # Rough estimate: assume average 1KB per cache entry
        cache_size_mb = (local_cache_size * 0.001) if local_cache_size > 0 else 0.0
        
        # Get query statistics
        query_optimizer = optimizer.get_query_optimizer(db)
        query_stats = query_optimizer.get_query_statistics()
        
        # Calculate average query time across all queries
        total_queries = 0
        total_time_ms = 0.0
        slow_queries_list: List[Dict[str, Any]] = []
        
        for query_name, stats in query_stats.items():
            count = stats.get("count", 0)
            avg_time = stats.get("avg_time_ms", 0)
            total_queries += count
            total_time_ms += avg_time * count
            
            # Identify slow queries (>100ms)
            if avg_time > 100:
                slow_queries_list.append({
                    "query": query_name,
                    "avg_time_ms": round(avg_time, 2),
                    "count": count,
                    "slow_queries": stats.get("slow_queries", 0),
                })
        
        avg_query_time_ms = (total_time_ms / total_queries) if total_queries > 0 else 0.0
        
        # Get connection pool status
        connection_pool_info: Dict[str, Any] = {}
        max_wait_ms = 0  # Not directly tracked, could be added in future
        try:
            if hasattr(db_manager, "engine") and db_manager.engine:
                pool_status = ConnectionPoolManager.get_pool_status(db_manager.engine)
                connection_pool_info = {
                    "active": pool_status.get("checked_out", 0),
                    "idle": pool_status.get("checked_in", 0),
                    "total": pool_status.get("total_connections", 0),
                    "pool_size": pool_status.get("pool_size", 0),
                    "overflow": pool_status.get("overflow", 0),
                }
        except Exception as exc:
            logger.warning(f"Failed to get connection pool status: {exc}")
            connection_pool_info = {"error": str(exc)}
        
        # Get system resources
        system_resources = get_system_resources()
        
        # Compile comprehensive metrics
        metrics = {
            "cache": {
                "hit_rate": round(cache_hit_rate, 2),
                "size_mb": round(cache_size_mb, 2),
                "hits": total_hits,
                "misses": total_misses,
                "evictions": 0,  # Not tracked currently, could add eviction tracking
            },
            "queries": {
                "avg_time_ms": round(avg_query_time_ms, 2),
                "slow_queries": len(slow_queries_list),
                "total_queries": total_queries,
                "slow_queries_list": slow_queries_list,
            },
            "connections": {
                "active": connection_pool_info.get("active", 0),
                "idle": connection_pool_info.get("idle", 0),
                "max_wait_ms": max_wait_ms,
            },
            "system": system_resources,
            "timestamp": time.time(),
        }
        
        return metrics
        
    except Exception as exc:
        logger.error(f"Error getting performance metrics: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve metrics: {str(exc)}",
        )


@router.get("/health")
async def health_check(
    request: Request,
    db: Session = Depends(get_database_session),
) -> Dict[str, Any]:
    """
    Component health check endpoint.
    
    Quick check for all components:
    - MySQL/PostgreSQL: Can execute query?
    - Redis: Can ping?
    - Cache: Within memory limit?
    
    Returns 200 if healthy, 503 if not.
    Use for load balancer health checks.
    
    Returns:
        Health status dictionary with status code
    """
    optimizer = get_optimizer(request)
    health_status = "healthy"
    issues: List[str] = []
    
    # Check MySQL/PostgreSQL
    db_healthy = False
    try:
        # Try to execute a simple query
        db.execute(text("SELECT 1"))
        db.commit()
        db_healthy = True
    except Exception as exc:
        db_healthy = False
        health_status = "unhealthy"
        issues.append(f"Database error: {str(exc)}")
        logger.error(f"Database health check failed: {exc}")
    
    # Check Redis
    redis_healthy = False
    try:
        cache_manager = optimizer.get_cache_manager()
        if cache_manager.redis_client:
            # Try to ping Redis
            cache_manager.redis_client.ping()
            redis_healthy = True
        else:
            redis_healthy = False
            if health_status == "healthy":
                health_status = "degraded"
            issues.append("Redis client not available")
    except Exception as exc:
        redis_healthy = False
        if health_status == "healthy":
            health_status = "degraded"
        issues.append(f"Redis error: {str(exc)}")
        logger.warning(f"Redis health check failed: {exc}")
    
    # Check cache memory
    cache_healthy = True
    try:
        cache_manager = optimizer.get_cache_manager()
        cache_stats = cache_manager.get_stats()
        cache_size_mb = cache_stats.get("local_cache_size", 0) * 0.001  # Rough estimate
        
        # Check if cache is within limit (500MB)
        cache_limit_mb = 500
        if cache_size_mb > cache_limit_mb:
            cache_healthy = False
            if health_status == "healthy":
                health_status = "degraded"
            issues.append(f"Cache size ({cache_size_mb:.2f}MB) exceeds limit ({cache_limit_mb}MB)")
    except Exception as exc:
        cache_healthy = False
        if health_status == "healthy":
            health_status = "degraded"
        issues.append(f"Cache check error: {str(exc)}")
        logger.warning(f"Cache health check failed: {exc}")
    
    # Compile health response
    response_data: Dict[str, Any] = {
        "status": health_status,
        "database": "healthy" if db_healthy else "unhealthy",
        "redis": "healthy" if redis_healthy else ("degraded" if cache_manager.redis_client is None else "unhealthy"),
        "cache": "healthy" if cache_healthy else "degraded",
    }
    
    if issues:
        response_data["issues"] = issues
    
    # Return appropriate status code
    # Return 503 if unhealthy, 200 otherwise
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE if health_status == "unhealthy" else status.HTTP_200_OK
    
    return JSONResponse(
        content=response_data,
        status_code=status_code,
    )
