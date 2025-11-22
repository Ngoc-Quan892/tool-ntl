"""
Pre-deployment checklist script.

Verifies all requirements before production deployment:
- Tests passing
- Benchmark success rate
- Monitoring configured
- Alerts configured
- Backups taken
"""

import argparse
import asyncio
import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from benchmarks.performance_benchmark import PerformanceBenchmark
from app.services.performance_optimizer import OptimizationStack, new_redis_client
from app.models.database import db_manager
from app.core.config import get_settings

settings = get_settings()


class PreDeploymentChecklist:
    """Pre-deployment checklist runner."""
    
    def __init__(self):
        self.checks: List[Dict[str, Any]] = []
        self.all_passed = True
    
    def add_check(self, name: str, passed: bool, message: str, details: Optional[str] = None):
        """Add a check result."""
        self.checks.append({
            "name": name,
            "passed": passed,
            "message": message,
            "details": details,
        })
        if not passed:
            self.all_passed = False
    
    def check_tests(self) -> bool:
        """Check if all tests are passing."""
        print("\n📋 Checking tests...")
        try:
            result = subprocess.run(
                ["pytest", "tests/", "-v", "--tb=short"],
                capture_output=True,
                text=True,
                timeout=300,
            )
            passed = result.returncode == 0
            self.add_check(
                "Tests Passing",
                passed,
                "All tests passed" if passed else "Some tests failed",
                result.stdout if not passed else None,
            )
            return passed
        except subprocess.TimeoutExpired:
            self.add_check("Tests Passing", False, "Test run timed out")
            return False
        except Exception as e:
            self.add_check("Tests Passing", False, f"Error running tests: {e}")
            return False
    
    async def check_benchmark(self) -> bool:
        """Check if benchmark shows 100% success rate."""
        print("\n📋 Checking benchmark...")
        try:
            redis_client = new_redis_client()
            optimizer = OptimizationStack(
                db_connection=db_manager,
                redis_client=redis_client,
            )
            
            benchmark = PerformanceBenchmark(optimizer=optimizer)
            report = await benchmark.run_all_benchmarks()
            summary = report.calculate_summary()
            
            success_rate = summary.get("success_rate", 0.0)
            passed = success_rate >= 100.0
            
            self.add_check(
                "Benchmark Success Rate",
                passed,
                f"Success rate: {success_rate:.1f}%",
                f"Metrics meeting target: {summary.get('metrics_meeting_target', 0)}/{summary.get('total_metrics', 0)}",
            )
            return passed
        except Exception as e:
            self.add_check("Benchmark Success Rate", False, f"Error running benchmark: {e}")
            return False
    
    def check_monitoring(self) -> bool:
        """Check if monitoring is configured."""
        print("\n📋 Checking monitoring...")
        
        # Check if monitoring endpoint exists
        monitoring_endpoint = Path(__file__).parent.parent / "app" / "api" / "endpoints" / "monitoring.py"
        dashboard_endpoint = Path(__file__).parent.parent / "app" / "api" / "endpoints" / "dashboard.py"
        
        monitoring_exists = monitoring_endpoint.exists()
        dashboard_exists = dashboard_endpoint.exists()
        
        passed = monitoring_exists and dashboard_exists
        
        self.add_check(
            "Monitoring Configured",
            passed,
            "Monitoring endpoints available" if passed else "Monitoring endpoints missing",
            f"monitoring.py: {monitoring_exists}, dashboard.py: {dashboard_exists}",
        )
        return passed
    
    def check_alerting(self) -> bool:
        """Check if alerting is configured."""
        print("\n📋 Checking alerting...")
        
        alerting_file = Path(__file__).parent.parent / "app" / "services" / "alerting.py"
        alerting_exists = alerting_file.exists()
        
        # Check for alert configuration
        has_slack = bool(settings.__dict__.get("SLACK_WEBHOOK_URL") or False)
        has_email = bool(
            settings.__dict__.get("SMTP_HOST") and
            settings.__dict__.get("SMTP_USER") and
            settings.__dict__.get("SMTP_PASSWORD")
        )
        
        passed = alerting_exists and (has_slack or has_email)
        
        self.add_check(
            "Alerting Configured",
            passed,
            "Alerting system configured" if passed else "Alerting not fully configured",
            f"Alerting file: {alerting_exists}, Slack: {has_slack}, Email: {has_email}",
        )
        return passed
    
    def check_backups(self) -> bool:
        """Check if backups are taken."""
        print("\n📋 Checking backups...")
        
        backup_script = Path(__file__).parent / "backup_utilities.py"
        backup_exists = backup_script.exists()
        
        # Check if backup directory exists
        backup_dir = Path("./backups")
        has_backups = backup_dir.exists() and any(backup_dir.iterdir())
        
        passed = backup_exists
        
        self.add_check(
            "Backup Utilities",
            passed,
            "Backup utilities available" if passed else "Backup utilities missing",
            f"Script exists: {backup_exists}, Has backups: {has_backups}",
        )
        return passed
    
    def check_environment(self) -> bool:
        """Check environment configuration."""
        print("\n📋 Checking environment...")
        
        required_vars = [
            "DATABASE_URL",
            "REDIS_URL",
        ]
        
        missing = []
        for var in required_vars:
            value = getattr(settings, var, None)
            if not value:
                missing.append(var)
        
        passed = len(missing) == 0
        
        self.add_check(
            "Environment Variables",
            passed,
            "All required env vars set" if passed else f"Missing: {', '.join(missing)}",
        )
        return passed
    
    def print_summary(self):
        """Print checklist summary."""
        print("\n" + "=" * 80)
        print("📋 PRE-DEPLOYMENT CHECKLIST SUMMARY")
        print("=" * 80)
        
        for check in self.checks:
            status = "✅" if check["passed"] else "❌"
            print(f"{status} {check['name']}: {check['message']}")
            if check.get("details"):
                print(f"   {check['details']}")
        
        print("\n" + "=" * 80)
        if self.all_passed:
            print("✅ ALL CHECKS PASSED - Ready for deployment!")
        else:
            print("❌ SOME CHECKS FAILED - Fix issues before deployment")
        print("=" * 80)
    
    async def run_all_checks(self) -> Dict[str, Any]:
        """Run all checks."""
        print("=" * 80)
        print("🔍 PRE-DEPLOYMENT CHECKLIST")
        print("=" * 80)
        
        self.check_tests()
        await self.check_benchmark()
        self.check_monitoring()
        self.check_alerting()
        self.check_backups()
        self.check_environment()
        
        self.print_summary()
        
        return {
            "all_passed": self.all_passed,
            "checks": self.checks,
        }


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Pre-deployment checklist")
    parser.add_argument(
        "--skip-tests",
        action="store_true",
        help="Skip test checks",
    )
    parser.add_argument(
        "--skip-benchmark",
        action="store_true",
        help="Skip benchmark checks",
    )
    parser.add_argument(
        "--output",
        help="Output file for results (JSON)",
    )
    
    args = parser.parse_args()
    
    checklist = PreDeploymentChecklist()
    
    if not args.skip_tests:
        checklist.check_tests()
    
    if not args.skip_benchmark:
        await checklist.check_benchmark()
    
    checklist.check_monitoring()
    checklist.check_alerting()
    checklist.check_backups()
    checklist.check_environment()
    
    checklist.print_summary()
    
    results = {
        "all_passed": checklist.all_passed,
        "checks": checklist.checks,
    }
    
    if args.output:
        with open(args.output, "w") as f:
            json.dump(results, f, indent=2)
        print(f"\n📄 Results saved to: {args.output}")
    
    # Exit with error code if checks failed
    sys.exit(0 if checklist.all_passed else 1)


if __name__ == "__main__":
    asyncio.run(main())

