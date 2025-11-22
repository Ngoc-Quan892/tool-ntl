import pytest

from app.core.engine import Predictor


def test_predictor_initial_prediction():
    predictor = Predictor()
    prediction = predictor.predict()
    assert prediction["recommend"] in {"B", "P"}
    assert prediction["confidence"] == 50.0


def test_predictor_after_history():
    predictor = Predictor()
    for _ in range(20):
        predictor.add("B")
    prediction = predictor.predict()
    assert "recommend" in prediction
    assert prediction["confidence"] >= 50.0
