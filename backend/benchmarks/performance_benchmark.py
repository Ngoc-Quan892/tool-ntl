"""
Performance benchmark system to measure before/after optimization.

This module provides:
- Benchmark targets and baseline measurements
- Performance measurement utilities
- Comparison and reporting
- Integration with monitoring system
"""

from __future__ import annotations

import asyncio
import json
import logging
import statistics
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

import httpx

from app.core.config import get_settings
from app.models.database import db_manager
from app.services.performance_optimizer import OptimizationStack

logger = logging.getLogger(__name__)
settings = get_settings()


# ==================== BENCHMARK TARGETS ====================

TARGETS = {
    # API Response Times
    "get_game_results": {
        "baseline": 250,      # ms (before optimization)
        "target": 25,         # ms (after optimization)
        "improvement": "10x",
        "description": "Get game results endpoint",
    },
    
    "get_pattern_stats": {
        "baseline": 800,
        "target": 80,
        "improvement": "10x",
        "description": "Get pattern statistics endpoint",
    },
    
    # Cache Performance
    "cache_hit_rate": {
        "baseline": 0,        # No cache before
        "target": 0.85,       # 85% hit rate
        "improvement": "∞",
        "description": "Cache hit rate percentage",
    },
    
    # Throughput
    "requests_per_second": {
        "baseline": 100,
        "target": 1000,
        "improvement": "10x",
        "description": "Requests per second throughput",
    },
    
    # Resource Usage
    "database_connections": {
        "baseline": 50,       # Many connections
        "target": 10,         # Pooled efficiently
        "improvement": "5x reduction",
        "description": "Active database connections",
    },
    
    # Additional metrics
    "avg_query_time_ms": {
        "baseline": 150,
        "target": 15,
        "improvement": "10x",
        "description": "Average database query time",
    },
    
    "slow_query_rate": {
        "baseline": 0.15,     # 15% slow queries
        "target": 0.01,       # 1% slow queries
        "improvement": "15x reduction",
        "description": "Percentage of slow queries (>100ms)",
    },
    
    "memory_usage_mb": {
        "baseline": 500,
        "target": 200,
        "improvement": "2.5x reduction",
        "description": "Memory usage in MB",
    },
}


@dataclass
class BenchmarkResult:
    """Result of a single benchmark measurement."""
    
    metric_name: str
    measured_value: float
    baseline: float
    target: float
    improvement_ratio: float = field(init=False)
    meets_target: bool = field(init=False)
    description: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def __post_init__(self):
        """Calculate improvement ratio and target status."""
        if self.baseline > 0:
            # For metrics where lower is better (response time, connections, etc.)
            if self.target < self.baseline:
                self.improvement_ratio = self.baseline / self.measured_value
                self.meets_target = self.measured_value <= self.target
            # For metrics where higher is better (hit rate, throughput, etc.)
            else:
                self.improvement_ratio = self.measured_value / self.baseline
                self.meets_target = self.measured_value >= self.target
        else:
            # Baseline is 0 (e.g., no cache before)
            self.improvement_ratio = float('inf') if self.measured_value > 0 else 0.0
            self.meets_target = self.measured_value >= self.target


@dataclass
class BenchmarkReport:
    """Complete benchmark report with all results."""
    
    timestamp: datetime = field(default_factory=datetime.utcnow)
    results: List[BenchmarkResult] = field(default_factory=list)
    summary: Dict[str, Any] = field(default_factory=dict)
    
    def add_result(self, result: BenchmarkResult) -> None:
        """Add a benchmark result."""
        self.results.append(result)
    
    def calculate_summary(self) -> Dict[str, Any]:
        """Calculate summary statistics."""
        total_metrics = len(self.results)
        metrics_meeting_target = sum(1 for r in self.results if r.meets_target)
        metrics_below_target = total_metrics - metrics_meeting_target
        
        avg_improvement = statistics.mean([
            r.improvement_ratio for r in self.results 
            if r.improvement_ratio != float('inf') and r.improvement_ratio > 0
        ]) if self.results else 0.0
        
        self.summary = {
            "total_metrics": total_metrics,
            "metrics_meeting_target": metrics_meeting_target,
            "metrics_below_target": metrics_below_target,
            "success_rate": (metrics_meeting_target / total_metrics * 100) if total_metrics > 0 else 0.0,
            "average_improvement": avg_improvement,
            "timestamp": self.timestamp.isoformat(),
        }
        
        return self.summary
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert report to dictionary."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "summary": self.summary,
            "results": [
                {
                    "metric_name": r.metric_name,
                    "measured_value": r.measured_value,
                    "baseline": r.baseline,
                    "target": r.target,
                    "improvement_ratio": r.improvement_ratio if r.improvement_ratio != float('inf') else "∞",
                    "meets_target": r.meets_target,
                    "description": r.description,
                }
                for r in self.results
            ],
        }
    
    def to_json(self) -> str:
        """Convert report to JSON string."""
        return json.dumps(self.to_dict(), indent=2)


class PerformanceBenchmark:
    """Performance benchmark runner."""
    
    def __init__(self, optimizer: Optional[OptimizationStack] = None, base_url: str = "http://localhost:8000"):
        """
        Initialize benchmark runner.
        
        Args:
            optimizer: OptimizationStack instance (optional)
            base_url: Base URL for API endpoints
        """
        self.optimizer = optimizer
        self.base_url = base_url
        self.report = BenchmarkReport()
    
    async def measure_api_response_time(
        self,
        endpoint: str,
        method: str = "GET",
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        iterations: int = 10,
    ) -> float:
        """
        Measure API endpoint response time.
        
        Args:
            endpoint: API endpoint path
            method: HTTP method
            params: Query parameters
            json_data: JSON body for POST requests
            iterations: Number of iterations to average
            
        Returns:
            Average response time in milliseconds
        """
        url = f"{self.base_url}{endpoint}"
        times = []
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            for _ in range(iterations):
                start = time.perf_counter()
                try:
                    if method == "GET":
                        response = await client.get(url, params=params)
                    elif method == "POST":
                        response = await client.post(url, json=json_data, params=params)
                    else:
                        raise ValueError(f"Unsupported method: {method}")
                    
                    response.raise_for_status()
                    elapsed = (time.perf_counter() - start) * 1000  # Convert to ms
                    times.append(elapsed)
                except Exception as exc:
                    logger.error(f"Error measuring {endpoint}: {exc}")
                    # Use a high value for failed requests
                    times.append(10000.0)
        
        return statistics.mean(times) if times else 0.0
    
    async def measure_cache_hit_rate(self) -> float:
        """
        Measure cache hit rate from optimizer.
        
        Returns:
            Cache hit rate as a float (0.0 to 1.0)
        """
        if not self.optimizer:
            return 0.0
        
        try:
            cache_manager = self.optimizer.get_cache_manager()
            stats = cache_manager.get_stats()
            
            local_hits = stats.get("stats", {}).get("local_hits", 0)
            local_misses = stats.get("stats", {}).get("local_misses", 0)
            redis_hits = stats.get("stats", {}).get("redis_hits", 0)
            redis_misses = stats.get("stats", {}).get("redis_misses", 0)
            
            total_hits = local_hits + redis_hits
            total_misses = local_misses + redis_misses
            total_requests = total_hits + total_misses
            
            if total_requests == 0:
                return 0.0
            
            return total_hits / total_requests
        except Exception as exc:
            logger.error(f"Error measuring cache hit rate: {exc}")
            return 0.0
    
    async def measure_throughput(
        self,
        endpoint: str,
        method: str = "GET",
        duration_seconds: int = 10,
        concurrency: int = 10,
    ) -> float:
        """
        Measure requests per second throughput.
        
        Args:
            endpoint: API endpoint path
            method: HTTP method
            duration_seconds: Duration of test
            concurrency: Number of concurrent requests
            
        Returns:
            Requests per second
        """
        url = f"{self.base_url}{endpoint}"
        request_count = 0
        start_time = time.time()
        end_time = start_time + duration_seconds
        
        async def make_request():
            nonlocal request_count
            async with httpx.AsyncClient(timeout=5.0) as client:
                while time.time() < end_time:
                    try:
                        if method == "GET":
                            await client.get(url)
                        elif method == "POST":
                            await client.post(url, json={})
                        request_count += 1
                    except Exception:
                        pass
                    # Small delay to avoid overwhelming
                    await asyncio.sleep(0.01)
        
        # Run concurrent requests
        tasks = [make_request() for _ in range(concurrency)]
        await asyncio.gather(*tasks)
        
        elapsed = time.time() - start_time
        return request_count / elapsed if elapsed > 0 else 0.0
    
    async def measure_database_connections(self) -> int:
        """
        Measure active database connections.
        
        Returns:
            Number of active connections
        """
        if not self.optimizer:
            return 0
        
        try:
            from app.services.performance_optimizer import ConnectionPoolManager
            
            if hasattr(db_manager, "engine") and db_manager.engine:
                pool_status = ConnectionPoolManager.get_pool_status(db_manager.engine)
                return pool_status.get("checked_out", 0)
        except Exception as exc:
            logger.error(f"Error measuring database connections: {exc}")
        
        return 0
    
    async def measure_query_performance(self) -> Dict[str, float]:
        """
        Measure query performance metrics.
        
        Returns:
            Dictionary with avg_query_time_ms and slow_query_rate
        """
        if not self.optimizer:
            return {"avg_query_time_ms": 0.0, "slow_query_rate": 0.0}
        
        try:
            with db_manager.get_session() as session:
                query_optimizer = self.optimizer.get_query_optimizer(session)
                query_stats = query_optimizer.get_query_statistics()
                
                total_queries = 0
                total_time_ms = 0.0
                slow_queries = 0
                
                for query_name, stats in query_stats.items():
                    count = stats.get("count", 0)
                    avg_time = stats.get("avg_time_ms", 0)
                    slow_count = stats.get("slow_queries", 0)
                    
                    total_queries += count
                    total_time_ms += avg_time * count
                    slow_queries += slow_count
                
                avg_query_time_ms = (total_time_ms / total_queries) if total_queries > 0 else 0.0
                slow_query_rate = (slow_queries / total_queries) if total_queries > 0 else 0.0
                
                return {
                    "avg_query_time_ms": avg_query_time_ms,
                    "slow_query_rate": slow_query_rate,
                }
        except Exception as exc:
            logger.error(f"Error measuring query performance: {exc}")
            return {"avg_query_time_ms": 0.0, "slow_query_rate": 0.0}
    
    async def measure_memory_usage(self) -> float:
        """
        Measure memory usage.
        
        Returns:
            Memory usage in MB
        """
        try:
            import psutil
            process = psutil.Process()
            memory_mb = process.memory_info().rss / 1024 / 1024
            return memory_mb
        except ImportError:
            logger.warning("psutil not available, cannot measure memory")
            return 0.0
        except Exception as exc:
            logger.error(f"Error measuring memory: {exc}")
            return 0.0
    
    async def run_benchmark(self, metric_name: str) -> BenchmarkResult:
        """
        Run benchmark for a specific metric.
        
        Args:
            metric_name: Name of metric to benchmark
            
        Returns:
            BenchmarkResult
        """
        target_config = TARGETS.get(metric_name)
        if not target_config:
            raise ValueError(f"Unknown metric: {metric_name}")
        
        logger.info(f"Benchmarking {metric_name}...")
        
        measured_value = 0.0
        
        # Measure based on metric type
        if metric_name == "get_game_results":
            measured_value = await self.measure_api_response_time(
                "/api/v2/game/1/results",
                iterations=20,
            )
        elif metric_name == "get_pattern_stats":
            measured_value = await self.measure_api_response_time(
                "/api/v2/analysis/pattern",
                params={"pattern_type": "all", "days": 7},
                iterations=10,
            )
        elif metric_name == "cache_hit_rate":
            hit_rate = await self.measure_cache_hit_rate()
            measured_value = hit_rate  # Already 0.0 to 1.0
        elif metric_name == "requests_per_second":
            measured_value = await self.measure_throughput(
                "/api/v2/game/1/results",
                duration_seconds=5,
                concurrency=20,
            )
        elif metric_name == "database_connections":
            measured_value = await self.measure_database_connections()
        elif metric_name == "avg_query_time_ms":
            query_perf = await self.measure_query_performance()
            measured_value = query_perf.get("avg_query_time_ms", 0.0)
        elif metric_name == "slow_query_rate":
            query_perf = await self.measure_query_performance()
            measured_value = query_perf.get("slow_query_rate", 0.0)
        elif metric_name == "memory_usage_mb":
            measured_value = await self.measure_memory_usage()
        else:
            logger.warning(f"No measurement method for {metric_name}")
        
        result = BenchmarkResult(
            metric_name=metric_name,
            measured_value=measured_value,
            baseline=target_config["baseline"],
            target=target_config["target"],
            description=target_config.get("description", ""),
        )
        
        return result
    
    async def run_all_benchmarks(self) -> BenchmarkReport:
        """
        Run all benchmarks and generate report.
        
        Returns:
            BenchmarkReport with all results
        """
        logger.info("Starting comprehensive benchmark...")
        
        self.report = BenchmarkReport()
        
        for metric_name in TARGETS.keys():
            try:
                result = await self.run_benchmark(metric_name)
                self.report.add_result(result)
                logger.info(
                    f"{metric_name}: {result.measured_value:.2f} "
                    f"(target: {result.target:.2f}, "
                    f"improvement: {result.improvement_ratio:.2f}x, "
                    f"meets target: {result.meets_target})"
                )
            except Exception as exc:
                logger.error(f"Error benchmarking {metric_name}: {exc}")
        
        self.report.calculate_summary()
        
        return self.report
    
    def get_failed_metrics(self) -> List[BenchmarkResult]:
        """
        Get list of metrics that failed to meet targets.
        
        Returns:
            List of BenchmarkResult objects that don't meet targets
        """
        return [r for r in self.report.results if not r.meets_target]
    
    def identify_bottleneck(self, result: BenchmarkResult) -> str:
        """
        Identify potential bottleneck for a failed metric.
        
        Args:
            result: BenchmarkResult that failed
            
        Returns:
            String describing potential bottleneck
        """
        metric_name = result.metric_name
        measured = result.measured_value
        target = result.target
        
        # API response time bottlenecks
        if "get_game_results" in metric_name or "get_pattern_stats" in metric_name:
            if measured > target * 2:
                return "Very slow - Check database queries, indexes, or network latency"
            elif measured > target * 1.5:
                return "Slow - Review query optimization and caching strategy"
            else:
                return "Slightly over target - Minor optimization needed"
        
        # Cache hit rate bottlenecks
        elif "cache_hit_rate" in metric_name:
            if measured < 0.5:
                return "Low cache hit rate - Check cache TTL, invalidation strategy, or cache size"
            elif measured < 0.7:
                return "Moderate cache hit rate - Review cache keys and access patterns"
            else:
                return "Close to target - Fine-tune cache configuration"
        
        # Throughput bottlenecks
        elif "requests_per_second" in metric_name:
            if measured < target * 0.5:
                return "Very low throughput - Check server resources, connection pooling, or bottlenecks"
            elif measured < target * 0.8:
                return "Below target - Review async processing and concurrency limits"
            else:
                return "Close to target - Minor scaling needed"
        
        # Database connection bottlenecks
        elif "database_connections" in metric_name:
            if measured > target * 2:
                return "Too many connections - Check connection pooling, leaks, or query efficiency"
            elif measured > target * 1.5:
                return "Above target - Review connection pool size and query patterns"
            else:
                return "Slightly over - Optimize connection usage"
        
        # Query performance bottlenecks
        elif "query_time" in metric_name or "slow_query" in metric_name:
            if measured > target * 2:
                return "Very slow queries - Add indexes, optimize queries, or review database schema"
            elif measured > target * 1.5:
                return "Slow queries - Review query patterns and add missing indexes"
            else:
                return "Slightly over - Fine-tune query optimization"
        
        # Memory bottlenecks
        elif "memory" in metric_name:
            if measured > target * 2:
                return "High memory usage - Check for memory leaks, reduce cache size, or scale resources"
            elif measured > target * 1.5:
                return "Above target - Review cache configuration and memory-intensive operations"
            else:
                return "Slightly over - Optimize memory usage"
        
        return "Unknown bottleneck - Review metric configuration"
    
    def print_failed_metrics(self) -> None:
        """Print detailed breakdown of failed metrics."""
        failed = self.get_failed_metrics()
        
        if not failed:
            print("\n✅ All metrics meet their targets!")
            return
        
        print("\n" + "=" * 80)
        print("❌ METRICS CẦN IMPROVE")
        print("=" * 80)
        print(f"Total Failed: {len(failed)}/{len(self.report.results)}")
        print()
        
        for result in failed:
            bottleneck = self.identify_bottleneck(result)
            gap = abs(result.measured_value - result.target)
            
            # Determine if higher or lower is better
            if result.target < result.baseline:
                # Lower is better (response time, connections, etc.)
                direction = "slower" if result.measured_value > result.target else "faster"
                gap_pct = (gap / result.target * 100) if result.target > 0 else 0
            else:
                # Higher is better (hit rate, throughput, etc.)
                direction = "lower" if result.measured_value < result.target else "higher"
                gap_pct = (gap / result.target * 100) if result.target > 0 else 0
            
            print(f"Metric: {result.metric_name}")
            print(f"  Description: {result.description}")
            print(f"  Current: {result.measured_value:.2f}")
            print(f"  Target: {result.target:.2f}")
            print(f"  Baseline: {result.baseline:.2f}")
            print(f"  Gap: {gap:.2f} ({gap_pct:.1f}% {'over' if direction in ['slower', 'lower'] else 'under'} target)")
            print(f"  Improvement: {result.improvement_ratio:.2f}x" if result.improvement_ratio != float('inf') else "  Improvement: ∞")
            print(f"  Bottleneck: {bottleneck}")
            print()
        
        print("=" * 80)
    
    def print_report(self) -> None:
        """Print benchmark report to console."""
        print("\n" + "=" * 80)
        print("PERFORMANCE BENCHMARK REPORT")
        print("=" * 80)
        print(f"Timestamp: {self.report.timestamp.isoformat()}")
        print(f"\nSummary:")
        print(f"  Total Metrics: {self.report.summary.get('total_metrics', 0)}")
        print(f"  Metrics Meeting Target: {self.report.summary.get('metrics_meeting_target', 0)}")
        print(f"  Metrics Failed: {self.report.summary.get('metrics_below_target', 0)}")
        print(f"  Success Rate: {self.report.summary.get('success_rate', 0):.1f}%")
        print(f"  Average Improvement: {self.report.summary.get('average_improvement', 0):.2f}x")
        
        print(f"\nDetailed Results:")
        print("-" * 80)
        for result in self.report.results:
            status = "✅" if result.meets_target else "❌"
            improvement_str = f"{result.improvement_ratio:.2f}x" if result.improvement_ratio != float('inf') else "∞"
            print(f"{status} {result.metric_name}")
            print(f"    Measured: {result.measured_value:.2f}")
            print(f"    Baseline: {result.baseline:.2f}")
            print(f"    Target: {result.target:.2f}")
            print(f"    Improvement: {improvement_str}")
            print(f"    Description: {result.description}")
            print()
        
        print("=" * 80)
        
        # Print failed metrics breakdown
        self.print_failed_metrics()


async def main():
    """Main benchmark runner."""
    from app.services.performance_optimizer import OptimizationStack, new_redis_client
    
    # Initialize optimizer
    redis_client = new_redis_client()
    optimizer = OptimizationStack(
        db_connection=db_manager,
        redis_client=redis_client,
    )
    
    # Create benchmark runner
    benchmark = PerformanceBenchmark(optimizer=optimizer)
    
    # Run all benchmarks
    report = await benchmark.run_all_benchmarks()
    
    # Print report
    benchmark.print_report()
    
    # Save report to file
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    report_file = f"benchmark_report_{timestamp}.json"
    with open(report_file, "w") as f:
        f.write(report.to_json())
    
    print(f"\nReport saved to: {report_file}")
    
    # Return report for programmatic access
    return report


if __name__ == "__main__":
    asyncio.run(main())

