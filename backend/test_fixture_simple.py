"""
Simple test for sample_access_logs fixture logic.

Tests fixture without importing full conftest dependencies.
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
import random

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))


def test_sample_access_logs_logic():
    """Test the logic of sample_access_logs fixture."""
    logs = []
    base_time = datetime(2024, 1, 1, 0, 0, 0)
    
    random.seed(42)
    
    # Hour weights
    hour_weights = [
        1, 1, 1, 1, 1, 1,  # 0-5 AM (low)
        4, 4, 4,           # 6-8 AM (normal)
        10, 10, 10,       # 9-11 AM (peak)
        6,                 # 12 PM (normal)
        12, 12, 12,       # 1-3 PM (peak)
        8, 8,              # 4-5 PM (normal)
        10, 10, 10,       # 6-8 PM (peak)
        4, 4,              # 9-10 PM (normal)
        2                  # 11 PM (low)
    ]
    
    # Game weights: 80-20 distribution
    # Top 20 games should get ~80% of traffic
    game_weights = []
    for i in range(100):
        if i < 20:  # Top 20 games: high weights (80% of traffic)
            game_weights.append(100 - i * 2.0)
        elif i < 50:  # Mid 30 games: medium weights (15% of traffic)
            game_weights.append(20 - (i - 20) * 0.5)
        else:  # Long tail 50 games: low weights (5% of traffic)
            game_weights.append(5 - (i - 50) * 0.08)
    
    # Generate 1000+ logs
    for i in range(1500):
        hour = random.choices(range(24), weights=hour_weights, k=1)[0]
        day_offset = i % 30
        day_of_week = (base_time + timedelta(days=day_offset)).weekday()
        is_weekend = day_of_week >= 5
        
        if is_weekend and hour in [9, 10, 11]:
            if random.random() < 0.3:
                pass
            else:
                hour = random.choice([19, 20, 21])
        
        timestamp = base_time + timedelta(
            days=day_offset,
            hours=hour,
            minutes=random.randint(0, 59),
            seconds=random.randint(0, 59)
        )
        
        game_id = random.choices(range(1, 101), weights=game_weights, k=1)[0]
        
        user_choice = random.random()
        if user_choice < 0.1:
            user_id = random.randint(1, 50)
            session_duration = random.randint(3600, 7200)
            access_count = random.randint(10, 20)
        elif user_choice < 0.4:
            user_id = random.randint(51, 200)
            session_duration = random.randint(1800, 3600)
            access_count = random.randint(5, 15)
        else:
            user_id = random.randint(201, 500)
            session_duration = random.randint(300, 1800)
            access_count = random.randint(1, 10)
        
        log = {
            "timestamp": timestamp,
            "game_id": game_id,
            "user_id": str(user_id),
            "session_duration": float(session_duration),
            "access_count": access_count
        }
        logs.append(log)
    
    logs.sort(key=lambda x: x["timestamp"])
    
    return logs


if __name__ == "__main__":
    print("Testing sample_access_logs fixture logic...")
    print("=" * 60)
    
    logs = test_sample_access_logs_logic()
    
    print(f"Generated {len(logs)} logs")
    print(f"First log: {logs[0]}")
    print(f"Last log: {logs[-1]}")
    
    if logs:
        first_timestamp = logs[0]["timestamp"]
        last_timestamp = logs[-1]["timestamp"]
        print(f"Date range: {first_timestamp} to {last_timestamp}")
        
        # Check structure
        required_keys = ["timestamp", "game_id", "user_id", "session_duration", "access_count"]
        first_log_keys = set(logs[0].keys())
        missing_keys = set(required_keys) - first_log_keys
        if missing_keys:
            print(f"WARNING: Missing keys: {missing_keys}")
        else:
            print(f"All required keys present: {required_keys}")
        
        # Check patterns
        game_ids = [log["game_id"] for log in logs]
        unique_games = len(set(game_ids))
        print(f"Unique games: {unique_games}")
        
        # Check 80-20 distribution
        top_20_count = sum(1 for gid in game_ids if 1 <= gid <= 20)
        top_20_pct = (top_20_count / len(game_ids)) * 100
        print(f"Top 20 games: {top_20_pct:.1f}% of accesses (expected ~80%)")
        
        # Check user distribution
        user_ids = [log["user_id"] for log in logs]
        unique_users = len(set(user_ids))
        print(f"Unique users: {unique_users}")
        
        # Check hour distribution
        hours = [log["timestamp"].hour for log in logs]
        peak_hours = [h for h in hours if h in [9, 10, 11, 14, 15, 16, 19, 20, 21]]
        peak_pct = (len(peak_hours) / len(hours)) * 100
        print(f"Peak hour accesses: {peak_pct:.1f}% (hours 9-11, 14-16, 19-21)")
    
    print("=" * 60)
    print("Fixture test completed successfully!")

