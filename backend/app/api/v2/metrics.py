"""
Metrics and monitoring endpoints.

Endpoints:
- /metrics - Prometheus metrics
- /metrics/dashboard - Metrics dashboard
"""
from __future__ import annotations

from typing import Dict

from fastapi import APIRouter, Response
from fastapi.responses import JSONResponse

from app.api.v2.base import SuccessResponse
from app.services.cache import cache_manager
from app.services.monitoring import get_metrics, get_metrics_content_type
from app.models.database import db_manager

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("")
async def prometheus_metrics() -> Response:
    """
    Prometheus metrics endpoint.
    
    Returns:
        Prometheus metrics in text format
    """
    metrics = get_metrics()
    return Response(
        content=metrics,
        media_type=get_metrics_content_type(),
    )


@router.get("/prometheus")
async def prometheus_metrics_endpoint() -> Response:
    """
    Prometheus metrics endpoint (alternative path).
    
    This endpoint is used by Prometheus scraper.
    
    Returns:
        Prometheus metrics in text format
    """
    metrics = get_metrics()
    return Response(
        content=metrics,
        media_type=get_metrics_content_type(),
    )


@router.get("/dashboard")
async def metrics_dashboard() -> Dict:
    """
    Metrics dashboard with system statistics.
    
    Returns:
        JSON with system metrics
    """
    # Get cache stats
    cache_stats = await cache_manager.get_stats()
    
    # Get database stats
    db_healthy = db_manager.health_check()
    
    # Get WebSocket stats (if available)
    ws_stats = {}
    try:
        from app.api.websocket_manager import ws_manager
        ws_stats = ws_manager.get_stats()
    except Exception:
        pass
    
    return SuccessResponse.create({
        "cache": cache_stats,
        "database": {
            "connected": db_healthy,
            "pool_size": db_manager.engine.pool.size() if db_manager.engine else 0,
            "checked_out": db_manager.engine.pool.checkedout() if db_manager.engine else 0,
        },
        "websocket": ws_stats,
        "system": {
            "status": "healthy" if db_healthy and cache_stats.get("connected", False) else "degraded",
        },
    })

