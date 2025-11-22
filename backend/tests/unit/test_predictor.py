"""
Unit tests for predictor module.
"""
import pytest
from app.core.predictor import Predictor


class TestPredictor:
    """Tests for Predictor class."""
    
    def test_initial_state(self):
        """Test initial predictor state."""
        predictor = Predictor()
        assert len(predictor.history) == 0
        assert predictor.prediction_hits == 0
        assert predictor.total_predictions == 0
    
    def test_add_result(self):
        """Test adding results."""
        predictor = Predictor()
        predictor.add("B")
        predictor.add("P")
        predictor.add("T")
        
        assert len(predictor.history) == 3
        assert predictor.history == ["B", "P", "T"]
    
    def test_predict_no_history(self):
        """Test prediction with no history."""
        predictor = Predictor()
        prediction = predictor.predict()
        
        assert prediction["recommend"] in ["B", "P"]
        assert 0 <= prediction["confidence"] <= 1
        assert "pattern" in prediction
    
    def test_predict_with_history(self):
        """Test prediction with history."""
        predictor = Predictor()
        predictor.add("B")
        predictor.add("B")
        predictor.add("B")
        
        prediction = predictor.predict()
        assert prediction["recommend"] in ["B", "P"]
        assert "confidence" in prediction
    
    def test_reset(self):
        """Test resetting predictor."""
        predictor = Predictor()
        predictor.add("B")
        predictor.add("P")
        predictor.reset()
        
        assert len(predictor.history) == 0
        assert predictor.prediction_hits == 0
        assert predictor.total_predictions == 0

