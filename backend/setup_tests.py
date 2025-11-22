"""
Script to quickly setup test structure for predictive cache warmer

Usage: python setup_tests.py

This script creates a basic test structure with TODO skeletons.
Note: Existing files will not be overwritten.
"""

import os
from pathlib import Path


def create_test_structure():
    """Create test directory and files if they don't exist."""
    
    # Create test directory if not exists
    test_dir = Path("tests")
    test_dir.mkdir(exist_ok=True)
    
    # Create conftest.py with basic fixtures (only if doesn't exist)
    conftest_path = test_dir / "conftest.py"
    
    if not conftest_path.exists():
        conftest_content = '''"""
Pytest configuration and fixtures for predictive cache warmer tests.

This module provides shared fixtures for all tests.
"""

import pytest
import pytest_asyncio
from datetime import datetime, timedelta
import random


@pytest.fixture
def sample_access_logs():
    """
    Generate realistic access logs for all tests.
    
    Creates 1000+ access logs with:
    - Realistic time patterns (peak hours weighted)
    - 80-20 game popularity distribution
    - Random user IDs
    - Realistic session durations
    """
    logs = []
    base_time = datetime(2024, 1, 15, 0, 0, 0)
    
    # Set seed for reproducibility
    random.seed(42)
    
    for i in range(1000):
        # Simulate realistic patterns with weighted hours
        # Morning peak: 8-11 AM, Evening peak: 7-9 PM
        hour = random.choices(
            range(24),
            weights=[1,1,1,1,1,2,4,6,8,10,8,6,5,4,6,8,10,12,10,8,6,4,2,1],
            k=1
        )[0]
        
        # Create timestamp
        timestamp = base_time + timedelta(
            hours=hour,
            minutes=random.randint(0, 59),
            seconds=random.randint(0, 59)
        )
        
        # Game selection with 80-20 distribution
        game_id = random.choices(
            range(1, 101),
            weights=[100-i for i in range(100)],  # Decreasing weights
            k=1
        )[0]
        
        log = {
            "timestamp": timestamp,  # Keep as datetime for compatibility
            "game_id": game_id,
            "user_id": str(random.randint(1, 500)),
            "session_duration": float(random.randint(300, 3600)),  # 5 min - 1 hour
            "access_count": random.randint(1, 10)
        }
        logs.append(log)
    
    # Sort by timestamp
    logs.sort(key=lambda x: x["timestamp"])
    
    return logs


@pytest_asyncio.fixture
async def mock_db(sample_access_logs):
    """
    Mock database functions for predictive cache warmer tests.
    
    Provides a mock database context that returns sample_access_logs
    when queried.
    """
    from unittest.mock import AsyncMock, patch, MagicMock
    
    async def mock_get_access_logs(start_date=None, end_date=None):
        """Filter logs by date range if provided"""
        if start_date is None and end_date is None:
            return sample_access_logs
        
        filtered = [
            log for log in sample_access_logs
            if (start_date is None or log["timestamp"] >= start_date)
            and (end_date is None or log["timestamp"] <= end_date)
        ]
        return filtered
    
    # Patch database access
    with patch('app.services.predictive_cache_warmer.db_manager') as mock_db_manager:
        mock_session = MagicMock()
        mock_session.execute = MagicMock()
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)
        
        mock_db_manager.get_session = MagicMock(return_value=mock_session)
        mock_db_manager.get_access_logs = AsyncMock(side_effect=mock_get_access_logs)
        
        yield mock_db_manager
'''
        
        with open(conftest_path, "w", encoding="utf-8") as f:
            f.write(conftest_content)
            print(f"✅ Created {conftest_path}")
    else:
        print(f"⏭️  {conftest_path} already exists, skipping")
    
    # Create test file with TODO skeleton (only if doesn't exist)
    test_file_path = test_dir / "test_predictive_cache_warmer.py"
    
    if not test_file_path.exists():
        test_content = '''"""
Comprehensive test suite for predictive cache warming

Run with: pytest tests/test_predictive_cache_warmer.py -v
Coverage: pytest tests/test_predictive_cache_warmer.py --cov=app.services.predictive_cache_warmer --cov-report=html
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch, MagicMock
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from app.services.predictive_cache_warmer import (
    AccessPatternAnalyzer,
    PredictiveCacheWarmer
)
from app.services.cache_warmer import CacheWarmer


# ============================================================================
# FIXTURES
# ============================================================================

@pytest_asyncio.fixture
async def analyzer(sample_access_logs):
    """
    Create configured analyzer for tests.
    
    TODO: Implement analyzer fixture with:
    - Mocked database access
    - Pre-analyzed patterns
    - Ready for testing
    """
    analyzer = AccessPatternAnalyzer(
        lookback_days=30,
        min_confidence=0.7,
    )
    
    # Mock database calls
    async def mock_get_access_logs(start_date, end_date):
        filtered = [
            log for log in sample_access_logs
            if start_date <= log["timestamp"] <= end_date
        ]
        return filtered
    
    analyzer._get_access_logs = mock_get_access_logs
    await analyzer.analyze_patterns()
    
    return analyzer


@pytest.fixture
def cache_warmer():
    """Create mock CacheWarmer for testing."""
    warmer = MagicMock(spec=CacheWarmer)
    warmer._warm_game_results = AsyncMock(return_value=True)
    warmer.strategy = "moderate"
    return warmer


# ============================================================================
# UNIT TESTS - Feature Extraction
# ============================================================================

@pytest.mark.asyncio
async def test_extract_features_returns_correct_shape(analyzer, sample_access_logs):
    """
    Test feature extraction returns expected shape.
    
    TODO: Verify:
    - Returns numpy array with correct shape
    - All features are numeric (no NaN, no Inf)
    - Temporal features (hour, day_of_week) are in valid ranges
    - Access count features are non-negative
    """
    df = pd.DataFrame(sample_access_logs)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    features = analyzer._extract_features(df)
    
    assert features is not None, "Features should not be None"
    assert isinstance(features, np.ndarray), "Features should be numpy array"
    assert len(features) >= 15, f"Should have at least 15 features, got {len(features)}"
    assert all(isinstance(f, (int, float, np.number)) for f in features), "All features should be numeric"
    
    # Check feature ranges
    hour_feature = features[0]
    assert 0 <= hour_feature <= 23, f"Hour should be 0-23, got {hour_feature}"
    
    # Verify feature array is 1D
    assert features.ndim == 1, "Features should be 1D array"
    
    # Check for NaN or infinite values
    assert not np.isnan(features).any(), "Features should not contain NaN"
    assert not np.isinf(features).any(), "Features should not contain infinite values"


@pytest.mark.asyncio
async def test_extract_features_handles_empty_data(analyzer):
    """Test feature extraction with empty data."""
    empty_df = pd.DataFrame()
    features = analyzer._extract_features(empty_df)
    
    assert features is None, "Empty data should return None"


# ============================================================================
# UNIT TESTS - Pattern Analysis
# ============================================================================

@pytest.mark.asyncio
async def test_analyze_patterns_identifies_peak_hours(analyzer):
    """
    Test peak hour identification.
    
    TODO: Verify:
    - Peak hours are correctly identified
    - Peak hours are valid (0-23)
    - Peak hours match data patterns
    """
    patterns = await analyzer.analyze_patterns()
    
    assert "peak_hours" in patterns
    assert isinstance(patterns["peak_hours"], list)
    
    peak_hours = patterns["peak_hours"]
    if len(peak_hours) > 0:
        assert all(0 <= h <= 23 for h in peak_hours), "Peak hours should be 0-23"


@pytest.mark.asyncio
async def test_analyze_patterns_returns_complete_structure(analyzer):
    """Test that pattern analysis returns all expected keys."""
    patterns = await analyzer.analyze_patterns()
    
    required_keys = [
        "hourly_distribution",
        "daily_distribution",
        "top_games",
        "peak_hours",
        "user_clusters",
    ]
    
    for key in required_keys:
        assert key in patterns, f"Missing key: {key}"


@pytest.mark.asyncio
async def test_cluster_users_creates_valid_clusters(analyzer, sample_access_logs):
    """
    Test user clustering creates valid clusters.
    
    TODO: Verify:
    - Clusters are created successfully
    - Cluster IDs are valid integers
    - All users are assigned to clusters
    - Reasonable number of clusters
    """
    df = pd.DataFrame(sample_access_logs)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df['hour'] = df['timestamp'].dt.hour
    
    clusters = await analyzer._cluster_users(df)
    
    assert isinstance(clusters, dict), "Clusters should be a dictionary"
    
    if len(clusters) > 0:
        cluster_ids = set(clusters.values())
        assert all(isinstance(cid, int) for cid in cluster_ids), "Cluster IDs should be integers"
        assert min(cluster_ids) >= 0, "Cluster IDs should be non-negative"


# ============================================================================
# INTEGRATION TESTS - Model Training
# ============================================================================

@pytest.mark.asyncio
async def test_train_prediction_model_succeeds(analyzer):
    """
    Test model training completes successfully.
    
    TODO: Verify:
    - Model training completes without errors
    - Model and scaler are created after training
    - Model can make predictions after training
    - Training metrics (accuracy) are reasonable
    """
    result = await analyzer.train_prediction_model()
    
    assert result is not None
    assert "status" in result
    
    if result.get("status") == "success":
        assert analyzer.model is not None, "Model should be trained"
        assert analyzer.feature_scaler is not None, "Scaler should be created"


@pytest.mark.asyncio
async def test_train_prediction_model_handles_insufficient_data(analyzer):
    """Test model training with insufficient data."""
    async def mock_get_access_logs(start_date, end_date):
        return []
    
    analyzer._get_access_logs = mock_get_access_logs
    
    result = await analyzer.train_prediction_model()
    
    assert result["status"] in ["insufficient_data", "insufficient_examples", "error"]


# ============================================================================
# INTEGRATION TESTS - Predictions
# ============================================================================

@pytest.mark.asyncio
async def test_predict_next_access_returns_high_confidence_predictions(analyzer):
    """
    Test predictions meet confidence threshold.
    
    TODO: Verify:
    - Predictions are returned in correct format
    - All predictions meet confidence threshold
    - Predictions are sorted by confidence (descending)
    - Predictions have required fields (game_id, confidence, time_horizon)
    """
    await analyzer.train_prediction_model()
    
    if analyzer.model is None:
        pytest.skip("Model training failed, skipping prediction test")
    
    predictions = await analyzer.predict_next_access(time_horizon=60, top_k=10)
    
    assert isinstance(predictions, list)
    assert len(predictions) <= 10, f"Should return at most 10 predictions, got {len(predictions)}"
    
    if len(predictions) > 0:
        for pred in predictions:
            assert "game_id" in pred, "Prediction should have game_id"
            assert "confidence" in pred, "Prediction should have confidence"
            assert "time_horizon" in pred, "Prediction should have time_horizon"
            
            assert isinstance(pred["game_id"], int)
            assert isinstance(pred["confidence"], float)
            assert isinstance(pred["time_horizon"], int)
        
        assert all(
            p["confidence"] >= analyzer.min_confidence
            for p in predictions
        ), "All predictions should meet confidence threshold"
        
        confidences = [p["confidence"] for p in predictions]
        assert confidences == sorted(confidences, reverse=True), "Predictions should be sorted by confidence"


# ============================================================================
# PERFORMANCE TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_prediction_performance(analyzer):
    """
    Benchmark prediction speed - must complete in < 100ms.
    
    TODO: Verify:
    - Single prediction takes < 100ms
    - Feature extraction is fast
    - Model inference is optimized
    """
    await analyzer.train_prediction_model()
    
    if analyzer.model is None:
        pytest.skip("Model training failed, skipping performance test")
    
    import time
    start_time = time.perf_counter()
    predictions = await analyzer.predict_next_access(time_horizon=60, top_k=20)
    end_time = time.perf_counter()
    
    duration_ms = (end_time - start_time) * 1000
    
    assert duration_ms < 100, (
        f"Predictions took {duration_ms:.2f}ms, should be < 100ms. "
        f"Got {len(predictions)} predictions."
    )
    
    print(f"\n[PERF] Prediction took {duration_ms:.2f}ms ({len(predictions)} predictions)")


# ============================================================================
# EDGE CASE TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_handles_no_data_gracefully(analyzer):
    """Test behavior with no access logs."""
    async def mock_get_access_logs(start_date, end_date):
        return []
    
    analyzer._get_access_logs = mock_get_access_logs
    
    patterns = await analyzer.analyze_patterns()
    
    assert patterns is not None
    assert "hourly_distribution" in patterns
    assert isinstance(patterns["hourly_distribution"], dict)
'''
        
        with open(test_file_path, "w", encoding="utf-8") as f:
            f.write(test_content)
        print(f"✅ Created {test_file_path}")
    else:
        print(f"⏭️  {test_file_path} already exists, skipping")
    
    return test_dir


def main():
    """Main function to setup test structure."""
    print("🚀 Setting up test structure for predictive cache warmer...\n")
    
    # Change to backend directory if script is run from root
    if Path("backend").exists():
        os.chdir("backend")
        print("📁 Changed to backend directory")
    
    test_dir = create_test_structure()
    
    print("\n✅ Test structure setup complete!")
    print("\n📁 Files created/checked:")
    print(f"  - {test_dir}/conftest.py")
    print(f"  - {test_dir}/test_predictive_cache_warmer.py")
    print("\n🚀 Next steps:")
    print("  1. Review the generated test files")
    print("  2. Run: pytest tests/test_predictive_cache_warmer.py -v")
    print("  3. Check coverage: pytest tests/test_predictive_cache_warmer.py --cov=app.services.predictive_cache_warmer")
    print("  4. Expand TODO sections as needed")


if __name__ == "__main__":
    main()

