"""
Simple Predictor wrapper for compatibility with existing code.

This provides a simple interface that wraps EnhancedShoe functionality
for prediction purposes.
"""
from __future__ import annotations

from typing import Dict, List
from datetime import datetime

from .engine import EnhancedShoe, Outcome
from .roadmap import generate_roadmaps


class Predictor:
    """
    Simple predictor that tracks history and makes predictions.
    
    This is a lightweight wrapper that maintains history and uses
    pattern detection for predictions.
    """
    
    def __init__(self):
        self.history: List[str] = []
        self.prediction_hits = 0
        self.total_predictions = 0
    
    def add(self, result: str) -> None:
        """Add a result to history."""
        if result in ["B", "P", "T"]:
            self.history.append(result)
    
    def predict(self) -> Dict:
        """
        Generate a prediction based on current history.
        
        Returns:
            Dictionary with prediction data
        """
        if not self.history:
            # Default prediction when no history
            return {
                "recommend": "B",
                "confidence": 0.50,
                "edge_pct": 0.0,
                "pattern": "No pattern detected",
                "true_count": 0.0,
                "next_suggested": "B",
            }
        
        # Simple pattern-based prediction
        recent = self.history[-10:] if len(self.history) >= 10 else self.history
        banker_count = recent.count("B")
        player_count = recent.count("P")
        
        # Calculate confidence based on pattern strength
        total = len(recent)
        if total > 0:
            banker_pct = banker_count / total
            player_pct = player_count / total
            
            if banker_pct > 0.6:
                recommend = "B"
                confidence = min(0.5 + (banker_pct - 0.5) * 2, 0.95)
                pattern = "Banker streak"
            elif player_pct > 0.6:
                recommend = "P"
                confidence = min(0.5 + (player_pct - 0.5) * 2, 0.95)
                pattern = "Player streak"
            else:
                # Use last result as indicator
                last_result = self.history[-1]
                if last_result == "B":
                    recommend = "P"  # Alternation tendency
                    confidence = 0.55
                    pattern = "Alternation pattern"
                elif last_result == "P":
                    recommend = "B"
                    confidence = 0.55
                    pattern = "Alternation pattern"
                else:
                    recommend = "B"  # Default to banker
                    confidence = 0.50
                    pattern = "No clear pattern"
        else:
            recommend = "B"
            confidence = 0.50
            pattern = "Insufficient data"
        
        # Calculate edge (simplified)
        edge_pct = (confidence - 0.5) * 2.0
        
        return {
            "recommend": recommend,
            "confidence": round(confidence, 2),
            "edge_pct": round(edge_pct, 2),
            "pattern": pattern,
            "true_count": 0.0,  # Would need EnhancedShoe for real counting
            "next_suggested": recommend,
        }
    
    def reset(self) -> None:
        """Reset predictor state."""
        self.history.clear()
        self.prediction_hits = 0
        self.total_predictions = 0

