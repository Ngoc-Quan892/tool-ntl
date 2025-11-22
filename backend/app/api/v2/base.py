"""
Base API router for v2 with exception handlers and dependency injection.

This module provides:
- Base router with common configuration
- Global exception handlers
- Dependency injection utilities
- Common response models
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Generator, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.database import db_manager, get_db
from app.models.schemas import ErrorMessage

logger = logging.getLogger(__name__)
settings = get_settings()

# Base router for v2 API
router = APIRouter(
    prefix="/v2",
    tags=["v2"],
    responses={
        404: {"description": "Not found"},
        422: {"description": "Validation error"},
        500: {"description": "Internal server error"},
    },
)


# Exception Handlers
class APIException(HTTPException):
    """Base API exception with custom error format."""

    def __init__(
        self,
        status_code: int,
        message: str,
        detail: Optional[Dict[str, Any]] = None,
        error_code: Optional[str] = None,
    ):
        super().__init__(status_code=status_code, detail=message)
        self.message = message
        self.error_code = error_code or f"ERR_{status_code}"
        self.detail_dict = detail or {}


class NotFoundError(APIException):
    """Resource not found exception."""

    def __init__(self, resource: str, identifier: Optional[str] = None):
        message = f"{resource} not found"
        if identifier:
            message += f": {identifier}"
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            message=message,
            error_code="NOT_FOUND",
        )


class RequestValidationError(APIException):
    """Request validation error exception."""

    def __init__(self, message: str, errors: Optional[Dict[str, Any]] = None):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            message=message,
            detail=errors or {},
            error_code="VALIDATION_ERROR",
        )


class DatabaseError(APIException):
    """Database operation error exception."""

    def __init__(self, message: str = "Database operation failed"):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=message,
            error_code="DATABASE_ERROR",
        )


# Exception handler functions
@router.exception_handler(APIException)
async def api_exception_handler(request: Request, exc: APIException) -> JSONResponse:
    """Handle custom API exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": exc.error_code,
                "message": exc.message,
                "detail": exc.detail_dict,
            },
            "timestamp": request.state.get("timestamp") if hasattr(request.state, "timestamp") else None,
        },
    )


@router.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle FastAPI HTTP exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": f"HTTP_{exc.status_code}",
                "message": exc.detail,
                "detail": {},
            },
        },
    )


@router.exception_handler(ValidationError)
async def validation_exception_handler(request: Request, exc: ValidationError) -> JSONResponse:
    """Handle Pydantic validation errors."""
    errors = {}
    if hasattr(exc, "errors"):
        for error in exc.errors():
            field = ".".join(str(loc) for loc in error.get("loc", []))
            errors[field] = error.get("msg", "Validation error")

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Request validation failed",
                "detail": errors,
            },
        },
    )


@router.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected exceptions."""
    logger.exception(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred",
                "detail": {"type": type(exc).__name__} if settings.DEBUG else {},
            },
        },
    )


# Dependency Injection Utilities
def get_database_session() -> Generator[Session, None, None]:
    """
    FastAPI dependency for database sessions.

    Usage:
        @router.get("/items")
        def get_items(db: Session = Depends(get_database_session)):
            return db.query(Item).all()
    """
    yield from get_db()


def get_current_request(request: Request) -> Request:
    """
    Dependency to get the current request object.

    Usage:
        @router.get("/items")
        def get_items(request: Request = Depends(get_current_request)):
            return request.app.state.something
    """
    return request


def verify_database_health() -> bool:
    """
    Dependency to verify database health before processing requests.

    Raises:
        DatabaseError: If database is not healthy
    """
    if not db_manager.health_check():
        raise DatabaseError("Database connection is not available")
    return True


# Common Response Models
class SuccessResponse:
    """Helper for creating success responses."""

    @staticmethod
    def create(data: Any, message: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a standardized success response.

        Args:
            data: Response data
            message: Optional success message

        Returns:
            Standardized success response dict
        """
        response = {"success": True, "data": data}
        if message:
            response["message"] = message
        return response


class PaginatedResponse:
    """Helper for creating paginated responses."""

    @staticmethod
    def create(
        items: list,
        total: int,
        page: int = 1,
        page_size: int = 100,
    ) -> Dict[str, Any]:
        """
        Create a standardized paginated response.

        Args:
            items: List of items for current page
            total: Total number of items
            page: Current page number
            page_size: Number of items per page

        Returns:
            Standardized paginated response dict
        """
        total_pages = (total + page_size - 1) // page_size if total > 0 else 0
        return {
            "success": True,
            "data": {
                "items": items,
                "pagination": {
                    "total": total,
                    "page": page,
                    "page_size": page_size,
                    "total_pages": total_pages,
                    "has_next": page < total_pages,
                    "has_prev": page > 1,
                },
            },
        }


# Health Check Endpoint
@router.get("/health", tags=["health"])
async def health_check() -> Dict[str, Any]:
    """
    Health check endpoint.

    Returns:
        Health status of the API and dependencies
    """
    db_healthy = db_manager.health_check()

    return {
        "status": "healthy" if db_healthy else "degraded",
        "version": settings.APP_VERSION,
        "database": "connected" if db_healthy else "disconnected",
        "timestamp": None,  # Will be set by middleware if available
    }


# Database Health Check Endpoint
@router.get("/health/db", tags=["health"])
async def database_health_check() -> Dict[str, Any]:
    """
    Database-specific health check.

    Returns:
        Database connection status
    """
    is_healthy = db_manager.health_check()
    if not is_healthy:
        raise DatabaseError("Database is not available")

    return {
        "status": "healthy",
        "database_url": db_manager.database_url.split("@")[-1] if "@" in db_manager.database_url else "configured",
        "pool_size": settings.DB_POOL_SIZE,
        "max_overflow": settings.DB_MAX_OVERFLOW,
    }


# Detailed Health Check Endpoint
@router.get("/health/detailed", tags=["health"])
async def detailed_health_check(
    db: Session = Depends(get_database_session)
) -> Dict[str, Any]:
    """
    Comprehensive health check with all system components.

    Returns:
        Detailed health status of all system components
    """
    from app.services.health_check import HealthChecker
    from app.services.cache import cache_manager
    import redis
    
    # Get Redis client (sync version for health checker)
    try:
        redis_client = redis.from_url(settings.REDIS_URL)
    except Exception:
        # Fallback if Redis connection fails
        redis_client = None
    
    if redis_client:
        health_checker = HealthChecker(db=db, redis_client=redis_client)
        return await health_checker.check_health()
    else:
        # Return basic health if Redis unavailable
        return {
            "status": "degraded",
            "timestamp": None,
            "checks": {
                "redis": {
                    "status": "unhealthy",
                    "error": "Redis connection unavailable"
                }
            },
            "health_score": 0
        }
