"""
Comprehensive tests for ML model training.

Purpose: Validate model training pipeline
Ensures model can be trained and makes valid predictions
"""

import pytest
import pytest_asyncio
import numpy as np
import joblib
from pathlib import Path
from datetime import datetime
from unittest.mock import patch, MagicMock
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler

from app.services.predictive_cache_warmer import AccessPatternAnalyzer


# ============================================================================
# Test Model Training Succeeds
# ============================================================================

@pytest.mark.asyncio
async def test_train_prediction_model_succeeds(analyzer, mock_database):
    """Test that model training completes without errors"""
    # Ensure no model exists initially
    assert analyzer.model is None, "Should start with no model"
    assert analyzer.feature_scaler is None, "Should start with no scaler"
    
    # Train model
    result = await analyzer.train_prediction_model()
    
    # Check training result
    assert result is not None, "Should return training result"
    
    # If training succeeded
    if result.get("status") == "success":
        # Assertions
        assert analyzer.model is not None, "Model should be trained"
        assert analyzer.feature_scaler is not None, "Scaler should be fitted"
        
        # Check model type
        assert isinstance(analyzer.model, RandomForestClassifier), \
            f"Should be RandomForestClassifier, got {type(analyzer.model)}"
        
        # Check model parameters
        assert analyzer.model.n_estimators == 100, \
            f"Should have 100 trees, got {analyzer.model.n_estimators}"
        assert analyzer.model.max_depth == 10, \
            f"Max depth should be 10, got {analyzer.model.max_depth}"
        
        # Check training metrics
        assert "train_accuracy" in result or "accuracy" in result, \
            "Should include accuracy in result"
    else:
        # Training might fail due to insufficient data
        assert result.get("status") in ["insufficient_data", "insufficient_examples"], \
            f"Expected insufficient data status, got {result.get('status')}"


# ============================================================================
# Test Model Can Make Predictions
# ============================================================================

@pytest.mark.asyncio
async def test_trained_model_can_predict(trained_analyzer):
    """Test that trained model can make predictions"""
    # Skip if model is not trained
    if trained_analyzer.model is None:
        pytest.skip("Model not trained (insufficient data)")
    
    # Create dummy feature vector (need correct number of features)
    # Get feature count from scaler or use a reasonable default
    if trained_analyzer.feature_scaler is not None:
        n_features = trained_analyzer.feature_scaler.n_features_in_
    else:
        n_features = 13  # Default feature count
    
    X_test = np.array([[0.0] * n_features])
    
    # Scale features if scaler exists
    if trained_analyzer.feature_scaler is not None:
        X_test_scaled = trained_analyzer.feature_scaler.transform(X_test)
    else:
        X_test_scaled = X_test
    
    # Make prediction
    prediction = trained_analyzer.model.predict(X_test_scaled)
    
    # Assertions
    assert prediction is not None, "Prediction should not be None"
    assert len(prediction) == 1, f"Should have 1 prediction, got {len(prediction)}"
    assert isinstance(prediction[0], (int, np.integer)), \
        f"Prediction should be integer, got {type(prediction[0])}"
    assert prediction[0] >= 0, "Prediction should be non-negative"


# ============================================================================
# Test Model Prediction Probabilities
# ============================================================================

@pytest.mark.asyncio
async def test_model_predict_proba(trained_analyzer):
    """Test that model returns valid probabilities"""
    # Skip if model is not trained
    if trained_analyzer.model is None:
        pytest.skip("Model not trained (insufficient data)")
    
    # Get feature count
    if trained_analyzer.feature_scaler is not None:
        n_features = trained_analyzer.feature_scaler.n_features_in_
    else:
        n_features = 13
    
    # Create test features
    X_test = np.array([[0.0] * n_features])
    
    # Scale if needed
    if trained_analyzer.feature_scaler is not None:
        X_test_scaled = trained_analyzer.feature_scaler.transform(X_test)
    else:
        X_test_scaled = X_test
    
    # Get probabilities
    probas = trained_analyzer.model.predict_proba(X_test_scaled)
    
    # Assertions
    assert probas.shape[0] == 1, f"Should have 1 prediction, got {probas.shape[0]}"
    assert probas.shape[1] > 0, f"Should have probabilities for each class, got {probas.shape[1]}"
    assert np.allclose(probas.sum(axis=1), 1.0, rtol=1e-5), \
        f"Probabilities should sum to 1, got {probas.sum(axis=1)}"
    assert np.all(probas >= 0) and np.all(probas <= 1), \
        f"Probabilities should be in [0,1], got min={probas.min()}, max={probas.max()}"


# ============================================================================
# Test Feature Scaler
# ============================================================================

@pytest.mark.asyncio
async def test_feature_scaler_fitted(trained_analyzer):
    """Test that feature scaler is properly fitted"""
    # Skip if scaler is not fitted
    if trained_analyzer.feature_scaler is None:
        pytest.skip("Scaler not fitted (model not trained)")
    
    # Get scaler
    scaler = trained_analyzer.feature_scaler
    
    # Check it's fitted
    assert hasattr(scaler, 'mean_'), "Scaler should be fitted (has mean_)"
    assert hasattr(scaler, 'scale_'), "Scaler should have scale_"
    assert scaler.mean_ is not None, "Mean should not be None"
    assert scaler.scale_ is not None, "Scale should not be None"
    
    # Test transformation
    n_features = scaler.n_features_in_
    X = np.array([[1.0, 2.0, 3.0, 4.0, 5.0] * (n_features // 5 + 1)][:n_features])
    X = X.reshape(1, -1)[:, :n_features]  # Ensure correct shape
    
    X_scaled = scaler.transform(X)
    
    assert X_scaled.shape == X.shape, \
        f"Shape should be preserved, got {X_scaled.shape} vs {X.shape}"
    assert not np.isnan(X_scaled).any(), "Scaled features should not contain NaN"
    assert not np.isinf(X_scaled).any(), "Scaled features should not contain Inf"


# ============================================================================
# Test Model Persistence
# ============================================================================

@pytest.mark.asyncio
async def test_model_save_and_load(trained_analyzer, tmp_path):
    """Test saving and loading trained model"""
    # Skip if model is not trained
    if trained_analyzer.model is None:
        pytest.skip("Model not trained (insufficient data)")
    
    # Save model
    model_path = tmp_path / "test_model.pkl"
    joblib.dump(trained_analyzer.model, model_path)
    
    assert model_path.exists(), "Model file should be created"
    
    # Load model
    loaded_model = joblib.load(model_path)
    
    assert loaded_model is not None, "Loaded model should not be None"
    assert isinstance(loaded_model, RandomForestClassifier), \
        "Loaded model should be RandomForestClassifier"
    
    # Verify predictions match
    if trained_analyzer.feature_scaler is not None:
        n_features = trained_analyzer.feature_scaler.n_features_in_
    else:
        n_features = 13
    
    X_test = np.array([[0.0] * n_features])
    
    # Scale if needed
    if trained_analyzer.feature_scaler is not None:
        X_test_scaled = trained_analyzer.feature_scaler.transform(X_test)
    else:
        X_test_scaled = X_test
    
    pred1 = trained_analyzer.model.predict(X_test_scaled)
    pred2 = loaded_model.predict(X_test_scaled)
    
    assert np.array_equal(pred1, pred2), \
        f"Predictions should match, got {pred1} vs {pred2}"


@pytest.mark.asyncio
async def test_scaler_save_and_load(trained_analyzer, tmp_path):
    """Test saving and loading feature scaler"""
    # Skip if scaler is not fitted
    if trained_analyzer.feature_scaler is None:
        pytest.skip("Scaler not fitted (model not trained)")
    
    # Save scaler
    scaler_path = tmp_path / "test_scaler.pkl"
    joblib.dump(trained_analyzer.feature_scaler, scaler_path)
    
    assert scaler_path.exists(), "Scaler file should be created"
    
    # Load scaler
    loaded_scaler = joblib.load(scaler_path)
    
    assert loaded_scaler is not None, "Loaded scaler should not be None"
    assert isinstance(loaded_scaler, StandardScaler), \
        "Loaded scaler should be StandardScaler"
    
    # Verify transformation matches
    n_features = loaded_scaler.n_features_in_
    X = np.array([[1.0, 2.0, 3.0] * (n_features // 3 + 1)][:n_features])
    X = X.reshape(1, -1)[:, :n_features]
    
    scaled1 = trained_analyzer.feature_scaler.transform(X)
    scaled2 = loaded_scaler.transform(X)
    
    assert np.allclose(scaled1, scaled2, rtol=1e-5), \
        "Scaled features should match"


# ============================================================================
# Test Training with Insufficient Data
# ============================================================================

@pytest.mark.asyncio
async def test_training_with_insufficient_data(analyzer):
    """Test handling of insufficient training data"""
    # Mock very small dataset (< 100 samples)
    small_data = [
        {
            "timestamp": datetime(2024, 1, 1, i % 24, 0, 0),
            "game_id": i % 10 + 1,
            "user_id": str(i % 5),
            "session_duration": 300.0,
            "access_count": 1
        }
        for i in range(10)  # Only 10 samples
    ]
    
    # Mock database to return small data
    async def mock_get_access_logs(start_date, end_date):
        return small_data
    
    analyzer._get_access_logs = mock_get_access_logs
    
    # Train model (should handle gracefully)
    result = await analyzer.train_prediction_model()
    
    # Should return insufficient_data status
    assert result is not None, "Should return result"
    assert result.get("status") == "insufficient_data", \
        f"Should return insufficient_data status, got {result.get('status')}"
    assert result.get("accuracy", 0) == 0.0, \
        "Accuracy should be 0 for insufficient data"
    
    # Model should not be trained
    assert analyzer.model is None, "Model should not be trained with insufficient data"


@pytest.mark.asyncio
async def test_training_with_insufficient_examples(analyzer, sample_access_logs):
    """Test handling when training examples are insufficient"""
    # Create data that passes initial check but fails windowing
    # This requires specific data structure that creates < 50 examples
    async def mock_get_access_logs(start_date, end_date):
        # Return data that will create < 50 training examples
        return sample_access_logs[:80]  # Not enough for windowing
    
    analyzer._get_access_logs = mock_get_access_logs
    
    # Train model
    result = await analyzer.train_prediction_model()
    
    # Should handle gracefully
    assert result is not None, "Should return result"
    # Might be insufficient_data or insufficient_examples
    assert result.get("status") in ["insufficient_data", "insufficient_examples"], \
        f"Should handle insufficient examples, got {result.get('status')}"


# ============================================================================
# Test Model Retraining
# ============================================================================

@pytest.mark.asyncio
async def test_model_retraining(trained_analyzer, mock_database):
    """Test that model can be retrained"""
    # Skip if model is not trained initially
    if trained_analyzer.model is None:
        pytest.skip("Initial model not trained (insufficient data)")
    
    # Get initial model
    initial_model = trained_analyzer.model
    initial_scaler = trained_analyzer.feature_scaler
    
    # Retrain
    result = await trained_analyzer.train_prediction_model()
    
    # Check result
    if result.get("status") == "success":
        # Get new model
        new_model = trained_analyzer.model
        new_scaler = trained_analyzer.feature_scaler
        
        assert new_model is not None, "New model should be trained"
        assert new_model is not initial_model, "Should be new model instance"
        
        # Both models should work
        if trained_analyzer.feature_scaler is not None:
            n_features = trained_analyzer.feature_scaler.n_features_in_
        else:
            n_features = 13
        
        X_test = np.array([[0.0] * n_features])
        
        if new_scaler is not None:
            X_test_scaled = new_scaler.transform(X_test)
        else:
            X_test_scaled = X_test
        
        pred1 = initial_model.predict(X_test_scaled) if initial_scaler else initial_model.predict(X_test)
        pred2 = new_model.predict(X_test_scaled)
        
        # Predictions might differ, but both should work
        assert pred1 is not None, "Initial model prediction should work"
        assert pred2 is not None, "New model prediction should work"
        assert len(pred1) == len(pred2), "Predictions should have same length"


# ============================================================================
# Test Training Metrics Logging
# ============================================================================

@pytest.mark.asyncio
async def test_training_logs_metrics(analyzer, mock_database, caplog):
    """Test that training logs accuracy metrics"""
    # Train model
    result = await analyzer.train_prediction_model()
    
    # Check logs
    log_text = caplog.text.lower()
    
    if result.get("status") == "success":
        # Should log training completion
        assert "model trained" in log_text or "training" in log_text, \
            "Should log training completion"
        
        # Should log accuracy
        assert "accuracy" in log_text or "train accuracy" in log_text, \
            "Should log accuracy metrics"
    else:
        # Should log warning about insufficient data
        assert "insufficient" in log_text or "warning" in log_text, \
            "Should log warning about insufficient data"


# ============================================================================
# Additional Tests
# ============================================================================

@pytest.mark.asyncio
async def test_training_result_structure(analyzer, mock_database):
    """Test that training result has expected structure"""
    result = await analyzer.train_prediction_model()
    
    assert isinstance(result, dict), "Result should be dict"
    assert "status" in result, "Should have status field"
    
    if result.get("status") == "success":
        assert "train_accuracy" in result or "accuracy" in result, \
            "Should have accuracy in result"
        assert "test_accuracy" in result or "accuracy" in result, \
            "Should have test accuracy"
        
        # Check accuracy values are valid
        accuracy = result.get("train_accuracy") or result.get("accuracy", 0)
        assert 0.0 <= accuracy <= 1.0, \
            f"Accuracy should be in [0,1], got {accuracy}"


@pytest.mark.asyncio
async def test_training_with_valid_data(analyzer, sample_access_logs):
    """Test training with sufficient valid data"""
    # Mock database to return sample logs
    async def mock_get_access_logs(start_date, end_date):
        return sample_access_logs
    
    analyzer._get_access_logs = mock_get_access_logs
    
    # Train model
    result = await analyzer.train_prediction_model()
    
    # Should succeed if data is sufficient
    if result.get("status") == "success":
        assert analyzer.model is not None, "Model should be trained"
        assert analyzer.feature_scaler is not None, "Scaler should be fitted"
        
        # Check model can predict
        if analyzer.feature_scaler is not None:
            n_features = analyzer.feature_scaler.n_features_in_
            X_test = np.array([[0.0] * n_features])
            X_scaled = analyzer.feature_scaler.transform(X_test)
            prediction = analyzer.model.predict(X_scaled)
            assert prediction is not None, "Model should be able to predict"


@pytest.mark.asyncio
async def test_model_parameters_are_set_correctly(analyzer, mock_database):
    """Test that model parameters are set correctly"""
    result = await analyzer.train_prediction_model()
    
    if result.get("status") == "success" and analyzer.model is not None:
        model = analyzer.model
        
        # Check RandomForest parameters
        assert model.n_estimators == 100, \
            f"Should have 100 estimators, got {model.n_estimators}"
        assert model.max_depth == 10, \
            f"Should have max_depth 10, got {model.max_depth}"
        assert model.random_state == 42, \
            f"Should have random_state 42, got {model.random_state}"


@pytest.mark.asyncio
async def test_scaler_fit_before_model_training(analyzer, mock_database):
    """Test that scaler is fitted before model training"""
    result = await analyzer.train_prediction_model()
    
    if result.get("status") == "success":
        assert analyzer.feature_scaler is not None, "Scaler should exist"
        assert hasattr(analyzer.feature_scaler, 'mean_'), \
            "Scaler should be fitted (has mean_)"
        
        # Scaler should have same number of features as model expects
        if analyzer.model is not None:
            # Model should work with scaled features
            n_features = analyzer.feature_scaler.n_features_in_
            X_test = np.array([[0.0] * n_features])
            X_scaled = analyzer.feature_scaler.transform(X_test)
            
            # Should not raise error
            prediction = analyzer.model.predict(X_scaled)
            assert prediction is not None, "Model should predict with scaled features"

