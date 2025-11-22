#!/usr/bin/env python3
"""
CLI wrapper script for easy load test execution with presets.

Usage:
    python run_load_test.py --preset=light
    python run_load_test.py --preset=medium
    python run_load_test.py --preset=heavy
    python run_load_test.py --preset=stress
    python run_load_test.py --custom --users=200 --duration=30m
"""

import argparse
import subprocess
import sys
from pathlib import Path


# Preset configurations
PRESETS = {
    "light": {
        "users": 10,
        "spawn_rate": 2,
        "duration": "5m",
        "description": "Light load test: 10 users for 5 minutes",
    },
    "medium": {
        "users": 100,
        "spawn_rate": 10,
        "duration": "10m",
        "description": "Medium load test: 100 users for 10 minutes",
    },
    "heavy": {
        "users": 500,
        "spawn_rate": 50,
        "duration": "15m",
        "description": "Heavy load test: 500 users for 15 minutes",
    },
    "stress": {
        "users": 1000,
        "spawn_rate": 100,
        "duration": "20m",
        "description": "Stress test: 1000 users for 20 minutes",
    },
    "progressive": {
        "shape": "ProgressiveLoadShape",
        "description": "Progressive load: gradually increase from 10 to 1000 users",
    },
    "burst": {
        "shape": "BurstLoadShape",
        "description": "Burst test: traffic spikes and recovery",
    },
    "soak": {
        "shape": "SoakLoadShape",
        "description": "Soak test: 200 users for 60 minutes (endurance)",
    },
}


def parse_duration(duration_str: str) -> str:
    """
    Parse duration string to Locust format.
    
    Supports: 30s, 5m, 1h, etc.
    """
    return duration_str


def build_locust_command(args) -> list:
    """Build Locust command from arguments."""
    locustfile = Path(__file__).parent / "locustfile.py"
    
    if not locustfile.exists():
        print(f"Error: locustfile.py not found at {locustfile}")
        sys.exit(1)
    
    cmd = ["locust", "-f", str(locustfile)]
    
    # Add host
    if args.host:
        cmd.extend(["--host", args.host])
    else:
        cmd.extend(["--host", "http://localhost:8000"])
    
    # Handle preset or custom
    if args.preset:
        preset = PRESETS.get(args.preset)
        if not preset:
            print(f"Error: Unknown preset '{args.preset}'")
            print(f"Available presets: {', '.join(PRESETS.keys())}")
            sys.exit(1)
        
        if "shape" in preset:
            # Use LoadTestShape
            cmd.extend(["--shape", preset["shape"]])
        else:
            # Use fixed users
            cmd.extend(["--users", str(preset["users"])])
            cmd.extend(["--spawn-rate", str(preset["spawn_rate"])])
            cmd.extend(["--run-time", preset["duration"]])
    else:
        # Custom configuration
        if args.users:
            cmd.extend(["--users", str(args.users)])
        if args.spawn_rate:
            cmd.extend(["--spawn-rate", str(args.spawn_rate)])
        if args.duration:
            cmd.extend(["--run-time", parse_duration(args.duration)])
        if args.shape:
            cmd.extend(["--shape", args.shape])
    
    # Add headless mode
    if args.headless:
        cmd.append("--headless")
    
    # Add HTML report
    if args.report:
        cmd.extend(["--html", args.report])
    
    # Add CSV output
    if args.csv:
        cmd.extend(["--csv", args.csv])
    
    # Add log level
    if args.log_level:
        cmd.extend(["--loglevel", args.log_level])
    
    # Add web UI port
    if args.web_port:
        cmd.extend(["--web-port", str(args.web_port)])
    
    return cmd


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run load tests against Baccarat Predictor API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run light preset
  python run_load_test.py --preset=light
  
  # Run progressive load shape
  python run_load_test.py --preset=progressive --headless
  
  # Custom test
  python run_load_test.py --custom --users=200 --duration=30m --spawn-rate=20
  
  # With HTML report
  python run_load_test.py --preset=medium --report=report.html
  
Available presets:
  light       - 10 users, 5 minutes
  medium      - 100 users, 10 minutes
  heavy       - 500 users, 15 minutes
  stress      - 1000 users, 20 minutes
  progressive - Gradually increase from 10 to 1000 users
  burst       - Traffic spikes and recovery
  soak        - 200 users for 60 minutes (endurance test)
        """
    )
    
    # Preset or custom
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--preset",
        choices=list(PRESETS.keys()),
        help="Use preset configuration"
    )
    group.add_argument(
        "--custom",
        action="store_true",
        help="Use custom configuration"
    )
    
    # Custom options
    parser.add_argument(
        "--users",
        type=int,
        help="Number of concurrent users (custom mode only)"
    )
    parser.add_argument(
        "--spawn-rate",
        type=int,
        help="Users spawned per second (custom mode only)"
    )
    parser.add_argument(
        "--duration",
        type=str,
        help="Test duration (e.g., 30s, 5m, 1h) (custom mode only)"
    )
    parser.add_argument(
        "--shape",
        type=str,
        choices=["ProgressiveLoadShape", "BurstLoadShape", "SoakLoadShape"],
        help="Load test shape (custom mode only)"
    )
    
    # General options
    parser.add_argument(
        "--host",
        type=str,
        default="http://localhost:8000",
        help="Target host (default: http://localhost:8000)"
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run in headless mode (no web UI)"
    )
    parser.add_argument(
        "--report",
        type=str,
        help="Path to HTML report output"
    )
    parser.add_argument(
        "--csv",
        type=str,
        help="CSV output prefix (generates multiple CSV files)"
    )
    parser.add_argument(
        "--log-level",
        type=str,
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="INFO",
        help="Log level (default: INFO)"
    )
    parser.add_argument(
        "--web-port",
        type=int,
        default=8089,
        help="Web UI port (default: 8089)"
    )
    
    args = parser.parse_args()
    
    # Validate custom mode arguments
    if args.custom:
        if not args.users and not args.shape:
            parser.error("--custom requires either --users or --shape")
        if args.users and not args.duration and not args.shape:
            parser.error("--custom with --users requires --duration or --shape")
    
    # Show preset info
    if args.preset:
        preset = PRESETS[args.preset]
        print(f"📊 Preset: {args.preset}")
        print(f"   {preset['description']}")
        if "shape" in preset:
            print(f"   Using LoadTestShape: {preset['shape']}")
        print()
    
    # Build and run command
    cmd = build_locust_command(args)
    
    print("🚀 Starting load test...")
    print(f"   Command: {' '.join(cmd)}")
    print()
    
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Load test failed with exit code {e.returncode}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n⚠️  Load test interrupted by user")
        sys.exit(130)
    except FileNotFoundError:
        print("\n❌ Error: 'locust' command not found")
        print("   Please install Locust: pip install locust")
        sys.exit(1)


if __name__ == "__main__":
    main()

