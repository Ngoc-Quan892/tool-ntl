"""
Helper script to run coverage report for predictive cache warmer tests.

Usage:
    python run_coverage.py

This will:
1. Run pytest with coverage
2. Generate HTML report
3. Print summary
4. Open HTML report in browser (optional)
"""

import subprocess
import sys
from pathlib import Path


def run_coverage():
    """Run coverage report."""
    print("🔍 Running coverage analysis for predictive_cache_warmer...\n")
    
    # Run pytest with coverage
    cmd = [
        "pytest",
        "tests/test_predictive_cache_warmer.py",
        "--cov=app.services.predictive_cache_warmer",
        "--cov-report=html",
        "--cov-report=term",
        "--cov-report=term-missing",
        "-v"
    ]
    
    try:
        result = subprocess.run(cmd, cwd=Path(__file__).parent, check=False)
        
        htmlcov_path = Path(__file__).parent / "htmlcov" / "index.html"
        
        if htmlcov_path.exists():
            print(f"\n✅ Coverage report generated!")
            print(f"📊 HTML report: {htmlcov_path.absolute()}")
            print(f"\n💡 Open in browser:")
            print(f"   file://{htmlcov_path.absolute()}")
            
            # Try to open in browser (optional)
            try:
                import webbrowser
                webbrowser.open(f"file://{htmlcov_path.absolute()}")
                print("   (Opened in default browser)")
            except:
                pass
        else:
            print("\n⚠️  HTML report not found. Check for errors above.")
        
        return result.returncode
        
    except FileNotFoundError:
        print("❌ Error: pytest not found. Install with: pip install pytest pytest-cov")
        return 1
    except Exception as e:
        print(f"❌ Error running coverage: {e}")
        return 1


if __name__ == "__main__":
    exit_code = run_coverage()
    sys.exit(exit_code)

