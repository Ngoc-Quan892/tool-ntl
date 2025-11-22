"""
API endpoints for performance monitoring and cache management.
"""

from __future__ import annotations

import logging
from typing import Dict, Optional
import time

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.database import get_db
from app.services.authentication import get_current_user
from app.services.performance_optimizer import (
    CacheManager,
    PerformanceMonitor,
    QueryOptimizer,
    get_cache_manager,
    get_performance_monitor,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/performance", tags=["Performance"])


@router.get("/cache/stats")
async def cache_stats(user_id: str = Depends(get_current_user)) -> Dict[str, any]:
    try:
        cache_manager = get_cache_manager()
        return cache_manager.get_stats()
    except Exception as exc:
        logger.error("Cache stats failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to retrieve cache statistics")


@router.post("/cache/clear")
async def clear_cache(
    pattern: Optional[str] = None,
    user_id: str = Depends(get_current_user),
) -> Dict[str, str]:
    try:
        cache_manager = get_cache_manager()
        if pattern:
            cache_manager.delete_pattern(pattern)
            return {"message": f"Cleared cache matching pattern '{pattern}'"}
        cache_manager.clear_all()
        return {"message": "All cache layers cleared"}
    except Exception as exc:
        logger.error("Cache clear failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to clear cache")


@router.get("/metrics")
async def performance_metrics(user_id: str = Depends(get_current_user)) -> Dict[str, any]:
    try:
        monitor = get_performance_monitor()
        return monitor.get_metrics()
    except Exception as exc:
        logger.error("Performance metrics failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to retrieve metrics")


@router.post("/metrics/reset")
async def reset_metrics(user_id: str = Depends(get_current_user)) -> Dict[str, str]:
    try:
        monitor = get_performance_monitor()
        monitor.reset()
        return {"message": "Performance metrics reset"}
    except Exception as exc:
        logger.error("Metrics reset failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to reset metrics")


@router.get("/database/stats")
async def database_stats(
    db: Session = Depends(get_db), user_id: str = Depends(get_current_user)
) -> Dict[str, any]:
    try:
        optimizer = QueryOptimizer(db)
        return optimizer.get_query_statistics()
    except Exception as exc:
        logger.error("Database stats failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to retrieve database statistics")


@router.get("/health/detailed")
async def detailed_health_check(db: Session = Depends(get_db)) -> Dict[str, any]:
    db_latency_ms = -1.0
    db_healthy = True
    try:
        start = time.time()
        db.execute(text("SELECT 1"))
        db_latency_ms = (time.time() - start) * 1000
    except Exception as exc:
        db_healthy = False
        logger.error("Database health check failed: %s", exc)

    try:
        cache_manager = get_cache_manager()
        cache_stats = cache_manager.get_stats()
        cache_healthy = True
    except Exception as exc:
        cache_healthy = False
        cache_stats = {}
        logger.error("Cache health check failed: %s", exc)

    performance = get_performance_monitor().get_metrics()
    status = "healthy"
    if not db_healthy or not cache_healthy:
        status = "degraded"
    if performance.get("error_rate", 0) > 5:
        status = "unhealthy"

    return {
        "status": status,
        "database": {"healthy": db_healthy, "latency_ms": round(db_latency_ms, 2)},
        "cache": {"healthy": cache_healthy, **cache_stats},
        "performance": performance,
    }

