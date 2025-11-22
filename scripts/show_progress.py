#!/usr/bin/env python3
"""Display current project progress from PROGRESS.md."""

from pathlib import Path
import re


def main():
    """Read and display progress summary."""
    progress_file = Path("PROGRESS.md")
    if not progress_file.exists():
        print("❌ PROGRESS.md not found")
        return
    
    content = progress_file.read_text(encoding="utf-8")
    
    # Extract progress percentage
    progress_match = re.search(r"## 📊 PHASE 0 PROGRESS: (\d+)/(\d+)", content)
    if progress_match:
        completed, total = progress_match.groups()
        percentage = (int(completed) / int(total)) * 100
        print(f"📊 Progress: {completed}/{total} tasks ({percentage:.1f}%)")
    
    # Show current phase
    phase_match = re.search(r"\*\*Current Phase:\*\* (.+)", content)
    if phase_match:
        print(f"🎯 Phase: {phase_match.group(1)}")
    
    print("\n📝 See PROGRESS.md for details")


if __name__ == "__main__":
    main()

