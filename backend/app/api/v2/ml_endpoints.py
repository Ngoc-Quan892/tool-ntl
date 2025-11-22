"""
FastAPI endpoints for ML predictions.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
import logging

from app.ml.predictor import BaccaratPredictor, get_predictor
from app.services.authentication import get_current_user, get_optional_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ml", tags=["Machine Learning"])


class PredictionRequest(BaseModel):
    shoe_state: Dict = Field(..., description="Current shoe state")
    history: List[str] = Field(..., description="Outcome history")
    use_cache: bool = Field(True, description="Whether to use cache")


class PredictionResponse(BaseModel):
    recommendation: str
    probabilities: Dict[str, float]
    confidence: float
    calibrated_confidence: float
    edge_pct: float
    kelly_bet_fraction: float
    ensemble_size: int
    model_used: str
    inference_time_ms: float
    from_cache: bool
    timestamp: str


class FeedbackRequest(BaseModel):
    prediction: Dict = Field(..., description="Original prediction dictionary")
    actual_outcome: str = Field(..., description="Actual outcome (B/P/T)")


class PerformanceStats(BaseModel):
    predictions_made: int
    average_inference_time_ms: float
    cache_hit_rate_pct: float
    average_confidence: float
    recent_accuracy_pct: float
    accuracy_sample_size: int
    models_loaded: int
    ensemble_active: bool
    device: str
    calibrator_trained: bool


@router.post("/predict", response_model=PredictionResponse)
async def predict(
    request: PredictionRequest,
    user_id: Optional[str] = Depends(get_optional_user),
):
    """Make ML prediction for next hand."""
    try:
        predictor = get_predictor()
        prediction = await predictor.predict(request.shoe_state, request.history, request.use_cache)
        return PredictionResponse(**prediction)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Prediction error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Prediction failed")


@router.post("/feedback")
async def submit_feedback(
    request: FeedbackRequest,
    user_id: str = Depends(get_current_user),
):
    """Submit feedback to update calibrator & metrics."""
    try:
        predictor = get_predictor()
        if request.actual_outcome not in {"B", "P", "T"}:
            raise HTTPException(status_code=400, detail="Invalid outcome")
        predictor.update_accuracy(request.prediction, request.actual_outcome)
        return {
            "message": "Feedback recorded",
            "was_correct": request.prediction.get("recommendation") == request.actual_outcome,
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Feedback error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to record feedback")


@router.get("/stats", response_model=PerformanceStats)
async def get_performance_stats(
    user_id: Optional[str] = Depends(get_optional_user),
):
    """Return predictor performance statistics."""
    try:
        predictor = get_predictor()
        stats = predictor.get_performance_stats()
        return PerformanceStats(**stats)
    except Exception as exc:
        logger.error("Stats error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get statistics")


@router.post("/cache/clear")
async def clear_cache(
    user_id: str = Depends(get_current_user),
):
    """Clear prediction cache."""
    try:
        predictor = get_predictor()
        predictor.clear_cache()
        return {"message": "Cache cleared successfully"}
    except Exception as exc:
        logger.error("Cache clear error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to clear cache")


@router.post("/models/reload")
async def reload_models(
    user_id: str = Depends(get_current_user),
):
    """Reload models from disk."""
    try:
        predictor = get_predictor()
        predictor.reload_models()
        stats = predictor.get_performance_stats()
        return {
            "message": "Models reloaded successfully",
            "models_loaded": stats["models_loaded"],
            "ensemble_active": stats["ensemble_active"],
        }
    except Exception as exc:
        logger.error("Model reload error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to reload models")


@router.get("/health")
async def ml_health_check():
    """Health check endpoint for ML subsystem."""
    try:
        predictor = get_predictor()
        stats = predictor.get_performance_stats()
        status = "healthy"
        issues = []
        if stats["models_loaded"] == 0:
            status = "degraded"
            issues.append("No models loaded - fallback mode")
        if stats["average_inference_time_ms"] > 100:
            status = "degraded"
            issues.append("High inference latency")
        return {
            "status": status,
            "models_loaded": stats["models_loaded"],
            "ensemble_active": stats["ensemble_active"],
            "device": stats["device"],
            "issues": issues,
        }
    except Exception as exc:
        logger.error("ML health check error: %s", exc, exc_info=True)
        return {"status": "unhealthy", "error": str(exc)}


