"""
Performance monitoring middleware.

Features:
- Request timing
- Slow request detection
- Performance logging
"""
from __future__ import annotations

import time
import logging
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.services.monitoring import track_request

logger = logging.getLogger(__name__)

# Slow request threshold (100ms)
SLOW_REQUEST_THRESHOLD = 0.1


class PerformanceMiddleware(BaseHTTPMiddleware):
    """Middleware to track request performance."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and track performance."""
        start_time = time.time()
        
        # Get endpoint path (simplified)
        endpoint = request.url.path
        method = request.method
        
        # Track request
        with track_request(method=method, endpoint=endpoint):
            try:
                response = await call_next(request)
            except Exception as e:
                # Track error
                duration = time.time() - start_time
                logger.error(
                    f"Request error: {method} {endpoint} - {str(e)} (took {duration:.3f}s)"
                )
                raise
            finally:
                duration = time.time() - start_time
                
                # Log slow requests
                if duration > SLOW_REQUEST_THRESHOLD:
                    logger.warning(
                        f"Slow request: {method} {endpoint} took {duration:.3f}s "
                        f"(threshold: {SLOW_REQUEST_THRESHOLD}s)"
                    )
                
                # Add performance headers
                response.headers["X-Response-Time"] = f"{duration:.3f}"
                response.headers["X-Request-ID"] = request.headers.get("X-Request-ID", "unknown")
        
        return response

