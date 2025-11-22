"""
Unit tests for ML module.
"""
import pytest
import numpy as np
from app.ml.model import FeatureEngineer, LSTMPredictor
from app.ml.versioning import ModelVersionManager, ModelVersion


class TestFeatureEngineer:
    """Tests for feature engineering."""
    
    def test_encode_outcomes(self):
        """Test outcome encoding."""
        engineer = FeatureEngineer()
        outcomes = ["B", "P", "T"]
        encoded = engineer.encode_outcomes(outcomes)
        
        assert len(encoded) == 3
        assert encoded[0] == 1.0  # B
        assert encoded[1] == 0.0  # P
        assert encoded[2] == 0.5  # T
    
    def test_extract_sequence_features(self):
        """Test sequence feature extraction."""
        engineer = FeatureEngineer(sequence_length=10)
        outcomes = ["B", "P", "B", "P"] * 5
        features = engineer.extract_sequence_features(outcomes)
        
        assert len(features) == 10
        assert all(0 <= f <= 1 for f in features)
    
    def test_extract_statistical_features(self):
        """Test statistical feature extraction."""
        engineer = FeatureEngineer()
        outcomes = ["B", "P", "B", "B", "P", "T"] * 10
        features = engineer.extract_statistical_features(outcomes)
        
        assert len(features) == 10
        assert all(isinstance(f, (int, float, np.floating)) for f in features)
    
    def test_extract_features(self):
        """Test combined feature extraction."""
        engineer = FeatureEngineer(sequence_length=5)
        outcomes = ["B", "P", "B", "P", "B"]
        seq_feat, stat_feat = engineer.extract_features(outcomes)
        
        assert len(seq_feat) == 5
        assert len(stat_feat) == 10


class TestLSTMPredictor:
    """Tests for LSTM predictor."""
    
    @pytest.mark.skipif(not pytest.importorskip("tensorflow", reason="TensorFlow not available"), reason="TensorFlow required")
    def test_build_model(self):
        """Test model building."""
        model = LSTMPredictor(sequence_length=10, lstm_units=32)
        model.build_model()
        
        assert model.model is not None
        assert model.is_compiled is True
    
    def test_prepare_training_data(self):
        """Test training data preparation."""
        model = LSTMPredictor(sequence_length=5)
        sequences = [["B", "P", "B", "P", "B"]] * 10
        labels = ["B"] * 10
        
        (X_seq, X_stat), y = model.prepare_training_data(sequences, labels)
        
        assert len(X_seq) == 10
        assert len(X_stat) == 10
        assert len(y) == 10
        assert all(len(seq) == 5 for seq in X_seq)


class TestModelVersionManager:
    """Tests for model versioning."""
    
    def test_register_version(self):
        """Test version registration."""
        manager = ModelVersionManager(registry_path="test_registry.json")
        
        version = manager.register_version(
            version="v1.0.0",
            model_path="test_model",
            accuracy=0.85,
            precision=0.82,
            recall=0.88,
            f1_score=0.85,
            training_samples=1000,
            validation_samples=200,
            hyperparameters={"lr": 0.001},
            description="Test model"
        )
        
        assert version.version == "v1.0.0"
        assert version.accuracy == 0.85
        assert manager.get_version("v1.0.0") is not None
    
    def test_get_latest_version(self):
        """Test getting latest version."""
        manager = ModelVersionManager(registry_path="test_registry.json")
        
        manager.register_version(
            version="v1.0.0",
            model_path="test1",
            accuracy=0.8,
            precision=0.8,
            recall=0.8,
            f1_score=0.8,
            training_samples=100,
            validation_samples=20,
            hyperparameters={}
        )
        
        latest = manager.get_latest_version()
        assert latest == "v1.0.0"
    
    def test_set_production(self):
        """Test setting production version."""
        manager = ModelVersionManager(registry_path="test_registry.json")
        
        manager.register_version(
            version="v1.0.0",
            model_path="test1",
            accuracy=0.8,
            precision=0.8,
            recall=0.8,
            f1_score=0.8,
            training_samples=100,
            validation_samples=20,
            hyperparameters={},
            is_production=True
        )
        
        prod_version = manager.get_production_version()
        assert prod_version == "v1.0.0"

