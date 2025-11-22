"""
ML module for Baccarat prediction.

This module provides:
- LSTM model implementation
- Feature engineering
- Inference engine
- Model training pipeline
- Model versioning
"""

from .model import LSTMPredictor, FeatureEngineer, create_model
from .inference import MLInferenceEngine, get_inference_engine, ConfidenceCalibrator, ABTestManager
from .trainer import ModelTrainer, prepare_training_data, calculate_metrics
from .versioning import ModelVersionManager, ModelVersion

__all__ = [
    'LSTMPredictor',
    'FeatureEngineer',
    'create_model',
    'MLInferenceEngine',
    'get_inference_engine',
    'ConfidenceCalibrator',
    'ABTestManager',
    'ModelTrainer',
    'prepare_training_data',
    'calculate_metrics',
    'ModelVersionManager',
    'ModelVersion',
]
