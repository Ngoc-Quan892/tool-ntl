"""
Real-time dashboard endpoint for monitoring.

Provides:
- Current metrics
- Historical trends (last 1 hour)
- Active alerts
- Update every 5 seconds
"""

from __future__ import annotations

import logging
import time
from collections import deque
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.v2.base import get_database_session
from app.services.performance_optimizer import OptimizationStack
from app.services.alerting import AlertManager
from app.api.endpoints.monitoring import get_optimizer, get_performance_metrics

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/monitoring", tags=["monitoring"])

# In-memory storage for trends (last 1 hour, 5-second intervals = 720 points)
# In production, use Redis or time-series database
_metrics_history: deque = deque(maxlen=720)  # 1 hour of 5-second intervals
_alert_manager: Optional[AlertManager] = None


def get_alert_manager(request: Request) -> AlertManager:
    """Get or create AlertManager instance."""
    global _alert_manager
    
    if _alert_manager is None:
        optimizer = get_optimizer(request)
        _alert_manager = AlertManager(optimizer=optimizer)
        logger.info("AlertManager initialized")
    
    return _alert_manager


@router.get("/dashboard")
async def get_dashboard_data(
    request: Request,
    db: Session = Depends(get_database_session),
) -> Dict[str, Any]:
    """
    TODO: Real-time dashboard data
    
    - Update every 5 seconds
    - Show last 1 hour trends
    - Highlight alerts
    
    Returns:
        {
            "current": {...},  # Current metrics
            "trends": {...},   # Historical trends
            "alerts": [...],   # Active alerts
            "timestamp": "..."
        }
    """
    optimizer = get_optimizer(request)
    
    # Get current metrics
    current_metrics = await get_performance_metrics(request, db)
    
    # Store in history
    _metrics_history.append({
        "timestamp": time.time(),
        "metrics": current_metrics,
    })
    
    # Calculate trends (last 1 hour)
    trends = _calculate_trends()
    
    # Get active alerts
    alert_manager = get_alert_manager(request)
    alerts = _identify_alerts(current_metrics, alert_manager)
    
    return {
        "current": current_metrics,
        "trends": trends,
        "alerts": alerts,
        "timestamp": datetime.utcnow().isoformat(),
    }


def _calculate_trends() -> Dict[str, Any]:
    """Calculate trends from metrics history."""
    if len(_metrics_history) < 2:
        return {
            "response_times": [],
            "cache_hit_rate": [],
            "error_rate": [],
            "query_times": [],
        }
    
    # Extract data points
    response_times = []
    cache_hit_rates = []
    error_rates = []
    query_times = []
    timestamps = []
    
    for entry in _metrics_history:
        metrics = entry.get("metrics", {})
        timestamp = entry.get("timestamp", 0)
        
        timestamps.append(datetime.fromtimestamp(timestamp).isoformat())
        
        # Extract metrics
        queries = metrics.get("queries", {})
        cache = metrics.get("cache", {})
        
        # Response time (approximate from query time)
        avg_query_time = queries.get("avg_time_ms", 0)
        response_times.append(avg_query_time)
        
        # Cache hit rate
        hit_rate = cache.get("hit_rate", 0)
        cache_hit_rates.append(hit_rate)
        
        # Error rate (not directly tracked, use 0 for now)
        error_rates.append(0.0)
        
        # Query times
        query_times.append(avg_query_time)
    
    return {
        "response_times": {
            "timestamps": timestamps,
            "values": response_times,
            "avg": sum(response_times) / len(response_times) if response_times else 0,
            "min": min(response_times) if response_times else 0,
            "max": max(response_times) if response_times else 0,
        },
        "cache_hit_rate": {
            "timestamps": timestamps,
            "values": cache_hit_rates,
            "avg": sum(cache_hit_rates) / len(cache_hit_rates) if cache_hit_rates else 0,
            "min": min(cache_hit_rates) if cache_hit_rates else 0,
            "max": max(cache_hit_rates) if cache_hit_rates else 0,
        },
        "error_rate": {
            "timestamps": timestamps,
            "values": error_rates,
            "avg": sum(error_rates) / len(error_rates) if error_rates else 0,
        },
        "query_times": {
            "timestamps": timestamps,
            "values": query_times,
            "avg": sum(query_times) / len(query_times) if query_times else 0,
        },
    }


def _identify_alerts(
    metrics: Dict[str, Any],
    alert_manager: AlertManager,
) -> List[Dict[str, Any]]:
    """Identify active alerts based on current metrics."""
    alerts: List[Dict[str, Any]] = []
    
    # Check cache hit rate
    cache_hit_rate = metrics.get("cache", {}).get("hit_rate", 0)
    if cache_hit_rate < 70:
        alerts.append({
            "severity": "warning",
            "message": f"Cache hit rate below 70%: {cache_hit_rate:.1f}%",
            "value": cache_hit_rate,
            "metric": "cache_hit_rate",
            "threshold": 70,
        })
    
    # Check query time
    avg_query_time = metrics.get("queries", {}).get("avg_time_ms", 0)
    if avg_query_time > 100:
        severity = "critical" if avg_query_time > 200 else "warning"
        alerts.append({
            "severity": severity,
            "message": f"Queries too slow: {avg_query_time:.2f}ms average",
            "value": avg_query_time,
            "metric": "avg_query_time_ms",
            "threshold": 100 if severity == "warning" else 200,
        })
    
    # Check connection pool
    connections = metrics.get("connections", {})
    active = connections.get("active", 0)
    pool_size = connections.get("pool_size", 0)
    if pool_size > 0:
        utilization = (active / pool_size) * 100
        if utilization > 80:
            severity = "critical" if utilization > 90 else "warning"
            alerts.append({
                "severity": severity,
                "message": f"Connection pool {utilization:.1f}% utilized ({active}/{pool_size})",
                "value": utilization,
                "metric": "connection_pool_utilization",
                "threshold": 80 if severity == "warning" else 90,
            })
    
    # Check slow queries
    slow_queries = metrics.get("queries", {}).get("slow_queries", 0)
    total_queries = metrics.get("queries", {}).get("total_queries", 0)
    if total_queries > 0:
        slow_query_rate = (slow_queries / total_queries) * 100
        if slow_query_rate > 5:  # More than 5% slow queries
            alerts.append({
                "severity": "warning",
                "message": f"High slow query rate: {slow_query_rate:.1f}% ({slow_queries}/{total_queries})",
                "value": slow_query_rate,
                "metric": "slow_query_rate",
                "threshold": 5,
            })
    
    # Check system memory
    system = metrics.get("system", {})
    memory_percent = system.get("memory_percent")
    if memory_percent and memory_percent > 90:
        alerts.append({
            "severity": "critical",
            "message": f"High memory usage: {memory_percent:.1f}%",
            "value": memory_percent,
            "metric": "memory_percent",
            "threshold": 90,
        })
    
    return alerts

