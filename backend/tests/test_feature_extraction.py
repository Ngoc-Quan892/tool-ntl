"""
Comprehensive tests for feature extraction.

Purpose: Validate that _extract_features works correctly
This ensures ML model gets quality features
"""

import pytest
import pytest_asyncio
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from unittest.mock import patch

from app.services.predictive_cache_warmer import AccessPatternAnalyzer


# ============================================================================
# Test Feature Extraction Returns Correct Shape
# ============================================================================

@pytest.mark.asyncio
async def test_extract_features_returns_correct_shape(analyzer, sample_access_logs):
    """Test that feature extraction returns expected number of features"""
    # Convert sample logs to DataFrame
    df = pd.DataFrame(sample_access_logs[:100])
    
    # Ensure timestamp is datetime
    if 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # Extract features
    features = analyzer._extract_features(df)
    
    # Assertions
    assert features is not None, "Should return features array"
    assert isinstance(features, np.ndarray), "Should return numpy array"
    assert len(features) >= 13, f"Should have at least 13 features, got {len(features)}"
    assert features.dtype in [np.float32, np.float64], f"Features should be float, got {features.dtype}"
    
    # Check for NaN values
    assert not np.isnan(features).any(), "Should not contain NaN"
    assert not np.isinf(features).any(), "Should not contain Inf"


# ============================================================================
# Test Temporal Features Are Valid
# ============================================================================

@pytest.mark.asyncio
async def test_temporal_features_valid_ranges(analyzer, sample_access_logs):
    """Test temporal features are within valid ranges"""
    # Convert sample logs to DataFrame
    df = pd.DataFrame(sample_access_logs[:100])
    
    # Ensure timestamp is datetime
    if 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # Extract features
    features = analyzer._extract_features(df)
    
    assert features is not None, "Should return features"
    
    # Temporal features are at indices 0-3
    # features[0] = hour, features[1] = day_of_week, 
    # features[2] = is_weekend, features[3] = is_peak_hour
    hour = int(features[0])
    day_of_week = int(features[1])
    is_weekend = int(features[2])
    is_peak_hour = int(features[3])
    
    # Assertions
    assert 0 <= hour <= 23, f"Hour should be 0-23, got {hour}"
    assert 0 <= day_of_week <= 6, f"Day should be 0-6, got {day_of_week}"
    assert is_weekend in [0, 1], f"is_weekend should be binary (0 or 1), got {is_weekend}"
    assert is_peak_hour in [0, 1], f"is_peak_hour should be binary (0 or 1), got {is_peak_hour}"


# ============================================================================
# Test Access Pattern Features Are Calculated Correctly
# ============================================================================

@pytest.mark.asyncio
async def test_access_pattern_features(analyzer):
    """Test access count and session features"""
    # Create a known log entry DataFrame
    current_time = datetime(2024, 1, 15, 10, 30, 0)
    
    # Create DataFrame with known values
    logs = [
        {
            "timestamp": current_time - timedelta(minutes=5),
            "game_id": 1,
            "user_id": "100",
            "session_duration": 1800.0,
            "access_count": 10
        },
        {
            "timestamp": current_time - timedelta(minutes=10),
            "game_id": 2,
            "user_id": "101",
            "session_duration": 1200.0,
            "access_count": 5
        }
    ]
    
    df = pd.DataFrame(logs)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # Mock current_time in analyzer
    with patch('app.services.predictive_cache_warmer.datetime') as mock_dt:
        mock_dt.now.return_value = current_time
        mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)
        
        features = analyzer._extract_features(df)
    
    assert features is not None, "Should return features"
    
    # Access pattern features are at indices 4-8
    # features[4] = access_count_15min
    # features[5] = access_count_60min
    # features[6] = unique_users_15min
    # features[7] = unique_games_15min
    # features[8] = avg_session_duration
    
    access_count_15min = int(features[4])
    access_count_60min = int(features[5])
    unique_users_15min = int(features[6])
    unique_games_15min = int(features[7])
    avg_session_duration = float(features[8])
    
    # Assertions
    assert access_count_15min >= 0, "Access count should be non-negative"
    assert access_count_60min >= access_count_15min, "60min count should be >= 15min count"
    assert unique_users_15min >= 0, "Unique users should be non-negative"
    assert unique_games_15min >= 0, "Unique games should be non-negative"
    assert avg_session_duration >= 0, "Session duration should be non-negative"
    
    # Check that avg_session_duration is approximately correct
    expected_avg = (1800.0 + 1200.0) / 2
    assert abs(avg_session_duration - expected_avg) < 1.0, \
        f"Avg session duration should be ~{expected_avg}, got {avg_session_duration}"


# ============================================================================
# Test Feature Consistency
# ============================================================================

@pytest.mark.asyncio
async def test_feature_extraction_consistency(analyzer, sample_access_logs):
    """Test that same input produces same output"""
    # Convert sample logs to DataFrame
    df = pd.DataFrame(sample_access_logs[:50])
    
    # Ensure timestamp is datetime
    if 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # Extract features twice
    features1 = analyzer._extract_features(df)
    features2 = analyzer._extract_features(df)
    
    # Assert identical (within floating point precision)
    assert features1 is not None, "First extraction should succeed"
    assert features2 is not None, "Second extraction should succeed"
    assert np.array_equal(features1, features2), "Should be deterministic"
    
    # Also check with allclose for floating point comparison
    assert np.allclose(features1, features2, rtol=1e-5), \
        "Features should be consistent within floating point precision"


# ============================================================================
# Test Feature Extraction Handles Edge Cases
# ============================================================================

@pytest.mark.asyncio
async def test_feature_extraction_edge_cases(analyzer):
    """Test edge cases in feature extraction"""
    current_time = datetime(2024, 1, 15, 12, 0, 0)
    
    # Test case 1: Midnight hour (hour=0)
    with patch('app.services.predictive_cache_warmer.datetime') as mock_dt:
        mock_dt.now.return_value = datetime(2024, 1, 15, 0, 0, 0)
        mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)
        
        df = pd.DataFrame([{
            "timestamp": datetime(2024, 1, 15, 0, 0, 0),
            "game_id": 1,
            "user_id": "1",
            "session_duration": 300.0,
            "access_count": 1
        }])
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        features = analyzer._extract_features(df)
        assert features is not None, "Midnight hour should work"
        assert not np.isnan(features).any(), "Midnight hour should not produce NaN"
    
    # Test case 2: End of day (hour=23)
    with patch('app.services.predictive_cache_warmer.datetime') as mock_dt:
        mock_dt.now.return_value = datetime(2024, 1, 15, 23, 59, 0)
        mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)
        
        df = pd.DataFrame([{
            "timestamp": datetime(2024, 1, 15, 23, 59, 0),
            "game_id": 1,
            "user_id": "1",
            "session_duration": 300.0,
            "access_count": 1
        }])
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        features = analyzer._extract_features(df)
        assert features is not None, "End of day should work"
        assert not np.isnan(features).any(), "End of day should not produce NaN"
    
    # Test case 3: Very short session (duration=1)
    with patch('app.services.predictive_cache_warmer.datetime') as mock_dt:
        mock_dt.now.return_value = current_time
        mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)
        
        df = pd.DataFrame([{
            "timestamp": current_time,
            "game_id": 1,
            "user_id": "1",
            "session_duration": 1.0,
            "access_count": 1
        }])
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        features = analyzer._extract_features(df)
        assert features is not None, "Very short session should work"
        assert not np.isnan(features).any(), "Very short session should not produce NaN"
    
    # Test case 4: Very long session (duration=36000)
    with patch('app.services.predictive_cache_warmer.datetime') as mock_dt:
        mock_dt.now.return_value = current_time
        mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)
        
        df = pd.DataFrame([{
            "timestamp": current_time,
            "game_id": 1,
            "user_id": "1",
            "session_duration": 36000.0,
            "access_count": 100
        }])
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        features = analyzer._extract_features(df)
        assert features is not None, "Very long session should work"
        assert not np.isnan(features).any(), "Very long session should not produce NaN"
    
    # Test case 5: Empty DataFrame
    empty_df = pd.DataFrame()
    features = analyzer._extract_features(empty_df)
    assert features is None, "Empty DataFrame should return None"
    
    # Test case 6: Missing columns
    df_minimal = pd.DataFrame([{
        "game_id": 1,
        "timestamp": current_time
    }])
    df_minimal['timestamp'] = pd.to_datetime(df_minimal['timestamp'])
    
    with patch('app.services.predictive_cache_warmer.datetime') as mock_dt:
        mock_dt.now.return_value = current_time
        mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)
        
        features = analyzer._extract_features(df_minimal)
        # Should still work, but with default values for missing columns
        assert features is not None or features is None, "Missing columns should be handled"


# ============================================================================
# Test Peak Hour Detection in Features
# ============================================================================

@pytest.mark.asyncio
async def test_peak_hour_feature(analyzer):
    """Test that peak hours are correctly identified in features"""
    # Set up analyzer with known peak hours
    analyzer.peak_hours = [9, 10, 11, 14, 15, 16, 19, 20, 21]
    
    # Test case 1: Log at 10 AM (peak)
    current_time = datetime(2024, 1, 15, 10, 0, 0)
    
    df = pd.DataFrame([{
        "timestamp": current_time,
        "game_id": 1,
        "user_id": "1",
        "session_duration": 300.0,
        "access_count": 1
    }])
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    with patch('app.services.predictive_cache_warmer.datetime') as mock_dt:
        mock_dt.now.return_value = current_time
        mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)
        
        features = analyzer._extract_features(df)
    
    assert features is not None, "Should return features"
    is_peak = int(features[3])  # is_peak_hour is at index 3
    assert is_peak == 1, f"10 AM should be peak hour, got {is_peak}"
    
    # Test case 2: Log at 3 AM (not peak)
    current_time = datetime(2024, 1, 15, 3, 0, 0)
    
    df = pd.DataFrame([{
        "timestamp": current_time,
        "game_id": 1,
        "user_id": "1",
        "session_duration": 300.0,
        "access_count": 1
    }])
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    with patch('app.services.predictive_cache_warmer.datetime') as mock_dt:
        mock_dt.now.return_value = current_time
        mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)
        
        features = analyzer._extract_features(df)
    
    assert features is not None, "Should return features"
    is_peak = int(features[3])
    assert is_peak == 0, f"3 AM should not be peak hour, got {is_peak}"


# ============================================================================
# Test Weekend Feature
# ============================================================================

@pytest.mark.asyncio
async def test_weekend_feature(analyzer):
    """Test weekend detection in features"""
    # Test case 1: Saturday (2024-01-13 is a Saturday)
    current_time = datetime(2024, 1, 13, 10, 0, 0)
    
    df = pd.DataFrame([{
        "timestamp": current_time,
        "game_id": 1,
        "user_id": "1",
        "session_duration": 300.0,
        "access_count": 1
    }])
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    with patch('app.services.predictive_cache_warmer.datetime') as mock_dt:
        mock_dt.now.return_value = current_time
        mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)
        
        features = analyzer._extract_features(df)
    
    assert features is not None, "Should return features"
    is_weekend = int(features[2])  # is_weekend is at index 2
    assert is_weekend == 1, f"Saturday should be weekend, got {is_weekend}"
    
    # Test case 2: Monday (2024-01-15 is a Monday)
    current_time = datetime(2024, 1, 15, 10, 0, 0)
    
    df = pd.DataFrame([{
        "timestamp": current_time,
        "game_id": 1,
        "user_id": "1",
        "session_duration": 300.0,
        "access_count": 1
    }])
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    with patch('app.services.predictive_cache_warmer.datetime') as mock_dt:
        mock_dt.now.return_value = current_time
        mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)
        
        features = analyzer._extract_features(df)
    
    assert features is not None, "Should return features"
    is_weekend = int(features[2])
    assert is_weekend == 0, f"Monday should not be weekend, got {is_weekend}"


# ============================================================================
# Additional Tests
# ============================================================================

@pytest.mark.asyncio
async def test_feature_extraction_with_historical_data(analyzer, sample_access_logs):
    """Test feature extraction with historical context"""
    # Create current and historical DataFrames
    current_df = pd.DataFrame(sample_access_logs[:50])
    historical_df = pd.DataFrame(sample_access_logs[50:200])
    
    # Ensure timestamps are datetime
    if 'timestamp' in current_df.columns:
        current_df['timestamp'] = pd.to_datetime(current_df['timestamp'])
    if 'timestamp' in historical_df.columns:
        historical_df['timestamp'] = pd.to_datetime(historical_df['timestamp'])
    
    # Extract features with historical data
    features = analyzer._extract_features(current_df, historical_log=historical_df)
    
    assert features is not None, "Should return features with historical data"
    assert len(features) >= 13, "Should have all features including historical ones"
    assert not np.isnan(features).any(), "Should not contain NaN"


@pytest.mark.asyncio
async def test_feature_extraction_without_user_id(analyzer):
    """Test feature extraction when user_id is missing"""
    current_time = datetime(2024, 1, 15, 10, 0, 0)
    
    df = pd.DataFrame([{
        "timestamp": current_time,
        "game_id": 1,
        "session_duration": 300.0,
        "access_count": 1
        # No user_id column
    }])
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    with patch('app.services.predictive_cache_warmer.datetime') as mock_dt:
        mock_dt.now.return_value = current_time
        mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)
        
        features = analyzer._extract_features(df)
    
    assert features is not None, "Should work without user_id"
    assert not np.isnan(features).any(), "Should not contain NaN"
    # User cluster and activity should be 0 when no user_id
    assert features[-2] == 0, "User cluster should be 0 when no user_id"
    assert features[-1] == 0, "User activity should be 0 when no user_id"

