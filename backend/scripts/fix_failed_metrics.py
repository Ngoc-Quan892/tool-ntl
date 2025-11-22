"""
Automated script to fix failed metrics.

Quy trình tự động:
1. Debug failed metrics (1 giờ)
2. Apply fixes (2 giờ)
3. Re-benchmark (30 phút)
4. Load test (30 phút)

Usage:
    python scripts/fix_failed_metrics.py [--skip-debug] [--skip-fixes] [--skip-benchmark] [--skip-load-test]
"""

import argparse
import asyncio
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, Any, Optional

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session

from app.services.performance_optimizer import OptimizationStack, new_redis_client
from app.models.database import db_manager
from app.core.config import get_settings
from benchmarks.debug_failed_metrics import (
    debug_cache_effectiveness,
    debug_query_performance,
    debug_connection_pool,
)
from benchmarks.performance_benchmark import PerformanceBenchmark

settings = get_settings()


class FailedMetricsFixer:
    """Automated fixer for failed metrics."""
    
    def __init__(self):
        self.optimizer: Optional[OptimizationStack] = None
        self.debug_results: Dict[str, Any] = {}
        self.benchmark_results: Optional[Any] = None
        self.fixes_applied: list = []
    
    def initialize_optimizer(self):
        """Initialize optimizer."""
        print("\n" + "=" * 80)
        print("📋 Initializing Optimizer")
        print("=" * 80)
        
        redis_client = new_redis_client()
        self.optimizer = OptimizationStack(
            db_connection=db_manager,
            redis_client=redis_client,
            cache_ttl=settings.REDIS_CACHE_TTL or 300,
        )
        print("✅ Optimizer initialized")
    
    def step1_debug_failed_metrics(self):
        """
        Step 1: Debug failed metrics (1 giờ)
        
        Chạy 3 debug functions để xác định root cause.
        """
        print("\n" + "=" * 80)
        print("🔍 STEP 1: DEBUG FAILED METRICS")
        print("=" * 80)
        print("Estimated time: 1 hour")
        
        if self.optimizer is None:
            self.initialize_optimizer()
        
        start_time = time.time()
        
        with db_manager.get_session() as session:
            # Debug Cache Effectiveness
            print("\n" + "-" * 80)
            print("1️⃣  Debugging Cache Effectiveness...")
            print("-" * 80)
            try:
                debug_cache_effectiveness(self.optimizer, session)
                self.debug_results["cache"] = "completed"
            except Exception as e:
                print(f"❌ Error in cache debugging: {e}")
                self.debug_results["cache"] = f"error: {e}"
            
            # Debug Query Performance
            print("\n" + "-" * 80)
            print("2️⃣  Debugging Query Performance...")
            print("-" * 80)
            try:
                debug_query_performance(self.optimizer, session)
                self.debug_results["query"] = "completed"
            except Exception as e:
                print(f"❌ Error in query debugging: {e}")
                self.debug_results["query"] = f"error: {e}"
            
            # Debug Connection Pool
            print("\n" + "-" * 80)
            print("3️⃣  Debugging Connection Pool...")
            print("-" * 80)
            try:
                debug_connection_pool(self.optimizer)
                self.debug_results["connection_pool"] = "completed"
            except Exception as e:
                print(f"❌ Error in connection pool debugging: {e}")
                self.debug_results["connection_pool"] = f"error: {e}"
        
        elapsed = time.time() - start_time
        print(f"\n✅ Step 1 completed in {elapsed/60:.1f} minutes")
        
        return self.debug_results
    
    def step2_apply_fixes(self):
        """
        Step 2: Apply fixes (2 giờ)
        
        Dựa trên debug output, apply specific fixes.
        """
        print("\n" + "=" * 80)
        print("🔧 STEP 2: APPLY FIXES")
        print("=" * 80)
        print("Estimated time: 2 hours")
        
        if self.optimizer is None:
            self.initialize_optimizer()
        
        # Run initial benchmark to identify failed metrics
        print("\n📊 Running initial benchmark to identify failed metrics...")
        benchmark = PerformanceBenchmark(optimizer=self.optimizer)
        
        async def run_benchmark():
            return await benchmark.run_all_benchmarks()
        
        report = asyncio.run(run_benchmark())
        self.benchmark_results = report
        
        # Identify failed metrics
        failed_metrics = [r for r in report.results if not r.meets_target]
        
        if not failed_metrics:
            print("\n✅ No failed metrics found! All metrics meet targets.")
            return []
        
        print(f"\n❌ Found {len(failed_metrics)} failed metrics:")
        for result in failed_metrics:
            print(f"  - {result.metric_name}: {result.measured_value:.2f} (target: {result.target:.2f})")
        
        # Apply fixes based on failed metrics
        fixes = []
        
        for result in failed_metrics:
            metric_name = result.metric_name
            
            if "cache" in metric_name.lower() or "hit_rate" in metric_name.lower():
                print(f"\n🔧 Applying cache fixes for {metric_name}...")
                fix = self._fix_cache_issues()
                fixes.append(fix)
            
            if "query" in metric_name.lower() or "pattern" in metric_name.lower() or "game_results" in metric_name.lower():
                print(f"\n🔧 Applying query fixes for {metric_name}...")
                fix = self._fix_query_issues()
                fixes.append(fix)
            
            if "connection" in metric_name.lower():
                print(f"\n🔧 Applying connection pool fixes for {metric_name}...")
                fix = self._fix_connection_pool_issues()
                fixes.append(fix)
        
        self.fixes_applied = fixes
        
        print("\n" + "=" * 80)
        print("✅ STEP 2 COMPLETE: Fixes applied/suggested")
        print("=" * 80)
        print("\n⚠️  Please review the fixes above and apply them manually.")
        print("   After applying fixes, re-run this script with --skip-debug --skip-fixes")
        
        return fixes
    
    def _fix_cache_issues(self) -> Dict[str, Any]:
        """Fix cache-related issues."""
        print("   → Checking Redis connection...")
        if self.optimizer and self.optimizer.redis_client:
            try:
                self.optimizer.redis_client.ping()
                print("   ✅ Redis connection is active")
            except Exception as e:
                print(f"   ❌ Redis connection failed: {e}")
                print("   → Fix: Check REDIS_URL in .env file")
        
        print("   → Suggested fixes:")
        print("   1. Increase cache TTL: REDIS_CACHE_TTL=600 (10 minutes)")
        print("   2. Verify cache keys are consistent")
        print("   3. Check cache invalidation strategy")
        print("   4. Review cache patterns and access frequency")
        
        return {
            "type": "cache",
            "actions": [
                "Check Redis connection",
                "Increase cache TTL",
                "Verify cache keys",
                "Review cache patterns",
            ],
        }
    
    def _fix_query_issues(self) -> Dict[str, Any]:
        """Fix query-related issues."""
        print("   → Checking for missing indexes...")
        print("   → Suggested SQL:")
        print("""
        -- Index cho timestamp
        CREATE INDEX IF NOT EXISTS idx_game_results_timestamp 
        ON game_results(timestamp DESC);
        
        -- Composite index cho shoe_number + timestamp
        CREATE INDEX IF NOT EXISTS idx_game_results_shoe_timestamp 
        ON game_results(shoe_number, timestamp DESC);
        
        -- Composite index cho result + timestamp
        CREATE INDEX IF NOT EXISTS idx_game_results_result_timestamp 
        ON game_results(result, timestamp DESC);
        """)
        
        print("   → To apply:")
        print("   1. Create Alembic migration: alembic revision -m 'add_performance_indexes'")
        print("   2. Add indexes to migration file")
        print("   3. Run migration: alembic upgrade head")
        
        return {
            "type": "query",
            "actions": [
                "Add missing indexes",
                "Run EXPLAIN ANALYZE on slow queries",
                "Optimize query patterns",
            ],
        }
    
    def _fix_connection_pool_issues(self) -> Dict[str, Any]:
        """Fix connection pool issues."""
        print("   → Current pool settings:")
        print(f"   - DB_POOL_SIZE: {settings.DB_POOL_SIZE}")
        print(f"   - DB_MAX_OVERFLOW: {settings.DB_MAX_OVERFLOW}")
        print("   → Suggested fixes:")
        print("   1. Increase pool size: DB_POOL_SIZE=20")
        print("   2. Increase max overflow: DB_MAX_OVERFLOW=15")
        print("   3. Ensure connections are properly closed")
        print("   4. Review query efficiency")
        
        return {
            "type": "connection_pool",
            "actions": [
                "Increase pool size",
                "Increase max overflow",
                "Review connection usage",
            ],
        }
    
    async def step3_re_benchmark(self):
        """
        Step 3: Re-benchmark (30 phút)
        
        Target: 100% success rate
        """
        print("\n" + "=" * 80)
        print("📊 STEP 3: RE-BENCHMARK")
        print("=" * 80)
        print("Estimated time: 30 minutes")
        print("Target: 100% success rate")
        
        if self.optimizer is None:
            self.initialize_optimizer()
        
        print("\nRunning full benchmark suite...")
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
            return True
        else:
            print(f"\n⚠️  Not yet at 100%. {total_metrics - metrics_meeting_target} metrics still need improvement.")
            print("   Consider:")
            print("   1. Reviewing debug output from Step 1")
            print("   2. Applying additional fixes from Step 2")
            print("   3. Re-running this script")
            return False
    
    def step4_load_test(self):
        """
        Step 4: Load test (30 phút)
        
        Run Locust load test to verify performance under load.
        """
        print("\n" + "=" * 80)
        print("🚀 STEP 4: LOAD TEST")
        print("=" * 80)
        print("Estimated time: 30 minutes")
        
        locustfile = Path(__file__).parent.parent / "tests" / "load" / "locustfile.py"
        
        if not locustfile.exists():
            print(f"⚠️  Locust file not found: {locustfile}")
            print("   Skipping load test.")
            return False
        
        print("\nStarting Locust load test...")
        print("Command:")
        print(f"""
        locust -f {locustfile} \\
            --host=http://localhost:8000 \\
            --users=100 \\
            --spawn-rate=10 \\
            --run-time=5m \\
            --headless \\
            --html=load_test_report.html
        """)
        
        # Ask user if they want to run automatically
        response = input("\nRun load test now? (y/n): ").strip().lower()
        
        if response == 'y':
            try:
                print("\n🚀 Running load test...")
                result = subprocess.run([
                    "locust",
                    "-f", str(locustfile),
                    "--host=http://localhost:8000",
                    "--users=100",
                    "--spawn-rate=10",
                    "--run-time=5m",
                    "--headless",
                    "--html=load_test_report.html"
                ], check=True, timeout=400)
                
                print("\n✅ Load test completed. Check load_test_report.html")
                return True
            except subprocess.TimeoutExpired:
                print("\n❌ Load test timed out")
                return False
            except subprocess.CalledProcessError as e:
                print(f"\n❌ Load test failed: {e}")
                return False
            except FileNotFoundError:
                print("\n⚠️  Locust not installed. Install with: pip install locust")
                print("   Or run manually using the command above.")
                return False
        else:
            print("\n⏭️  Skipping automatic load test.")
            print("   Run manually when ready using the command above.")
            return False
    
    async def run_full_process(
        self,
        skip_debug: bool = False,
        skip_fixes: bool = False,
        skip_benchmark: bool = False,
        skip_load_test: bool = False,
    ) -> Dict[str, Any]:
        """
        Run full process to fix failed metrics.
        
        Args:
            skip_debug: Skip Step 1 (debug)
            skip_fixes: Skip Step 2 (fixes)
            skip_benchmark: Skip Step 3 (re-benchmark)
            skip_load_test: Skip Step 4 (load test)
            
        Returns:
            Summary dictionary
        """
        print("=" * 80)
        print("🎯 FIX FAILED METRICS - AUTOMATED PROCESS")
        print("=" * 80)
        print("\nQuy trình:")
        print("  Step 1: Debug failed metrics (1 giờ)")
        print("  Step 2: Apply fixes (2 giờ)")
        print("  Step 3: Re-benchmark (30 phút)")
        print("  Step 4: Load test (30 phút)")
        print("\n" + "=" * 80)
        
        results = {
            "step1": None,
            "step2": None,
            "step3": None,
            "step4": None,
            "success": False,
        }
        
        # Step 1: Debug
        if not skip_debug:
            debug_results = self.step1_debug_failed_metrics()
            results["step1"] = debug_results
        else:
            print("\n⏭️  Skipping Step 1 (debug)")
        
        # Step 2: Apply fixes
        if not skip_fixes:
            fixes = self.step2_apply_fixes()
            results["step2"] = fixes
        else:
            print("\n⏭️  Skipping Step 2 (fixes)")
        
        # Step 3: Re-benchmark
        if not skip_benchmark:
            benchmark_success = await self.step3_re_benchmark()
            results["step3"] = {"success": benchmark_success}
            results["success"] = benchmark_success
        else:
            print("\n⏭️  Skipping Step 3 (re-benchmark)")
        
        # Step 4: Load test
        if not skip_load_test:
            load_test_success = self.step4_load_test()
            results["step4"] = {"success": load_test_success}
        else:
            print("\n⏭️  Skipping Step 4 (load test)")
        
        # Final summary
        print("\n" + "=" * 80)
        print("📋 PROCESS SUMMARY")
        print("=" * 80)
        print(f"Step 1 (Debug): {'✅' if results.get('step1') else '⏭️'}")
        print(f"Step 2 (Fixes): {'✅' if results.get('step2') else '⏭️'}")
        print(f"Step 3 (Benchmark): {'✅' if results.get('step3', {}).get('success') else '⏭️'}")
        print(f"Step 4 (Load Test): {'✅' if results.get('step4', {}).get('success') else '⏭️'}")
        
        if results.get("success"):
            print("\n✅ SUCCESS: All metrics meet targets!")
        else:
            print("\n⚠️  Some steps need attention. Review output above.")
        
        print("=" * 80)
        
        return results


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Automated script to fix failed metrics",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    
    parser.add_argument(
        "--skip-debug",
        action="store_true",
        help="Skip Step 1 (debug)",
    )
    
    parser.add_argument(
        "--skip-fixes",
        action="store_true",
        help="Skip Step 2 (fixes)",
    )
    
    parser.add_argument(
        "--skip-benchmark",
        action="store_true",
        help="Skip Step 3 (re-benchmark)",
    )
    
    parser.add_argument(
        "--skip-load-test",
        action="store_true",
        help="Skip Step 4 (load test)",
    )
    
    args = parser.parse_args()
    
    fixer = FailedMetricsFixer()
    results = await fixer.run_full_process(
        skip_debug=args.skip_debug,
        skip_fixes=args.skip_fixes,
        skip_benchmark=args.skip_benchmark,
        skip_load_test=args.skip_load_test,
    )
    
    # Exit with error code if not successful
    sys.exit(0 if results.get("success", False) else 1)


if __name__ == "__main__":
    asyncio.run(main())

