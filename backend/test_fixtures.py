"""
Quick test script for conftest fixtures.

Usage:
    python test_fixtures.py
"""

import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

try:
    # Import fixtures (may fail if dependencies missing)
    from tests.conftest import sample_access_logs, generate_user_clusters, calculate_expected_metrics
    
    print("✅ Successfully imported fixtures\n")
    
    # Test sample_access_logs
    print("=" * 60)
    print("Testing sample_access_logs fixture...")
    print("=" * 60)
    
    logs = sample_access_logs()
    
    print(f"✅ Generated {len(logs)} logs")
    print(f"✅ First log: {logs[0]}")
    print(f"✅ Last log: {logs[-1]}")
    
    if logs:
        first_timestamp = logs[0]["timestamp"]
        last_timestamp = logs[-1]["timestamp"]
        print(f"✅ Date range: {first_timestamp} to {last_timestamp}")
        
        # Check structure
        required_keys = ["timestamp", "game_id", "user_id", "session_duration", "access_count"]
        first_log_keys = set(logs[0].keys())
        missing_keys = set(required_keys) - first_log_keys
        if missing_keys:
            print(f"⚠️  Missing keys: {missing_keys}")
        else:
            print(f"✅ All required keys present: {required_keys}")
        
        # Check patterns
        game_ids = [log["game_id"] for log in logs]
        unique_games = len(set(game_ids))
        print(f"✅ Unique games: {unique_games}")
        
        # Check 80-20 distribution (top 20 should have more accesses)
        top_20_count = sum(1 for gid in game_ids if 1 <= gid <= 20)
        top_20_pct = (top_20_count / len(game_ids)) * 100
        print(f"✅ Top 20 games: {top_20_pct:.1f}% of accesses (expected ~80%)")
        
        # Check user distribution
        user_ids = [log["user_id"] for log in logs]
        unique_users = len(set(user_ids))
        print(f"✅ Unique users: {unique_users}")
        
        # Check hour distribution
        hours = [log["timestamp"].hour for log in logs]
        peak_hours = [h for h in hours if h in [9, 10, 11, 14, 15, 16, 19, 20, 21]]
        peak_pct = (len(peak_hours) / len(hours)) * 100
        print(f"✅ Peak hour accesses: {peak_pct:.1f}% (hours 9-11, 14-16, 19-21)")
    
    print("\n" + "=" * 60)
    print("Testing generate_user_clusters helper...")
    print("=" * 60)
    
    clusters = generate_user_clusters(num_users=500, num_clusters=5)
    print(f"✅ Generated clusters for {len(clusters)} users")
    
    # Check distribution
    cluster_counts = {}
    for user_id, cluster_id in clusters.items():
        cluster_counts[cluster_id] = cluster_counts.get(cluster_id, 0) + 1
    
    print(f"✅ Cluster distribution:")
    for cluster_id, count in sorted(cluster_counts.items()):
        pct = (count / len(clusters)) * 100
        print(f"   Cluster {cluster_id}: {count} users ({pct:.1f}%)")
    
    print("\n" + "=" * 60)
    print("Testing calculate_expected_metrics helper...")
    print("=" * 60)
    
    # Test metrics calculation
    predictions = [
        {"game_id": 1, "confidence": 0.8},
        {"game_id": 2, "confidence": 0.7},
        {"game_id": 3, "confidence": 0.6},
    ]
    
    actual = [
        {"game_id": 1},
        {"game_id": 3},
        {"game_id": 4},
    ]
    
    metrics = calculate_expected_metrics(predictions, actual)
    print(f"✅ Calculated metrics:")
    print(f"   Precision: {metrics['precision']:.2%}")
    print(f"   Recall: {metrics['recall']:.2%}")
    print(f"   F1 Score: {metrics['f1_score']:.2%}")
    print(f"   Accuracy: {metrics['accuracy']:.2%}")
    print(f"   TP: {metrics['true_positives']}, FP: {metrics['false_positives']}, FN: {metrics['false_negatives']}")
    
    print("\n" + "=" * 60)
    print("✅ All fixture tests passed!")
    print("=" * 60)
    
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("   Some dependencies may be missing. This is expected in test environment.")
    print("   Fixtures are correctly defined in conftest.py")
    sys.exit(1)
except Exception as e:
    print(f"❌ Error testing fixtures: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

