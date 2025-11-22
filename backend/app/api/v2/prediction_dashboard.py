"""
Prediction monitoring dashboard endpoint.

Provides comprehensive metrics and monitoring for predictive cache warming.
"""

from __future__ import annotations

import logging
from collections import Counter
from typing import Any, Dict

from fastapi import APIRouter, Request

from app.api.v2.base import get_database_session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/monitoring/dashboard", tags=["monitoring-dashboard"])

# Try to import prediction monitoring (optional)
try:
    from app.services.prediction_monitor import get_prediction_metrics, get_drift_detector
    from app.services.predictive_cache_warmer import PredictiveCacheWarmer
    HAS_PREDICTION_MONITOR = True
except ImportError:
    HAS_PREDICTION_MONITOR = False
    get_prediction_metrics = None
    get_drift_detector = None
    PredictiveCacheWarmer = None


@router.get("/predictions")
async def get_prediction_dashboard(
    request: Request,
) -> Dict[str, Any]:
    """
    Get comprehensive prediction monitoring dashboard data.
    
    Returns:
        Dictionary with prediction metrics, trends, and model info
    """
    if not HAS_PREDICTION_MONITOR:
        return {
            "error": "Prediction monitoring not available",
            "current_accuracy": 0.0,
            "accuracy_trend": [],
            "top_predicted_games": [],
            "model_info": {},
            "cache_metrics": {},
        }
    
    try:
        metrics = get_prediction_metrics()
        drift_detector = get_drift_detector()
        
        # Get current accuracy
        current_accuracy = metrics.get_current_accuracy()
        
        # Get accuracy trend (last 24 hours)
        accuracy_trend = metrics.get_accuracy_trend(minutes=1440)
        
        # Get top predicted games (from recent predictions)
        top_predicted_games = []
        if hasattr(metrics, '_recent_predictions'):
            predicted_counts = Counter(
                p["predicted_game_id"]
                for p in metrics._recent_predictions
                if p.get("evaluated", False)
            )
            
            # Calculate hit rates
            for game_id, count in predicted_counts.most_common(10):
                # Count correct predictions for this game
                correct = sum(
                    1 for p in metrics._recent_predictions
                    if p.get("predicted_game_id") == game_id
                    and p.get("evaluated", False)
                    and p.get("predicted_game_id") == p.get("actual_game_id")
                )
                hit_rate = correct / count if count > 0 else 0.0
                
                top_predicted_games.append({
                    "game_id": game_id,
                    "prediction_count": count,
                    "hit_rate": round(hit_rate, 2),
                })
        
        # Get model info (try to get from analyzer if available)
        model_info = {
            "last_trained": None,
            "training_samples": 0,
            "feature_count": 24,  # Default feature count
        }
        
        # Try to get from app state
        predictive_warmer = getattr(request.app.state, "predictive_cache_warmer", None)
        if predictive_warmer and hasattr(predictive_warmer, "analyzer"):
            analyzer = predictive_warmer.analyzer
            if analyzer.model is not None:
                model_info["feature_count"] = analyzer.model.n_features_in_ if hasattr(analyzer.model, 'n_features_in_') else 24
        
        # Get cache metrics
        cache_metrics = {
            "hit_rate_with_prediction": 0.0,
            "hit_rate_without_prediction": 0.0,
            "improvement": "0%",
        }
        
        # Try to get cache hit improvement
        if hasattr(metrics, 'cache_hit_improvement'):
            try:
                # Check if prometheus_client is available
                try:
                    from prometheus_client import HAS_PROMETHEUS
                except:
                    HAS_PROMETHEUS = False
                
                if HAS_PROMETHEUS and hasattr(metrics.cache_hit_improvement, '_value'):
                    improvement = metrics.cache_hit_improvement._value.get()
                else:
                    improvement = 0.0
                
                cache_metrics["improvement"] = f"+{improvement:.1f}%" if improvement > 0 else f"{improvement:.1f}%"
            except Exception:
                pass
        
        # Get drift detection status
        drift_status = drift_detector.get_status() if drift_detector else {}
        
        return {
            "current_accuracy": round(current_accuracy, 3),
            "accuracy_trend": accuracy_trend,
            "top_predicted_games": top_predicted_games,
            "model_info": model_info,
            "cache_metrics": cache_metrics,
            "drift_detection": drift_status,
            "summary": metrics.get_summary(),
        }
        
    except Exception as exc:
        logger.error(f"Failed to get prediction dashboard: {exc}", exc_info=True)
        return {
            "error": str(exc),
            "current_accuracy": 0.0,
            "accuracy_trend": [],
            "top_predicted_games": [],
            "model_info": {},
            "cache_metrics": {},
        }

