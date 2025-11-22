#!/usr/bin/env python3
"""Resume script to check progress and continue from last checkpoint."""

import os
import re
from datetime import datetime
from pathlib import Path


def read_progress():
    """Read PROGRESS.md and extract current status."""
    progress_file = Path("PROGRESS.md")
    if not progress_file.exists():
        print("❌ PROGRESS.md not found. Run from project root.")
        return None

    content = progress_file.read_text(encoding="utf-8")
    
    # Extract current phase
    phase_match = re.search(r"\*\*Current Phase:\*\* (.+)", content)
    current_phase = phase_match.group(1) if phase_match else "Unknown"
    
    # Extract overall status
    status_match = re.search(r"\*\*Overall Status:\*\* (.+)", content)
    overall_status = status_match.group(1) if status_match else "Unknown"
    
    # Find incomplete tasks
    incomplete = []
    for line in content.split("\n"):
        if re.match(r"^- \[ \]", line):
            task = line.strip()
            incomplete.append(task)
    
    return {
        "phase": current_phase,
        "status": overall_status,
        "incomplete_tasks": incomplete[:10],  # First 10
    }


def main():
    """Main entry point."""
    print("🔄 Baccarat Predictor Pro - Resume Check\n")
    
    progress = read_progress()
    if not progress:
        return
    
    print(f"📊 Current Phase: {progress['phase']}")
    print(f"📈 Overall Status: {progress['status']}\n")
    
    if progress["incomplete_tasks"]:
        print("📋 Next Tasks:")
        for task in progress["incomplete_tasks"]:
            print(f"  {task}")
    else:
        print("✅ All tracked tasks complete!")
    
    print("\n💡 Tip: Check PROGRESS.md for detailed status")


if __name__ == "__main__":
    main()

