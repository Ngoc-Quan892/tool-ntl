"""
Daily metrics report generator.

Generates daily metrics summary for review.
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.performance_optimizer import OptimizationStack, new_redis_client
from app.models.database import db_manager
from app.core.config import get_settings

settings = get_settings()


def generate_daily_report(optimizer: OptimizationStack) -> Dict[str, Any]:
    """Generate daily metrics report."""
    print("\n📊 Generating Daily Metrics Report")
    print("=" * 80)
    
    report = {
        "date": datetime.now().isoformat(),
        "metrics": {},
        "alerts": [],
        "recommendations": [],
    }
    
    # Get cache statistics
    cache_manager = optimizer.get_cache_manager()
    cache_stats = cache_manager.get_stats()
    
    # Get query statistics
    with db_manager.get_session() as session:
        query_optimizer = optimizer.get_query_optimizer(session)
        query_stats = query_optimizer.get_query_statistics()
    
    # Calculate metrics
    total_hits = cache_stats.get("stats", {}).get("local_hits", 0) + \
                 cache_stats.get("stats", {}).get("redis_hits", 0)
    total_misses = cache_stats.get("stats", {}).get("local_misses", 0) + \
                   cache_stats.get("stats", {}).get("redis_misses", 0)
    total_requests = total_hits + total_misses
    cache_hit_rate = (total_hits / total_requests * 100) if total_requests > 0 else 0
    
    # Calculate average query time
    total_queries = 0
    total_time_ms = 0.0
    slow_queries = 0
    for query_name, stats in query_stats.items():
        count = stats.get("count", 0)
        avg_time = stats.get("avg_time_ms", 0)
        total_queries += count
        total_time_ms += avg_time * count
        slow_queries += stats.get("slow_queries", 0)
    
    avg_query_time = (total_time_ms / total_queries) if total_queries > 0 else 0.0
    
    report["metrics"] = {
        "cache_hit_rate": round(cache_hit_rate, 2),
        "cache_hits": total_hits,
        "cache_misses": total_misses,
        "avg_query_time_ms": round(avg_query_time, 2),
        "total_queries": total_queries,
        "slow_queries": slow_queries,
        "slow_query_rate": round((slow_queries / total_queries * 100) if total_queries > 0 else 0, 2),
    }
    
    # Generate recommendations
    recommendations = []
    
    if cache_hit_rate < 70:
        recommendations.append({
            "priority": "high",
            "metric": "cache_hit_rate",
            "message": f"Cache hit rate is {cache_hit_rate:.1f}% (target: >80%)",
            "action": "Review cache TTLs and key patterns",
        })
    
    if avg_query_time > 100:
        recommendations.append({
            "priority": "critical",
            "metric": "avg_query_time",
            "message": f"Average query time is {avg_query_time:.2f}ms (target: <50ms)",
            "action": "Analyze slow queries and add indexes",
        })
    
    if slow_queries > total_queries * 0.05:  # More than 5% slow queries
        recommendations.append({
            "priority": "high",
            "metric": "slow_query_rate",
            "message": f"Slow query rate is {(slow_queries/total_queries*100):.1f}% (target: <5%)",
            "action": "Review and optimize slow queries",
        })
    
    report["recommendations"] = recommendations
    
    # Print report
    print(f"\n📈 Metrics:")
    print(f"  Cache Hit Rate: {cache_hit_rate:.1f}%")
    print(f"  Cache Hits: {total_hits:,}")
    print(f"  Cache Misses: {total_misses:,}")
    print(f"  Avg Query Time: {avg_query_time:.2f}ms")
    print(f"  Total Queries: {total_queries:,}")
    print(f"  Slow Queries: {slow_queries:,} ({(slow_queries/total_queries*100) if total_queries > 0 else 0:.1f}%)")
    
    if recommendations:
        print(f"\n⚠️  Recommendations:")
        for rec in recommendations:
            print(f"  [{rec['priority'].upper()}] {rec['message']}")
            print(f"    Action: {rec['action']}")
    else:
        print(f"\n✅ All metrics within target ranges")
    
    print("\n" + "=" * 80)
    
    return report


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Generate daily metrics report")
    parser.add_argument(
        "--output",
        help="Output file for report (JSON)",
    )
    
    args = parser.parse_args()
    
    # Initialize optimizer
    redis_client = new_redis_client()
    optimizer = OptimizationStack(
        db_connection=db_manager,
        redis_client=redis_client,
    )
    
    # Generate report
    report = generate_daily_report(optimizer)
    
    # Save to file if requested
    if args.output:
        with open(args.output, "w") as f:
            json.dump(report, f, indent=2)
        print(f"\n📄 Report saved to: {args.output}")


if __name__ == "__main__":
    main()

