"""
Game Analysis API endpoints with performance optimization.

This module provides optimized endpoints for game results and pattern statistics
using the OptimizationStack for caching, query optimization, and monitoring.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.api.v2.base import get_database_session
from app.models.database import db_manager
from app.services.performance_optimizer import (
    OptimizationStack,
    PerformanceMonitor,
    get_cache_manager,
    new_redis_client,
)
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(prefix="/api/v2/game", tags=["game-analysis"])

# Initialize OptimizationStack singleton
# This will be initialized at application startup in main.py
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
        redis_client = new_redis_client()
        _optimizer = OptimizationStack(
            db_connection=db_manager,
            redis_client=redis_client,
            cache_ttl=settings.REDIS_CACHE_TTL or 300,
        )
        logger.info("OptimizationStack initialized (lazy initialization)")
    return _optimizer


@router.get("/{game_id}/results")
async def get_game_results(
    request: Request,
    game_id: int,
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of results to return"),
    db: Session = Depends(get_database_session),
) -> Dict[str, Any]:
    """
    Get game results for a specific game/shoe with optimized query.
    
    This endpoint uses:
    - QueryOptimizer for efficient database queries with proper indexes
    - L1 (memory) + L2 (Redis) caching with 1-minute TTL
    - Performance monitoring
    - Batching for related data
    
    Args:
        request: FastAPI request object
        game_id: Shoe/game number identifier
        limit: Maximum number of results (1-1000)
        db: Database session
        
    Returns:
        Dictionary containing game results list and metadata
    """
    optimizer = get_optimizer(request)
    query_optimizer = optimizer.get_query_optimizer(db)
    cache_manager = optimizer.get_cache_manager()
    
    # Generate cache key
    cache_key = cache_manager._generate_key("game_results", "get_game_results", game_id, limit=limit)
    
    # Check cache first
    cached_result = cache_manager.get(cache_key)
    if cached_result is not None:
        logger.debug("Cache hit for game_results: game_id=%s", game_id)
        return cached_result
    
    # Cache miss - execute query with monitoring
    with PerformanceMonitor(f"get_game_results_{game_id}") as monitor:
        try:
            results = query_optimizer.get_game_results(
                game_id=game_id,
                limit=limit
            )
            
            response = {
                "game_id": game_id,
                "results": results,
                "count": len(results),
                "limit": limit,
            }
            
            # Cache the result for 60 seconds
            cache_manager.set(cache_key, response, ttl=60)
            
            return response
        except Exception as exc:
            logger.error("Error fetching game results for game_id %s: %s", game_id, exc)
            raise


@router.get("/statistics/pattern")
async def get_pattern_statistics(
    request: Request,
    pattern_type: str = Query(..., description="Pattern type to analyze (e.g., 'B', 'P', 'T', 'all')"),
    days: int = Query(7, ge=1, le=365, description="Number of days to analyze"),
    db: Session = Depends(get_database_session),
) -> Dict[str, Any]:
    """
    Get pattern statistics with heavy computation optimization.
    
    This endpoint:
    - Caches aggressively (5+ minutes) due to heavy computation
    - Uses optimized queries with proper indexes
    - Supports batch processing for multiple patterns
    - Pre-warms cache for popular patterns
    
    Args:
        request: FastAPI request object
        pattern_type: Type of pattern to analyze ('B', 'P', 'T', or 'all')
        days: Number of days to look back (1-365)
        db: Database session
        
    Returns:
        Dictionary containing pattern statistics
    """
    optimizer = get_optimizer(request)
    query_optimizer = optimizer.get_query_optimizer(db)
    cache_manager = optimizer.get_cache_manager()
    
    # Generate cache key
    cache_key = cache_manager._generate_key("pattern_stats", "get_pattern_statistics", pattern_type, days=days)
    
    # Check cache first (aggressive caching for heavy computation)
    cached_result = cache_manager.get(cache_key)
    if cached_result is not None:
        logger.debug("Cache hit for pattern_stats: pattern_type=%s, days=%s", pattern_type, days)
        return cached_result
    
    # Cache miss - execute query with monitoring
    with PerformanceMonitor(f"pattern_stats_{pattern_type}") as monitor:
        try:
            stats = query_optimizer.get_pattern_statistics(
                pattern_type=pattern_type,
                days=days,
                limit=1000,  # Default limit for pattern analysis
                use_cache=True
            )
            
            response = {
                "pattern_type": pattern_type,
                "days": days,
                "statistics": stats,
                "count": len(stats),
            }
            
            # Cache aggressively for 5 minutes (300 seconds)
            cache_manager.set(cache_key, response, ttl=300)
            
            return response
        except Exception as exc:
            logger.error("Error fetching pattern statistics: %s", exc)
            raise

