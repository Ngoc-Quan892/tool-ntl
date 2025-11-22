#!/usr/bin/env python3
"""
CLI script to run performance benchmarks.

Usage:
    python scripts/run_benchmark.py [--metric METRIC_NAME] [--all] [--output OUTPUT_FILE]
"""

import argparse
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from benchmarks.performance_benchmark import (
    PerformanceBenchmark,
    TARGETS,
    main as run_benchmark_main,
)


async def run_single_benchmark(metric_name: str, optimizer=None, base_url: str = "http://localhost:8000"):
    """Run benchmark for a single metric."""
    benchmark = PerformanceBenchmark(optimizer=optimizer, base_url=base_url)
    result = await benchmark.run_benchmark(metric_name)
    
    print(f"\n{'=' * 60}")
    print(f"Benchmark: {metric_name}")
    print(f"{'=' * 60}")
    print(f"Description: {result.description}")
    print(f"Measured Value: {result.measured_value:.2f}")
    print(f"Baseline: {result.baseline:.2f}")
    print(f"Target: {result.target:.2f}")
    
    improvement_str = f"{result.improvement_ratio:.2f}x" if result.improvement_ratio != float('inf') else "∞"
    print(f"Improvement: {improvement_str}")
    print(f"Meets Target: {'✅ YES' if result.meets_target else '❌ NO'}")
    print(f"{'=' * 60}\n")
    
    return result


async def run_all_benchmarks(optimizer=None, base_url: str = "http://localhost:8000"):
    """Run all benchmarks."""
    benchmark = PerformanceBenchmark(optimizer=optimizer, base_url=base_url)
    report = await benchmark.run_all_benchmarks()
    benchmark.print_report()
    return report


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Run performance benchmarks",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run all benchmarks
  python scripts/run_benchmark.py --all
  
  # Run specific metric
  python scripts/run_benchmark.py --metric get_game_results
  
  # Run with custom base URL
  python scripts/run_benchmark.py --all --base-url http://localhost:8000
  
  # Save report to file
  python scripts/run_benchmark.py --all --output benchmark_report.json
        """
    )
    
    parser.add_argument(
        "--metric",
        type=str,
        choices=list(TARGETS.keys()),
        help="Run benchmark for specific metric",
    )
    
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run all benchmarks",
    )
    
    parser.add_argument(
        "--base-url",
        type=str,
        default="http://localhost:8000",
        help="Base URL for API endpoints (default: http://localhost:8000)",
    )
    
    parser.add_argument(
        "--output",
        type=str,
        help="Output file for JSON report",
    )
    
    args = parser.parse_args()
    
    if not args.metric and not args.all:
        parser.print_help()
        sys.exit(1)
    
    # Initialize optimizer
    try:
        from app.services.performance_optimizer import OptimizationStack, new_redis_client
        from app.models.database import db_manager
        
        redis_client = new_redis_client()
        optimizer = OptimizationStack(
            db_connection=db_manager,
            redis_client=redis_client,
        )
    except Exception as exc:
        print(f"Warning: Could not initialize optimizer: {exc}")
        optimizer = None
    
    # Run benchmarks
    if args.all:
        report = asyncio.run(run_all_benchmarks(optimizer=optimizer, base_url=args.base_url))
        
        # Save report if output file specified
        if args.output:
            with open(args.output, "w") as f:
                f.write(report.to_json())
            print(f"\nReport saved to: {args.output}")
    else:
        result = asyncio.run(run_single_benchmark(args.metric, optimizer=optimizer, base_url=args.base_url))
        
        # Save single result if output file specified
        if args.output:
            import json
            from datetime import datetime
            
            report_data = {
                "timestamp": datetime.utcnow().isoformat(),
                "results": [{
                    "metric_name": result.metric_name,
                    "measured_value": result.measured_value,
                    "baseline": result.baseline,
                    "target": result.target,
                    "improvement_ratio": result.improvement_ratio if result.improvement_ratio != float('inf') else "∞",
                    "meets_target": result.meets_target,
                    "description": result.description,
                }],
            }
            
            with open(args.output, "w") as f:
                json.dump(report_data, f, indent=2)
            print(f"\nReport saved to: {args.output}")


if __name__ == "__main__":
    main()

