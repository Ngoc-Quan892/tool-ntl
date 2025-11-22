"""
Intelligent cache warming service for application startup.

This service pre-loads critical data into cache before serving traffic,
with support for different warming strategies and progress tracking.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Callable, Coroutine, Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.database import db_manager, GameResult
from app.services.performance_optimizer import OptimizationStack

logger = logging.getLogger(__name__)

# Warming strategies configuration
WARMING_STRATEGIES = {
    "minimal": {
        "priority_0": {"games": 5},
        "priority_1": {"games": 10},
        "priority_2": {"patterns": 3, "time_ranges": [7]},
        "priority_3": {"users": 20},
        "timeout_seconds": 30,
    },
    "moderate": {
        "priority_0": {"games": 5},
        "priority_1": {"games": 50},
        "priority_2": {"patterns": 10, "time_ranges": [7, 30]},
        "priority_3": {"users": 100},
        "timeout_seconds": 120,
    },
    "aggressive": {
        "priority_0": {"games": 10},
        "priority_1": {"games": 200},
        "priority_2": {"patterns": 20, "time_ranges": [7, 14, 30, 90]},
        "priority_3": {"users": 500},
        "priority_4": {"historical": True},
        "timeout_seconds": 600,
    },
}


class CacheWarmer:
    """
    Intelligent cache warming service.
    
    Pre-loads critical data into cache with configurable strategies,
    progress tracking, and graceful error handling.
    """

    def __init__(
        self,
        optimizer: OptimizationStack,
        strategy: str = "moderate",
        max_concurrent: int = 10,
    ):
        """
        Initialize CacheWarmer.
        
        Args:
            optimizer: OptimizationStack instance with cache manager
            strategy: Warming strategy (minimal, moderate, aggressive)
            max_concurrent: Maximum concurrent warming tasks
        """
        self.optimizer = optimizer
        self.strategy = strategy.lower()
        self.max_concurrent = max_concurrent
        self.logger = logging.getLogger(__name__)
        
        if self.strategy not in WARMING_STRATEGIES:
            raise ValueError(f"Invalid strategy: {strategy}. Must be one of {list(WARMING_STRATEGIES.keys())}")
        
        self.config = WARMING_STRATEGIES[self.strategy]
        self.stats: Dict[str, Any] = {
            "items_warmed": 0,
            "items_failed": 0,
            "cache_keys": [],
            "items_by_category": {
                "game_results": 0,
                "pattern_stats": 0,
                "user_sessions": 0,
                "aggregations": 0,
            },
            "start_time": None,
            "end_time": None,
        }
        self.progress_tracker: Dict[str, Dict[str, Any]] = {}
        self.progress_callback: Optional[Callable[[int, int, str], None]] = None

    async def warm_cache(self) -> Dict[str, Any]:
        """
        Main method to warm cache based on configured strategy.
        
        Returns:
            Dict with warming statistics including:
            - strategy: Strategy used
            - items_warmed: Total items successfully warmed
            - items_failed: Total items that failed
            - success_rate: Success rate (0.0-1.0)
            - time_taken_seconds: Total time taken
            - cache_hit_rate_before: Cache hit rate before warming
            - cache_hit_rate_after: Cache hit rate after warming
            - items_by_category: Breakdown by category
        """
        self.logger.info(f"🔥 Starting cache warming with strategy: {self.strategy}")
        self.stats["start_time"] = datetime.utcnow()
        
        try:
            # Get baseline cache hit rate
            cache_hit_rate_before = self._verify_cache_hit_rate()
            self.logger.info(f"Cache hit rate before warming: {cache_hit_rate_before:.2%}")
            
            # Initialize stats
            self.stats = {
                "items_warmed": 0,
                "items_failed": 0,
                "cache_keys": [],
                "items_by_category": {
                    "game_results": 0,
                    "pattern_stats": 0,
                    "user_sessions": 0,
                    "aggregations": 0,
                },
                "start_time": self.stats["start_time"],
                "end_time": None,
            }
            
            # Warm by priority level
            try:
                # P0: Active games (most critical)
                self.logger.info("Warming Priority 0: Active games")
                p0_keys = await self._warm_priority_0()
                self.stats["cache_keys"].extend(p0_keys)
                self.stats["items_by_category"]["game_results"] += len(p0_keys)
                
                # P1: Popular games
                self.logger.info("Warming Priority 1: Popular games")
                p1_keys = await self._warm_priority_1()
                self.stats["cache_keys"].extend(p1_keys)
                self.stats["items_by_category"]["game_results"] += len(p1_keys)
                
                # P2: Pattern statistics
                self.logger.info("Warming Priority 2: Pattern statistics")
                p2_keys = await self._warm_priority_2()
                self.stats["cache_keys"].extend(p2_keys)
                self.stats["items_by_category"]["pattern_stats"] += len(p2_keys)
                
                # P3: User sessions
                self.logger.info("Warming Priority 3: User sessions")
                p3_keys = await self._warm_priority_3()
                self.stats["cache_keys"].extend(p3_keys)
                self.stats["items_by_category"]["user_sessions"] += len(p3_keys)
                
            except Exception as exc:
                self.logger.error(f"Error during cache warming: {exc}", exc_info=True)
            
            # Verify cache hit rate improved
            cache_hit_rate_after = self._verify_cache_hit_rate()
            self.logger.info(f"Cache hit rate after warming: {cache_hit_rate_after:.2%}")
            
            # Generate final report
            self.stats["end_time"] = datetime.utcnow()
            report = self._generate_report(cache_hit_rate_before, cache_hit_rate_after)
            
            self.logger.info(
                f"✅ Cache warming completed: {report['items_warmed']} items warmed, "
                f"{report['success_rate']:.1%} success rate, "
                f"{report['time_taken_seconds']:.1f}s"
            )
            
            return report
            
        except Exception as exc:
            self.logger.error(f"Cache warming failed: {exc}", exc_info=True)
            self.stats["end_time"] = datetime.utcnow()
            return self._generate_report(0.0, 0.0)

    async def _warm_priority_0(self) -> List[str]:
        """
        Warm Priority 0: Active games (most critical).
        
        Returns:
            List of cache keys warmed
        """
        cache_keys: List[str] = []
        num_games = self.config["priority_0"]["games"]
        
        try:
            with db_manager.get_session() as session:
                # Query for active games (games with activity in last hour)
                query = text("""
                    SELECT DISTINCT shoe_number
                    FROM game_results
                    WHERE timestamp >= CURRENT_TIMESTAMP - INTERVAL '1 hour'
                    GROUP BY shoe_number
                    ORDER BY MAX(timestamp) DESC
                    LIMIT :limit
                """)
                
                result = session.execute(query, {"limit": num_games})
                active_game_ids = [row[0] for row in result.fetchall()]
                
                if not active_game_ids:
                    # Fallback: get most recent games
                    fallback_query = text("""
                        SELECT DISTINCT shoe_number
                        FROM game_results
                        GROUP BY shoe_number
                        ORDER BY MAX(timestamp) DESC
                        LIMIT :limit
                    """)
                    result = session.execute(fallback_query, {"limit": num_games})
                    active_game_ids = [row[0] for row in result.fetchall()]
                
                self.logger.info(f"Found {len(active_game_ids)} active games to warm")
                
                # Warm each game
                semaphore = asyncio.Semaphore(self.max_concurrent)
                tasks = [
                    self._warm_with_semaphore(
                        semaphore,
                        self._warm_game_results(game_id, limit=100)
                    )
                    for game_id in active_game_ids
                ]
                
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                for i, result in enumerate(results):
                    if isinstance(result, Exception):
                        self.logger.warning(f"Failed to warm game {active_game_ids[i]}: {result}")
                        self.stats["items_failed"] += 1
                    elif result:
                        cache_key = self.optimizer.cache_manager._generate_key(
                            "game_results", "get_game_results", active_game_ids[i], limit=100
                        )
                        cache_keys.append(cache_key)
                        self.stats["items_warmed"] += 1
                    else:
                        self.stats["items_failed"] += 1
                        
        except Exception as exc:
            self.logger.error(f"Error warming priority 0: {exc}", exc_info=True)
        
        return cache_keys

    async def _warm_priority_1(self) -> List[str]:
        """
        Warm Priority 1: Popular games.
        
        Returns:
            List of cache keys warmed
        """
        cache_keys: List[str] = []
        num_games = self.config["priority_1"]["games"]
        
        try:
            with db_manager.get_session() as session:
                # Query for popular games (by access count, last 7 days)
                query = text("""
                    SELECT shoe_number, COUNT(*) as access_count
                    FROM game_results
                    WHERE timestamp >= CURRENT_TIMESTAMP - INTERVAL '7 days'
                    GROUP BY shoe_number
                    ORDER BY access_count DESC
                    LIMIT :limit
                """)
                
                result = session.execute(query, {"limit": num_games})
                popular_games = [(row[0], row[1]) for row in result.fetchall()]
                
                if not popular_games:
                    # Fallback: get games with most results
                    fallback_query = text("""
                        SELECT shoe_number, COUNT(*) as result_count
                        FROM game_results
                        GROUP BY shoe_number
                        ORDER BY result_count DESC
                        LIMIT :limit
                    """)
                    result = session.execute(fallback_query, {"limit": num_games})
                    popular_games = [(row[0], row[1]) for row in result.fetchall()]
                
                self.logger.info(f"Found {len(popular_games)} popular games to warm")
                
                # Update progress
                total = len(popular_games)
                self._update_progress(0, total, "popular_games")
                
                # Warm each game with concurrency control
                semaphore = asyncio.Semaphore(self.max_concurrent)
                tasks = [
                    self._warm_with_semaphore(
                        semaphore,
                        self._warm_game_results(game_id, limit=100)
                    )
                    for game_id, _ in popular_games
                ]
                
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                for i, (result, (game_id, _)) in enumerate(zip(results, popular_games)):
                    self._update_progress(i + 1, total, "popular_games")
                    
                    if isinstance(result, Exception):
                        self.logger.warning(f"Failed to warm game {game_id}: {result}")
                        self.stats["items_failed"] += 1
                    elif result:
                        cache_key = self.optimizer.cache_manager._generate_key(
                            "game_results", "get_game_results", game_id, limit=100
                        )
                        cache_keys.append(cache_key)
                        self.stats["items_warmed"] += 1
                    else:
                        self.stats["items_failed"] += 1
                        
        except Exception as exc:
            self.logger.error(f"Error warming priority 1: {exc}", exc_info=True)
        
        return cache_keys

    async def _warm_priority_2(self) -> List[str]:
        """
        Warm Priority 2: Pattern statistics.
        
        Returns:
            List of cache keys warmed
        """
        cache_keys: List[str] = []
        patterns = ["banker_streak", "player_streak", "alternating", "tie_pattern", "B", "P", "T", "all"]
        num_patterns = min(self.config["priority_2"]["patterns"], len(patterns))
        time_ranges = self.config["priority_2"]["time_ranges"]
        
        patterns_to_warm = patterns[:num_patterns]
        
        try:
            with db_manager.get_session() as session:
                query_optimizer = self.optimizer.get_query_optimizer(session)
                
                total_tasks = len(patterns_to_warm) * len(time_ranges)
                self._update_progress(0, total_tasks, "pattern_stats")
                
                semaphore = asyncio.Semaphore(self.max_concurrent)
                tasks = []
                
                for pattern in patterns_to_warm:
                    for days in time_ranges:
                        task = self._warm_with_semaphore(
                            semaphore,
                            self._warm_pattern_statistics(pattern, days)
                        )
                        tasks.append((task, pattern, days))
                
                results = await asyncio.gather(*[t[0] for t in tasks], return_exceptions=True)
                
                for i, ((result, pattern, days), task_result) in enumerate(zip(tasks, results)):
                    self._update_progress(i + 1, total_tasks, "pattern_stats")
                    
                    if isinstance(task_result, Exception):
                        self.logger.warning(f"Failed to warm pattern {pattern} (days={days}): {task_result}")
                        self.stats["items_failed"] += 1
                    elif task_result:
                        cache_key = self.optimizer.cache_manager._generate_key(
                            "pattern_stats", "get_pattern_statistics", pattern, days=days
                        )
                        cache_keys.append(cache_key)
                        self.stats["items_warmed"] += 1
                    else:
                        self.stats["items_failed"] += 1
                        
        except Exception as exc:
            self.logger.error(f"Error warming priority 2: {exc}", exc_info=True)
        
        return cache_keys

    async def _warm_priority_3(self) -> List[str]:
        """
        Warm Priority 3: User sessions.
        
        Note: This is a placeholder implementation since we don't have user sessions
        in the current schema. In a real implementation, this would warm user session data.
        
        Returns:
            List of cache keys warmed
        """
        cache_keys: List[str] = []
        num_users = self.config["priority_3"]["users"]
        
        # Since we don't have user sessions in the current schema,
        # we'll warm recent game aggregations instead
        try:
            with db_manager.get_session() as session:
                query_optimizer = self.optimizer.get_query_optimizer(session)
                
                # Warm aggregated statistics for recent periods
                time_ranges = [1, 7, 30]  # days
                total_tasks = len(time_ranges)
                self._update_progress(0, total_tasks, "aggregations")
                
                semaphore = asyncio.Semaphore(self.max_concurrent)
                tasks = []
                
                for days in time_ranges:
                    # Capture days in closure properly
                    async def warm_aggregation(days_param: int = days):
                        try:
                            stats = query_optimizer.get_aggregated_statistics(days=days_param)
                            if stats:
                                cache_key = self.optimizer.cache_manager._generate_key(
                                    "aggregated_stats", "get_aggregated_statistics", days=days_param
                                )
                                self.optimizer.cache_manager.set(cache_key, stats, ttl=300)
                                return True
                        except Exception as exc:
                            self.logger.warning(f"Failed to warm aggregation (days={days_param}): {exc}")
                            return False
                    
                    task = self._warm_with_semaphore(semaphore, warm_aggregation(days))
                    tasks.append((task, days))
                
                results = await asyncio.gather(*[t[0] for t in tasks], return_exceptions=True)
                
                for i, ((task, days), result) in enumerate(zip(tasks, results)):
                    self._update_progress(i + 1, total_tasks, "aggregations")
                    
                    if isinstance(result, Exception):
                        self.logger.warning(f"Failed to warm aggregation (days={days}): {result}")
                        self.stats["items_failed"] += 1
                    elif result:
                        cache_key = self.optimizer.cache_manager._generate_key(
                            "aggregated_stats", "get_aggregated_statistics", days=days
                        )
                        cache_keys.append(cache_key)
                        self.stats["items_warmed"] += 1
                        self.stats["items_by_category"]["aggregations"] += 1
                    else:
                        self.stats["items_failed"] += 1
                        
        except Exception as exc:
            self.logger.error(f"Error warming priority 3: {exc}", exc_info=True)
        
        return cache_keys

    async def _warm_game_results(self, game_id: int, limit: int = 100) -> bool:
        """
        Warm game results for a specific game.
        
        Args:
            game_id: Game/shoe ID to warm
            limit: Number of results to fetch
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with db_manager.get_session() as session:
                query_optimizer = self.optimizer.get_query_optimizer(session)
                cache_manager = self.optimizer.get_cache_manager()
                
                # Fetch game results (this will populate cache)
                results = query_optimizer.get_game_results(game_id, limit=limit)
                
                if results:
                    # Verify data was cached
                    cache_key = cache_manager._generate_key(
                        "game_results", "get_game_results", game_id, limit=limit
                    )
                    
                    # Explicitly cache the result
                    cache_manager.set(
                        cache_key,
                        {
                            "game_id": game_id,
                            "results": results,
                            "count": len(results),
                            "limit": limit,
                        },
                        ttl=60,
                    )
                    
                    # Verify cache key exists
                    cached_value = cache_manager.get(cache_key)
                    return cached_value is not None
                
                return False
                
        except Exception as exc:
            self.logger.warning(f"Failed to warm game results for game_id={game_id}: {exc}")
            return False

    async def _warm_pattern_statistics(self, pattern: str, days: int) -> bool:
        """
        Warm pattern statistics for a specific pattern and time range.
        
        Args:
            pattern: Pattern type to warm
            days: Time range in days
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with db_manager.get_session() as session:
                query_optimizer = self.optimizer.get_query_optimizer(session)
                cache_manager = self.optimizer.get_cache_manager()
                
                # Fetch pattern statistics (this will populate cache)
                stats = query_optimizer.get_pattern_statistics(pattern_type=pattern, days=days)
                
                if stats is not None:
                    # Verify data was cached
                    cache_key = cache_manager._generate_key(
                        "pattern_stats", "get_pattern_statistics", pattern, days=days
                    )
                    
                    # Explicitly cache the result
                    cache_manager.set(cache_key, stats, ttl=300)
                    
                    # Verify cache key exists
                    cached_value = cache_manager.get(cache_key)
                    return cached_value is not None
                
                return False
                
        except Exception as exc:
            self.logger.warning(f"Failed to warm pattern statistics for pattern={pattern}, days={days}: {exc}")
            return False

    def _verify_cache_hit_rate(self) -> float:
        """
        Check current cache hit rate.
        
        Returns:
            Cache hit rate (0.0-1.0)
        """
        try:
            cache_stats = self.optimizer.cache_manager.get_stats()
            local_hits = cache_stats["stats"]["local_hits"]
            local_misses = cache_stats["stats"]["local_misses"]
            redis_hits = cache_stats["stats"]["redis_hits"]
            redis_misses = cache_stats["stats"]["redis_misses"]
            
            total_hits = local_hits + redis_hits
            total_misses = local_misses + redis_misses
            total_requests = total_hits + total_misses
            
            if total_requests == 0:
                return 0.0
            
            return total_hits / total_requests
            
        except Exception as exc:
            self.logger.warning(f"Failed to verify cache hit rate: {exc}")
            return 0.0

    def set_progress_callback(
        self, callback: Callable[[int, int, str], None]
    ) -> None:
        """
        Set progress callback for external monitoring.
        
        Args:
            callback: Function called with (current, total, category) parameters
        """
        self.progress_callback = callback
    
    def _generate_report(
        self, cache_hit_rate_before: float, cache_hit_rate_after: float
    ) -> Dict[str, Any]:
        """
        Generate detailed warming report.
        
        Args:
            cache_hit_rate_before: Cache hit rate before warming
            cache_hit_rate_after: Cache hit rate after warming
            
        Returns:
            Dict with complete statistics
        """
        total_items = self.stats["items_warmed"] + self.stats["items_failed"]
        success_rate = (
            self.stats["items_warmed"] / total_items if total_items > 0 else 0.0
        )
        
        time_taken = 0.0
        if self.stats["start_time"] and self.stats["end_time"]:
            delta = self.stats["end_time"] - self.stats["start_time"]
            time_taken = delta.total_seconds()
        
        # Calculate items by priority
        items_by_priority = {
            "P0": self.stats["items_by_category"].get("game_results", 0) // 2,  # Approximate
            "P1": self.stats["items_by_category"].get("game_results", 0) // 2,
            "P2": self.stats["items_by_category"].get("pattern_stats", 0),
            "P3": self.stats["items_by_category"].get("user_sessions", 0) + 
                  self.stats["items_by_category"].get("aggregations", 0),
        }
        
        # Calculate improvement
        improvement = cache_hit_rate_after - cache_hit_rate_before
        improvement_str = f"{improvement*100:+.1f}%" if improvement != 0 else "0%"
        
        return {
            "strategy": self.strategy,
            "items_warmed": self.stats["items_warmed"],
            "items_failed": self.stats["items_failed"],
            "success_rate": round(success_rate, 3),
            "time_taken_seconds": round(time_taken, 1),
            "cache_hit_rate_before": round(cache_hit_rate_before, 3),
            "cache_hit_rate_after": round(cache_hit_rate_after, 3),
            "improvement": improvement_str,
            "items_by_category": self.stats["items_by_category"].copy(),
            "items_by_priority": items_by_priority,
        }

    def _update_progress(self, current: int, total: int, category: str) -> None:
        """
        Update progress tracking.
        
        Args:
            current: Items completed
            total: Total items to warm
            category: What's being warmed
        """
        if total == 0:
            return
        
        percentage = (current / total) * 100
        
        # Estimate time remaining
        if category not in self.progress_tracker:
            self.progress_tracker[category] = {
                "start_time": datetime.utcnow(),
                "last_update": datetime.utcnow(),
                "last_count": 0,
            }
        
        tracker = self.progress_tracker[category]
        now = datetime.utcnow()
        
        # Calculate rate
        elapsed = (now - tracker["start_time"]).total_seconds()
        if elapsed > 0 and current > 0:
            rate = current / elapsed  # items per second
            remaining = total - current
            eta_seconds = remaining / rate if rate > 0 else 0
            eta_str = f"{eta_seconds:.0f}s" if eta_seconds > 0 else "N/A"
        else:
            eta_str = "calculating..."
        
        if current % max(1, total // 10) == 0 or current == total:
            self.logger.info(
                f"Warming {category}: {current}/{total} ({percentage:.1f}%) - ETA {eta_str}"
            )
        
        # Call progress callback if set
        if self.progress_callback:
            try:
                self.progress_callback(current, total, category)
            except Exception as exc:
                self.logger.warning(f"Progress callback failed: {exc}")
        
        tracker["last_update"] = now
        tracker["last_count"] = current

    async def _warm_with_semaphore(
        self, semaphore: asyncio.Semaphore, coro: Coroutine
    ) -> Any:
        """
        Execute warming task with semaphore to limit concurrency.
        
        Args:
            semaphore: Semaphore to limit concurrent tasks
            coro: Coroutine to execute
            
        Returns:
            Result of coroutine
        """
        async with semaphore:
            return await coro

    async def _warm_with_retry(
        self,
        func: Callable[[], Coroutine],
        max_retries: int = 3,
        delay: float = 1.0,
    ) -> bool:
        """
        Execute warming function with retry logic.
        
        Args:
            func: Async function to execute
            max_retries: Maximum number of retries
            delay: Initial delay between retries (exponential backoff)
            
        Returns:
            True if successful after retries, False otherwise
        """
        for attempt in range(max_retries):
            try:
                result = await func()
                if result:
                    return True
            except Exception as exc:
                self.logger.warning(
                    f"Warming attempt {attempt + 1}/{max_retries} failed: {exc}"
                )
            
            if attempt < max_retries - 1:
                await asyncio.sleep(delay * (2 ** attempt))  # Exponential backoff
        
        return False
    
    async def verify_warming(self) -> Dict[str, Any]:
        """
        Verify warmed items actually in cache.
        
        Returns:
            Dict with verification results
        """
        self.logger.info("Verifying warmed cache items...")
        
        verification_results = {
            "total_checked": 0,
            "found_in_cache": 0,
            "missing_from_cache": 0,
            "verification_rate": 0.0,
            "missing_keys": [],
        }
        
        # Sample 10 random items that should be warmed
        cache_keys_to_check = self.stats["cache_keys"][:10] if len(self.stats["cache_keys"]) >= 10 else self.stats["cache_keys"]
        
        if not cache_keys_to_check:
            self.logger.warning("No cache keys to verify")
            return verification_results
        
        cache_manager = self.optimizer.get_cache_manager()
        
        for cache_key in cache_keys_to_check:
            verification_results["total_checked"] += 1
            cached_value = cache_manager.get(cache_key)
            
            if cached_value is not None:
                verification_results["found_in_cache"] += 1
            else:
                verification_results["missing_from_cache"] += 1
                verification_results["missing_keys"].append(cache_key)
                self.logger.warning(f"Cache key missing: {cache_key}")
        
        if verification_results["total_checked"] > 0:
            verification_results["verification_rate"] = (
                verification_results["found_in_cache"] / verification_results["total_checked"]
            )
        
        self.logger.info(
            f"Verification complete: {verification_results['found_in_cache']}/{verification_results['total_checked']} "
            f"({verification_results['verification_rate']:.1%})"
        )
        
        return verification_results
    
    def export_metrics(self) -> Dict[str, float]:
        """
        Export warming metrics to monitoring system.
        
        Returns:
            Dict with Prometheus-compatible metrics
        """
        time_taken = 0.0
        if self.stats["start_time"] and self.stats["end_time"]:
            delta = self.stats["end_time"] - self.stats["start_time"]
            time_taken = delta.total_seconds()
        
        metrics = {
            "cache_warming_duration_seconds": time_taken,
            "cache_warming_items_total": float(self.stats["items_warmed"]),
            "cache_warming_failures_total": float(self.stats["items_failed"]),
        }
        
        # Add per-category metrics
        for category, count in self.stats["items_by_category"].items():
            metrics[f"cache_warming_{category}_total"] = float(count)
        
        return metrics
    
    async def warm_based_on_traffic(self) -> Dict[str, Any]:
        """
        Intelligently warm based on traffic patterns.
        
        Analyzes last 24 hours of traffic and warms most accessed endpoints.
        
        Returns:
            Dict with warming statistics
        """
        self.logger.info("Analyzing traffic patterns for adaptive warming...")
        
        try:
            with db_manager.get_session() as session:
                # Analyze most accessed game IDs in last 24 hours
                query = text("""
                    SELECT shoe_number, COUNT(*) as access_count
                    FROM game_results
                    WHERE timestamp >= CURRENT_TIMESTAMP - INTERVAL '24 hours'
                    GROUP BY shoe_number
                    ORDER BY access_count DESC
                    LIMIT 50
                """)
                
                result = session.execute(query)
                popular_games = [(row[0], row[1]) for row in result.fetchall()]
                
                if not popular_games:
                    self.logger.warning("No traffic data found, using default warming")
                    return await self.warm_cache()
                
                self.logger.info(f"Found {len(popular_games)} games with recent activity")
                
                # Warm games in priority order (most accessed first)
                semaphore = asyncio.Semaphore(self.max_concurrent)
                tasks = [
                    self._warm_with_semaphore(
                        semaphore,
                        self._warm_game_results(game_id, limit=100)
                    )
                    for game_id, _ in popular_games
                ]
                
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                success_count = sum(1 for r in results if r is True and not isinstance(r, Exception))
                failed_count = len(results) - success_count
                
                self.stats["items_warmed"] += success_count
                self.stats["items_failed"] += failed_count
                
                # Adjust TTL based on access frequency
                # More popular = longer TTL
                cache_manager = self.optimizer.get_cache_manager()
                for (game_id, access_count), result in zip(popular_games, results):
                    if result is True:
                        cache_key = cache_manager._generate_key(
                            "game_results", "get_game_results", game_id, limit=100
                        )
                        # Higher access = longer TTL (60s to 300s)
                        ttl = min(60 + (access_count * 2), 300)
                        # Update TTL if key exists
                        cached = cache_manager.get(cache_key)
                        if cached:
                            cache_manager.set(cache_key, cached, ttl=ttl)
                
                return {
                    "strategy": "adaptive",
                    "items_warmed": success_count,
                    "items_failed": failed_count,
                    "games_analyzed": len(popular_games),
                }
                
        except Exception as exc:
            self.logger.error(f"Adaptive warming failed: {exc}", exc_info=True)
            return {
                "strategy": "adaptive",
                "items_warmed": 0,
                "items_failed": 0,
                "error": str(exc),
            }


# Schedule support (requires APScheduler)
try:
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from apscheduler.triggers.cron import CronTrigger
    HAS_SCHEDULER = True
except ImportError:
    HAS_SCHEDULER = False


def schedule_periodic_warming(
    warmer: CacheWarmer,
    interval_hours: int = 6,
    time_of_day: Optional[str] = None,
) -> Optional[Any]:
    """
    Schedule periodic cache warming.
    
    Args:
        warmer: CacheWarmer instance
        interval_hours: How often to warm (in hours)
        time_of_day: Optional specific time (e.g., "02:00")
        
    Returns:
        Scheduler instance if available, None otherwise
    """
    if not HAS_SCHEDULER:
        warmer.logger.warning(
            "APScheduler not available. Install with: pip install apscheduler"
        )
        return None
    
    scheduler = AsyncIOScheduler()
    
    if time_of_day:
        # Parse time (HH:MM)
        hour, minute = map(int, time_of_day.split(":"))
        trigger = CronTrigger(hour=hour, minute=minute)
        warmer.logger.info(f"Scheduled warming daily at {time_of_day}")
    else:
        # Use interval
        trigger = CronTrigger(hour=f"*/{interval_hours}")
        warmer.logger.info(f"Scheduled warming every {interval_hours} hours")
    
    async def warming_job():
        warmer.logger.info("Running scheduled cache warming...")
        try:
            report = await warmer.warm_cache()
            warmer.logger.info(
                f"Scheduled warming complete: {report['items_warmed']} items in "
                f"{report['time_taken_seconds']:.1f}s"
            )
        except Exception as exc:
            warmer.logger.error(f"Scheduled warming failed: {exc}", exc_info=True)
    
    scheduler.add_job(warming_job, trigger=trigger, id="cache_warming")
    scheduler.start()
    
    return scheduler


# CLI Interface
async def main():
    """CLI entry point for cache warming."""
    parser = argparse.ArgumentParser(description="Cache warming service")
    parser.add_argument(
        "--strategy",
        type=str,
        default="moderate",
        choices=["minimal", "moderate", "aggressive"],
        help="Warming strategy",
    )
    parser.add_argument(
        "--max-concurrent",
        type=int,
        default=10,
        help="Maximum concurrent warming tasks",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Verify cache after warming",
    )
    
    args = parser.parse_args()
    
    # Initialize OptimizationStack
    from app.core.config import get_settings
    from app.main import get_redis_client, get_mysql_pool
    
    settings = get_settings()
    redis_client = get_redis_client()
    db_connection = get_mysql_pool()
    
    optimizer = OptimizationStack(
        db_connection=db_connection,
        redis_client=redis_client,
        cache_ttl=settings.REDIS_CACHE_TTL or 300,
    )
    
    # Create CacheWarmer instance
    warmer = CacheWarmer(
        optimizer=optimizer,
        strategy=args.strategy,
        max_concurrent=args.max_concurrent,
    )
    
    # Run warming
    try:
        report = await warmer.warm_cache()
        
        # Print report
        print("\n" + "=" * 60)
        print("Cache Warming Report")
        print("=" * 60)
        print(f"Strategy: {report['strategy']}")
        print(f"Items warmed: {report['items_warmed']}")
        print(f"Items failed: {report['items_failed']}")
        print(f"Success rate: {report['success_rate']:.1%}")
        print(f"Time taken: {report['time_taken_seconds']:.1f}s")
        print(f"Cache hit rate before: {report['cache_hit_rate_before']:.1%}")
        print(f"Cache hit rate after: {report['cache_hit_rate_after']:.1%}")
        print("\nItems by category:")
        for category, count in report["items_by_category"].items():
            print(f"  - {category}: {count}")
        print("=" * 60)
        
        # Verify if requested
        if args.verify:
            print("\nVerifying cache...")
            verification = await warmer.verify_warming()
            print(f"Verification rate: {verification['verification_rate']:.1%}")
            print(f"Found in cache: {verification['found_in_cache']}/{verification['total_checked']}")
            if verification["missing_keys"]:
                print(f"Missing keys: {len(verification['missing_keys'])}")
        
        # Export metrics
        metrics = warmer.export_metrics()
        print("\nMetrics exported:")
        for key, value in metrics.items():
            print(f"  - {key}: {value}")
        
        exit_code = 0 if report["success_rate"] > 0.8 else 1
        exit(exit_code)
        
    except Exception as exc:
        logger.error(f"Cache warming failed: {exc}", exc_info=True)
        exit(1)


if __name__ == "__main__":
    asyncio.run(main())

