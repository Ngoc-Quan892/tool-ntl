#!/usr/bin/env python3
"""Validation script for project structure and setup."""

import os
import sys
from pathlib import Path


def check_directories():
    """Verify all required directories exist."""
    required_dirs = [
        "backend/app/core",
        "backend/app/models",
        "backend/app/api/v1",
        "backend/app/api/v2",
        "backend/tests/unit",
        "frontend/src/components",
        "docs/specifications",
        ".github/workflows",
    ]
    
    missing = []
    for dir_path in required_dirs:
        if not Path(dir_path).exists():
            missing.append(dir_path)
    
    if missing:
        print("❌ Missing directories:")
        for d in missing:
            print(f"   - {d}")
        return False
    
    print("✅ All required directories exist")
    return True


def check_init_files():
    """Check that all Python packages have __init__.py."""
    python_dirs = [
        "backend/app",
        "backend/app/core",
        "backend/app/models",
        "backend/app/api",
        "backend/app/api/v1",
        "backend/app/api/v2",
        "backend/tests",
        "backend/tests/unit",
    ]
    
    missing = []
    for dir_path in python_dirs:
        init_file = Path(dir_path) / "__init__.py"
        if not init_file.exists():
            missing.append(str(init_file))
    
    if missing:
        print("❌ Missing __init__.py files:")
        for f in missing:
            print(f"   - {f}")
        return False
    
    print("✅ All Python packages have __init__.py")
    return True


def check_config_files():
    """Check essential configuration files."""
    configs = {
        "PROGRESS.md": "Progress tracking",
        ".gitignore": "Git ignore rules",
        "README.md": "Project documentation",
        "backend/requirements.txt": "Python dependencies",
        "frontend/package.json": "Node dependencies",
    }
    
    missing = []
    for file_path, desc in configs.items():
        if not Path(file_path).exists():
            missing.append(f"{file_path} ({desc})")
    
    if missing:
        print("❌ Missing configuration files:")
        for f in missing:
            print(f"   - {f}")
        return False
    
    print("✅ Essential configuration files present")
    return True


def main():
    """Run all validation checks."""
    phase = sys.argv[1] if len(sys.argv) > 1 else "phase-0"
    
    print(f"🔍 Validating {phase}...\n")
    
    checks = [
        ("Directories", check_directories),
        ("__init__.py files", check_init_files),
        ("Config files", check_config_files),
    ]
    
    results = []
    for name, check_func in checks:
        try:
            result = check_func()
            results.append(result)
        except Exception as e:
            print(f"❌ Error in {name}: {e}")
            results.append(False)
    
    print("\n" + "=" * 50)
    if all(results):
        print("✅ All validations passed!")
        return 0
    else:
        print("❌ Some validations failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())

