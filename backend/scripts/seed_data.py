"""
Seed data script for initial database population.

This script creates sample data for development and testing purposes.
Run with: python -m scripts.seed_data
"""
from __future__ import annotations

import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import get_settings
from app.models.database import db_manager, GameResult, SimulationRun

settings = get_settings()


def seed_game_results(count: int = 100) -> None:
    """
    Seed game_results table with sample data.

    Args:
        count: Number of game results to create
    """
    print(f"Seeding {count} game results...")

    results = ["B", "P", "T"]
    base_time = datetime.utcnow() - timedelta(days=1)

    with db_manager.get_session() as session:
        for i in range(count):
            result = results[i % 3]  # Cycle through B, P, T
            shoe_number = (i // 50) + 1  # New shoe every 50 hands
            hand_number = (i % 50) + 1

            game_result = GameResult(
                result=result,
                prediction={
                    "recommend": "B" if i % 2 == 0 else "P",
                    "confidence": 0.5 + (i % 50) / 100,
                    "edge_pct": (i % 10) / 2,
                    "pattern": "Streak" if i % 3 == 0 else "Pattern",
                    "true_count": (i % 20) - 10,
                    "next_suggested": "B" if i % 2 == 0 else "P",
                    "timestamp": base_time.isoformat(),
                },
                shoe_number=shoe_number,
                hand_number=hand_number,
                timestamp=base_time + timedelta(minutes=i),
                true_count=(i % 20) - 10,
                edge=(i % 10) / 2,
            )
            session.add(game_result)

        session.commit()
        print(f"✓ Created {count} game results")


def seed_simulation_runs(count: int = 5) -> None:
    """
    Seed simulation_runs table with sample data.

    Args:
        count: Number of simulation runs to create
    """
    print(f"Seeding {count} simulation runs...")

    statuses = ["completed", "running", "pending", "failed"]
    base_time = datetime.utcnow() - timedelta(hours=2)

    with db_manager.get_session() as session:
        for i in range(count):
            status = statuses[i % len(statuses)]
            total_shoes = (i + 1) * 100
            completed_shoes = total_shoes if status == "completed" else (i + 1) * 20

            sim_run = SimulationRun(
                task_id=f"sim_{i+1:04d}_{int(base_time.timestamp())}",
                total_shoes=total_shoes,
                completed_shoes=completed_shoes,
                results={
                    "banker_wins": completed_shoes * 0.45,
                    "player_wins": completed_shoes * 0.45,
                    "ties": completed_shoes * 0.10,
                    "accuracy": 0.5 + (i % 30) / 100,
                } if status == "completed" else None,
                status=status,
                started_at=base_time + timedelta(minutes=i * 30),
                completed_at=base_time + timedelta(hours=1, minutes=i * 30) if status == "completed" else None,
            )
            session.add(sim_run)

        session.commit()
        print(f"✓ Created {count} simulation runs")


def clear_existing_data() -> None:
    """Clear existing data from tables."""
    print("Clearing existing data...")
    with db_manager.get_session() as session:
        session.query(SimulationRun).delete()
        session.query(GameResult).delete()
        session.commit()
    print("✓ Cleared existing data")


def main() -> None:
    """Main seed function."""
    print("=" * 60)
    print("Database Seed Script")
    print("=" * 60)
    print(f"Database: {db_manager.database_url.split('@')[-1] if '@' in db_manager.database_url else db_manager.database_url}")
    print()

    # Check database health
    if not db_manager.health_check():
        print("❌ Database connection failed. Please check your DATABASE_URL.")
        sys.exit(1)

    print("✓ Database connection successful")
    print()

    # Ask for confirmation
    import argparse
    parser = argparse.ArgumentParser(description="Seed database with sample data")
    parser.add_argument("--clear", action="store_true", help="Clear existing data before seeding")
    parser.add_argument("--game-results", type=int, default=100, help="Number of game results to create")
    parser.add_argument("--simulation-runs", type=int, default=5, help="Number of simulation runs to create")
    args = parser.parse_args()

    if args.clear:
        clear_existing_data()
        print()

    # Seed data
    try:
        seed_game_results(args.game_results)
        seed_simulation_runs(args.simulation_runs)
        print()
        print("=" * 60)
        print("✓ Seeding completed successfully!")
        print("=" * 60)
    except Exception as e:
        print()
        print("=" * 60)
        print(f"❌ Error during seeding: {e}")
        print("=" * 60)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

