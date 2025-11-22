"""
Prediction API endpoints.

Endpoints for getting predictions and accuracy metrics.
"""
from __future__ import annotations

from collections import Counter
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.v2.base import NotFoundError, SuccessResponse, get_database_session
from app.core.predictor import Predictor
from app.ml.inference import get_inference_engine, MLInferenceEngine
from app.models.database import GameResult
from app.models.schemas import (
    AccuracyMetricsResponse,
    ConfidenceScoresResponse,
    PredictRequest,
    PredictionResponse,
)

router = APIRouter(prefix="/predictions", tags=["predictions"])


def get_predictor(request: Request) -> Predictor:
    """Get predictor from app state."""
    if not hasattr(request.app.state, "predictor"):
        request.app.state.predictor = Predictor()
    return request.app.state.predictor


def get_ml_inference_engine(request: Request) -> MLInferenceEngine:
    """Get ML inference engine from app state."""
    if not hasattr(request.app.state, "ml_inference_engine"):
        # Try to load model from default path
        model_path = "ml-training/models"
        request.app.state.ml_inference_engine = get_inference_engine(model_path=model_path)
    return request.app.state.ml_inference_engine


@router.post("/predict", response_model=PredictionResponse)
async def get_prediction(
    request: Request,
    payload: PredictRequest,
    use_ml: bool = Query(False, description="Use ML model for prediction"),
    db: Session = Depends(get_database_session),
) -> PredictionResponse:
    """
    Get current prediction.
    
    Args:
        payload: Prediction request (optional shoe_id)
        use_ml: Whether to use ML model (default: False, uses simple predictor)
        db: Database session
        
    Returns:
        Current prediction
    """
    # Get historical outcomes
    results = db.query(GameResult).order_by(GameResult.timestamp.asc()).all()
    outcomes = [r.result for r in results] if results else []
    
    if use_ml:
        # Use ML inference engine
        try:
            ml_engine = get_ml_inference_engine(request)
            if ml_engine.is_loaded:
                prediction_dict = ml_engine.predict(outcomes)
                # Convert to PredictionResponse format
                return PredictionResponse(
                    recommend=prediction_dict['recommend'],
                    confidence=prediction_dict['confidence'],
                    edge_pct=prediction_dict['edge_pct'],
                    pattern=prediction_dict['pattern'],
                    true_count=prediction_dict.get('true_count', 0.0),
                    next_suggested=prediction_dict['next_suggested'],
                    timestamp=prediction_dict.get('timestamp')
                )
        except Exception as e:
            # Fallback to simple predictor if ML fails
            print(f"ML prediction failed, using fallback: {e}")
    
    # Use simple predictor
    predictor = get_predictor(request)
    predictor.history = outcomes  # Update history
    
    prediction = predictor.predict()
    
    # Add timestamp
    from datetime import datetime
    prediction["timestamp"] = datetime.utcnow()
    
    return PredictionResponse(**prediction)


@router.get("/accuracy", response_model=AccuracyMetricsResponse)
async def get_accuracy_metrics(
    db: Session = Depends(get_database_session),
    shoe_id: Optional[str] = Query(None, description="Filter by shoe ID"),
) -> AccuracyMetricsResponse:
    """
    Get accuracy metrics for predictions.
    
    Args:
        db: Database session
        shoe_id: Optional shoe filter
        
    Returns:
        Accuracy metrics
    """
    # Get all results with predictions
    query = db.query(GameResult).filter(GameResult.prediction.isnot(None))
    
    results = query.order_by(GameResult.timestamp.desc()).limit(1000).all()
    
    if not results:
        return AccuracyMetricsResponse(
            total_predictions=0,
            correct_predictions=0,
            accuracy=0.0,
            banker_accuracy=0.0,
            player_accuracy=0.0,
            recent_accuracy=0.0,
            confidence_distribution={},
        )
    
    # Calculate accuracy
    total = len(results)
    correct = 0
    banker_correct = 0
    banker_total = 0
    player_correct = 0
    player_total = 0
    
    # Recent (last 50)
    recent_correct = 0
    recent_total = min(50, total)
    
    confidence_levels = Counter()
    
    for i, result in enumerate(results):
        if result.prediction and "recommend" in result.prediction:
            predicted = result.prediction["recommend"]
            actual = result.result
            
            # Skip ties for accuracy calculation
            if actual != "T":
                if predicted == actual:
                    correct += 1
                    if i < recent_total:
                        recent_correct += 1
                
                if predicted == "B":
                    banker_total += 1
                    if actual == "B":
                        banker_correct += 1
                elif predicted == "P":
                    player_total += 1
                    if actual == "P":
                        player_correct += 1
                
                # Track confidence distribution
                if "confidence" in result.prediction:
                    conf = result.prediction["confidence"]
                    if conf < 0.5:
                        confidence_levels["low"] += 1
                    elif conf < 0.7:
                        confidence_levels["medium"] += 1
                    else:
                        confidence_levels["high"] += 1
    
    non_tie_total = sum(1 for r in results if r.result != "T")
    
    return AccuracyMetricsResponse(
        total_predictions=non_tie_total,
        correct_predictions=correct,
        accuracy=round((correct / non_tie_total * 100), 2) if non_tie_total > 0 else 0.0,
        banker_accuracy=round((banker_correct / banker_total * 100), 2) if banker_total > 0 else 0.0,
        player_accuracy=round((player_correct / player_total * 100), 2) if player_total > 0 else 0.0,
        recent_accuracy=round((recent_correct / recent_total * 100), 2) if recent_total > 0 else 0.0,
        confidence_distribution=dict(confidence_levels),
    )


@router.get("/confidence", response_model=ConfidenceScoresResponse)
async def get_confidence_scores(
    db: Session = Depends(get_database_session),
    limit: int = Query(100, ge=1, le=1000, description="Number of results to analyze"),
) -> ConfidenceScoresResponse:
    """
    Get confidence score statistics.
    
    Args:
        db: Database session
        limit: Number of recent results to analyze
        
    Returns:
        Confidence score statistics
    """
    results = (
        db.query(GameResult)
        .filter(GameResult.prediction.isnot(None))
        .order_by(GameResult.timestamp.desc())
        .limit(limit)
        .all()
    )
    
    if not results:
        return ConfidenceScoresResponse(
            current_confidence=0.5,
            average_confidence=0.5,
            confidence_history=[],
            confidence_by_outcome={},
        )
    
    confidences = []
    confidence_by_outcome = {"B": [], "P": [], "T": []}
    
    for result in results:
        if result.prediction and "confidence" in result.prediction:
            conf = result.prediction["confidence"]
            confidences.append(conf)
            confidence_by_outcome[result.result].append(conf)
    
    # Get current (most recent)
    current = confidences[0] if confidences else 0.5
    
    # Calculate averages
    avg = sum(confidences) / len(confidences) if confidences else 0.5
    avg_by_outcome = {
        outcome: sum(confs) / len(confs) if confs else 0.5
        for outcome, confs in confidence_by_outcome.items()
    }
    
    return ConfidenceScoresResponse(
        current_confidence=round(current, 3),
        average_confidence=round(avg, 3),
        confidence_history=[round(c, 3) for c in confidences[:50]],  # Last 50
        confidence_by_outcome={k: round(v, 3) for k, v in avg_by_outcome.items()},
    )

