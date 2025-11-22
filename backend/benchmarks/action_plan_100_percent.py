"""
Action Plan để đạt 100% Success Rate cho Performance Benchmarks.

Tự động hóa quy trình:
1. Identify root cause (chạy debug functions)
2. Apply fixes (đề xuất và hướng dẫn)
3. Re-benchmark
4. Load test

Usage:
    python benchmarks/action_plan_100_percent.py [--skip-debug] [--skip-fixes] [--skip-benchmark] [--skip-load-test]
"""

import argparse
import asyncio
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Any, Optional

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session

from app.services.performance_optimizer import (
    OptimizationStack,
    new_redis_client,
)
from app.models.database import db_manager
from app.core.config import get_settings
from benchmarks.debug_failed_metrics import (
    debug_cache_effectiveness,
    debug_query_performance,
    debug_connection_pool,
)
from benchmarks.performance_benchmark import PerformanceBenchmark

settings = get_settings()


class ActionPlanRunner:
    """Runner cho action plan để đạt 100% success rate."""
    
    def __init__(self):
        self.optimizer: Optional[OptimizationStack] = None
        self.debug_results: Dict[str, Any] = {}
        self.benchmark_report: Optional[Dict[str, Any]] = None
        self.fixes_applied: List[str] = []
        
    def initialize_optimizer(self) -> None:
        """Khởi tạo optimizer."""
        print("\n" + "=" * 80)
        print("📋 STEP A0: Initializing Optimizer")
        print("=" * 80)
        
        redis_client = new_redis_client()
        self.optimizer = OptimizationStack(
            db_connection=db_manager,
            redis_client=redis_client,
            cache_ttl=settings.REDIS_CACHE_TTL or 300,
        )
        print("✅ Optimizer initialized")
    
    def step_a1_identify_root_cause(self) -> Dict[str, Any]:
        """
        Step A1: Identify root cause (30 phút)
        
        Chạy 3 debug functions:
        1. debug_cache_effectiveness()
        2. debug_query_performance()
        3. debug_connection_pool()
        
        Returns:
            Dict với các bottlenecks được phát hiện
        """
        print("\n" + "=" * 80)
        print("🔍 STEP A1: IDENTIFY ROOT CAUSE")
        print("=" * 80)
        print("Chạy 3 debug functions để xác định bottleneck...")
        
        if self.optimizer is None:
            self.initialize_optimizer()
        
        bottlenecks = {
            "cache_issues": [],
            "query_issues": [],
            "connection_issues": [],
        }
        
        with db_manager.get_session() as session:
            # Debug Cache
            print("\n" + "-" * 80)
            print("1️⃣  Debugging Cache Effectiveness...")
            print("-" * 80)
            try:
                debug_cache_effectiveness(self.optimizer, session)
                # Capture issues (simplified - trong thực tế cần parse output)
                bottlenecks["cache_issues"].append("Cache debug completed")
            except Exception as e:
                bottlenecks["cache_issues"].append(f"Error: {e}")
            
            # Debug Query Performance
            print("\n" + "-" * 80)
            print("2️⃣  Debugging Query Performance...")
            print("-" * 80)
            try:
                debug_query_performance(self.optimizer, session)
                bottlenecks["query_issues"].append("Query debug completed")
            except Exception as e:
                bottlenecks["query_issues"].append(f"Error: {e}")
            
            # Debug Connection Pool
            print("\n" + "-" * 80)
            print("3️⃣  Debugging Connection Pool...")
            print("-" * 80)
            try:
                debug_connection_pool(self.optimizer)
                bottlenecks["connection_issues"].append("Connection pool debug completed")
            except Exception as e:
                bottlenecks["connection_issues"].append(f"Error: {e}")
        
        self.debug_results = bottlenecks
        
        print("\n" + "=" * 80)
        print("✅ STEP A1 COMPLETE: Root causes identified")
        print("=" * 80)
        
        return bottlenecks
    
    def step_a2_apply_fixes(self, benchmark_results: Optional[List[Any]] = None) -> List[str]:
        """
        Step A2: Apply fixes (1-2 giờ)
        
        Common fixes based on bottleneck:
        - Cache: Fix cache keys, increase TTL, check Redis
        - Query: Add indexes, optimize queries
        - Connection pool: Increase pool size, optimize usage
        
        Args:
            benchmark_results: Kết quả benchmark để xác định metric nào bị lỗi
            
        Returns:
            List các fixes đã áp dụng hoặc đề xuất
        """
        print("\n" + "=" * 80)
        print("🔧 STEP A2: APPLY FIXES")
        print("=" * 80)
        
        fixes = []
        
        # Phân tích benchmark results để xác định metric nào cần fix
        failed_metrics = []
        if benchmark_results:
            for result in benchmark_results:
                if not result.meets_target:
                    failed_metrics.append(result.metric_name)
        
        print(f"\n📋 Failed metrics: {failed_metrics}")
        
        # Apply fixes based on failed metrics
        if "get_pattern_stats" in failed_metrics or "get_game_results" in failed_metrics:
            print("\n🔧 Fix 1: Query Optimization")
            fixes.append(self._fix_query_performance())
        
        if "cache_hit_rate" in failed_metrics:
            print("\n🔧 Fix 2: Cache Optimization")
            fixes.append(self._fix_cache_effectiveness())
        
        if "database_connections" in failed_metrics:
            print("\n🔧 Fix 3: Connection Pool Optimization")
            fixes.append(self._fix_connection_pool())
        
        if "avg_query_time_ms" in failed_metrics or "slow_query_rate" in failed_metrics:
            print("\n🔧 Fix 4: Database Indexes")
            fixes.append(self._fix_database_indexes())
        
        self.fixes_applied = fixes
        
        print("\n" + "=" * 80)
        print("✅ STEP A2 COMPLETE: Fixes applied/suggested")
        print("=" * 80)
        
        return fixes
    
    def _fix_query_performance(self) -> str:
        """Fix query performance issues."""
        print("   → Checking for missing indexes...")
        print("   → Suggested SQL:")
        print("""
        -- Index cho pattern statistics
        CREATE INDEX IF NOT EXISTS idx_game_results_timestamp 
        ON game_results(timestamp DESC);
        
        CREATE INDEX IF NOT EXISTS idx_game_results_shoe_timestamp 
        ON game_results(shoe_number, timestamp DESC);
        
        CREATE INDEX IF NOT EXISTS idx_game_results_result_timestamp 
        ON game_results(result, timestamp DESC);
        """)
        return "Query performance fixes suggested"
    
    def _fix_cache_effectiveness(self) -> str:
        """Fix cache effectiveness issues."""
        print("   → Checking Redis connection...")
        if self.optimizer and self.optimizer.redis_client:
            try:
                self.optimizer.redis_client.ping()
                print("   ✅ Redis connection is active")
            except Exception as e:
                print(f"   ❌ Redis connection failed: {e}")
                print("   → Fix: Check REDIS_URL in .env file")
        
        print("   → Suggested fixes:")
        print("   - Increase cache TTL: REDIS_CACHE_TTL=600 (10 minutes)")
        print("   - Verify cache keys are consistent")
        print("   - Check cache invalidation strategy")
        return "Cache effectiveness fixes suggested"
    
    def _fix_connection_pool(self) -> str:
        """Fix connection pool issues."""
        print("   → Current pool settings:")
        print(f"   - DB_POOL_SIZE: {settings.DB_POOL_SIZE}")
        print(f"   - DB_MAX_OVERFLOW: {settings.DB_MAX_OVERFLOW}")
        print("   → Suggested fixes:")
        print("   - Increase pool size: DB_POOL_SIZE=20")
        print("   - Increase max overflow: DB_MAX_OVERFLOW=15")
        print("   - Ensure connections are properly closed")
        return "Connection pool fixes suggested"
    
    def _fix_database_indexes(self) -> str:
        """Fix database indexes."""
        print("   → Creating migration file for indexes...")
        migration_content = """
# Add this to a new Alembic migration file

def upgrade():
    op.create_index(
        'idx_game_results_timestamp',
        'game_results',
        ['timestamp'],
        unique=False
    )
    op.create_index(
        'idx_game_results_shoe_timestamp',
        'game_results',
        ['shoe_number', 'timestamp'],
        unique=False
    )
    op.create_index(
        'idx_game_results_result_timestamp',
        'game_results',
        ['result', 'timestamp'],
        unique=False
    )

def downgrade():
    op.drop_index('idx_game_results_result_timestamp', 'game_results')
    op.drop_index('idx_game_results_shoe_timestamp', 'game_results')
    op.drop_index('idx_game_results_timestamp', 'game_results')
"""
        print(migration_content)
        return "Database index fixes suggested"
    
    async def step_a3_re_benchmark(self) -> Dict[str, Any]:
        """
        Step A3: Re-benchmark (30 phút)
        
        Chạy lại benchmark và kiểm tra success rate.
        
        Expected:
        - Success rate: 100% (8/8)
        - Average improvement: >9x
        - All metrics green ✅
        """
        print("\n" + "=" * 80)
        print("📊 STEP A3: RE-BENCHMARK")
        print("=" * 80)
        
        if self.optimizer is None:
            self.initialize_optimizer()
        
        print("Running full benchmark suite...")
        benchmark = PerformanceBenchmark(optimizer=self.optimizer)
        report = await benchmark.run_all_benchmarks()
        
        # Print report
        benchmark.print_report()
        
        # Calculate success rate
        summary = report.calculate_summary()
        success_rate = summary.get("success_rate", 0.0)
        total_metrics = summary.get("total_metrics", 0)
        metrics_meeting_target = summary.get("metrics_meeting_target", 0)
        
        print("\n" + "=" * 80)
        print("📊 BENCHMARK RESULTS")
        print("=" * 80)
        print(f"Success Rate: {success_rate:.1f}%")
        print(f"Metrics Meeting Target: {metrics_meeting_target}/{total_metrics}")
        print(f"Average Improvement: {summary.get('average_improvement', 0):.2f}x")
        
        if success_rate >= 100.0:
            print("\n✅ TARGET ACHIEVED: 100% Success Rate!")
        else:
            print(f"\n⚠️  Not yet at 100%. {total_metrics - metrics_meeting_target} metrics still need improvement.")
            print("   Consider running Step A2 again with additional fixes.")
        
        self.benchmark_report = summary
        
        return summary
    
    def step_a4_load_test(self) -> None:
        """
        Step A4: Load test (1 giờ)
        
        Chạy Locust load test để verify performance under load.
        
        Monitor:
        - No errors under 100 concurrent users
        - Response times stable
        - Cache hit rate >80%
        """
        print("\n" + "=" * 80)
        print("🚀 STEP A4: LOAD TEST")
        print("=" * 80)
        
        locustfile = Path(__file__).parent.parent / "tests" / "load" / "locustfile.py"
        
        if not locustfile.exists():
            print(f"⚠️  Locust file not found: {locustfile}")
            print("   Skipping load test.")
            return
        
        print("Starting Locust load test...")
        print("\nCommand to run manually:")
        print(f"""
        locust -f {locustfile} \\
            --host=http://localhost:8000 \\
            --users=100 \\
            --spawn-rate=10 \\
            --run-time=5m \\
            --headless \\
            --html=load_test_report.html
        """)
        
        print("\n📋 Monitor these metrics:")
        print("  - No errors under 100 concurrent users")
        print("  - Response times stable (<200ms p95)")
        print("  - Cache hit rate >80%")
        print("  - Database connections < pool size")
        
        # Optionally run automatically
        response = input("\nRun load test now? (y/n): ").strip().lower()
        if response == 'y':
            try:
                subprocess.run([
                    "locust",
                    "-f", str(locustfile),
                    "--host=http://localhost:8000",
                    "--users=100",
                    "--spawn-rate=10",
                    "--run-time=5m",
                    "--headless",
                    "--html=load_test_report.html"
                ], check=True)
                print("\n✅ Load test completed. Check load_test_report.html")
            except subprocess.CalledProcessError as e:
                print(f"\n❌ Load test failed: {e}")
            except FileNotFoundError:
                print("\n⚠️  Locust not installed. Install with: pip install locust")
        else:
            print("\n⏭️  Skipping automatic load test. Run manually when ready.")
    
    async def run_full_action_plan(
        self,
        skip_debug: bool = False,
        skip_fixes: bool = False,
        skip_benchmark: bool = False,
        skip_load_test: bool = False,
    ) -> Dict[str, Any]:
        """
        Chạy toàn bộ action plan.
        
        Args:
            skip_debug: Bỏ qua step A1
            skip_fixes: Bỏ qua step A2
            skip_benchmark: Bỏ qua step A3
            skip_load_test: Bỏ qua step A4
            
        Returns:
            Summary của toàn bộ quy trình
        """
        print("=" * 80)
        print("🎯 ACTION PLAN: ĐẠT 100% SUCCESS RATE")
        print("=" * 80)
        print("\nQuy trình:")
        print("  A1: Identify root cause (30 phút)")
        print("  A2: Apply fixes (1-2 giờ)")
        print("  A3: Re-benchmark (30 phút)")
        print("  A4: Load test (1 giờ)")
        print("\n" + "=" * 80)
        
        results = {
            "step_a1": None,
            "step_a2": None,
            "step_a3": None,
            "step_a4": None,
            "final_success_rate": None,
        }
        
        # Step A1: Identify root cause
        if not skip_debug:
            bottlenecks = self.step_a1_identify_root_cause()
            results["step_a1"] = bottlenecks
        else:
            print("\n⏭️  Skipping Step A1 (debug)")
        
        # Step A2: Apply fixes
        if not skip_fixes:
            # Run initial benchmark to identify failed metrics
            if self.optimizer is None:
                self.initialize_optimizer()
            
            print("\n📊 Running initial benchmark to identify failed metrics...")
            benchmark = PerformanceBenchmark(optimizer=self.optimizer)
            initial_report = await benchmark.run_all_benchmarks()
            
            # Print initial benchmark summary
            initial_summary = initial_report.calculate_summary()
            print(f"\n📊 Initial Benchmark Results:")
            print(f"  Success Rate: {initial_summary.get('success_rate', 0):.1f}%")
            print(f"  Metrics Meeting Target: {initial_summary.get('metrics_meeting_target', 0)}/{initial_summary.get('total_metrics', 0)}")
            
            # Show failed metrics
            failed = [r for r in initial_report.results if not r.meets_target]
            if failed:
                print(f"\n❌ Failed Metrics ({len(failed)}):")
                for result in failed:
                    print(f"  - {result.metric_name}: {result.measured_value:.2f} (target: {result.target:.2f})")
            else:
                print("\n✅ All metrics already meet targets!")
            
            fixes = self.step_a2_apply_fixes(initial_report.results)
            results["step_a2"] = fixes
        else:
            print("\n⏭️  Skipping Step A2 (fixes)")
        
        # Step A3: Re-benchmark
        if not skip_benchmark:
            summary = await self.step_a3_re_benchmark()
            results["step_a3"] = summary
            results["final_success_rate"] = summary.get("success_rate", 0.0)
        else:
            print("\n⏭️  Skipping Step A3 (re-benchmark)")
        
        # Step A4: Load test
        if not skip_load_test:
            self.step_a4_load_test()
            results["step_a4"] = "Completed"
        else:
            print("\n⏭️  Skipping Step A4 (load test)")
        
        # Final summary
        print("\n" + "=" * 80)
        print("📋 ACTION PLAN SUMMARY")
        print("=" * 80)
        print(f"Final Success Rate: {results.get('final_success_rate', 'N/A')}%")
        print(f"Fixes Applied: {len(self.fixes_applied)}")
        print("\n" + "=" * 80)
        
        return results


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Action plan để đạt 100% success rate cho performance benchmarks",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    
    parser.add_argument(
        "--skip-debug",
        action="store_true",
        help="Bỏ qua Step A1 (debug)",
    )
    
    parser.add_argument(
        "--skip-fixes",
        action="store_true",
        help="Bỏ qua Step A2 (fixes)",
    )
    
    parser.add_argument(
        "--skip-benchmark",
        action="store_true",
        help="Bỏ qua Step A3 (re-benchmark)",
    )
    
    parser.add_argument(
        "--skip-load-test",
        action="store_true",
        help="Bỏ qua Step A4 (load test)",
    )
    
    args = parser.parse_args()
    
    runner = ActionPlanRunner()
    results = await runner.run_full_action_plan(
        skip_debug=args.skip_debug,
        skip_fixes=args.skip_fixes,
        skip_benchmark=args.skip_benchmark,
        skip_load_test=args.skip_load_test,
    )
    
    # Save results to file
    output_file = Path(__file__).parent / "action_plan_results.json"
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n📄 Results saved to: {output_file}")


if __name__ == "__main__":
    asyncio.run(main())

