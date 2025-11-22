"""
Schedule prediction validation to run automatically.

Usage:
    # Run as daemon/service
    python -m app.scripts.schedule_validation
    
    # Run with custom schedule
    python -m app.scripts.schedule_validation --daily --time=02:00
"""

import argparse
import logging
import subprocess
import sys
from pathlib import Path

try:
    import schedule
    import time
    SCHEDULE_AVAILABLE = True
except ImportError:
    SCHEDULE_AVAILABLE = False
    schedule = None

logger = logging.getLogger(__name__)


def run_validation(duration: int = 60, output: str = "logs"):
    """Run validation script."""
    script_path = Path(__file__).parent / "validate_predictions.py"
    
    cmd = [
        sys.executable,
        "-m", "app.scripts.validate_predictions",
        "--duration", str(duration),
        "--output", output,
    ]
    
    try:
        result = subprocess.run(
            cmd,
            cwd=Path(__file__).parent.parent.parent,
            capture_output=True,
            text=True,
        )
        
        if result.returncode == 0:
            logger.info("Validation completed successfully")
            print("✅ Validation completed")
        else:
            logger.error(f"Validation failed: {result.stderr}")
            print(f"❌ Validation failed: {result.stderr}")
        
        return result.returncode == 0
        
    except Exception as exc:
        logger.error(f"Failed to run validation: {exc}", exc_info=True)
        print(f"❌ Error running validation: {exc}")
        return False


def setup_daily_schedule(time_str: str = "02:00", duration: int = 60):
    """Setup daily validation schedule."""
    if not SCHEDULE_AVAILABLE:
        print("❌ Error: 'schedule' library not installed")
        print("   Install with: pip install schedule")
        return False
    
    schedule.every().day.at(time_str).do(run_validation, duration=duration)
    print(f"✅ Scheduled daily validation at {time_str}")
    return True


def setup_weekly_schedule(day: str = "monday", time_str: str = "03:00", duration: int = 120):
    """Setup weekly validation schedule."""
    if not SCHEDULE_AVAILABLE:
        print("❌ Error: 'schedule' library not installed")
        print("   Install with: pip install schedule")
        return False
    
    getattr(schedule.every(), day.lower()).at(time_str).do(run_validation, duration=duration)
    print(f"✅ Scheduled weekly validation every {day} at {time_str}")
    return True


def run_scheduler():
    """Run scheduler loop."""
    if not SCHEDULE_AVAILABLE:
        print("❌ Error: 'schedule' library not installed")
        return
    
    print("🕐 Validation scheduler started")
    print("   Press Ctrl+C to stop")
    
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
    except KeyboardInterrupt:
        print("\n⚠️  Scheduler stopped")


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Schedule prediction validation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run daily at 2 AM
  python -m app.scripts.schedule_validation --daily --time=02:00
  
  # Run weekly on Monday at 3 AM
  python -m app.scripts.schedule_validation --weekly --day=monday --time=03:00
  
  # Run every 6 hours
  python -m app.scripts.schedule_validation --interval=6
        """
    )
    
    parser.add_argument(
        "--daily",
        action="store_true",
        help="Schedule daily validation"
    )
    parser.add_argument(
        "--weekly",
        action="store_true",
        help="Schedule weekly validation"
    )
    parser.add_argument(
        "--day",
        type=str,
        default="monday",
        choices=["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"],
        help="Day of week for weekly schedule"
    )
    parser.add_argument(
        "--time",
        type=str,
        default="02:00",
        help="Time to run (HH:MM format, default: 02:00)"
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=60,
        help="Validation duration in minutes (default: 60)"
    )
    parser.add_argument(
        "--interval",
        type=int,
        help="Run every N hours (alternative to daily/weekly)"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="logs",
        help="Output directory for reports"
    )
    parser.add_argument(
        "--run-once",
        action="store_true",
        help="Run validation once and exit (for testing)"
    )
    
    args = parser.parse_args()
    
    # Run once for testing
    if args.run_once:
        print("🧪 Running validation once (test mode)...")
        success = run_validation(args.duration, args.output)
        sys.exit(0 if success else 1)
    
    # Setup schedule
    if args.interval:
        if not SCHEDULE_AVAILABLE:
            print("❌ Error: 'schedule' library required for interval scheduling")
            sys.exit(1)
        schedule.every(args.interval).hours.do(run_validation, args.duration, args.output)
        print(f"✅ Scheduled validation every {args.interval} hours")
    elif args.weekly:
        if not setup_weekly_schedule(args.day, args.time, args.duration):
            sys.exit(1)
    elif args.daily:
        if not setup_daily_schedule(args.time, args.duration):
            sys.exit(1)
    else:
        # Default: daily at 2 AM
        if not setup_daily_schedule("02:00", args.duration):
            sys.exit(1)
    
    # Run scheduler
    run_scheduler()


if __name__ == "__main__":
    main()

