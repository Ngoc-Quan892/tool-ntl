"""
Script to analyze failed metrics from benchmark results.

Usage:
    python benchmarks/analyze_failed_metrics.py [benchmark_report.json]
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Any

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from benchmarks.performance_benchmark import PerformanceBenchmark, BenchmarkResult


def analyze_failed_metrics_from_report(report_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Analyze failed metrics from report data.
    
    Args:
        report_data: Report data dictionary
        
    Returns:
        List of failed metrics with analysis
    """
    failed_metrics = []
    
    for result_data in report_data.get("results", []):
        if not result_data.get("meets_target", True):
            metric_name = result_data["metric_name"]
            measured = result_data["measured_value"]
            target = result_data["target"]
            baseline = result_data["baseline"]
            
            gap = abs(measured - target)
            
            # Determine direction
            if target < baseline:
                # Lower is better
                direction = "slower" if measured > target else "faster"
                gap_pct = (gap / target * 100) if target > 0 else 0
            else:
                # Higher is better
                direction = "lower" if measured < target else "higher"
                gap_pct = (gap / target * 100) if target > 0 else 0
            
            # Identify bottleneck
            bottleneck = identify_bottleneck_static(metric_name, measured, target)
            
            failed_metrics.append({
                "name": metric_name,
                "measured": measured,
                "target": target,
                "baseline": baseline,
                "gap": gap,
                "gap_percent": gap_pct,
                "direction": direction,
                "bottleneck": bottleneck,
                "description": result_data.get("description", ""),
            })
    
    return failed_metrics


def identify_bottleneck_static(metric_name: str, measured: float, target: float) -> str:
    """
    Identify bottleneck for a metric (static version).
    
    Args:
        metric_name: Name of metric
        measured: Measured value
        target: Target value
        
    Returns:
        Bottleneck description
    """
    if "get_game_results" in metric_name or "get_pattern_stats" in metric_name:
        if measured > target * 2:
            return "Very slow - Check database queries, indexes, or network latency"
        elif measured > target * 1.5:
            return "Slow - Review query optimization and caching strategy"
        else:
            return "Slightly over target - Minor optimization needed"
    
    elif "cache_hit_rate" in metric_name:
        if measured < 0.5:
            return "Low cache hit rate - Check cache TTL, invalidation strategy, or cache size"
        elif measured < 0.7:
            return "Moderate cache hit rate - Review cache keys and access patterns"
        else:
            return "Close to target - Fine-tune cache configuration"
    
    elif "requests_per_second" in metric_name:
        if measured < target * 0.5:
            return "Very low throughput - Check server resources, connection pooling, or bottlenecks"
        elif measured < target * 0.8:
            return "Below target - Review async processing and concurrency limits"
        else:
            return "Close to target - Minor scaling needed"
    
    elif "database_connections" in metric_name:
        if measured > target * 2:
            return "Too many connections - Check connection pooling, leaks, or query efficiency"
        elif measured > target * 1.5:
            return "Above target - Review connection pool size and query patterns"
        else:
            return "Slightly over - Optimize connection usage"
    
    elif "query_time" in metric_name or "slow_query" in metric_name:
        if measured > target * 2:
            return "Very slow queries - Add indexes, optimize queries, or review database schema"
        elif measured > target * 1.5:
            return "Slow queries - Review query patterns and add missing indexes"
        else:
            return "Slightly over - Fine-tune query optimization"
    
    elif "memory" in metric_name:
        if measured > target * 2:
            return "High memory usage - Check for memory leaks, reduce cache size, or scale resources"
        elif measured > target * 1.5:
            return "Above target - Review cache configuration and memory-intensive operations"
        else:
            return "Slightly over - Optimize memory usage"
    
    return "Unknown bottleneck - Review metric configuration"


def print_failed_metrics_analysis(failed_metrics: List[Dict[str, Any]]) -> None:
    """Print analysis of failed metrics."""
    if not failed_metrics:
        print("\n✅ All metrics meet their targets!")
        return
    
    print("\n" + "=" * 80)
    print("❌ METRICS CẦN IMPROVE")
    print("=" * 80)
    print(f"Total Failed: {len(failed_metrics)}")
    print()
    
    for metric in failed_metrics:
        print(f"Metric: {metric['name']}")
        print(f"  Description: {metric['description']}")
        print(f"  Current: {metric['measured']:.2f}")
        print(f"  Target: {metric['target']:.2f}")
        print(f"  Baseline: {metric['baseline']:.2f}")
        print(f"  Gap: {metric['gap']:.2f} ({metric['gap_percent']:.1f}% {'over' if metric['direction'] in ['slower', 'lower'] else 'under'} target)")
        print(f"  Reason: {metric['bottleneck']}")
        print()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Analyze failed metrics from benchmark report",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    
    parser.add_argument(
        "report_file",
        nargs="?",
        help="Path to benchmark report JSON file (if not provided, will run new benchmark)",
    )
    
    parser.add_argument(
        "--run-benchmark",
        action="store_true",
        help="Run new benchmark instead of analyzing existing report",
    )
    
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Run deep dive debugging for failed metrics",
    )
    
    args = parser.parse_args()
    
    if args.run_benchmark or not args.report_file:
        # Run new benchmark
        print("Running new benchmark...")
        import asyncio
        from app.services.performance_optimizer import OptimizationStack, new_redis_client
        from app.models.database import db_manager
        
        async def run():
            redis_client = new_redis_client()
            optimizer = OptimizationStack(
                db_connection=db_manager,
                redis_client=redis_client,
            )
            
            benchmark = PerformanceBenchmark(optimizer=optimizer)
            report = await benchmark.run_all_benchmarks()
            
            # Get failed metrics
            failed = benchmark.get_failed_metrics()
            
            if failed:
                print_failed_metrics_analysis([
                    {
                        "name": r.metric_name,
                        "measured": r.measured_value,
                        "target": r.target,
                        "baseline": r.baseline,
                        "gap": abs(r.measured_value - r.target),
                        "gap_percent": (abs(r.measured_value - r.target) / r.target * 100) if r.target > 0 else 0,
                        "direction": "slower" if r.measured_value > r.target else "faster",
                        "bottleneck": benchmark.identify_bottleneck(r),
                        "description": r.description,
                    }
                    for r in failed
                ])
                
                # Run deep dive debugging if requested
                if args.debug:
                    print("\n" + "=" * 80)
                    print("🔧 Running deep dive debugging...")
                    print("=" * 80)
                    from benchmarks.debug_failed_metrics import (
                        debug_cache_effectiveness,
                        debug_query_performance,
                        debug_connection_pool,
                    )
                    
                    with db_manager.get_session() as session:
                        try:
                            debug_cache_effectiveness(optimizer, session)
                        except Exception as e:
                            print(f"❌ Error in cache debugging: {e}")
                        
                        try:
                            debug_query_performance(optimizer, session)
                        except Exception as e:
                            print(f"❌ Error in query performance debugging: {e}")
                        
                        try:
                            debug_connection_pool(optimizer)
                        except Exception as e:
                            print(f"❌ Error in connection pool debugging: {e}")
            else:
                print("\n✅ All metrics meet their targets!")
            
            return report
        
        asyncio.run(run())
    else:
        # Analyze existing report
        try:
            with open(args.report_file, "r") as f:
                report_data = json.load(f)
            
            failed_metrics = analyze_failed_metrics_from_report(report_data)
            print_failed_metrics_analysis(failed_metrics)
            
            # Run deep dive debugging if requested
            if args.debug and failed_metrics:
                print("\n" + "=" * 80)
                print("🔧 Running deep dive debugging...")
                print("=" * 80)
                import asyncio
                from app.services.performance_optimizer import OptimizationStack, new_redis_client
                from app.models.database import db_manager
                from benchmarks.debug_failed_metrics import (
                    debug_cache_effectiveness,
                    debug_query_performance,
                    debug_connection_pool,
                )
                
                redis_client = new_redis_client()
                optimizer = OptimizationStack(
                    db_connection=db_manager,
                    redis_client=redis_client,
                )
                
                with db_manager.get_session() as session:
                    try:
                        debug_cache_effectiveness(optimizer, session)
                    except Exception as e:
                        print(f"❌ Error in cache debugging: {e}")
                    
                    try:
                        debug_query_performance(optimizer, session)
                    except Exception as e:
                        print(f"❌ Error in query performance debugging: {e}")
                    
                    try:
                        debug_connection_pool(optimizer)
                    except Exception as e:
                        print(f"❌ Error in connection pool debugging: {e}")
            
        except FileNotFoundError:
            print(f"Error: Report file not found: {args.report_file}")
            sys.exit(1)
        except json.JSONDecodeError:
            print(f"Error: Invalid JSON file: {args.report_file}")
            sys.exit(1)


if __name__ == "__main__":
    main()

