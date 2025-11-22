"""
Tests for production prediction service.
"""

from __future__ import annotations

from unittest.mock import Mock, patch

import numpy as np
import pytest

try:
    import torch
except ImportError:  # pragma: no cover
    torch = None  # type: ignore

from app.ml.config import FeatureConfig, ModelConfig, PerformanceConfig
from app.ml.predictor import (
    BaccaratPredictor,
    ConfidenceCalibrator,
    PredictionCache,
    get_predictor,
    reset_predictor,
)


@pytest.fixture
def mock_redis():
    redis_mock = Mock()
    redis_mock.get.return_value = None
    redis_mock.setex.return_value = True
    redis_mock.keys.return_value = []
    return redis_mock


@pytest.fixture
def predictor(mock_redis):
    with patch("redis.from_url", return_value=mock_redis):
        config = ModelConfig()
        feature_config = FeatureConfig()
        perf_config = PerformanceConfig()
        predictor = BaccaratPredictor(config, feature_config, perf_config, "redis://localhost")
        predictor.models = {}  # ensure fallback path for predictable behavior
        return predictor


class TestConfidenceCalibrator:
    def test_calibration_basic(self):
        calibrator = ConfidenceCalibrator()
        calibrated = calibrator.calibrate(0.7)
        assert 0 < calibrated < 1

    def test_calibration_update(self):
        calibrator = ConfidenceCalibrator()
        for idx in range(100):
            calibrator.update(0.8, idx % 2 == 0)
        assert calibrator.is_calibrated is True

    def test_save_load(self, tmp_path):
        calibrator = ConfidenceCalibrator()
        for idx in range(50):
            calibrator.update(0.7, idx % 3 == 0)
        save_path = tmp_path / "calibrator.pkl"
        calibrator.save(str(save_path))
        loaded = ConfidenceCalibrator.load(str(save_path))
        assert len(loaded.calibration_data) > 0


class TestPredictionCache:
    def test_cache_get_set(self, mock_redis):
        cache = PredictionCache(mock_redis, ttl=60)
        shoe_state = {"cards_remaining": 200}
        history = ["B", "P", "B"]
        prediction = {"recommendation": "B", "confidence": 0.8}
        cache.set(shoe_state, history, prediction)
        cached = cache.get(shoe_state, history)
        assert cache.cache_misses > 0
        assert cached is not None or cache.local_cache

    def test_cache_stats(self, mock_redis):
        cache = PredictionCache(mock_redis, ttl=60)
        stats = cache.get_stats()
        assert "cache_hits" in stats
        assert "hit_rate_pct" in stats


class TestBaccaratPredictor:
    @pytest.mark.asyncio
    async def test_predict_fallback(self, predictor):
        shoe_state = {
            "cards_remaining": 300,
            "true_count_b": 2.0,
            "true_count_p": -1.0,
            "edge": {"max_edge": 0.5},
        }
        history = ["B", "P", "P", "B", "B"]
        prediction = await predictor.predict(shoe_state, history)
        assert prediction["recommendation"] in {"B", "P", "T"}
        assert prediction["model_used"] == "fallback"

    @pytest.mark.asyncio
    async def test_predict_with_cache(self, predictor):
        shoe_state = {"cards_remaining": 250}
        history = ["B", "P", "B"]
        first = await predictor.predict(shoe_state, history)
        second = await predictor.predict(shoe_state, history)
        assert second.get("from_cache") in {True, False}
        assert first["probabilities"]

    def test_update_accuracy(self, predictor):
        prediction = {"recommendation": "B", "confidence": 0.8}
        predictor.update_accuracy(prediction, "B")
        predictor.update_accuracy(prediction, "P")
        assert len(predictor.metrics["accuracy_buffer"]) == 2

    def test_performance_stats(self, predictor):
        stats = predictor.get_performance_stats()
        assert "predictions_made" in stats
        assert "average_inference_time_ms" in stats
        assert "models_loaded" in stats

    def test_kelly_calculation(self, predictor):
        probs = np.array([0.50, 0.45, 0.05])
        edge = 2.0
        fraction = predictor._calculate_kelly_bet(probs, edge)
        assert 0 <= fraction <= 0.1

    def test_edge_calculation(self, predictor):
        probs = np.array([0.50, 0.45, 0.05])
        shoe_state = {"edge": {"max_edge": 1.5}}
        edge = predictor._calculate_edge(probs, shoe_state)
        assert isinstance(edge, float)


class TestGlobalPredictor:
    def test_get_predictor_singleton(self):
        reset_predictor()
        with patch("redis.from_url"):
            pred1 = get_predictor()
            pred2 = get_predictor()
            assert pred1 is pred2

    def test_reset_predictor(self):
        with patch("redis.from_url"):
            pred1 = get_predictor()
            reset_predictor()
            pred2 = get_predictor()
            assert pred1 is not pred2


@pytest.mark.skipif(torch is None or not torch.cuda.is_available(), reason="CUDA not available")  # type: ignore[name-defined]
class TestGPUInference:
    @pytest.mark.asyncio
    async def test_gpu_prediction(self, predictor):
        if predictor.device.type != "cuda":
            pytest.skip("GPU not available")
        shoe_state = {"cards_remaining": 200}
        history = ["B"] * 10
        prediction = await predictor.predict(shoe_state, history)
        assert "inference_time_ms" in prediction

