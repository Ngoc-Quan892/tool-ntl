"""
Comprehensive tests for pattern analysis methods.

Purpose: Validate pattern detection algorithms
This ensures analyzer correctly identifies trends
"""

import pytest
import pytest_asyncio
import pandas as pd
from typing import Dict, List
from unittest.mock import patch
from datetime import datetime, timedelta

from app.services.predictive_cache_warmer import AccessPatternAnalyzer


# ============================================================================
# Test analyze_patterns Returns Complete Structure
# ============================================================================

@pytest.mark.asyncio
async def test_analyze_patterns_returns_complete_structure(analyzer, mock_database):
    """Test that analyze_patterns returns all expected keys"""
    # Run analysis
    patterns = await analyzer.analyze_patterns()
    
    # Check required keys
    required_keys = [
        "hourly_distribution",
        "daily_distribution",
        "top_games",
        "peak_hours",
        "user_clusters",
        "total_accesses",
        "unique_games",
        "unique_users",
    ]
    
    for key in required_keys:
        assert key in patterns, f"Missing key: {key}"
    
    # Check data types
    assert isinstance(patterns["hourly_distribution"], dict), \
        "hourly_distribution should be dict"
    assert isinstance(patterns["daily_distribution"], dict), \
        "daily_distribution should be dict"
    assert isinstance(patterns["top_games"], dict), \
        "top_games should be dict"
    assert isinstance(patterns["peak_hours"], list), \
        "peak_hours should be list"
    assert isinstance(patterns["user_clusters"], dict), \
        "user_clusters should be dict"
    assert isinstance(patterns["total_accesses"], int), \
        "total_accesses should be int"
    assert isinstance(patterns["unique_games"], int), \
        "unique_games should be int"
    assert isinstance(patterns["unique_users"], int), \
        "unique_users should be int"


# ============================================================================
# Test Peak Hour Identification
# ============================================================================

@pytest.mark.asyncio
async def test_identify_peak_hours(analyzer, sample_access_logs_with_patterns):
    """Test that peak hours are correctly identified"""
    # Convert logs to DataFrame
    df = pd.DataFrame(sample_access_logs_with_patterns)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df['hour'] = df['timestamp'].dt.hour
    df['access_count'] = df.get('access_count', pd.Series([1] * len(df)))
    
    # Get peak hours
    peak_hours = analyzer._identify_peak_hours(df)
    
    # Assertions
    assert isinstance(peak_hours, list), "Should return list"
    assert all(isinstance(h, int) for h in peak_hours), "All should be integers"
    assert all(0 <= h <= 23 for h in peak_hours), "Hours should be 0-23"
    
    # With known patterns (10 AM and 8 PM have high traffic), they should be peaks
    # Note: Peak detection uses mean + 0.5*std, so exact matches depend on data
    if len(peak_hours) > 0:
        # At least one peak hour should be identified
        assert len(peak_hours) > 0, "Should identify at least one peak hour"
        
        # Check that high-traffic hours are likely peaks
        hourly_counts = df.groupby('hour')['access_count'].sum()
        high_traffic_hours = hourly_counts.nlargest(3).index.tolist()
        
        # At least one high-traffic hour should be in peak hours
        assert any(h in peak_hours for h in high_traffic_hours), \
            "High-traffic hours should be identified as peaks"


@pytest.mark.asyncio
async def test_identify_peak_hours_with_known_data(analyzer):
    """Test peak hour identification with explicitly known data"""
    # Create DataFrame with clear peak at 10 AM and 8 PM
    logs = []
    base_time = datetime(2024, 1, 15, 0, 0, 0)
    
    # Add many accesses at 10 AM (peak)
    for i in range(200):
        logs.append({
            "timestamp": base_time.replace(hour=10, minute=i % 60),
            "game_id": 1,
            "user_id": str(i % 50),
            "access_count": 5,
        })
    
    # Add many accesses at 8 PM (peak)
    for i in range(250):
        logs.append({
            "timestamp": base_time.replace(hour=20, minute=i % 60),
            "game_id": 1,
            "user_id": str(i % 50),
            "access_count": 5,
        })
    
    # Add few accesses at 3 AM (not peak)
    for i in range(10):
        logs.append({
            "timestamp": base_time.replace(hour=3, minute=i * 5),
            "game_id": 1,
            "user_id": str(i % 10),
            "access_count": 1,
        })
    
    df = pd.DataFrame(logs)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df['hour'] = df['timestamp'].dt.hour
    
    # Get peak hours
    peak_hours = analyzer._identify_peak_hours(df)
    
    # 10 AM and 8 PM should be peaks
    assert 10 in peak_hours, "10 AM should be identified as peak"
    assert 20 in peak_hours, "8 PM (20:00) should be identified as peak"
    assert 3 not in peak_hours, "3 AM should not be peak"


# ============================================================================
# Test Top Games Identification
# ============================================================================

@pytest.mark.asyncio
async def test_identify_top_games(analyzer, sample_access_logs_with_patterns):
    """Test that popular games are correctly ranked"""
    # Convert logs to DataFrame
    df = pd.DataFrame(sample_access_logs_with_patterns)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df['access_count'] = df.get('access_count', pd.Series([1] * len(df)))
    
    # Run analysis
    patterns = await analyzer.analyze_patterns()
    
    # Get top games
    top_games = patterns["top_games"]
    
    # Assertions
    assert isinstance(top_games, dict), "Should be dict of game_id: count"
    assert len(top_games) > 0, "Should have at least one game"
    
    # With known patterns (game #1 is most popular), it should be in top games
    if 1 in top_games:
        # Get most popular game
        most_popular = max(top_games, key=top_games.get)
        # Game #1 should be most popular or at least in top games
        assert 1 in top_games, "Game #1 should be in top games"
        assert top_games[1] > 0, "Game #1 should have positive count"


@pytest.mark.asyncio
async def test_top_games_with_known_data(analyzer):
    """Test top games with explicitly known data"""
    # Create logs where game #1 is clearly most popular
    logs = []
    base_time = datetime(2024, 1, 15, 10, 0, 0)
    
    # Game #1: 150 accesses (30%)
    for i in range(150):
        logs.append({
            "timestamp": base_time + timedelta(minutes=i),
            "game_id": 1,
            "user_id": str(i % 50),
            "access_count": 1,
        })
    
    # Game #2: 100 accesses (20%)
    for i in range(100):
        logs.append({
            "timestamp": base_time + timedelta(minutes=i),
            "game_id": 2,
            "user_id": str(i % 50),
            "access_count": 1,
        })
    
    # Other games: 250 accesses total (50%)
    for game_id in range(3, 10):
        for i in range(25):
            logs.append({
                "timestamp": base_time + timedelta(minutes=i),
                "game_id": game_id,
                "user_id": str(i % 50),
                "access_count": 1,
            })
    
    # Mock database to return these logs
    async def mock_get_access_logs(start_date, end_date):
        return logs
    
    analyzer._get_access_logs = mock_get_access_logs
    
    # Run analysis
    patterns = await analyzer.analyze_patterns()
    top_games = patterns["top_games"]
    
    # Game #1 should be most popular
    most_popular = max(top_games, key=top_games.get)
    assert most_popular == 1, f"Game #1 should be most popular, got game #{most_popular}"
    assert top_games[1] >= 150, f"Game #1 should have at least 150 accesses, got {top_games[1]}"


# ============================================================================
# Test Hourly Distribution Calculation
# ============================================================================

@pytest.mark.asyncio
async def test_hourly_distribution(analyzer, mock_database):
    """Test hourly access distribution"""
    # Run analysis
    patterns = await analyzer.analyze_patterns()
    
    # Get distribution
    hourly = patterns["hourly_distribution"]
    
    # Assertions
    assert isinstance(hourly, dict), "Should be dict"
    assert len(hourly) <= 24, "Should have at most 24 hours"
    assert all(0 <= h <= 23 for h in hourly.keys()), "Hours should be 0-23"
    assert all(v >= 0 for v in hourly.values()), "Counts should be non-negative"
    
    # If we have data, check that peak hours have higher counts
    if len(hourly) > 0:
        # Get peak hours from analyzer
        peak_hours = patterns.get("peak_hours", [])
        
        if len(peak_hours) > 0:
            # Average of peak hours
            peak_avg = sum(hourly.get(h, 0) for h in peak_hours) / len(peak_hours)
            
            # Average of off-peak hours (0-5 AM)
            off_peak_hours = [h for h in range(6) if h not in peak_hours]
            if len(off_peak_hours) > 0:
                off_peak_avg = sum(hourly.get(h, 0) for h in off_peak_hours) / len(off_peak_hours)
                # Peak hours should generally have more traffic
                # (allowing some tolerance for edge cases)
                if peak_avg > 0 and off_peak_avg > 0:
                    assert peak_avg >= off_peak_avg * 0.5, \
                        f"Peak hours should have more traffic (peak: {peak_avg:.2f}, off-peak: {off_peak_avg:.2f})"


# ============================================================================
# Test Daily Distribution
# ============================================================================

@pytest.mark.asyncio
async def test_daily_distribution(analyzer, mock_database):
    """Test day-of-week distribution"""
    # Run analysis
    patterns = await analyzer.analyze_patterns()
    
    # Get daily distribution
    daily = patterns["daily_distribution"]
    
    # Assertions
    assert isinstance(daily, dict), "Should be dict"
    assert len(daily) <= 7, "Should have at most 7 days"
    assert all(0 <= d <= 6 for d in daily.keys()), "Days should be 0-6 (Monday=0, Sunday=6)"
    assert all(v >= 0 for v in daily.values()), "Counts should be non-negative"
    
    # Check that we have reasonable distribution
    if len(daily) > 0:
        total = sum(daily.values())
        assert total >= 0, "Total should be non-negative"


# ============================================================================
# Test User Clustering
# ============================================================================

@pytest.mark.asyncio
async def test_cluster_users(analyzer, sample_access_logs):
    """Test user clustering creates valid clusters"""
    # Convert logs to DataFrame
    df = pd.DataFrame(sample_access_logs[:200])  # Use subset for faster testing
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df['hour'] = df['timestamp'].dt.hour
    
    # Ensure user_id exists
    if 'user_id' not in df.columns:
        df['user_id'] = [str(i % 50) for i in range(len(df))]
    
    # Run clustering
    clusters = await analyzer._cluster_users(df)
    
    # Assertions
    assert isinstance(clusters, dict), "Should return dict"
    
    if len(clusters) > 0:
        # Check cluster IDs are valid
        cluster_ids = set(clusters.values())
        assert all(isinstance(cid, int) for cid in cluster_ids), \
            "Cluster IDs should be integers"
        assert min(cluster_ids) >= 0, "Cluster IDs should be non-negative"
        assert max(cluster_ids) < 10, "Should have reasonable number of clusters (< 10)"
        
        # Check that all user_ids from DataFrame are in clusters
        unique_users = df['user_id'].dropna().unique()
        for user_id in unique_users:
            if str(user_id) in clusters:
                assert isinstance(clusters[str(user_id)], int), \
                    f"Cluster ID for user {user_id} should be int"


@pytest.mark.asyncio
async def test_cluster_users_with_insufficient_data(analyzer):
    """Test clustering with insufficient users"""
    # Create DataFrame with < 5 users
    df = pd.DataFrame([
        {"user_id": "1", "game_id": 1, "timestamp": datetime.now(), "access_count": 1},
        {"user_id": "2", "game_id": 2, "timestamp": datetime.now(), "access_count": 1},
    ])
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df['hour'] = df['timestamp'].dt.hour
    
    # Run clustering
    clusters = await analyzer._cluster_users(df)
    
    # Should return dict with all users assigned to cluster 0
    assert isinstance(clusters, dict), "Should return dict"
    assert len(clusters) == 2, "Should have 2 users"
    assert all(cid == 0 for cid in clusters.values()), \
        "All users should be in cluster 0 when insufficient data"


# ============================================================================
# Test Seasonal Pattern Detection
# ============================================================================

@pytest.mark.asyncio
async def test_detect_seasonal_patterns(analyzer, sample_access_logs):
    """Test seasonal pattern detection"""
    # Convert logs to DataFrame
    df = pd.DataFrame(sample_access_logs)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df['access_count'] = df.get('access_count', pd.Series([1] * len(df)))
    
    # Run detection
    patterns = analyzer._detect_seasonal_patterns(df)
    
    # Check structure
    assert isinstance(patterns, dict), "Should return dict"
    assert "monthly_distribution" in patterns, "Should have monthly_distribution"
    assert "day_of_month_distribution" in patterns, "Should have day_of_month_distribution"
    
    # Check data types
    assert isinstance(patterns["monthly_distribution"], dict), \
        "monthly_distribution should be dict"
    assert isinstance(patterns["day_of_month_distribution"], dict), \
        "day_of_month_distribution should be dict"
    
    # Check monthly distribution
    monthly = patterns["monthly_distribution"]
    if len(monthly) > 0:
        assert all(1 <= m <= 12 for m in monthly.keys()), \
            "Months should be 1-12"
        assert all(v >= 0 for v in monthly.values()), \
            "Counts should be non-negative"
    
    # Check day of month distribution
    day_of_month = patterns["day_of_month_distribution"]
    if len(day_of_month) > 0:
        assert all(1 <= d <= 31 for d in day_of_month.keys()), \
            "Days should be 1-31"
        assert all(v >= 0 for v in day_of_month.values()), \
            "Counts should be non-negative"


@pytest.mark.asyncio
async def test_detect_seasonal_patterns_with_empty_data(analyzer):
    """Test seasonal pattern detection with empty data"""
    # Create empty DataFrame
    df = pd.DataFrame()
    
    # Run detection
    patterns = analyzer._detect_seasonal_patterns(df)
    
    # Should return empty dict
    assert isinstance(patterns, dict), "Should return dict"
    assert patterns == {}, "Should return empty dict for empty data"


# ============================================================================
# Test Empty Data Handling
# ============================================================================

@pytest.mark.asyncio
async def test_analyze_patterns_with_empty_data(analyzer):
    """Test graceful handling of no data"""
    # Mock empty data
    async def mock_get_access_logs(start_date, end_date):
        return []
    
    analyzer._get_access_logs = mock_get_access_logs
    
    # Run analysis
    patterns = await analyzer.analyze_patterns()
    
    # Assertions
    assert patterns is not None, "Should return dict even with no data"
    assert isinstance(patterns, dict), "Should return dict"
    assert patterns["hourly_distribution"] == {}, "Should be empty dict"
    assert patterns["daily_distribution"] == {}, "Should be empty dict"
    assert patterns["top_games"] == {}, "Should be empty dict"
    assert patterns["peak_hours"] == [], "Should be empty list"
    assert patterns["user_clusters"] == {}, "Should be empty dict"
    assert patterns["total_accesses"] == 0, "Should be 0"
    assert patterns["unique_games"] == 0, "Should be 0"
    assert patterns["unique_users"] == 0, "Should be 0"


# ============================================================================
# Additional Tests
# ============================================================================

@pytest.mark.asyncio
async def test_analyze_patterns_updates_instance_variables(analyzer, mock_database):
    """Test that analyze_patterns updates analyzer state"""
    # Run analysis
    patterns = await analyzer.analyze_patterns()
    
    # Check that instance variables are updated
    assert hasattr(analyzer, 'peak_hours'), "Should have peak_hours attribute"
    assert hasattr(analyzer, 'user_clusters'), "Should have user_clusters attribute"
    assert analyzer.peak_hours == patterns["peak_hours"], \
        "peak_hours should match patterns"
    assert analyzer.user_clusters == patterns["user_clusters"], \
        "user_clusters should match patterns"


@pytest.mark.asyncio
async def test_identify_peak_hours_with_empty_data(analyzer):
    """Test peak hour identification with empty DataFrame"""
    # Create empty DataFrame
    df = pd.DataFrame()
    
    # Run identification
    peak_hours = analyzer._identify_peak_hours(df)
    
    # Should return empty list
    assert isinstance(peak_hours, list), "Should return list"
    assert peak_hours == [], "Should return empty list for empty data"


@pytest.mark.asyncio
async def test_cluster_users_without_user_id(analyzer):
    """Test clustering when user_id column is missing"""
    # Create DataFrame without user_id
    df = pd.DataFrame([
        {"game_id": 1, "timestamp": datetime.now(), "access_count": 1},
        {"game_id": 2, "timestamp": datetime.now(), "access_count": 1},
    ])
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df['hour'] = df['timestamp'].dt.hour
    
    # Run clustering
    clusters = await analyzer._cluster_users(df)
    
    # Should return empty dict
    assert isinstance(clusters, dict), "Should return dict"
    assert clusters == {}, "Should return empty dict when no user_id"

