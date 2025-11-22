"""
Real-time ML inference system for Baccarat predictions.

This module provides:
- Real-time prediction
- Confidence calibration
- A/B testing framework
- Model versioning integration
"""
from __future__ import annotations

import os
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
import numpy as np

from .model import LSTMPredictor, FeatureEngineer
from .versioning import ModelVersionManager


# ==================== CONFIDENCE CALIBRATION ====================

class ConfidenceCalibrator:
    """
    Calibrate prediction confidence scores.
    
    Uses Platt scaling or temperature scaling to improve
    confidence calibration.
    """
    
    def __init__(self, method: str = 'temperature'):
        """
        Initialize calibrator.
        
        Args:
            method: Calibration method ('temperature' or 'platt')
        """
        self.method = method
        self.temperature = 1.0
        self.is_fitted = False
    
    def fit(self, probabilities: np.ndarray, labels: np.ndarray) -> None:
        """
        Fit calibrator on validation data.
        
        Args:
            probabilities: Predicted probabilities
            labels: True labels
        """
        if self.method == 'temperature':
            # Temperature scaling
            # Find optimal temperature using validation set
            try:
                from scipy.optimize import minimize_scalar
                
                def objective(temp):
                    scaled_probs = probabilities ** (1.0 / temp)
                    scaled_probs = scaled_probs / scaled_probs.sum(axis=1, keepdims=True)
                    # Calculate negative log likelihood
                    nll = -np.mean(np.log(scaled_probs[np.arange(len(labels)), labels] + 1e-10))
                    return nll
                
                result = minimize_scalar(objective, bounds=(0.1, 10.0), method='bounded')
                self.temperature = result.x
            except ImportError:
                # Fallback: use default temperature
                self.temperature = 1.0
        else:
            # Platt scaling (simplified)
            self.temperature = 1.0
        
        self.is_fitted = True
    
    def calibrate(self, probabilities: np.ndarray) -> np.ndarray:
        """
        Calibrate probabilities.
        
        Args:
            probabilities: Raw probabilities
            
        Returns:
            Calibrated probabilities
        """
        if not self.is_fitted:
            return probabilities
        
        if self.method == 'temperature':
            # Apply temperature scaling
            scaled = probabilities ** (1.0 / self.temperature)
            scaled = scaled / scaled.sum(axis=1, keepdims=True)
            return scaled
        else:
            return probabilities


# ==================== A/B TESTING FRAMEWORK ====================

class ABTestManager:
    """
    A/B testing framework for comparing model versions.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize A/B test manager.
        
        Args:
            config_path: Path to A/B test configuration
        """
        self.config_path = config_path
        self.tests: Dict[str, Dict[str, Any]] = {}
        self.results: Dict[str, Dict[str, Any]] = {}
        self._load_config()
    
    def _load_config(self) -> None:
        """Load A/B test configuration."""
        if self.config_path and os.path.exists(self.config_path):
            with open(self.config_path, 'r') as f:
                config = json.load(f)
                self.tests = config.get('tests', {})
        else:
            # Default: no active tests
            self.tests = {}
    
    def get_variant(
        self,
        test_name: str,
        user_id: Optional[str] = None
    ) -> str:
        """
        Get A/B test variant for user.
        
        Args:
            test_name: Name of A/B test
            user_id: Optional user ID for consistent assignment
            
        Returns:
            Variant name ('A' or 'B')
        """
        if test_name not in self.tests:
            return 'A'  # Default to control
        
        test_config = self.tests[test_name]
        if not test_config.get('active', False):
            return 'A'
        
        # Simple hash-based assignment for consistency
        if user_id:
            import hashlib
            hash_val = int(hashlib.md5(f"{test_name}_{user_id}".encode()).hexdigest(), 16)
            return 'B' if (hash_val % 100) < test_config.get('traffic_percent_b', 50) else 'A'
        else:
            # Random assignment
            import random
            return 'B' if random.random() * 100 < test_config.get('traffic_percent_b', 50) else 'A'
    
    def record_result(
        self,
        test_name: str,
        variant: str,
        prediction: str,
        actual: str,
        confidence: float
    ) -> None:
        """
        Record A/B test result.
        
        Args:
            test_name: Name of A/B test
            variant: Variant ('A' or 'B')
            prediction: Predicted outcome
            actual: Actual outcome
            confidence: Prediction confidence
        """
        if test_name not in self.results:
            self.results[test_name] = {
                'A': {'correct': 0, 'total': 0, 'avg_confidence': []},
                'B': {'correct': 0, 'total': 0, 'avg_confidence': []}
            }
        
        variant_results = self.results[test_name][variant]
        variant_results['total'] += 1
        variant_results['avg_confidence'].append(confidence)
        
        if prediction == actual:
            variant_results['correct'] += 1
    
    def get_test_results(self, test_name: str) -> Dict[str, Any]:
        """
        Get A/B test results.
        
        Args:
            test_name: Name of A/B test
            
        Returns:
            Test results dictionary
        """
        if test_name not in self.results:
            return {}
        
        results = self.results[test_name]
        summary = {}
        
        for variant in ['A', 'B']:
            variant_data = results[variant]
            total = variant_data['total']
            if total > 0:
                accuracy = variant_data['correct'] / total
                avg_conf = np.mean(variant_data['avg_confidence']) if variant_data['avg_confidence'] else 0.0
                summary[variant] = {
                    'accuracy': accuracy,
                    'total_predictions': total,
                    'correct': variant_data['correct'],
                    'average_confidence': float(avg_conf)
                }
            else:
                summary[variant] = {
                    'accuracy': 0.0,
                    'total_predictions': 0,
                    'correct': 0,
                    'average_confidence': 0.0
                }
        
        return summary


# ==================== INFERENCE ENGINE ====================

class MLInferenceEngine:
    """
    Real-time ML inference engine for Baccarat predictions.
    
    Handles model loading, prediction, and confidence calibration.
    """
    
    def __init__(
        self,
        model_path: Optional[str] = None,
        version_manager: Optional[ModelVersionManager] = None,
        enable_calibration: bool = True,
        enable_ab_testing: bool = False
    ):
        """
        Initialize inference engine.
        
        Args:
            model_path: Path to model file
            version_manager: Model version manager
            enable_calibration: Enable confidence calibration
            enable_ab_testing: Enable A/B testing
        """
        self.model: Optional[LSTMPredictor] = None
        self.version_manager = version_manager or ModelVersionManager()
        self.calibrator = ConfidenceCalibrator() if enable_calibration else None
        self.ab_manager = ABTestManager() if enable_ab_testing else None
        self.model_version: Optional[str] = None
        self.is_loaded = False
        
        if model_path:
            self.load_model(model_path)
    
    def load_model(self, model_path: Optional[str] = None, version: Optional[str] = None) -> bool:
        """
        Load ML model.
        
        Args:
            model_path: Path to model file
            version: Model version to load
            
        Returns:
            True if loaded successfully
        """
        try:
            if version:
                # Load specific version
                model_path = self.version_manager.get_model_path(version)
            
            if not model_path or not os.path.exists(f"{model_path}.h5"):
                # Try to load latest version
                latest_version = self.version_manager.get_latest_version()
                if latest_version:
                    model_path = self.version_manager.get_model_path(latest_version)
                else:
                    return False
            
            self.model = LSTMPredictor()
            self.model.load(model_path)
            self.model_version = version or self.version_manager.get_latest_version()
            self.is_loaded = True
            
            return True
        except Exception as e:
            print(f"Error loading model: {e}")
            return False
    
    def predict(
        self,
        outcomes: List[str],
        user_id: Optional[str] = None,
        ab_test_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Make prediction from outcomes.
        
        Args:
            outcomes: List of historical outcomes
            user_id: Optional user ID for A/B testing
            ab_test_name: Optional A/B test name
            
        Returns:
            Prediction dictionary
        """
        if not self.is_loaded or self.model is None:
            # Fallback to simple prediction
            return self._fallback_predict(outcomes)
        
        # Get A/B test variant if enabled
        variant = None
        if self.ab_manager and ab_test_name:
            variant = self.ab_manager.get_variant(ab_test_name, user_id)
            # Could load different model version based on variant
            # For now, use same model
        
        # Make prediction
        prediction, confidence, probabilities = self.model.predict(outcomes)
        
        # Calibrate confidence if enabled
        if self.calibrator and self.calibrator.is_fitted:
            calibrated_probs = self.calibrator.calibrate(probabilities.reshape(1, -1))
            confidence = float(np.max(calibrated_probs))
            probabilities = calibrated_probs[0]
        
        # Calculate edge
        edge_pct = (confidence - 0.5) * 2.0
        
        # Determine pattern
        pattern = self._detect_pattern(outcomes)
        
        return {
            'recommend': prediction,
            'confidence': round(confidence, 4),
            'edge_pct': round(edge_pct, 4),
            'pattern': pattern,
            'true_count': 0.0,  # Would need shoe state
            'next_suggested': prediction,
            'probabilities': {
                'banker': float(probabilities[0]),
                'player': float(probabilities[1])
            },
            'model_version': self.model_version,
            'ab_variant': variant,
            'timestamp': datetime.utcnow()
        }
    
    def update_prediction_result(
        self,
        prediction: str,
        actual: str,
        confidence: float,
        ab_test_name: Optional[str] = None,
        variant: Optional[str] = None
    ) -> None:
        """
        Update prediction result for tracking.
        
        Args:
            prediction: Predicted outcome
            actual: Actual outcome
            confidence: Prediction confidence
            ab_test_name: A/B test name
            variant: A/B test variant
        """
        if self.ab_manager and ab_test_name and variant:
            self.ab_manager.record_result(
                ab_test_name,
                variant,
                prediction,
                actual,
                confidence
            )
    
    def _fallback_predict(self, outcomes: List[str]) -> Dict[str, Any]:
        """
        Fallback prediction when model not loaded.
        
        Args:
            outcomes: List of outcomes
            
        Returns:
            Simple prediction
        """
        if not outcomes:
            return {
                'recommend': 'B',
                'confidence': 0.5,
                'edge_pct': 0.0,
                'pattern': 'No data',
                'true_count': 0.0,
                'next_suggested': 'B',
                'model_version': None,
                'timestamp': datetime.utcnow()
            }
        
        recent = outcomes[-10:] if len(outcomes) >= 10 else outcomes
        banker_count = recent.count('B')
        player_count = recent.count('P')
        total = len([o for o in recent if o != 'T'])
        
        if total > 0:
            banker_pct = banker_count / total
            if banker_pct > 0.5:
                recommend = 'B'
                confidence = min(0.5 + (banker_pct - 0.5) * 2, 0.9)
            else:
                recommend = 'P'
                confidence = min(0.5 + (0.5 - banker_pct) * 2, 0.9)
        else:
            recommend = 'B'
            confidence = 0.5
        
        return {
            'recommend': recommend,
            'confidence': round(confidence, 4),
            'edge_pct': round((confidence - 0.5) * 2.0, 4),
            'pattern': 'Simple pattern',
            'true_count': 0.0,
            'next_suggested': recommend,
            'model_version': None,
            'timestamp': datetime.utcnow()
        }
    
    def _detect_pattern(self, outcomes: List[str]) -> str:
        """
        Detect pattern in outcomes.
        
        Args:
            outcomes: List of outcomes
            
        Returns:
            Pattern description
        """
        if len(outcomes) < 3:
            return 'Insufficient data'
        
        recent = outcomes[-10:] if len(outcomes) >= 10 else outcomes
        no_ties = [o for o in recent if o != 'T']
        
        if len(no_ties) < 3:
            return 'Insufficient data'
        
        # Check for streaks
        last_result = no_ties[-1]
        streak_length = 1
        for i in range(len(no_ties) - 2, -1, -1):
            if no_ties[i] == last_result:
                streak_length += 1
            else:
                break
        
        if streak_length >= 3:
            return f'{last_result} streak ({streak_length})'
        
        # Check for alternation
        alternations = sum(1 for i in range(1, len(no_ties)) if no_ties[i] != no_ties[i-1])
        if alternations / len(no_ties) > 0.7:
            return 'Alternating pattern'
        
        return 'No clear pattern'


# ==================== SINGLETON INSTANCE ====================

_inference_engine: Optional[MLInferenceEngine] = None


def get_inference_engine(
    model_path: Optional[str] = None,
    reload: bool = False
) -> MLInferenceEngine:
    """
    Get or create inference engine singleton.
    
    Args:
        model_path: Path to model file
        reload: Force reload model
        
    Returns:
        MLInferenceEngine instance
    """
    global _inference_engine
    
    if _inference_engine is None or reload:
        _inference_engine = MLInferenceEngine(model_path=model_path)
    
    return _inference_engine

