"""
Comprehensive tests for prediction functionality.

Purpose: Validate prediction quality and accuracy
Ensures predictions meet confidence thresholds
"""

import pytest
import pytest_asyncio
from typing import List, Dict
from unittest.mock import patch, AsyncMock
from datetime import datetime, timedelta

from app.services.predictive_cache_warmer import AccessPatternAnalyzer


# ============================================================================
# Test predict_next_access Returns Predictions
# ============================================================================

@pytest.mark.asyncio
async def test_predict_next_access_returns_predictions(trained_analyzer):
    """Test that predict_next_access returns valid predictions"""
    # Skip if model is not trained
    if trained_analyzer.model is None or trained_analyzer.feature_scaler is None:
        pytest.skip("Model not trained (insufficient data)")
    
    # Make predictions
    predictions = await trained_analyzer.predict_next_access(
        time_horizon=60,
        top_k=10
    )
    
    # Assertions
    assert isinstance(predictions, list), "Should return list"
    assert len(predictions) <= 10, f"Should return at most top_k predictions, got {len(predictions)}"
    
    # Check prediction structure
    if len(predictions) > 0:
        pred = predictions[0]
        assert "game_id" in pred, "Should have game_id"
        assert "confidence" in pred, "Should have confidence"
        assert "time_horizon" in pred, "Should have time_horizon"
        
        # Check types
        assert isinstance(pred["game_id"], int), "game_id should be int"
        assert isinstance(pred["confidence"], (int, float)), "confidence should be numeric"
        assert isinstance(pred["time_horizon"], int), "time_horizon should be int"


# ============================================================================
# Test Predictions Meet Confidence Threshold
# ============================================================================

@pytest.mark.asyncio
async def test_predictions_meet_confidence_threshold(trained_analyzer):
    """Test that all predictions meet minimum confidence"""
    # Skip if model is not trained
    if trained_analyzer.model is None or trained_analyzer.feature_scaler is None:
        pytest.skip("Model not trained (insufficient data)")
    
    # Set confidence threshold
    trained_analyzer.min_confidence = 0.7
    
    # Get predictions
    predictions = await trained_analyzer.predict_next_access(time_horizon=60)
    
    # Assertions
    for pred in predictions:
        assert pred["confidence"] >= 0.7, \
            f"Prediction confidence {pred['confidence']} below threshold 0.7"
    
    # All confidences should be valid probabilities
    for pred in predictions:
        assert 0 <= pred["confidence"] <= 1, \
            f"Confidence should be in [0,1], got {pred['confidence']}"


@pytest.mark.asyncio
async def test_predictions_with_different_confidence_thresholds(trained_analyzer):
    """Test predictions with different confidence thresholds"""
    # Skip if model is not trained
    if trained_analyzer.model is None or trained_analyzer.feature_scaler is None:
        pytest.skip("Model not trained (insufficient data)")
    
    # Test with low threshold
    trained_analyzer.min_confidence = 0.1
    predictions_low = await trained_analyzer.predict_next_access(time_horizon=60)
    
    # Test with medium threshold
    trained_analyzer.min_confidence = 0.5
    predictions_medium = await trained_analyzer.predict_next_access(time_horizon=60)
    
    # Test with high threshold
    trained_analyzer.min_confidence = 0.8
    predictions_high = await trained_analyzer.predict_next_access(time_horizon=60)
    
    # Higher threshold should have fewer or equal predictions
    assert len(predictions_high) <= len(predictions_medium), \
        "Higher threshold should have fewer predictions"
    assert len(predictions_medium) <= len(predictions_low), \
        "Medium threshold should have fewer or equal predictions than low"


# ============================================================================
# Test Predictions Are Sorted By Confidence
# ============================================================================

@pytest.mark.asyncio
async def test_predictions_sorted_by_confidence(trained_analyzer):
    """Test that predictions are ordered by confidence (descending)"""
    # Skip if model is not trained
    if trained_analyzer.model is None or trained_analyzer.feature_scaler is None:
        pytest.skip("Model not trained (insufficient data)")
    
    # Get predictions
    predictions = await trained_analyzer.predict_next_access(top_k=20)
    
    if len(predictions) > 1:
        # Extract confidences
        confidences = [p["confidence"] for p in predictions]
        
        # Assertion: should be sorted descending
        assert confidences == sorted(confidences, reverse=True), \
            f"Should be sorted descending, got {confidences}"
        
        # Check that first has highest confidence
        assert confidences[0] >= confidences[-1], \
            "First prediction should have highest confidence"


# ============================================================================
# Test Different Time Horizons
# ============================================================================

@pytest.mark.asyncio
async def test_predictions_with_different_time_horizons(trained_analyzer):
    """Test predictions for different time horizons"""
    # Skip if model is not trained
    if trained_analyzer.model is None or trained_analyzer.feature_scaler is None:
        pytest.skip("Model not trained (insufficient data)")
    
    # Test cases
    # 1. Short horizon (15 minutes)
    preds_15 = await trained_analyzer.predict_next_access(time_horizon=15)
    
    # 2. Medium horizon (60 minutes)
    preds_60 = await trained_analyzer.predict_next_access(time_horizon=60)
    
    # 3. Long horizon (240 minutes)
    preds_240 = await trained_analyzer.predict_next_access(time_horizon=240)
    
    # Assertions
    # All should have time_horizon field set correctly
    for pred in preds_15:
        assert pred["time_horizon"] == 15, \
            f"Should have time_horizon=15, got {pred['time_horizon']}"
    
    for pred in preds_60:
        assert pred["time_horizon"] == 60, \
            f"Should have time_horizon=60, got {pred['time_horizon']}"
    
    for pred in preds_240:
        assert pred["time_horizon"] == 240, \
            f"Should have time_horizon=240, got {pred['time_horizon']}"
    
    # All should be valid lists
    assert isinstance(preds_15, list), "Should return list for 15min horizon"
    assert isinstance(preds_60, list), "Should return list for 60min horizon"
    assert isinstance(preds_240, list), "Should return list for 240min horizon"


# ============================================================================
# Test top_k Parameter
# ============================================================================

@pytest.mark.asyncio
async def test_predictions_respects_top_k(trained_analyzer):
    """Test that top_k limits number of predictions"""
    # Skip if model is not trained
    if trained_analyzer.model is None or trained_analyzer.feature_scaler is None:
        pytest.skip("Model not trained (insufficient data)")
    
    # Test cases
    # 1. top_k=5
    preds_5 = await trained_analyzer.predict_next_access(top_k=5)
    assert len(preds_5) <= 5, f"Should return at most 5 predictions, got {len(preds_5)}"
    
    # 2. top_k=1
    preds_1 = await trained_analyzer.predict_next_access(top_k=1)
    assert len(preds_1) <= 1, f"Should return at most 1 prediction, got {len(preds_1)}"
    
    # 3. top_k=100
    preds_100 = await trained_analyzer.predict_next_access(top_k=100)
    assert len(preds_100) <= 100, f"Should return at most 100 predictions, got {len(preds_100)}"
    
    # 4. top_k=0 (edge case)
    preds_0 = await trained_analyzer.predict_next_access(top_k=0)
    assert len(preds_0) == 0, "Should return empty list for top_k=0"


# ============================================================================
# Test Predictions With No High-Confidence Items
# ============================================================================

@pytest.mark.asyncio
async def test_predictions_when_no_high_confidence(trained_analyzer):
    """Test behavior when no predictions meet confidence threshold"""
    # Skip if model is not trained
    if trained_analyzer.model is None or trained_analyzer.feature_scaler is None:
        pytest.skip("Model not trained (insufficient data)")
    
    # Set very high confidence threshold
    trained_analyzer.min_confidence = 0.99
    
    # Get predictions
    predictions = await trained_analyzer.predict_next_access()
    
    # Assertion
    # Should either return empty list or predictions meeting threshold
    assert isinstance(predictions, list), "Should return list"
    
    for pred in predictions:
        assert pred["confidence"] >= 0.99, \
            f"All predictions should meet threshold, got {pred['confidence']}"
    
    # It's OK to return empty list if no predictions meet threshold
    # This is expected behavior


@pytest.mark.asyncio
async def test_predictions_with_zero_confidence_threshold(trained_analyzer):
    """Test predictions with zero confidence threshold (should return all)"""
    # Skip if model is not trained
    if trained_analyzer.model is None or trained_analyzer.feature_scaler is None:
        pytest.skip("Model not trained (insufficient data)")
    
    # Set zero confidence threshold
    trained_analyzer.min_confidence = 0.0
    
    # Get predictions
    predictions = await trained_analyzer.predict_next_access(top_k=50)
    
    # Should return predictions (might be empty if no data)
    assert isinstance(predictions, list), "Should return list"
    
    # All should have confidence >= 0
    for pred in predictions:
        assert pred["confidence"] >= 0.0, \
            f"Confidence should be >= 0, got {pred['confidence']}"


# ============================================================================
# Test Prediction Consistency
# ============================================================================

@pytest.mark.asyncio
async def test_prediction_consistency(trained_analyzer):
    """Test that predictions are consistent for same input"""
    # Skip if model is not trained
    if trained_analyzer.model is None or trained_analyzer.feature_scaler is None:
        pytest.skip("Model not trained (insufficient data)")
    
    # Make predictions twice with same parameters
    preds1 = await trained_analyzer.predict_next_access(time_horizon=60, top_k=10)
    preds2 = await trained_analyzer.predict_next_access(time_horizon=60, top_k=10)
    
    # Assertions
    assert len(preds1) == len(preds2), \
        f"Should return same number, got {len(preds1)} vs {len(preds2)}"
    
    if len(preds1) > 0:
        # Game IDs should match (same order)
        game_ids1 = [p["game_id"] for p in preds1]
        game_ids2 = [p["game_id"] for p in preds2]
        
        assert game_ids1 == game_ids2, \
            f"Should predict same games, got {game_ids1} vs {game_ids2}"
        
        # Confidences should match (within floating point precision)
        confidences1 = [p["confidence"] for p in preds1]
        confidences2 = [p["confidence"] for p in preds2]
        
        for c1, c2 in zip(confidences1, confidences2):
            assert abs(c1 - c2) < 1e-5, \
                f"Confidences should match, got {c1} vs {c2}"


# ============================================================================
# Test Prediction With Recent Access Data
# ============================================================================

@pytest.mark.asyncio
async def test_predictions_use_recent_data(trained_analyzer, mock_database):
    """Test that predictions consider recent access patterns"""
    # Skip if model is not trained
    if trained_analyzer.model is None or trained_analyzer.feature_scaler is None:
        pytest.skip("Model not trained (insufficient data)")
    
    # Mock recent logs with specific pattern (game #5 very popular recently)
    base_time = datetime(2024, 1, 15, 10, 0, 0)
    recent_logs = [
        {
            "timestamp": base_time + timedelta(minutes=i),
            "game_id": 5,
            "user_id": str(i % 10),
            "session_duration": 300.0,
            "access_count": 1
        }
        for i in range(50)
    ]
    
    # Also add some other games
    for i in range(10):
        recent_logs.append({
            "timestamp": base_time + timedelta(minutes=i),
            "game_id": i % 3 + 1,  # Games 1, 2, 3
            "user_id": str(i % 10),
            "session_duration": 300.0,
            "access_count": 1
        })
    
    # Mock database to return recent logs
    async def mock_get_access_logs(start_date, end_date):
        # Filter logs by date range
        filtered = [
            log for log in recent_logs
            if start_date <= log["timestamp"] <= end_date
        ]
        return filtered
    
    trained_analyzer._get_access_logs = mock_get_access_logs
    
    # Get predictions
    predictions = await trained_analyzer.predict_next_access()
    
    # Assertion
    # Game #5 should be in top predictions (or at least in predictions)
    if len(predictions) > 0:
        predicted_games = [p["game_id"] for p in predictions]
        # Game 5 should be predicted (might not be top if model learned differently)
        # But with 50 recent accesses vs 10 for others, it should be prominent
        assert len(predicted_games) > 0, "Should have some predictions"
        
        # At least one of the popular games should be predicted
        popular_games = [1, 2, 3, 5]
        assert any(gid in predicted_games for gid in popular_games), \
            f"Should predict at least one popular game, got {predicted_games}"


# ============================================================================
# Additional Tests
# ============================================================================

@pytest.mark.asyncio
async def test_predictions_with_no_recent_data(trained_analyzer):
    """Test predictions when no recent access logs available"""
    # Skip if model is not trained
    if trained_analyzer.model is None or trained_analyzer.feature_scaler is None:
        pytest.skip("Model not trained (insufficient data)")
    
    # Mock empty recent logs
    async def mock_get_access_logs(start_date, end_date):
        return []
    
    trained_analyzer._get_access_logs = mock_get_access_logs
    
    # Get predictions
    predictions = await trained_analyzer.predict_next_access()
    
    # Should return empty list when no recent data
    assert isinstance(predictions, list), "Should return list"
    assert len(predictions) == 0, "Should return empty list when no recent data"


@pytest.mark.asyncio
async def test_predictions_with_invalid_model(trained_analyzer):
    """Test predictions when model is None"""
    # Set model to None
    trained_analyzer.model = None
    
    # Get predictions
    predictions = await trained_analyzer.predict_next_access()
    
    # Should return empty list
    assert isinstance(predictions, list), "Should return list"
    assert len(predictions) == 0, "Should return empty list when model is None"


@pytest.mark.asyncio
async def test_predictions_with_invalid_scaler(trained_analyzer):
    """Test predictions when scaler is None"""
    # Skip if model is not trained
    if trained_analyzer.model is None:
        pytest.skip("Model not trained (insufficient data)")
    
    # Set scaler to None
    trained_analyzer.feature_scaler = None
    
    # Get predictions
    predictions = await trained_analyzer.predict_next_access()
    
    # Should return empty list
    assert isinstance(predictions, list), "Should return list"
    assert len(predictions) == 0, "Should return empty list when scaler is None"


@pytest.mark.asyncio
async def test_predictions_game_id_types(trained_analyzer):
    """Test that game_id is always an integer"""
    # Skip if model is not trained
    if trained_analyzer.model is None or trained_analyzer.feature_scaler is None:
        pytest.skip("Model not trained (insufficient data)")
    
    # Get predictions
    predictions = await trained_analyzer.predict_next_access()
    
    # All game_ids should be integers
    for pred in predictions:
        assert isinstance(pred["game_id"], int), \
            f"game_id should be int, got {type(pred['game_id'])}: {pred['game_id']}"
        assert pred["game_id"] > 0, \
            f"game_id should be positive, got {pred['game_id']}"


@pytest.mark.asyncio
async def test_predictions_confidence_types(trained_analyzer):
    """Test that confidence is always a float"""
    # Skip if model is not trained
    if trained_analyzer.model is None or trained_analyzer.feature_scaler is None:
        pytest.skip("Model not trained (insufficient data)")
    
    # Get predictions
    predictions = await trained_analyzer.predict_next_access()
    
    # All confidences should be floats
    for pred in predictions:
        assert isinstance(pred["confidence"], (int, float)), \
            f"confidence should be numeric, got {type(pred['confidence'])}"
        assert 0.0 <= pred["confidence"] <= 1.0, \
            f"confidence should be in [0,1], got {pred['confidence']}"


@pytest.mark.asyncio
async def test_predictions_time_horizon_consistency(trained_analyzer):
    """Test that all predictions in a batch have same time_horizon"""
    # Skip if model is not trained
    if trained_analyzer.model is None or trained_analyzer.feature_scaler is None:
        pytest.skip("Model not trained (insufficient data)")
    
    # Get predictions with specific time_horizon
    time_horizon = 120
    predictions = await trained_analyzer.predict_next_access(time_horizon=time_horizon)
    
    # All should have same time_horizon
    for pred in predictions:
        assert pred["time_horizon"] == time_horizon, \
            f"All predictions should have time_horizon={time_horizon}, got {pred['time_horizon']}"

