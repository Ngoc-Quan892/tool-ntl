"""
Deep dive debugging tools for failed performance metrics.

Cung cấp các công cụ debug chi tiết để phân tích các metric bị lỗi:
- Cache effectiveness debugging
- Query performance analysis
- Connection pool monitoring

Usage:
    python benchmarks/debug_failed_metrics.py
"""

import sys
import time
from pathlib import Path
from typing import Dict, Any, Optional

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.services.performance_optimizer import (
    OptimizationStack,
    ConnectionPoolManager,
    new_redis_client,
)
from app.models.database import db_manager
from app.core.config import get_settings

settings = get_settings()


def debug_cache_effectiveness(
    optimizer: OptimizationStack,
    session: Session,
    pattern_type: str = "banker_streak",
    days: int = 7,
) -> None:
    """
    TODO: Validate cache hit rate for specific endpoint
    
    - Should be >80% for read operations
    - Check Redis connection
    - Verify cache keys are correct
    
    Args:
        optimizer: OptimizationStack instance
        session: Database session
        pattern_type: Pattern type to test
        days: Number of days to analyze
    """
    print("\n" + "=" * 80)
    print("🔍 DEBUG CACHE EFFECTIVENESS")
    print("=" * 80)
    
    cache_manager = optimizer.get_cache_manager()
    query_optimizer = optimizer.get_query_optimizer(session)
    
    # Clear cache first
    print("\n📋 Step 1: Clearing cache...")
    cache_manager.clear_all()
    print("✅ Cache cleared")
    
    # Generate cache key (same as used in endpoint - using CacheManager's key generation)
    cache_key = cache_manager._generate_key("pattern_stats", "get_pattern_statistics", pattern_type, days=days)
    
    # First call (cold) - clear both caches first
    print(f"\n📋 Step 2: First call (cold cache)...")
    print(f"   Pattern: {pattern_type}, Days: {days}")
    
    # Clear query optimizer's internal cache
    query_optimizer.query_cache.clear()
    cache_manager.delete(cache_key)
    
    start = time.time()
    result1 = query_optimizer.get_pattern_statistics(pattern_type, days, use_cache=False)
    cold_time = time.time() - start
    
    # Check if cached in CacheManager (should be None)
    cached = cache_manager.get(cache_key)
    
    # Now manually set in CacheManager (simulating what endpoint does)
    print(f"\n📋 Step 3: Setting cache in CacheManager...")
    cache_manager.set(cache_key, result1, ttl=300)
    
    # Check if now cached
    cached_after_set = cache_manager.get(cache_key)
    
    # Second call (should be warm from CacheManager, but we'll test query_optimizer cache too)
    print(f"\n📋 Step 4: Second call (warm cache from CacheManager)...")
    
    # Clear query_optimizer cache to test CacheManager only
    query_optimizer.query_cache.clear()
    
    start = time.time()
    # Simulate endpoint behavior: check CacheManager first, then query if miss
    cached_result = cache_manager.get(cache_key)
    if cached_result is not None:
        result2 = cached_result
        warm_time = time.time() - start
        cache_source = "CacheManager"
    else:
        # Fallback to query
        result2 = query_optimizer.get_pattern_statistics(pattern_type, days, use_cache=True)
        warm_time = time.time() - start
        cache_source = "QueryOptimizer"
    
    # Get cache stats
    cache_stats = cache_manager.get_stats()
    
    # Calculate speedup
    speedup = cold_time / warm_time if warm_time > 0 else 0
    
    print(f"""
    🔍 Cache Debug Results:
    ├─ Cold time: {cold_time*1000:.2f}ms
    ├─ Warm time: {warm_time*1000:.2f}ms
    ├─ Speedup: {speedup:.1f}x
    ├─ Cache source: {cache_source}
    ├─ Cache key: {cache_key}
    ├─ Cached after set?: {cached_after_set is not None}
    ├─ Local cache size: {cache_stats['local_cache_size']}
    ├─ Local hit rate: {cache_stats['local_hit_rate']:.1f}%
    ├─ Redis hit rate: {cache_stats['redis_hit_rate']:.1f}%
    └─ Expected: >10x speedup
    """)
    
    if warm_time > cold_time / 10:
        print("⚠️  PROBLEM: Cache not effective!")
        print("Possible causes:")
        print("  - Cache key mismatch")
        print("  - Redis connection issue")
        print("  - TTL too short")
        print("  - Cache not being used in query_optimizer")
    else:
        print("✅ Cache is working effectively!")
    
    # Check Redis connection
    print(f"\n📋 Step 5: Checking Redis connection...")
    redis_client = optimizer.redis_client
    if redis_client is None:
        print("⚠️  Redis client is None - using local cache only")
    else:
        try:
            redis_client.ping()
            print("✅ Redis connection is active")
        except Exception as e:
            print(f"❌ Redis connection failed: {e}")


def debug_query_performance(
    optimizer: OptimizationStack,
    session: Session,
    pattern_type: str = "banker_streak",
    days: int = 7,
) -> None:
    """
    TODO: Use EXPLAIN to check query plan
    
    - Should use index
    - Should not scan full table
    - Should have reasonable rows examined
    
    Args:
        optimizer: OptimizationStack instance
        session: Database session
        pattern_type: Pattern type to test
        days: Number of days to analyze
    """
    print("\n" + "=" * 80)
    print("🔍 DEBUG QUERY PERFORMANCE")
    print("=" * 80)
    
    query_optimizer = optimizer.get_query_optimizer(session)
    
    # Get the actual query used
    print(f"\n📋 Step 1: Analyzing query plan for pattern_type='{pattern_type}', days={days}...")
    
    # Build EXPLAIN query (PostgreSQL/MySQL compatible)
    explain_query = text("""
    EXPLAIN 
    WITH recent AS (
        SELECT id, shoe_number, hand_number, result
        FROM game_results
        WHERE timestamp >= CURRENT_DATE - :days
        ORDER BY timestamp DESC
        LIMIT :limit
    ), patterns AS (
        SELECT
            shoe_number,
            result,
            LAG(result, 1) OVER (PARTITION BY shoe_number ORDER BY hand_number) AS prev_1,
            LAG(result, 2) OVER (PARTITION BY shoe_number ORDER BY hand_number) AS prev_2,
            LEAD(result, 1) OVER (PARTITION BY shoe_number ORDER BY hand_number) AS next_1
        FROM recent
    )
    SELECT
        COALESCE(prev_2, '') || '-' || COALESCE(prev_1, '') || '-' || result || '-' || COALESCE(next_1, '') AS pattern,
        COUNT(*) AS frequency
    FROM patterns
    WHERE prev_2 IS NOT NULL AND next_1 IS NOT NULL
    GROUP BY pattern
    ORDER BY frequency DESC
    LIMIT 50
    """)
    
    try:
        result = session.execute(explain_query, {"days": days, "limit": 1000})
        explain_rows = result.fetchall()
        
        print("\n📊 Query Execution Plan:")
        print("-" * 80)
        
        # Check for problems
        has_full_scan = False
        has_index = False
        total_rows = 0
        
        for row in explain_rows:
            # Convert row to dict if possible, otherwise use tuple
            if hasattr(row, '_asdict'):
                row_dict = row._asdict()
            else:
                # For PostgreSQL EXPLAIN output
                row_str = str(row)
                print(f"  {row_str}")
                
                # Check for full table scan indicators
                if 'Seq Scan' in row_str or 'ALL' in row_str:
                    has_full_scan = True
                if 'Index' in row_str or 'idx_' in row_str:
                    has_index = True
                continue
            
            # For MySQL/structured EXPLAIN output
            print(f"  {row_dict}")
            
            # Check query plan type
            query_type = row_dict.get('type', '').upper() if isinstance(row_dict.get('type'), str) else ''
            if query_type == 'ALL':
                has_full_scan = True
            if query_type in ('ref', 'range', 'index'):
                has_index = True
            
            # Check rows examined
            rows_examined = row_dict.get('rows', 0)
            if isinstance(rows_examined, (int, float)):
                total_rows += rows_examined
        
        print("-" * 80)
        
        # Analysis
        print("\n📋 Step 2: Query Analysis:")
        if has_full_scan:
            print("⚠️  PROBLEM: Full table scan detected!")
            print("   Solution: Add index on (timestamp) or (timestamp, result)")
            print("   Example SQL:")
            print("   CREATE INDEX idx_game_results_timestamp ON game_results(timestamp);")
        else:
            print("✅ No full table scan detected")
        
        if has_index:
            print("✅ Index usage detected")
        else:
            print("⚠️  WARNING: No index usage detected")
            print("   Consider adding indexes for better performance")
        
        if total_rows > 10000:
            print(f"⚠️  WARNING: High number of rows examined: {total_rows}")
            print("   Consider adding WHERE clause filters or indexes")
        else:
            print(f"✅ Reasonable rows examined: {total_rows}")
        
        # Get query statistics
        query_stats = query_optimizer.get_query_statistics()
        if 'get_pattern_statistics' in query_stats:
            stats = query_stats['get_pattern_statistics']
            print(f"\n📋 Step 3: Query Statistics:")
            print(f"   Average time: {stats['avg_time_ms']:.2f}ms")
            print(f"   Min time: {stats['min_time_ms']:.2f}ms")
            print(f"   Max time: {stats['max_time_ms']:.2f}ms")
            print(f"   Slow queries: {stats['slow_queries']} ({stats['slow_rate_pct']:.1f}%)")
            
            if stats['avg_time_ms'] > 200:
                print("⚠️  PROBLEM: Average query time is too high!")
                print("   Target: <200ms")
                print("   Solutions:")
                print("   - Add indexes")
                print("   - Optimize query")
                print("   - Increase cache TTL")
        
    except Exception as e:
        print(f"❌ Error analyzing query plan: {e}")
        print("   This might be due to database type differences (PostgreSQL vs MySQL)")
        import traceback
        traceback.print_exc()


def debug_connection_pool(
    optimizer: OptimizationStack,
) -> None:
    """
    TODO: Check if waiting for connections
    
    - Pool should have idle connections
    - Wait time should be <10ms
    - No connection timeouts
    
    Args:
        optimizer: OptimizationStack instance
    """
    print("\n" + "=" * 80)
    print("🔍 DEBUG CONNECTION POOL")
    print("=" * 80)
    
    # Get engine from db_manager
    engine = db_manager.engine
    if engine is None:
        print("❌ Database engine is not initialized")
        return
    
    # Get pool status
    pool_status = ConnectionPoolManager.get_pool_status(engine)
    
    print(f"""
    🔍 Connection Pool Status:
    ├─ Pool size: {pool_status.get('pool_size', 'N/A')}
    ├─ Checked in (idle): {pool_status.get('checked_in', 'N/A')}
    ├─ Checked out (active): {pool_status.get('checked_out', 'N/A')}
    ├─ Overflow: {pool_status.get('overflow', 'N/A')}
    ├─ Total connections: {pool_status.get('total_connections', 'N/A')}
    └─ Max pool size: {settings.DB_POOL_SIZE}
    """)
    
    # Calculate metrics
    pool_size = pool_status.get('pool_size', 0)
    checked_in = pool_status.get('checked_in', 0)
    checked_out = pool_status.get('checked_out', 0)
    overflow = pool_status.get('overflow', 0)
    
    # Check for problems
    print("\n📋 Analysis:")
    
    if checked_out >= pool_size:
        print("⚠️  PROBLEM: All connections are in use!")
        print("   Solution: Increase pool size or optimize queries")
        print(f"   Current: {checked_out}/{pool_size} connections active")
    else:
        idle_connections = checked_in
        utilization = (checked_out / pool_size * 100) if pool_size > 0 else 0
        print(f"✅ Connection utilization: {utilization:.1f}%")
        print(f"✅ Idle connections available: {idle_connections}")
    
    if overflow > 0:
        print(f"⚠️  WARNING: {overflow} overflow connections")
        print("   This means pool is saturated and creating temporary connections")
        print("   Solution: Increase DB_MAX_OVERFLOW or optimize query performance")
    else:
        print("✅ No overflow connections")
    
    # Test connection wait time
    print("\n📋 Step 2: Testing connection wait time...")
    wait_times = []
    for i in range(5):
        start = time.time()
        with db_manager.get_session() as test_session:
            test_session.execute(text("SELECT 1"))
        wait_time = (time.time() - start) * 1000  # Convert to ms
        wait_times.append(wait_time)
    
    avg_wait = sum(wait_times) / len(wait_times)
    max_wait = max(wait_times)
    
    print(f"   Average wait time: {avg_wait:.2f}ms")
    print(f"   Max wait time: {max_wait:.2f}ms")
    
    if max_wait > 10:
        print("⚠️  PROBLEM: Connection wait time is too high!")
        print("   Target: <10ms")
        print("   Solution: Increase pool size or optimize queries")
    else:
        print("✅ Connection wait time is acceptable")
    
    # Get performance monitor metrics
    monitor = optimizer.get_performance_monitor()
    metrics = monitor.get_metrics()
    
    print(f"\n📋 Step 3: Performance Monitor Metrics:")
    print(f"   Total requests: {metrics.get('total_requests', 0)}")
    print(f"   Avg response time: {metrics.get('avg_response_time_ms', 0):.2f}ms")
    print(f"   Slow requests: {metrics.get('slow_requests', 0)}")
    print(f"   Error rate: {metrics.get('error_rate', 0):.1f}%")


def main():
    """Main entry point for debugging failed metrics."""
    print("=" * 80)
    print("🔧 DEEP DIVE DEBUG TOOLS FOR FAILED METRICS")
    print("=" * 80)
    
    # Initialize optimizer
    print("\n📋 Initializing optimizer...")
    redis_client = new_redis_client()
    optimizer = OptimizationStack(
        db_connection=db_manager,
        redis_client=redis_client,
        cache_ttl=settings.REDIS_CACHE_TTL or 300,
    )
    print("✅ Optimizer initialized")
    
    # Get database session
    print("\n📋 Getting database session...")
    with db_manager.get_session() as session:
        print("✅ Database session acquired")
        
        # Run all debug functions
        try:
            debug_cache_effectiveness(optimizer, session)
        except Exception as e:
            print(f"\n❌ Error in cache debugging: {e}")
            import traceback
            traceback.print_exc()
        
        try:
            debug_query_performance(optimizer, session)
        except Exception as e:
            print(f"\n❌ Error in query performance debugging: {e}")
            import traceback
            traceback.print_exc()
        
        try:
            debug_connection_pool(optimizer)
        except Exception as e:
            print(f"\n❌ Error in connection pool debugging: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 80)
    print("✅ DEBUG COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()

