"""
ML model testing

Tests for advanced PyTorch-based LSTM model with attention mechanism
"""
import pytest
import numpy as np
from typing import Dict, List

# Skip tests if PyTorch not available
try:
    import torch
    import torch.nn as nn
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

from app.ml.advanced_model import (
    BaccaratLSTM, ModelConfig, AdvancedPredictor,
    FeatureExtractor, ConfidenceCalibrator
)


@pytest.mark.skipif(not TORCH_AVAILABLE, reason="PyTorch not available")
class TestBaccaratLSTM:
    """Test LSTM model"""
    
    def test_model_creation(self):
        """Test model can be created"""
        config = ModelConfig()
        model = BaccaratLSTM(config)
        
        assert model is not None
        assert isinstance(model, nn.Module)
    
    def test_forward_pass(self):
        """Test forward pass works"""
        config = ModelConfig()
        model = BaccaratLSTM(config)
        
        # Create dummy input
        batch_size = 16
        seq_len = 30
        input_size = 35
        
        x = torch.randn(batch_size, seq_len, input_size)
        
        # Forward pass
        probs, conf = model(x)
        
        assert probs.shape == (batch_size, 3)
        assert conf.shape == (batch_size, 1)
        assert torch.allclose(probs.sum(dim=1), torch.ones(batch_size), atol=1e-6)
    
    def test_attention_mechanism(self):
        """Test attention weights"""
        config = ModelConfig()
        model = BaccaratLSTM(config)
        
        x = torch.randn(8, 30, 35)
        probs, conf, attention = model(x, return_attention=True)
        
        assert attention is not None
        assert attention.shape[0] == 8  # batch size
    
    @pytest.mark.skipif(not torch.cuda.is_available(), reason="CUDA not available")
    def test_gpu_inference(self):
        """Test model works on GPU"""
        config = ModelConfig()
        model = BaccaratLSTM(config).cuda()
        
        x = torch.randn(4, 30, 35).cuda()
        probs, conf = model(x)
        
        assert probs.is_cuda
        assert conf.is_cuda


class TestFeatureExtractor:
    """Test feature extraction"""
    
    def test_feature_extraction(self):
        """Test feature extraction produces correct shape"""
        extractor = FeatureExtractor()
        
        shoe_state = {
            "true_count_b": 2.5,
            "true_count_p": -1.2,
            "cards_remaining": 200,
            "edge": {"max_edge": 0.5},
            "decks": 8,
            "hands_played": 10,
            "cards_dealt": 100
        }
        
        history = ['B', 'B', 'P', 'B', 'P', 'P', 'B', 'T', 'B', 'B']
        
        features = extractor.extract_all_features(shoe_state, history)
        
        assert features.shape == (30, 35)  # sequence_length x feature_dim
    
    def test_pattern_detection(self):
        """Test pattern detection features"""
        extractor = FeatureExtractor()
        
        # Dragon pattern
        dragon_history = ['B'] * 8 + ['P'] * 2
        features = extractor._extract_pattern_features(dragon_history)
        assert features[4] == 1.0  # Dragon detected
        
        # Ping pong pattern
        pingpong_history = ['B', 'P', 'B', 'P', 'B', 'P']
        features = extractor._extract_pattern_features(pingpong_history)
        assert features[5] > 0.8  # High alternation
    
    def test_statistical_features(self):
        """Test statistical feature extraction"""
        extractor = FeatureExtractor()
        
        history = ['B', 'P', 'B', 'P', 'B', 'P', 'B', 'P', 'B', 'P']
        features = extractor._extract_statistical_features(history)
        
        assert len(features) == 8
        assert all(0 <= f <= 1 or -1 <= f <= 1 for f in features)
    
    def test_counting_features(self):
        """Test card counting feature extraction"""
        extractor = FeatureExtractor()
        
        shoe_state = {
            "true_count_b": 2.0,
            "true_count_p": -1.0,
            "running_count_b": 16,
            "running_count_p": -8,
            "decks_remaining": 6,
            "edge": {"max_edge": 0.5}
        }
        
        features = extractor._extract_counting_features(shoe_state)
        
        assert len(features) == 6
        assert features[0] == 0.2  # true_count_b / 10
        assert features[1] == -0.1  # true_count_p / 10


@pytest.mark.skipif(not TORCH_AVAILABLE, reason="PyTorch not available")
class TestAdvancedPredictor:
    """Test prediction system"""
    
    @pytest.fixture
    def predictor(self):
        """Create predictor instance"""
        return AdvancedPredictor()
    
    def test_prediction_without_model(self, predictor):
        """Test prediction generation without loaded model (fallback)"""
        shoe_state = {
            "true_count_b": 1.0,
            "cards_remaining": 300,
            "edge": {"max_edge": 0.2},
            "decks": 8,
            "hands_played": 5,
            "cards_dealt": 50
        }
        
        history = ['B', 'P', 'P', 'B', 'B']
        
        # Should use fallback prediction
        prediction = predictor.predict(shoe_state, history)
        
        assert "recommendation" in prediction
        assert prediction["recommendation"] in ['B', 'P', 'T']
        assert 0 <= prediction["confidence"] <= 1
        assert "probabilities" in prediction
    
    def test_caching(self, predictor):
        """Test prediction caching"""
        shoe_state = {
            "cards_remaining": 200,
            "true_count_b": 0.0,
            "decks": 8,
            "hands_played": 0,
            "cards_dealt": 0
        }
        history = ['B', 'P', 'B']
        
        # First call - should cache
        pred1 = predictor.predict(shoe_state, history)
        
        # Second call - should use cache
        pred2 = predictor.predict(shoe_state, history)
        
        assert pred1 == pred2
        assert predictor.performance_metrics["cache_hits"] > 0
    
    def test_performance_stats(self, predictor):
        """Test performance statistics"""
        shoe_state = {
            "cards_remaining": 200,
            "true_count_b": 0.0,
            "decks": 8,
            "hands_played": 0,
            "cards_dealt": 0
        }
        history = ['B', 'P']
        
        # Make some predictions
        predictor.predict(shoe_state, history)
        predictor.predict(shoe_state, history)
        
        stats = predictor.get_performance_stats()
        
        assert "predictions_made" in stats
        assert "cache_hit_rate" in stats
        assert stats["predictions_made"] >= 2


class TestConfidenceCalibrator:
    """Test confidence calibration"""
    
    def test_calibration(self):
        """Test confidence calibration"""
        calibrator = ConfidenceCalibrator()
        
        raw_confidence = 0.7
        calibrated = calibrator.calibrate(raw_confidence)
        
        assert 0 <= calibrated <= 1
        assert calibrated != raw_confidence  # Should be different
    
    def test_calibration_bounds(self):
        """Test calibration stays within bounds"""
        calibrator = ConfidenceCalibrator()
        
        # Test extreme values
        assert 0.01 <= calibrator.calibrate(0.0) <= 0.99
        assert 0.01 <= calibrator.calibrate(1.0) <= 0.99
    
    def test_calibration_update(self):
        """Test calibration update mechanism"""
        calibrator = ConfidenceCalibrator()
        
        # Update with results
        for i in range(50):
            calibrator.update(0.7, i % 2 == 0)  # Alternating correct/incorrect
        
        # Should have history
        assert len(calibrator.history) == 50


class TestModelConfig:
    """Test model configuration"""
    
    def test_default_config(self):
        """Test default configuration"""
        config = ModelConfig()
        
        assert config.input_size == 35
        assert config.hidden_size == 128
        assert config.num_layers == 3
        assert config.dropout == 0.3
        assert config.attention_heads == 8
    
    def test_custom_config(self):
        """Test custom configuration"""
        config = ModelConfig(
            hidden_size=256,
            num_layers=4,
            dropout=0.5
        )
        
        assert config.hidden_size == 256
        assert config.num_layers == 4
        assert config.dropout == 0.5


# Integration tests
@pytest.mark.skipif(not TORCH_AVAILABLE, reason="PyTorch not available")
class TestMLIntegration:
    """Integration tests for ML system"""
    
    def test_end_to_end_prediction(self):
        """Test end-to-end prediction flow"""
        extractor = FeatureExtractor()
        predictor = AdvancedPredictor()
        
        shoe_state = {
            "true_count_b": 1.5,
            "true_count_p": -0.5,
            "running_count_b": 12,
            "running_count_p": -4,
            "cards_remaining": 250,
            "decks_remaining": 5,
            "edge": {"max_edge": 0.3},
            "decks": 8,
            "hands_played": 15,
            "cards_dealt": 150,
            "high_low_ratio": 1.2
        }
        
        history = ['B', 'P', 'B', 'B', 'P', 'P', 'B', 'T', 'B', 'B', 'P']
        
        # Extract features
        features = extractor.extract_all_features(shoe_state, history)
        assert features.shape == (30, 35)
        
        # Make prediction
        prediction = predictor.predict(shoe_state, history)
        
        assert "recommendation" in prediction
        assert "probabilities" in prediction
        assert "confidence" in prediction
        assert "edge_pct" in prediction
    
    def test_feature_consistency(self):
        """Test feature extraction consistency"""
        extractor = FeatureExtractor()
        
        shoe_state = {
            "true_count_b": 0.0,
            "cards_remaining": 400,
            "decks": 8,
            "hands_played": 0,
            "cards_dealt": 0
        }
        history = ['B', 'P', 'B']
        
        # Extract twice - should be similar (allowing for noise in sequence)
        features1 = extractor.extract_all_features(shoe_state, history)
        features2 = extractor.extract_all_features(shoe_state, history)
        
        # Last timestep should be identical (current features)
        assert np.allclose(features1[-1], features2[-1], atol=0.01)


