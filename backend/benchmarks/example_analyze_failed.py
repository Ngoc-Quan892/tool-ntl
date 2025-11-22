"""
Example script to identify which metrics failed and see detailed breakdown.

Usage:
    python benchmarks/example_analyze_failed.py
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from benchmarks.performance_benchmark import PerformanceBenchmark
from app.services.performance_optimizer import OptimizationStack, new_redis_client
from app.models.database import db_manager


async def main():
    """Main function to run benchmark and analyze failed metrics."""
    # Initialize optimizer
    redis_client = new_redis_client()
    optimizer = OptimizationStack(
        db_connection=db_manager,
        redis_client=redis_client,
    )
    
    # Create benchmark runner
    benchmark = PerformanceBenchmark(optimizer=optimizer)
    
    # Run all benchmarks
    print("Running benchmarks...")
    report = await benchmark.run_all_benchmarks()
    
    # Get failed metrics
    failed = benchmark.get_failed_metrics()
    
    if not failed:
        print("\n✅ All metrics meet their targets!")
        return
    
    # Print detailed breakdown
    print("\n" + "=" * 80)
    print("❌ METRICS CẦN IMPROVE")
    print("=" * 80)
    print(f"Total Failed: {len(failed)}/{len(report.results)}")
    print()
    
    for result in failed:
        bottleneck = benchmark.identify_bottleneck(result)
        gap = abs(result.measured_value - result.target)
        
        # Determine direction
        if result.target < result.baseline:
            # Lower is better
            direction = "slower" if result.measured_value > result.target else "faster"
            gap_pct = (gap / result.target * 100) if result.target > 0 else 0
        else:
            # Higher is better
            direction = "lower" if result.measured_value < result.target else "higher"
            gap_pct = (gap / result.target * 100) if result.target > 0 else 0
        
        print(f"Metric: {result.metric_name}")
        print(f"  Description: {result.description}")
        print(f"  Current: {result.measured_value:.2f}")
        print(f"  Target: {result.target:.2f}")
        print(f"  Baseline: {result.baseline:.2f}")
        print(f"  Gap: {gap:.2f} ({gap_pct:.1f}% {'over' if direction in ['slower', 'lower'] else 'under'} target)")
        print(f"  Improvement: {result.improvement_ratio:.2f}x" if result.improvement_ratio != float('inf') else "  Improvement: ∞")
        print(f"  Reason: {bottleneck}")
        print()
    
    print("=" * 80)
    
    # Alternative: Convert to dictionary format (as in original example)
    print("\n" + "=" * 80)
    print("ALTERNATIVE FORMAT (Dictionary)")
    print("=" * 80)
    
    failed_dicts = [
        {
            "name": r.metric_name,
            "measured": r.measured_value,
            "target": r.target,
            "baseline": r.baseline,
            "gap": abs(r.measured_value - r.target),
            "bottleneck": benchmark.identify_bottleneck(r),
            "description": r.description,
        }
        for r in failed
    ]
    
    for metric in failed_dicts:
        print(f"""
Metric: {metric['name']}
Current: {metric['measured']:.2f}
Target: {metric['target']:.2f}
Gap: {metric['gap']:.2f}
Reason: {metric['bottleneck']}
        """)


if __name__ == "__main__":
    asyncio.run(main())

