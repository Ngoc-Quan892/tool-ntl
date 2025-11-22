"""
Cache invalidation utilities for tiered caching strategy.

This module provides:
- Pattern-based cache invalidation
- Game-specific cache invalidation
- Automatic invalidation on write operations
- Manual invalidation endpoints
"""

from __future__ import annotations

import logging
from typing import List, Optional

from app.services.performance_optimizer import CacheManager

logger = logging.getLogger(__name__)


def invalidate_game_caches(
    cache_manager: CacheManager,
    game_id: int,
    patterns: Optional[List[str]] = None,
) -> None:
    """
    Clear all caches for a game.
    
    This function is called:
    - When new result added
    - When game updated
    - When patterns recalculated
    
    Args:
        cache_manager: CacheManager instance
        game_id: Game/shoe ID
        patterns: Optional list of additional patterns to invalidate
    """
    if patterns is None:
        patterns = []
    
    # Default patterns for game-related caches
    default_patterns = [
        f"game_results:{game_id}",
        f"game_results:{game_id}:*",
        f"pattern_stats:*:{game_id}",
        f"pattern_stats:*:{game_id}:*",
        f"game_state:{game_id}",
        f"game_state:{game_id}:*",
        f"shoe:{game_id}",
        f"shoe:{game_id}:*",
        f"statistics:{game_id}",
        f"statistics:{game_id}:*",
    ]
    
    # Combine default and custom patterns
    all_patterns = default_patterns + patterns
    
    logger.info(f"Invalidating caches for game_id={game_id} with {len(all_patterns)} patterns")
    
    # Delete all matching patterns
    cache_manager.delete_patterns(all_patterns)
    
    logger.debug(f"Cache invalidation completed for game_id={game_id}")


def invalidate_user_caches(
    cache_manager: CacheManager,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
) -> None:
    """
    Clear all caches for a user or session.
    
    Args:
        cache_manager: CacheManager instance
        user_id: User ID (optional)
        session_id: Session ID (optional)
    """
    patterns = []
    
    if user_id:
        patterns.extend([
            f"user:{user_id}",
            f"user:{user_id}:*",
            f"session:{user_id}:*",
        ])
    
    if session_id:
        patterns.extend([
            f"session:{session_id}",
            f"session:{session_id}:*",
        ])
    
    if patterns:
        logger.info(f"Invalidating user/session caches: {len(patterns)} patterns")
        cache_manager.delete_patterns(patterns)


def invalidate_pattern_caches(
    cache_manager: CacheManager,
    pattern_type: Optional[str] = None,
) -> None:
    """
    Clear pattern-related caches.
    
    Args:
        cache_manager: CacheManager instance
        pattern_type: Specific pattern type to invalidate (optional)
    """
    if pattern_type:
        patterns = [
            f"pattern_stats:{pattern_type}",
            f"pattern_stats:{pattern_type}:*",
        ]
    else:
        patterns = [
            "pattern_stats:*",
        ]
    
    logger.info(f"Invalidating pattern caches: {len(patterns)} patterns")
    cache_manager.delete_patterns(patterns)


def invalidate_statistics_caches(
    cache_manager: CacheManager,
    year: Optional[int] = None,
    month: Optional[int] = None,
) -> None:
    """
    Clear statistics-related caches.
    
    Args:
        cache_manager: CacheManager instance
        year: Specific year to invalidate (optional)
        month: Specific month to invalidate (optional)
    """
    patterns = []
    
    if year and month:
        patterns.extend([
            f"statistics:{year}:{month}",
            f"statistics:{year}:{month}:*",
            f"monthly_statistics:{year}:{month}",
        ])
    elif year:
        patterns.extend([
            f"statistics:{year}:*",
            f"monthly_statistics:{year}:*",
        ])
    else:
        patterns.extend([
            "statistics:*",
            "monthly_statistics:*",
        ])
    
    logger.info(f"Invalidating statistics caches: {len(patterns)} patterns")
    cache_manager.delete_patterns(patterns)


def invalidate_all_game_related_caches(cache_manager: CacheManager) -> None:
    """
    Clear all game-related caches (use with caution).
    
    Args:
        cache_manager: CacheManager instance
    """
    patterns = [
        "game_results:*",
        "game_state:*",
        "shoe:*",
        "pattern_stats:*",
        "statistics:*",
    ]
    
    logger.warning("Invalidating ALL game-related caches")
    cache_manager.delete_patterns(patterns)

