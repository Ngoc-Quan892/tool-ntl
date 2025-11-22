"""
Comprehensive monitoring for predictive cache warming.

Features:
- Track prediction accuracy over time
- Monitor model drift (accuracy degradation)
- Alert on anomalies
- Dashboard metrics (Prometheus + Grafana)
- A/B test results tracking
- Cost/benefit analysis
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections import deque
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

try:
    from prometheus_client import Counter, Gauge, Histogram
    HAS_PROMETHEUS = True
except ImportError:
    HAS_PROMETHEUS = False
    # Create dummy classes for when prometheus_client is not available
    class Counter:
        def __init__(self, *args, **kwargs):
            pass
        def inc(self, *args, **kwargs):
            pass
    class Gauge:
        def __init__(self, *args, **kwargs):
            pass
        def set(self, *args, **kwargs):
            pass
        def observe(self, *args, **kwargs):
            pass
    class Histogram:
        def __init__(self, *args, **kwargs):
            pass
        def observe(self, *args, **kwargs):
            pass

logger = logging.getLogger(__name__)


# ============================================================================
# Prediction Metrics
# ============================================================================

class PredictionMetrics:
    """
    Track and expose prediction metrics using Prometheus.
    """
    
    def __init__(self):
        """Initialize Prometheus metrics."""
        if not HAS_PROMETHEUS:
            logger.warning("prometheus_client not available, using dummy metrics")
        
        # Prediction accuracy (current)
        self.prediction_accuracy = Gauge(
            'predictive_cache_prediction_accuracy',
            'Current prediction accuracy (0.0-1.0)',
        )
        
        # Prediction latency
        self.prediction_latency = Histogram(
            'predictive_cache_prediction_latency_seconds',
            'Time taken to generate predictions',
            buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0],
        )
        
        # Cache hit improvement
        self.cache_hit_improvement = Gauge(
            'predictive_cache_hit_improvement_percent',
            'Cache hit rate improvement from predictions (%)',
        )
        
        # Prediction counters
        self.predictions_total = Counter(
            'predictive_cache_predictions_total',
            'Total number of predictions made',
        )
        
        self.predictions_correct = Counter(
            'predictive_cache_predictions_correct_total',
            'Total number of correct predictions',
        )
        
        self.predictions_incorrect = Counter(
            'predictive_cache_predictions_incorrect_total',
            'Total number of incorrect predictions',
        )
        
        # Model training metrics
        self.model_training_duration = Histogram(
            'predictive_cache_model_training_duration_seconds',
            'Time taken to train prediction model',
            buckets=[10, 30, 60, 120, 300, 600, 1800],
        )
        
        self.model_training_total = Counter(
            'predictive_cache_model_training_total',
            'Total number of model training runs',
        )
        
        self.model_training_failures = Counter(
            'predictive_cache_model_training_failures_total',
            'Total number of failed model training runs',
        )
        
        # Feature extraction metrics
        self.feature_extraction_duration = Histogram(
            'predictive_cache_feature_extraction_duration_seconds',
            'Time taken to extract features',
            buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5],
        )
        
        # Cache warming metrics
        self.items_warmed_total = Counter(
            'predictive_cache_items_warmed_total',
            'Total number of items warmed based on predictions',
        )
        
        self.warming_duration = Histogram(
            'predictive_cache_warming_duration_seconds',
            'Time taken to warm predicted items',
            buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0],
        )
        
        # Internal tracking
        self._recent_predictions: deque = deque(maxlen=1000)
        self._recent_accuracy: deque = deque(maxlen=100)
        self._current_accuracy: float = 0.0
        self._last_update: Optional[datetime] = None
    
    def record_prediction(
        self,
        predicted_game_id: int,
        actual_game_id: Optional[int] = None,
        confidence: float = 0.0,
        latency: float = 0.0,
    ) -> None:
        """
        Record a prediction.
        
        Args:
            predicted_game_id: Game ID that was predicted
            actual_game_id: Actual game ID that was accessed (None if not yet known)
            confidence: Prediction confidence (0.0-1.0)
            latency: Time taken to generate prediction (seconds)
        """
        self.predictions_total.inc()
        self.prediction_latency.observe(latency)
        
        # Store prediction for later evaluation
        self._recent_predictions.append({
            "predicted_game_id": predicted_game_id,
            "actual_game_id": actual_game_id,
            "confidence": confidence,
            "timestamp": datetime.now(),
            "evaluated": actual_game_id is not None,
        })
        
        # If we have actual result, evaluate immediately
        if actual_game_id is not None:
            is_correct = predicted_game_id == actual_game_id
            if is_correct:
                self.predictions_correct.inc()
            else:
                self.predictions_incorrect.inc()
            
            # Update accuracy
            self._update_accuracy()
    
    def record_training_time(self, duration: float, success: bool = True) -> None:
        """
        Record model training duration.
        
        Args:
            duration: Training duration in seconds
            success: Whether training succeeded
        """
        if success:
            self.model_training_duration.observe(duration)
            self.model_training_total.inc()
        else:
            self.model_training_failures.inc()
    
    def record_feature_extraction_time(self, duration: float) -> None:
        """
        Record feature extraction duration.
        
        Args:
            duration: Extraction duration in seconds
        """
        self.feature_extraction_duration.observe(duration)
    
    def record_warming(
        self,
        items_warmed: int,
        duration: float,
    ) -> None:
        """
        Record cache warming operation.
        
        Args:
            items_warmed: Number of items warmed
            duration: Warming duration in seconds
        """
        for _ in range(items_warmed):
            self.items_warmed_total.inc()
        self.warming_duration.observe(duration)
    
    def record_cache_hit_improvement(self, improvement_percent: float) -> None:
        """
        Record cache hit rate improvement.
        
        Args:
            improvement_percent: Improvement percentage (e.g., 22.0 for 22%)
        """
        self.cache_hit_improvement.set(improvement_percent)
    
    def _update_accuracy(self) -> None:
        """Update current accuracy from recent predictions."""
        # Get evaluated predictions
        evaluated = [
            p for p in self._recent_predictions
            if p.get("evaluated", False)
        ]
        
        if len(evaluated) == 0:
            return
        
        # Calculate accuracy
        correct = sum(
            1 for p in evaluated
            if p["predicted_game_id"] == p.get("actual_game_id")
        )
        accuracy = correct / len(evaluated) if len(evaluated) > 0 else 0.0
        
        self._current_accuracy = accuracy
        self.prediction_accuracy.set(accuracy)
        
        # Store in history
        self._recent_accuracy.append({
            "timestamp": datetime.now(),
            "accuracy": accuracy,
        })
        
        self._last_update = datetime.now()
    
    def get_current_accuracy(self) -> float:
        """
        Get current prediction accuracy.
        
        Returns:
            Accuracy (0.0-1.0)
        """
        return self._current_accuracy
    
    def get_accuracy_trend(self, minutes: int = 60) -> List[Dict[str, Any]]:
        """
        Get accuracy trend over time.
        
        Args:
            minutes: Number of minutes to look back
            
        Returns:
            List of accuracy data points
        """
        cutoff = datetime.now() - timedelta(minutes=minutes)
        
        trend = [
            {
                "timestamp": point["timestamp"].isoformat(),
                "accuracy": point["accuracy"],
            }
            for point in self._recent_accuracy
            if point["timestamp"] >= cutoff
        ]
        
        return trend
    
    def evaluate_pending_predictions(self, actual_accesses: Dict[int, int]) -> None:
        """
        Evaluate pending predictions against actual accesses.
        
        Args:
            actual_accesses: Dictionary mapping game_id to access count
        """
        for prediction in self._recent_predictions:
            if prediction.get("evaluated", False):
                continue
            
            predicted_id = prediction["predicted_game_id"]
            # Consider correct if the predicted game was accessed
            is_correct = predicted_id in actual_accesses and actual_accesses[predicted_id] > 0
            
            if is_correct:
                self.predictions_correct.inc()
            else:
                self.predictions_incorrect.inc()
            
            prediction["evaluated"] = True
            prediction["actual_game_id"] = predicted_id if is_correct else None
        
        # Update accuracy
        self._update_accuracy()
    
    def export_metrics(self) -> str:
        """
        Export metrics in Prometheus format.
        
        Returns:
            Prometheus metrics string
        """
        try:
            from prometheus_client import generate_latest
            return generate_latest().decode('utf-8')
        except ImportError:
            return "# Prometheus client not available\n"
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get summary of all metrics.
        
        Returns:
            Dictionary with metric summaries
        """
        return {
            "current_accuracy": self._current_accuracy,
            "total_predictions": self.predictions_total._value.get() if HAS_PROMETHEUS else 0,
            "correct_predictions": self.predictions_correct._value.get() if HAS_PROMETHEUS else 0,
            "incorrect_predictions": self.predictions_incorrect._value.get() if HAS_PROMETHEUS else 0,
            "model_trainings": self.model_training_total._value.get() if HAS_PROMETHEUS else 0,
            "model_training_failures": self.model_training_failures._value.get() if HAS_PROMETHEUS else 0,
            "items_warmed": self.items_warmed_total._value.get() if HAS_PROMETHEUS else 0,
            "last_update": self._last_update.isoformat() if self._last_update else None,
        }


# ============================================================================
# Model Drift Detector
# ============================================================================

class ModelDriftDetector:
    """
    Detect when model accuracy degrades (model drift).
    """
    
    def __init__(
        self,
        baseline_accuracy: float = 0.8,
        drift_threshold: float = 0.1,
        window_size: int = 100,
        alert_cooldown: int = 3600,  # 1 hour
    ):
        """
        Initialize model drift detector.
        
        Args:
            baseline_accuracy: Baseline accuracy to compare against
            drift_threshold: Accuracy drop threshold (0.1 = 10%)
            window_size: Rolling window size for accuracy calculation
            alert_cooldown: Seconds between alerts
        """
        self.baseline_accuracy = baseline_accuracy
        self.drift_threshold = drift_threshold
        self.window_size = window_size
        self.alert_cooldown = alert_cooldown
        
        self._accuracy_window: deque = deque(maxlen=window_size)
        self._last_alert_time: Optional[datetime] = None
        self._drift_detected: bool = False
        self.logger = logging.getLogger(__name__)
    
    async def check_drift(
        self,
        current_accuracy: float,
        metrics: Optional[PredictionMetrics] = None,
    ) -> Dict[str, Any]:
        """
        Check for model drift.
        
        Args:
            current_accuracy: Current prediction accuracy
            metrics: Optional PredictionMetrics instance
            
        Returns:
            Dictionary with drift detection results
        """
        # Add to rolling window
        self._accuracy_window.append({
            "accuracy": current_accuracy,
            "timestamp": datetime.now(),
        })
        
        # Calculate rolling accuracy
        rolling_accuracy = await self._calculate_rolling_accuracy()
        
        # Check for drift
        accuracy_drop = self.baseline_accuracy - rolling_accuracy
        drift_detected = accuracy_drop >= self.drift_threshold
        
        result = {
            "drift_detected": drift_detected,
            "baseline_accuracy": self.baseline_accuracy,
            "current_accuracy": current_accuracy,
            "rolling_accuracy": rolling_accuracy,
            "accuracy_drop": accuracy_drop,
            "drop_percent": (accuracy_drop / self.baseline_accuracy * 100) if self.baseline_accuracy > 0 else 0.0,
            "window_size": len(self._accuracy_window),
        }
        
        # Alert if drift detected
        if drift_detected and not self._drift_detected:
            await self.alert_drift_detected(result)
            self._drift_detected = True
        elif not drift_detected:
            self._drift_detected = False
        
        return result
    
    async def _calculate_rolling_accuracy(self) -> float:
        """
        Calculate rolling accuracy over window.
        
        Returns:
            Rolling accuracy (0.0-1.0)
        """
        if len(self._accuracy_window) == 0:
            return self.baseline_accuracy
        
        accuracies = [point["accuracy"] for point in self._accuracy_window]
        return sum(accuracies) / len(accuracies)
    
    async def alert_drift_detected(self, drift_info: Dict[str, Any]) -> None:
        """
        Send alert when drift is detected.
        
        Args:
            drift_info: Drift detection information
        """
        # Check cooldown
        now = datetime.now()
        if self._last_alert_time:
            elapsed = (now - self._last_alert_time).total_seconds()
            if elapsed < self.alert_cooldown:
                return
        
        self._last_alert_time = now
        
        # Log alert
        self.logger.warning(
            f"⚠️ MODEL DRIFT DETECTED: "
            f"Accuracy dropped {drift_info['drop_percent']:.1f}% "
            f"(baseline: {drift_info['baseline_accuracy']:.2%}, "
            f"current: {drift_info['current_accuracy']:.2%}, "
            f"rolling: {drift_info['rolling_accuracy']:.2%})"
        )
        
        # In production, would send to alerting system (PagerDuty, Slack, etc.)
        # For now, just log
    
    def update_baseline(self, new_baseline: float) -> None:
        """
        Update baseline accuracy.
        
        Args:
            new_baseline: New baseline accuracy
        """
        self.baseline_accuracy = new_baseline
        self.logger.info(f"Updated baseline accuracy to {new_baseline:.2%}")
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get current drift detector status.
        
        Returns:
            Dictionary with status information
        """
        rolling_accuracy = sum(
            p["accuracy"] for p in self._accuracy_window
        ) / len(self._accuracy_window) if len(self._accuracy_window) > 0 else 0.0
        
        return {
            "baseline_accuracy": self.baseline_accuracy,
            "rolling_accuracy": rolling_accuracy,
            "drift_detected": self._drift_detected,
            "window_size": len(self._accuracy_window),
            "last_alert": self._last_alert_time.isoformat() if self._last_alert_time else None,
        }


# ============================================================================
# Global Metrics Instance
# ============================================================================

# Global metrics instance (singleton)
_metrics: Optional[PredictionMetrics] = None
_drift_detector: Optional[ModelDriftDetector] = None


def get_prediction_metrics() -> PredictionMetrics:
    """Get global PredictionMetrics instance."""
    global _metrics
    if _metrics is None:
        _metrics = PredictionMetrics()
    return _metrics


def get_drift_detector() -> ModelDriftDetector:
    """Get global ModelDriftDetector instance."""
    global _drift_detector
    if _drift_detector is None:
        _drift_detector = ModelDriftDetector()
    return _drift_detector

