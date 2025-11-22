"""
Monitoring và error tracking service với Sentry integration.
"""
from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# Prometheus client (optional)
try:
    from prometheus_client import (
        Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST,
        REGISTRY
    )
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    logger.info("Prometheus client not installed. Install with: pip install prometheus-client")

# Sentry integration (optional)
sentry_sdk = None
try:
    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
    from sentry_sdk.integrations.redis import RedisIntegration
except ImportError:
    logger.info("Sentry SDK not installed. Error tracking disabled.")


def init_sentry(dsn: Optional[str] = None, environment: str = "development") -> None:
    """
    Initialize Sentry error tracking.
    
    Args:
        dsn: Sentry DSN (from environment if None)
        environment: Environment name (development, staging, production)
    """
    if sentry_sdk is None:
        logger.warning("Sentry SDK not available. Install with: pip install sentry-sdk")
        return
    
    dsn = dsn or os.getenv("SENTRY_DSN")
    if not dsn:
        logger.info("Sentry DSN not configured. Error tracking disabled.")
        return
    
    try:
        sentry_sdk.init(
            dsn=dsn,
            environment=environment,
            integrations=[
                FastApiIntegration(),
                SqlalchemyIntegration(),
                RedisIntegration(),
            ],
            # Set traces_sample_rate to 1.0 to capture 100%
            # of the transactions for performance monitoring.
            traces_sample_rate=1.0 if environment == "development" else 0.1,
            # Set profiles_sample_rate to 1.0 to profile 100%
            # of sampled transactions.
            profiles_sample_rate=1.0 if environment == "development" else 0.1,
            # Filter out health check endpoints
            ignore_errors=[
                KeyboardInterrupt,
            ],
            # Release tracking
            release=os.getenv("APP_VERSION", "1.0.0"),
        )
        logger.info(f"Sentry initialized for environment: {environment}")
    except Exception as e:
        logger.error(f"Failed to initialize Sentry: {e}")


def capture_exception(error: Exception, context: Optional[Dict[str, Any]] = None) -> None:
    """
    Capture exception to Sentry.
    
    Args:
        error: Exception to capture
        context: Additional context
    """
    if sentry_sdk is None:
        logger.error(f"Exception (Sentry not available): {error}", exc_info=True)
        return
    
    try:
        with sentry_sdk.push_scope() as scope:
            if context:
                for key, value in context.items():
                    scope.set_context(key, value)
            sentry_sdk.capture_exception(error)
    except Exception as e:
        logger.error(f"Failed to capture exception to Sentry: {e}")


def capture_message(message: str, level: str = "info", context: Optional[Dict[str, Any]] = None) -> None:
    """
    Capture message to Sentry.
    
    Args:
        message: Message to capture
        level: Log level (info, warning, error)
        context: Additional context
    """
    if sentry_sdk is None:
        logger.log(getattr(logging, level.upper(), logging.INFO), message)
        return
    
    try:
        with sentry_sdk.push_scope() as scope:
            if context:
                for key, value in context.items():
                    scope.set_context(key, value)
            sentry_sdk.capture_message(message, level=level)
    except Exception as e:
        logger.error(f"Failed to capture message to Sentry: {e}")


def set_user(user_id: Optional[str] = None, email: Optional[str] = None, username: Optional[str] = None) -> None:
    """
    Set user context for Sentry.
    
    Args:
        user_id: User ID
        email: User email
        username: Username
    """
    if sentry_sdk is None:
        return
    
    try:
        sentry_sdk.set_user({
            "id": user_id,
            "email": email,
            "username": username,
        })
    except Exception as e:
        logger.error(f"Failed to set Sentry user: {e}")


# Prometheus metrics (initialized lazily)
_prometheus_metrics: Dict[str, Any] = {}


def _init_prometheus_metrics():
    """Initialize Prometheus metrics."""
    if not PROMETHEUS_AVAILABLE:
        return
    
    global _prometheus_metrics
    
    if _prometheus_metrics:
        return  # Already initialized
    
    try:
        _prometheus_metrics = {
            # HTTP metrics
            'http_requests_total': Counter(
                'http_requests_total',
                'Total HTTP requests',
                ['method', 'endpoint', 'status']
            ),
            'http_request_duration_seconds': Histogram(
                'http_request_duration_seconds',
                'HTTP request duration in seconds',
                ['method', 'endpoint'],
                buckets=(0.01, 0.05, 0.1, 0.5, 1.0, 2.5, 5.0, 10.0)
            ),
            # Database metrics
            'database_queries_total': Counter(
                'database_queries_total',
                'Total database queries',
                ['query_type']
            ),
            'database_query_duration_seconds': Histogram(
                'database_query_duration_seconds',
                'Database query duration in seconds',
                ['query_type'],
                buckets=(0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 2.0)
            ),
            'slow_queries_total': Counter(
                'slow_queries_total',
                'Total slow queries (>100ms)',
                ['query_type']
            ),
            # Cache metrics
            'cache_hits_total': Counter(
                'cache_hits_total',
                'Total cache hits',
                ['cache_type']
            ),
            'cache_misses_total': Counter(
                'cache_misses_total',
                'Total cache misses',
                ['cache_type']
            ),
            # Connection metrics
            'active_connections': Gauge(
                'active_connections',
                'Active database connections'
            ),
            'connection_pool_size': Gauge(
                'connection_pool_size',
                'Connection pool size'
            ),
            # System metrics
            'memory_usage_bytes': Gauge(
                'memory_usage_bytes',
                'Memory usage in bytes'
            ),
            'cpu_usage_percent': Gauge(
                'cpu_usage_percent',
                'CPU usage percentage'
            ),
        }
        logger.info("Prometheus metrics initialized")
    except Exception as e:
        logger.error(f"Failed to initialize Prometheus metrics: {e}")


def get_metrics() -> str:
    """
    Get Prometheus metrics in text format.
    
    Returns:
        Prometheus metrics text format
    """
    if not PROMETHEUS_AVAILABLE:
        return "# Prometheus client not available\n"
    
    try:
        _init_prometheus_metrics()
        return generate_latest(REGISTRY).decode('utf-8')
    except Exception as e:
        logger.error(f"Failed to generate Prometheus metrics: {e}")
        return f"# Error generating metrics: {e}\n"


def get_metrics_content_type() -> str:
    """
    Get content type for Prometheus metrics.
    
    Returns:
        Content type string
    """
    if not PROMETHEUS_AVAILABLE:
        return "text/plain"
    return CONTENT_TYPE_LATEST


def get_prometheus_metric(name: str):
    """
    Get a Prometheus metric by name.
    
    Args:
        name: Metric name
        
    Returns:
        Metric object or None
    """
    if not PROMETHEUS_AVAILABLE:
        return None
    
    _init_prometheus_metrics()
    return _prometheus_metrics.get(name)
