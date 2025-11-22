"""
Production-ready prediction service with caching, confidence calibration, and ensemble.
"""

from __future__ import annotations

import json
import hashlib
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

import numpy as np

try:
    import torch
    from torch import nn
except ImportError:  # pragma: no cover - torch is required in production
    torch = None  # type: ignore
    nn = None  # type: ignore

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:  # pragma: no cover
    redis = None  # type: ignore
    REDIS_AVAILABLE = False

from app.ml.advanced_model import BaccaratLSTM, ModelConfig as AdvancedModelConfig
from app.ml.features import FeatureExtractor
from app.ml.config import ModelConfig, FeatureConfig, PerformanceConfig

logger = logging.getLogger(__name__)


class ConfidenceCalibrator:
    """
    Calibrate model confidence to match actual accuracy using Platt scaling style updates.
    """

    def __init__(self):
        self.calibration_data: List[Dict[str, Any]] = []
        self.is_calibrated = False
        self.calibration_map: Dict[float, float] = {}
        self.platt_a = 1.0
        self.platt_b = 0.0

    def calibrate(self, raw_confidence: float) -> float:
        """Calibrate raw confidence score."""
        if not self.is_calibrated:
            calibrated = 1 / (1 + np.exp(-(self.platt_a * raw_confidence + self.platt_b)))
        else:
            bucket = round(raw_confidence, 1)
            calibrated = self.calibration_map.get(bucket, raw_confidence)
        return float(np.clip(calibrated, 0.01, 0.99))

    def update(self, raw_confidence: float, was_correct: bool) -> None:
        """Update calibration dataset."""
        self.calibration_data.append(
            {
                "confidence": raw_confidence,
                "correct": was_correct,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )
        if len(self.calibration_data) % 100 == 0:
            self._retrain_calibration()

    def _retrain_calibration(self) -> None:
        """Rebuild calibration mapping from latest data."""
        if len(self.calibration_data) < 100:
            return

        buckets: Dict[float, Dict[str, int]] = {}
        for item in self.calibration_data[-1000:]:
            bucket = round(item["confidence"], 1)
            if bucket not in buckets:
                buckets[bucket] = {"total": 0, "correct": 0}
            buckets[bucket]["total"] += 1
            if item["correct"]:
                buckets[bucket]["correct"] += 1

        for bucket, stats in buckets.items():
            if stats["total"] >= 10:
                self.calibration_map[bucket] = stats["correct"] / stats["total"]

        self.is_calibrated = True
        logger.info("Confidence calibrator updated with %s buckets", len(buckets))

    def save(self, filepath: str) -> None:
        """Persist calibrator state."""
        import pickle

        state = {
            "calibration_data": self.calibration_data[-1000:],
            "calibration_map": self.calibration_map,
            "platt_a": self.platt_a,
            "platt_b": self.platt_b,
            "is_calibrated": self.is_calibrated,
        }
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "wb") as handle:
            pickle.dump(state, handle)
        logger.info("Calibrator saved to %s", filepath)

    @classmethod
    def load(cls, filepath: str) -> "ConfidenceCalibrator":
        """Load calibrator state from disk."""
        import pickle

        calibrator = cls()
        try:
            with open(filepath, "rb") as handle:
                state = pickle.load(handle)
            calibrator.calibration_data = state.get("calibration_data", [])
            calibrator.calibration_map = state.get("calibration_map", {})
            calibrator.platt_a = state.get("platt_a", 1.0)
            calibrator.platt_b = state.get("platt_b", 0.0)
            calibrator.is_calibrated = state.get("is_calibrated", False)
            logger.info("Calibrator loaded from %s", filepath)
        except FileNotFoundError:
            logger.info("Calibrator file %s not found. Using defaults.", filepath)
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("Failed to load calibrator: %s. Using defaults.", exc)
        return calibrator


class PredictionCache:
    """High-performance prediction cache with Redis + local fallback."""

    def __init__(self, redis_client: Optional["redis.Redis"], ttl: int = 60):
        self.redis_client = redis_client
        self.ttl = ttl
        self.local_cache: Dict[str, Dict[str, Any]] = {}
        self.cache_hits = 0
        self.cache_misses = 0

    def _generate_key(self, shoe_state: Dict, history: List[str]) -> str:
        recent_history = "".join(history[-20:]) if history else "empty"
        key_attrs = [
            shoe_state.get("cards_remaining", 0),
            shoe_state.get("hands_played", 0),
            round(shoe_state.get("true_count_b", 0.0), 2),
            round(shoe_state.get("true_count_p", 0.0), 2),
        ]
        key_string = f"{recent_history}:{'_'.join(map(str, key_attrs))}"
        return f"pred:{hashlib.md5(key_string.encode()).hexdigest()}"

    def get(self, shoe_state: Dict, history: List[str]) -> Optional[Dict[str, Any]]:
        key = self._generate_key(shoe_state, history)
        cached_bytes: Optional[bytes] = None
        if self.redis_client is not None:
            try:
                cached_bytes = self.redis_client.get(key)
            except redis.RedisError as exc:  # type: ignore[attr-defined]
                logger.warning("Redis cache read failed: %s", exc)
        if not cached_bytes:
            self.cache_misses += 1

        if cached_bytes:
            self.cache_hits += 1
            cached_str = cached_bytes.decode() if isinstance(cached_bytes, bytes) else cached_bytes
            return json.loads(cached_str)

        local_value = self.local_cache.get(key)
        if local_value:
            self.cache_hits += 1
            return local_value

        return None

    def set(self, shoe_state: Dict, history: List[str], prediction: Dict[str, Any]) -> None:
        key = self._generate_key(shoe_state, history)
        if self.redis_client is not None:
            try:
                self.redis_client.setex(key, self.ttl, json.dumps(prediction))
            except redis.RedisError as exc:  # type: ignore[attr-defined]
                logger.warning("Redis cache write failed: %s", exc)
        self.local_cache[key] = prediction
        if len(self.local_cache) > 1000:
            for stale_key in list(self.local_cache.keys())[:100]:
                self.local_cache.pop(stale_key, None)

    def clear(self) -> None:
        try:
            if self.redis_client is not None:
                keys = self.redis_client.keys("pred:*")
                if keys:
                    self.redis_client.delete(*keys)
        except redis.RedisError as exc:  # type: ignore[attr-defined]
            logger.error("Failed clearing Redis cache: %s", exc)
        self.local_cache.clear()
        self.cache_hits = 0
        self.cache_misses = 0

    def get_stats(self) -> Dict[str, Any]:
        total_requests = self.cache_hits + self.cache_misses
        hit_rate = (self.cache_hits / total_requests * 100) if total_requests else 0
        return {
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "hit_rate_pct": round(hit_rate, 2),
            "local_cache_size": len(self.local_cache),
        }


class ModelEnsemble:
    """Simple ensemble wrapper for multiple PyTorch models."""

    def __init__(self, models: List[nn.Module]):
        self.models = models
        for model in self.models:
            model.eval()

    def predict(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        prob_stack = []
        conf_stack = []
        with torch.no_grad():
            for model in self.models:
                probs, confidence = model(x)
                prob_stack.append(probs)
                conf_stack.append(confidence)
        probs_tensor = torch.stack(prob_stack)
        conf_tensor = torch.stack(conf_stack)
        weights = torch.softmax(conf_tensor.squeeze(-1), dim=0).unsqueeze(-1)
        blended_probs = (probs_tensor * weights.unsqueeze(-1)).sum(dim=0)
        avg_conf = conf_tensor.mean(dim=0)
        return blended_probs, avg_conf


class BaccaratPredictor:
    """Production-ready ML predictor with caching and calibration."""

    def __init__(
        self,
        model_config: ModelConfig,
        feature_config: FeatureConfig,
        performance_config: PerformanceConfig,
        redis_url: str,
    ):
        if torch is None:
            raise ImportError("PyTorch is required for BaccaratPredictor")

        self.model_config = model_config
        self.feature_config = feature_config
        self.performance_config = performance_config
        self.model_config.ensure_paths()

        self.redis_client: Optional["redis.Redis"] = None
        if REDIS_AVAILABLE:
            try:
                self.redis_client = redis.from_url(redis_url, decode_responses=False)  # type: ignore[arg-type]
            except Exception as exc:  # pragma: no cover - connection errors
                logger.warning("Redis unavailable for predictor: %s", exc)

        self.device = self._setup_device()
        self.feature_extractor = FeatureExtractor()
        self.calibrator = ConfidenceCalibrator()
        self.cache = PredictionCache(
            self.redis_client,
            ttl=self.performance_config.prediction_cache_ttl,
        )

        self.models: Dict[str, nn.Module] = {}
        self.ensemble: Optional[ModelEnsemble] = None
        self.metrics: Dict[str, Any] = {
            "predictions_made": 0,
            "total_inference_time": 0.0,
            "cache_hit_rate": 0.0,
            "average_confidence": 0.0,
            "accuracy_buffer": [],
        }
        self._load_models()

    def _setup_device(self) -> torch.device:
        if self.model_config.device == "auto":
            device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        else:
            device = torch.device(self.model_config.device)
        logger.info("Prediction device set to %s", device)
        return device

    def _load_models(self) -> None:
        model_dir = self.model_config.model_dir
        if not model_dir.exists():
            logger.warning("Model directory %s does not exist. Creating it.", model_dir)
            model_dir.mkdir(parents=True, exist_ok=True)
            return

        model_files = sorted(model_dir.glob("baccarat_lstm_*.pth"))
        if not model_files:
            logger.warning("No model checkpoints found in %s. Using fallback predictions.", model_dir)
            return

        loaded_models = []
        for model_file in model_files[: self.model_config.ensemble_size]:
            try:
                adv_config = AdvancedModelConfig(
                    input_size=self.model_config.input_size,
                    hidden_size=self.model_config.hidden_size,
                    num_layers=self.model_config.num_layers,
                    dropout=self.model_config.dropout,
                    attention_heads=self.model_config.attention_heads,
                    sequence_length=self.model_config.sequence_length,
                )
                model = BaccaratLSTM(adv_config).to(self.device)
                checkpoint = torch.load(model_file, map_location=self.device)
                state_dict = checkpoint.get("model_state_dict", checkpoint)
                model.load_state_dict(state_dict)
                model.eval()
                model_name = model_file.stem
                self.models[model_name] = model
                loaded_models.append(model)
                logger.info("Loaded model %s", model_name)
            except Exception as exc:
                logger.error("Failed to load model %s: %s", model_file, exc)

        if len(loaded_models) > 1:
            self.ensemble = ModelEnsemble(loaded_models)
            logger.info("Ensemble created with %s models", len(loaded_models))
        elif not loaded_models:
            logger.warning("Failed to load any models. Predictor will use fallback.")

        calibrator_path = model_dir / "calibrator.pkl"
        if calibrator_path.exists():
            self.calibrator = ConfidenceCalibrator.load(str(calibrator_path))

    async def predict(self, shoe_state: Dict, history: List[str], use_cache: bool = True) -> Dict[str, Any]:
        start_time = datetime.utcnow()

        if use_cache and self.performance_config.enable_prediction_cache:
            cached = self.cache.get(shoe_state, history)
            if cached is not None:
                cached["from_cache"] = True
                return cached

        try:
            features = self.feature_extractor.extract_all_features(shoe_state, history)
        except Exception as exc:
            logger.error("Feature extraction failed: %s", exc)
            fallback = self._fallback_prediction(shoe_state)
            fallback["from_cache"] = False
            return fallback

        try:
            prediction = await self._predict_with_model(features, shoe_state)
        except Exception as exc:
            logger.error("Model prediction failed: %s", exc)
            fallback = self._fallback_prediction(shoe_state)
            fallback["from_cache"] = False
            return fallback

        inference_time = (datetime.utcnow() - start_time).total_seconds()
        prediction["inference_time_ms"] = round(inference_time * 1000, 2)
        prediction["from_cache"] = False

        if use_cache and self.performance_config.enable_prediction_cache:
            self.cache.set(shoe_state, history, prediction)

        self._update_metrics(prediction, inference_time)

        if (
            self.performance_config.log_slow_predictions
            and inference_time > self.performance_config.slow_prediction_threshold
        ):
            logger.warning("Slow prediction detected: %.2f ms", inference_time * 1000)

        return prediction

    async def _predict_with_model(self, features: np.ndarray, shoe_state: Dict) -> Dict[str, Any]:
        if not self.models:
            return self._fallback_prediction(shoe_state)

        x = torch.FloatTensor(features).unsqueeze(0).to(self.device)
        with torch.no_grad():
            if self.ensemble is not None:
                probs_tensor, conf_tensor = self.ensemble.predict(x)
            else:
                model = next(iter(self.models.values()))
                probs_tensor, conf_tensor = model(x)

        probs = probs_tensor.cpu().numpy()[0]
        confidence = conf_tensor.cpu().numpy()[0][0]
        calibrated_confidence = self.calibrator.calibrate(confidence)
        outcomes = ["B", "P", "T"]
        best_idx = int(np.argmax(probs))
        recommendation = outcomes[best_idx]
        edge = self._calculate_edge(probs, shoe_state)
        kelly_fraction = self._calculate_kelly_bet(probs, edge)

        return {
            "recommendation": recommendation,
            "probabilities": {"B": float(probs[0]), "P": float(probs[1]), "T": float(probs[2])},
            "confidence": float(confidence),
            "calibrated_confidence": float(calibrated_confidence),
            "edge_pct": edge,
            "kelly_bet_fraction": kelly_fraction,
            "ensemble_size": len(self.models) if self.ensemble else 1,
            "model_used": "ensemble" if self.ensemble else "single",
            "timestamp": datetime.utcnow().isoformat(),
        }

    def _fallback_prediction(self, shoe_state: Dict) -> Dict[str, Any]:
        true_count_b = shoe_state.get("true_count_b", 0.0)
        true_count_p = shoe_state.get("true_count_p", 0.0)
        base_probs = np.array([0.4586, 0.4462, 0.0952])
        count_adjustment = (true_count_b - true_count_p) * 0.005
        adjusted_probs = base_probs.copy()
        adjusted_probs[0] += count_adjustment
        adjusted_probs[1] -= count_adjustment
        adjusted_probs = np.clip(adjusted_probs, 0.01, 0.98)
        adjusted_probs = adjusted_probs / adjusted_probs.sum()
        outcomes = ["B", "P", "T"]
        best_idx = int(np.argmax(adjusted_probs))
        recommendation = outcomes[best_idx]
        edge_pct = abs(true_count_b) * 0.5
        return {
            "recommendation": recommendation,
            "probabilities": {"B": float(adjusted_probs[0]), "P": float(adjusted_probs[1]), "T": float(adjusted_probs[2])},
            "confidence": 0.5,
            "calibrated_confidence": 0.5,
            "edge_pct": edge_pct,
            "kelly_bet_fraction": 0.0,
            "ensemble_size": 0,
            "model_used": "fallback",
            "timestamp": datetime.utcnow().isoformat(),
        }

    def _calculate_edge(self, probabilities: np.ndarray, shoe_state: Dict) -> float:
        counting_edge = shoe_state.get("edge", {}).get("max_edge", 0.0)
        theoretical = np.array([0.4586, 0.4462, 0.0952])
        prob_edge = float(np.max(probabilities - theoretical) * 100)
        total_edge = counting_edge * 0.4 + prob_edge * 0.6
        return round(total_edge, 3)

    def _calculate_kelly_bet(self, probabilities: np.ndarray, edge: float) -> float:
        if edge <= 0:
            return 0.0
        best_prob = float(np.max(probabilities))
        p = best_prob
        q = 1 - p
        b = 1.0
        kelly_fraction = (b * p - q) / b
        safe_fraction = kelly_fraction * 0.25
        return float(np.clip(safe_fraction, 0.0, 0.1))

    def update_accuracy(self, prediction: Dict[str, Any], actual: str) -> None:
        was_correct = prediction.get("recommendation") == actual
        self.metrics["accuracy_buffer"].append(was_correct)
        if len(self.metrics["accuracy_buffer"]) > self.performance_config.max_accuracy_buffer:
            self.metrics["accuracy_buffer"].pop(0)
        raw_confidence = prediction.get("confidence", 0.5)
        self.calibrator.update(raw_confidence, was_correct)

    def _update_metrics(self, prediction: Dict[str, Any], inference_time: float) -> None:
        self.metrics["predictions_made"] += 1
        self.metrics["total_inference_time"] += inference_time
        conf = prediction.get("calibrated_confidence", 0.5)
        n = self.metrics["predictions_made"]
        old_avg = self.metrics["average_confidence"]
        self.metrics["average_confidence"] = (old_avg * (n - 1) + conf) / n
        cache_stats = self.cache.get_stats()
        self.metrics["cache_hit_rate"] = cache_stats["hit_rate_pct"]

    def get_performance_stats(self) -> Dict[str, Any]:
        n = self.metrics["predictions_made"]
        avg_inference_ms = (self.metrics["total_inference_time"] / n * 1000) if n else 0
        accuracy_buffer = self.metrics["accuracy_buffer"]
        recent_accuracy = (sum(accuracy_buffer) / len(accuracy_buffer) * 100) if accuracy_buffer else 0
        return {
            "predictions_made": n,
            "average_inference_time_ms": round(avg_inference_ms, 2),
            "cache_hit_rate_pct": self.metrics["cache_hit_rate"],
            "average_confidence": round(self.metrics["average_confidence"], 3),
            "recent_accuracy_pct": round(recent_accuracy, 2),
            "accuracy_sample_size": len(accuracy_buffer),
            "models_loaded": len(self.models),
            "ensemble_active": self.ensemble is not None,
            "device": str(self.device),
            "calibrator_trained": self.calibrator.is_calibrated,
        }

    def clear_cache(self) -> None:
        self.cache.clear()

    def reload_models(self) -> None:
        logger.info("Reloading ML models from disk...")
        self.models.clear()
        self.ensemble = None
        self._load_models()

    def save_state(self) -> None:
        state_dir = self.model_config.model_dir
        calibrator_path = state_dir / "calibrator.pkl"
        self.calibrator.save(str(calibrator_path))
        metrics_path = state_dir / "predictor_metrics.json"
        with open(metrics_path, "w", encoding="utf-8") as handle:
            json.dump(self.get_performance_stats(), handle, indent=2)
        logger.info("Predictor state saved to %s", state_dir)


_predictor_instance: Optional[BaccaratPredictor] = None


def get_predictor(
    model_config: Optional[ModelConfig] = None,
    feature_config: Optional[FeatureConfig] = None,
    performance_config: Optional[PerformanceConfig] = None,
    redis_url: str = "redis://localhost:6379/0",
) -> BaccaratPredictor:
    global _predictor_instance
    if _predictor_instance is None:
        model_config = model_config or ModelConfig()
        feature_config = feature_config or FeatureConfig()
        performance_config = performance_config or PerformanceConfig()
        _predictor_instance = BaccaratPredictor(
            model_config=model_config,
            feature_config=feature_config,
            performance_config=performance_config,
            redis_url=redis_url,
        )
        logger.info("Global BaccaratPredictor instance created")
    return _predictor_instance


def reset_predictor() -> None:
    global _predictor_instance
    _predictor_instance = None
    logger.info("Global BaccaratPredictor instance reset")


