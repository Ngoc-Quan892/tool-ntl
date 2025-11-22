"""
Examples of tiered caching strategy usage.

This module demonstrates how to use the tiered caching decorator
with different cache levels for optimal performance.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.services.performance_optimizer import cached, CacheManager
from app.services.cache_invalidation import invalidate_game_caches


# ==================== TIER 1: HOT DATA (L1 Memory Only) ====================
# Very frequent access, <1 min TTL
# Use for: Current game state, active user sessions

@cached(ttl=60, level="l1", key_prefix="game_state")
def get_current_game_state(game_id: int, cache_manager: Optional[CacheManager] = None) -> Dict[str, Any]:
    """
    Get current game state - Tier 1 (Hot data).
    
    This is accessed very frequently, so we use L1 (memory only)
    with short TTL (60 seconds).
    
    Args:
        game_id: Game/shoe ID
        cache_manager: CacheManager instance (injected)
        
    Returns:
        Current game state dictionary
    """
    # Simulate fetching from database
    # In real implementation, this would query the database
    return {
        "game_id": game_id,
        "current_hand": 42,
        "cards_remaining": 156,
        "true_count": 2.5,
    }


@cached(ttl=30, level="l1", key_prefix="user_session")
def get_active_user_session(session_id: str, cache_manager: Optional[CacheManager] = None) -> Dict[str, Any]:
    """
    Get active user session - Tier 1 (Hot data).
    
    Very frequent access, short TTL (30 seconds).
    
    Args:
        session_id: Session ID
        cache_manager: CacheManager instance (injected)
        
    Returns:
        User session data
    """
    # Simulate fetching from database
    return {
        "session_id": session_id,
        "user_id": "user123",
        "last_activity": "2024-01-01T12:00:00Z",
    }


# ==================== TIER 2: WARM DATA (L1 + L2) ====================
# Frequent access, 5-15 min TTL
# Use for: Game results (last 100), popular patterns

@cached(ttl=300, level="l1_l2", key_prefix="game_results")
def get_game_results(
    game_id: int,
    limit: int = 100,
    cache_manager: Optional[CacheManager] = None,
) -> List[Dict[str, Any]]:
    """
    Get game results - Tier 2 (Warm data).
    
    Frequently accessed, uses both L1 (memory) and L2 (Redis)
    with medium TTL (5 minutes).
    
    Args:
        game_id: Game/shoe ID
        limit: Number of results to return
        cache_manager: CacheManager instance (injected)
        
    Returns:
        List of game results
    """
    # Simulate fetching from database
    # In real implementation, this would query the database
    return [
        {
            "hand_number": i,
            "result": "B" if i % 2 == 0 else "P",
            "timestamp": f"2024-01-01T12:{i:02d}:00Z",
        }
        for i in range(1, limit + 1)
    ]


@cached(ttl=600, level="l1_l2", key_prefix="pattern_stats")
def get_popular_patterns(
    pattern_type: str = "all",
    days: int = 7,
    cache_manager: Optional[CacheManager] = None,
) -> List[Dict[str, Any]]:
    """
    Get popular patterns - Tier 2 (Warm data).
    
    Frequently accessed patterns, uses L1 + L2 with 10 min TTL.
    
    Args:
        pattern_type: Type of pattern to get
        days: Number of days to look back
        cache_manager: CacheManager instance (injected)
        
    Returns:
        List of pattern statistics
    """
    # Simulate fetching from database
    return [
        {
            "pattern": "B-B-P",
            "frequency": 42,
            "probability": 0.15,
        },
        {
            "pattern": "P-P-B",
            "frequency": 38,
            "probability": 0.13,
        },
    ]


# ==================== TIER 3: COLD DATA (L2 Redis Only) ====================
# Infrequent access, 1+ hour TTL
# Use for: Historical statistics, monthly reports

@cached(ttl=3600, level="l2", key_prefix="monthly_statistics")
def get_monthly_statistics(
    year: int,
    month: int,
    cache_manager: Optional[CacheManager] = None,
) -> Dict[str, Any]:
    """
    Get monthly statistics - Tier 3 (Cold data).
    
    Infrequently accessed, uses L2 (Redis only) with long TTL (1 hour).
    
    Args:
        year: Year
        month: Month (1-12)
        cache_manager: CacheManager instance (injected)
        
    Returns:
        Monthly statistics dictionary
    """
    # Simulate fetching from database
    return {
        "year": year,
        "month": month,
        "total_hands": 10000,
        "banker_wins": 4586,
        "player_wins": 4462,
        "ties": 952,
    }


@cached(ttl=7200, level="l2", key_prefix="historical_stats")
def get_historical_statistics(
    start_date: str,
    end_date: str,
    cache_manager: Optional[CacheManager] = None,
) -> Dict[str, Any]:
    """
    Get historical statistics - Tier 3 (Cold data).
    
    Very infrequent access, uses L2 only with 2 hour TTL.
    
    Args:
        start_date: Start date (ISO format)
        end_date: End date (ISO format)
        cache_manager: CacheManager instance (injected)
        
    Returns:
        Historical statistics dictionary
    """
    # Simulate fetching from database
    return {
        "start_date": start_date,
        "end_date": end_date,
        "total_games": 500,
        "total_hands": 50000,
        "avg_hands_per_game": 100,
    }


# ==================== CACHE INVALIDATION EXAMPLES ====================

def add_game_result(
    game_id: int,
    result: str,
    cache_manager: CacheManager,
) -> None:
    """
    Add a new game result and invalidate related caches.
    
    This demonstrates cache invalidation on write operations.
    
    Args:
        game_id: Game/shoe ID
        result: Game result (B, P, or T)
        cache_manager: CacheManager instance
    """
    # Add result to database (simulated)
    # In real implementation, this would insert into database
    print(f"Adding result {result} for game {game_id}")
    
    # Invalidate all caches related to this game
    invalidate_game_caches(cache_manager, game_id)
    
    # Also invalidate pattern caches since patterns may have changed
    from app.services.cache_invalidation import invalidate_pattern_caches
    invalidate_pattern_caches(cache_manager)


def update_game_state(
    game_id: int,
    new_state: Dict[str, Any],
    cache_manager: CacheManager,
) -> None:
    """
    Update game state and invalidate related caches.
    
    Args:
        game_id: Game/shoe ID
        new_state: New game state
        cache_manager: CacheManager instance
    """
    # Update game state in database (simulated)
    print(f"Updating game state for game {game_id}")
    
    # Invalidate game-specific caches
    invalidate_game_caches(cache_manager, game_id)


# ==================== USAGE EXAMPLE ====================

def example_usage():
    """
    Example of how to use tiered caching in practice.
    """
    from app.services.performance_optimizer import OptimizationStack, new_redis_client
    from app.models.database import db_manager
    
    # Initialize optimizer with cache manager
    redis_client = new_redis_client()
    optimizer = OptimizationStack(
        db_connection=db_manager,
        redis_client=redis_client,
    )
    
    cache_manager = optimizer.get_cache_manager()
    
    # Example 1: Get hot data (Tier 1 - L1 only)
    game_state = get_current_game_state(
        game_id=1,
        cache_manager=cache_manager,
    )
    print(f"Game state: {game_state}")
    
    # Example 2: Get warm data (Tier 2 - L1 + L2)
    game_results = get_game_results(
        game_id=1,
        limit=100,
        cache_manager=cache_manager,
    )
    print(f"Game results: {len(game_results)} results")
    
    # Example 3: Get cold data (Tier 3 - L2 only)
    monthly_stats = get_monthly_statistics(
        year=2024,
        month=1,
        cache_manager=cache_manager,
    )
    print(f"Monthly stats: {monthly_stats}")
    
    # Example 4: Invalidate caches on write
    add_game_result(
        game_id=1,
        result="B",
        cache_manager=cache_manager,
    )


if __name__ == "__main__":
    example_usage()

