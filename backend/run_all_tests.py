"""
Script to run all tests and generate summary.

Usage:
    python run_all_tests.py
"""

import subprocess
import sys
from pathlib import Path


def run_command(cmd, description):
    """Run a command and return result."""
    print(f"\n{'='*70}")
    print(f"{description}")
    print(f"{'='*70}")
    print(f"Running: {cmd}\n")
    
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            cwd=Path(__file__).parent,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace'
        )
        
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        
        return result.returncode == 0
    except Exception as e:
        print(f"Error running command: {e}")
        return False


def main():
    """Run all test commands."""
    print("="*70)
    print("RUNNING ALL TESTS")
    print("="*70)
    
    # Check if pytest is available
    try:
        result = subprocess.run(
            ["pytest", "--version"],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            print("ERROR: pytest not found. Install with: pip install pytest pytest-asyncio pytest-cov")
            return 1
    except FileNotFoundError:
        print("ERROR: pytest not found. Install with: pip install pytest pytest-asyncio pytest-cov")
        return 1
    
    tests = [
        ("pytest tests/test_model_training.py -v", "1. Model Training Tests"),
        ("pytest tests/test_predictions.py -v", "2. Prediction Tests"),
        ("pytest tests/test_feature_extraction.py -v", "3. Feature Extraction Tests"),
        ("pytest tests/test_pattern_analysis.py -v", "4. Pattern Analysis Tests"),
    ]
    
    results = []
    for cmd, desc in tests:
        success = run_command(cmd, desc)
        results.append((desc, success))
    
    # Run coverage
    print(f"\n{'='*70}")
    print("5. Coverage Report")
    print(f"{'='*70}")
    coverage_cmd = (
        "pytest tests/test_model_training.py tests/test_predictions.py "
        "--cov=app.services.predictive_cache_warmer "
        "--cov-report=term-missing"
    )
    run_command(coverage_cmd, "Coverage for Model Training + Predictions")
    
    # Summary
    print(f"\n{'='*70}")
    print("SUMMARY")
    print(f"{'='*70}")
    
    for desc, success in results:
        status = "PASSED" if success else "FAILED/SKIPPED"
        print(f"{desc}: {status}")
    
    print(f"\n{'='*70}")
    print("To run all tests:")
    print("  pytest tests/ -v --tb=short")
    print(f"{'='*70}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

