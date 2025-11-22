"""
Automated hyperparameter tuning and model optimization service.

This module provides:
- Grid search for optimal hyperparameters
- Cross-validation
- Feature selection (remove low-importance features)
- Model comparison (RF vs XGBoost vs LightGBM)
- Online learning updates
- Model versioning
- Feature importance analysis
"""

from __future__ import annotations

import json
import logging
import pickle
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, asdict

import numpy as np
import pandas as pd

try:
    from sklearn.model_selection import GridSearchCV, cross_val_score, StratifiedKFold
    from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
    from sklearn.linear_model import SGDClassifier
    from sklearn.metrics import (
        accuracy_score, precision_score, recall_score, f1_score,
        classification_report, confusion_matrix
    )
    from sklearn.preprocessing import StandardScaler
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    GridSearchCV = None
    cross_val_score = None
    RandomForestClassifier = None
    GradientBoostingClassifier = None
    SGDClassifier = None

try:
    import xgboost as xgb
    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False
    xgb = None

try:
    import lightgbm as lgb
    LIGHTGBM_AVAILABLE = True
except ImportError:
    LIGHTGBM_AVAILABLE = False
    lgb = None

from app.ml.versioning import ModelVersionManager, ModelVersion
from app.ml.config import ModelConfig

logger = logging.getLogger(__name__)


@dataclass
class TuningResult:
    """Results from hyperparameter tuning."""
    best_params: Dict[str, Any]
    best_score: float
    cv_scores: List[float]
    model_type: str
    training_time: float
    feature_names: List[str]


@dataclass
class ModelComparisonResult:
    """Results from model comparison."""
    model_name: str
    accuracy: float
    precision: float
    recall: float
    f1_score: float
    training_time: float
    prediction_time: float
    params: Dict[str, Any]


@dataclass
class FeatureImportance:
    """Feature importance information."""
    name: str
    importance: float
    rank: int


class ModelTuner:
    """
    Automated hyperparameter tuning and model optimization.
    
    Provides:
    - Grid search for optimal parameters
    - Cross-validation
    - Feature selection
    - Model comparison
    - Online learning updates
    - Model versioning
    """
    
    def __init__(
        self,
        model_dir: Optional[Path] = None,
        registry_path: Optional[str] = None,
        min_feature_importance: float = 0.01,
        online_learning_threshold: int = 1000,
    ):
        """
        Initialize ModelTuner.
        
        Args:
            model_dir: Directory to save models
            registry_path: Path to model version registry
            min_feature_importance: Minimum importance to keep feature
            online_learning_threshold: Number of new samples before retraining
        """
        if not SKLEARN_AVAILABLE:
            raise ImportError("scikit-learn is required for ModelTuner")
        
        self.model_dir = model_dir or Path("./ml-training/models")
        self.model_dir.mkdir(parents=True, exist_ok=True)
        
        self.registry_path = registry_path or str(self.model_dir / "registry.json")
        self.version_manager = ModelVersionManager(self.registry_path)
        
        self.min_feature_importance = min_feature_importance
        self.online_learning_threshold = online_learning_threshold
        
        # Online learning state
        self.online_model: Optional[SGDClassifier] = None
        self.online_scaler: Optional[StandardScaler] = None
        self.new_samples_buffer: List[Tuple[np.ndarray, int]] = []
        self.last_training_time: Optional[datetime] = None
        
        # Current model state
        self.current_model = None
        self.current_scaler = None
        self.feature_names: List[str] = []
        self.selected_features: List[str] = []
        
        logger.info("ModelTuner initialized")
    
    async def tune_hyperparameters(
        self,
        X: np.ndarray,
        y: np.ndarray,
        model_type: str = "random_forest",
        param_grid: Optional[Dict[str, List[Any]]] = None,
        cv: int = 5,
        scoring: str = "f1_weighted",
        n_jobs: int = -1,
        feature_names: Optional[List[str]] = None,
    ) -> TuningResult:
        """
        Find optimal hyperparameters using grid search.
        
        Args:
            X: Feature matrix
            y: Target labels
            model_type: Type of model ('random_forest', 'xgboost', 'lightgbm', 'gradient_boosting')
            param_grid: Parameter grid for search. If None, uses default grid
            cv: Number of cross-validation folds
            scoring: Scoring metric
            n_jobs: Number of parallel jobs
            feature_names: Names of features (for tracking)
            
        Returns:
            TuningResult with best parameters and scores
        """
        if feature_names is None:
            feature_names = [f"feature_{i}" for i in range(X.shape[1])]
        
        self.feature_names = feature_names
        
        logger.info(f"Starting hyperparameter tuning for {model_type}")
        start_time = datetime.utcnow()
        
        # Get base model
        base_model = self._get_base_model(model_type)
        
        # Get default param grid if not provided
        if param_grid is None:
            param_grid = self._get_default_param_grid(model_type)
        
        # Perform grid search
        grid_search = GridSearchCV(
            base_model,
            param_grid,
            cv=cv,
            scoring=scoring,
            n_jobs=n_jobs,
            verbose=1,
            return_train_score=True,
        )
        
        grid_search.fit(X, y)
        
        training_time = (datetime.utcnow() - start_time).total_seconds()
        
        # Get cross-validation scores
        cv_scores = cross_val_score(
            grid_search.best_estimator_,
            X,
            y,
            cv=cv,
            scoring=scoring,
        )
        
        result = TuningResult(
            best_params=grid_search.best_params_,
            best_score=grid_search.best_score_,
            cv_scores=cv_scores.tolist(),
            model_type=model_type,
            training_time=training_time,
            feature_names=feature_names,
        )
        
        # Store best model
        self.current_model = grid_search.best_estimator_
        
        logger.info(
            f"Tuning complete. Best score: {result.best_score:.4f}, "
            f"Best params: {result.best_params}"
        )
        
        return result
    
    async def compare_models(
        self,
        X: np.ndarray,
        y: np.ndarray,
        models_to_compare: Optional[List[str]] = None,
        cv: int = 5,
        feature_names: Optional[List[str]] = None,
    ) -> List[ModelComparisonResult]:
        """
        Compare different ML algorithms.
        
        Args:
            X: Feature matrix
            y: Target labels
            models_to_compare: List of model types to compare.
                              Options: 'random_forest', 'xgboost', 'lightgbm', 'gradient_boosting'
            cv: Number of cross-validation folds
            feature_names: Names of features
            
        Returns:
            List of ModelComparisonResult for each model
        """
        if models_to_compare is None:
            models_to_compare = ["random_forest", "gradient_boosting"]
            if XGBOOST_AVAILABLE:
                models_to_compare.append("xgboost")
            if LIGHTGBM_AVAILABLE:
                models_to_compare.append("lightgbm")
        
        if feature_names is None:
            feature_names = [f"feature_{i}" for i in range(X.shape[1])]
        
        logger.info(f"Comparing models: {models_to_compare}")
        
        results = []
        skf = StratifiedKFold(n_splits=cv, shuffle=True, random_state=42)
        
        for model_type in models_to_compare:
            try:
                logger.info(f"Evaluating {model_type}")
                start_time = datetime.utcnow()
                
                # Get model with default params
                model = self._get_base_model(model_type)
                
                # Train model
                model.fit(X, y)
                training_time = (datetime.utcnow() - start_time).total_seconds()
                
                # Cross-validation
                cv_scores = cross_val_score(model, X, y, cv=skf, scoring='f1_weighted')
                
                # Prediction time
                pred_start = datetime.utcnow()
                y_pred = model.predict(X)
                prediction_time = (datetime.utcnow() - pred_start).total_seconds() / len(X)
                
                # Calculate metrics
                accuracy = accuracy_score(y, y_pred)
                precision = precision_score(y, y_pred, average='weighted', zero_division=0)
                recall = recall_score(y, y_pred, average='weighted', zero_division=0)
                f1 = f1_score(y, y_pred, average='weighted', zero_division=0)
                
                # Get model parameters
                params = model.get_params()
                
                result = ModelComparisonResult(
                    model_name=model_type,
                    accuracy=float(accuracy),
                    precision=float(precision),
                    recall=float(recall),
                    f1_score=float(f1),
                    training_time=training_time,
                    prediction_time=prediction_time,
                    params=params,
                )
                
                results.append(result)
                
                logger.info(
                    f"{model_type}: Accuracy={accuracy:.4f}, "
                    f"F1={f1:.4f}, Training time={training_time:.2f}s"
                )
                
            except Exception as exc:
                logger.error(f"Failed to evaluate {model_type}: {exc}")
                continue
        
        # Sort by F1 score
        results.sort(key=lambda x: x.f1_score, reverse=True)
        
        return results
    
    async def select_features(
        self,
        X: np.ndarray,
        y: np.ndarray,
        model: Optional[Any] = None,
        method: str = "importance",
        k: Optional[int] = None,
        feature_names: Optional[List[str]] = None,
    ) -> List[str]:
        """
        Select important features and remove low-importance ones.
        
        Args:
            X: Feature matrix
            y: Target labels
            model: Trained model to extract importances from. If None, trains a RandomForest
            method: Selection method ('importance' or 'mutual_info')
            k: Number of features to select (if None, uses min_feature_importance threshold)
            feature_names: Names of features
            
        Returns:
            List of selected feature names
        """
        if feature_names is None:
            feature_names = [f"feature_{i}" for i in range(X.shape[1])]
        
        logger.info(f"Selecting features using {method} method")
        
        if model is None:
            # Train a RandomForest to get feature importances
            model = RandomForestClassifier(n_estimators=100, random_state=42)
            model.fit(X, y)
        
        if method == "importance":
            # Get feature importances
            if hasattr(model, 'feature_importances_'):
                importances = model.feature_importances_
            elif hasattr(model, 'coef_'):
                # For linear models, use absolute coefficients
                importances = np.abs(model.coef_[0])
            else:
                logger.warning("Model doesn't have feature importances, using all features")
                self.selected_features = feature_names
                return feature_names
            
            # Create feature importance pairs
            feature_importance_pairs = list(zip(feature_names, importances))
            feature_importance_pairs.sort(key=lambda x: x[1], reverse=True)
            
            if k is not None:
                # Select top k features
                selected = [name for name, _ in feature_importance_pairs[:k]]
            else:
                # Select features above threshold
                selected = [
                    name for name, importance in feature_importance_pairs
                    if importance >= self.min_feature_importance
                ]
            
            self.selected_features = selected
            
            logger.info(
                f"Selected {len(selected)}/{len(feature_names)} features. "
                f"Removed {len(feature_names) - len(selected)} low-importance features"
            )
            
            return selected
        
        elif method == "mutual_info":
            from sklearn.feature_selection import SelectKBest, mutual_info_classif
            
            if k is None:
                k = max(1, int(len(feature_names) * 0.5))  # Select top 50% by default
            
            selector = SelectKBest(score_func=mutual_info_classif, k=k)
            X_selected = selector.fit_transform(X, y)
            
            selected_indices = selector.get_support(indices=True)
            selected = [feature_names[i] for i in selected_indices]
            
            self.selected_features = selected
            
            logger.info(f"Selected {len(selected)} features using mutual information")
            
            return selected
        
        else:
            raise ValueError(f"Unknown selection method: {method}")
    
    async def analyze_feature_importance(
        self,
        model: Optional[Any] = None,
        X: Optional[np.ndarray] = None,
        y: Optional[np.ndarray] = None,
        feature_names: Optional[List[str]] = None,
        visualize: bool = False,
    ) -> Dict[str, Any]:
        """
        Analyze feature importance from trained model.
        
        Args:
            model: Trained model. If None, trains a RandomForest
            X: Feature matrix (required if model is None)
            y: Target labels (required if model is None)
            feature_names: Names of features
            visualize: Whether to generate visualization (not implemented yet)
            
        Returns:
            Dictionary with feature importances and recommendations
        """
        if model is None:
            if X is None or y is None:
                raise ValueError("X and y required if model is not provided")
            model = RandomForestClassifier(n_estimators=100, random_state=42)
            model.fit(X, y)
        
        if feature_names is None:
            if hasattr(self, 'feature_names') and self.feature_names:
                feature_names = self.feature_names
            else:
                n_features = X.shape[1] if X is not None else len(model.feature_importances_)
                feature_names = [f"feature_{i}" for i in range(n_features)]
        
        # Get importances
        if hasattr(model, 'feature_importances_'):
            importances = model.feature_importances_
        elif hasattr(model, 'coef_'):
            importances = np.abs(model.coef_[0])
        else:
            logger.warning("Model doesn't have feature importances")
            return {
                "features": [],
                "recommendations": ["Model doesn't support feature importance analysis"]
            }
        
        # Create feature importance list
        feature_importance_pairs = list(zip(feature_names, importances))
        feature_importance_pairs.sort(key=lambda x: x[1], reverse=True)
        
        features = [
            {
                "name": name,
                "importance": float(importance),
                "rank": rank + 1,
            }
            for rank, (name, importance) in enumerate(feature_importance_pairs)
        ]
        
        # Generate recommendations
        recommendations = []
        low_importance_features = [
            name for name, importance in feature_importance_pairs
            if importance < self.min_feature_importance
        ]
        
        if low_importance_features:
            recommendations.append(
                f"Remove {len(low_importance_features)} low-importance features "
                f"(importance < {self.min_feature_importance}): "
                f"{', '.join(low_importance_features[:10])}"
                + ("..." if len(low_importance_features) > 10 else "")
            )
        
        # Top features
        top_features = [name for name, _ in feature_importance_pairs[:5]]
        recommendations.append(
            f"Top 5 most important features: {', '.join(top_features)}"
        )
        
        return {
            "features": features,
            "recommendations": recommendations,
            "total_features": len(features),
            "low_importance_count": len(low_importance_features),
        }
    
    async def update_model_incremental(
        self,
        X_new: np.ndarray,
        y_new: np.ndarray,
        retrain_threshold: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Update model with new data using online learning.
        
        Args:
            X_new: New feature matrix
            y_new: New target labels
            retrain_threshold: Number of samples before full retrain. 
                             If None, uses self.online_learning_threshold
            
        Returns:
            Dictionary with update results
        """
        if retrain_threshold is None:
            retrain_threshold = self.online_learning_threshold
        
        logger.info(f"Updating model with {len(X_new)} new samples")
        
        # Add to buffer
        for x, y in zip(X_new, y_new):
            self.new_samples_buffer.append((x, y))
        
        # Check if we should retrain
        if len(self.new_samples_buffer) >= retrain_threshold:
            logger.info(
                f"Buffer reached {len(self.new_samples_buffer)} samples. "
                "Performing full retrain"
            )
            return await self._full_retrain()
        else:
            # Incremental update using partial_fit
            return await self._incremental_update(X_new, y_new)
    
    async def _incremental_update(
        self,
        X_new: np.ndarray,
        y_new: np.ndarray,
    ) -> Dict[str, Any]:
        """Perform incremental update using partial_fit."""
        if self.online_model is None:
            # Initialize online model
            self.online_model = SGDClassifier(
                loss='log_loss',
                learning_rate='adaptive',
                random_state=42,
            )
            self.online_scaler = StandardScaler()
            
            # Need initial fit with some data
            if self.current_model is not None and hasattr(self.current_model, 'feature_importances_'):
                # Use current model's feature space
                n_features = len(self.current_model.feature_importances_)
                X_dummy = np.zeros((1, n_features))
                y_dummy = np.array([0])
                self.online_scaler.fit(X_dummy)
                self.online_model.partial_fit(X_dummy, y_dummy, classes=np.unique(y_new))
        
        # Scale new data
        X_scaled = self.online_scaler.transform(X_new)
        
        # Partial fit
        self.online_model.partial_fit(X_scaled, y_new)
        
        return {
            "update_type": "incremental",
            "samples_added": len(X_new),
            "buffer_size": len(self.new_samples_buffer),
            "status": "success",
        }
    
    async def _full_retrain(self) -> Dict[str, Any]:
        """Perform full retraining with accumulated data."""
        if not self.new_samples_buffer:
            return {"status": "no_data", "message": "No new data to retrain with"}
        
        # Extract all buffered samples
        X_all = np.array([x for x, _ in self.new_samples_buffer])
        y_all = np.array([y for _, y in self.new_samples_buffer])
        
        # Clear buffer
        self.new_samples_buffer = []
        
        # Retrain model (use RandomForest as default)
        logger.info(f"Retraining model with {len(X_all)} samples")
        start_time = datetime.utcnow()
        
        model = RandomForestClassifier(n_estimators=100, random_state=42)
        model.fit(X_all, y_all)
        
        training_time = (datetime.utcnow() - start_time).total_seconds()
        
        # Evaluate
        y_pred = model.predict(X_all)
        accuracy = accuracy_score(y_all, y_pred)
        f1 = f1_score(y_all, y_pred, average='weighted', zero_division=0)
        
        # Update current model if accuracy improved
        old_accuracy = 0.0
        if self.current_model is not None:
            # Evaluate old model on new data
            try:
                old_pred = self.current_model.predict(X_all)
                old_accuracy = accuracy_score(y_all, old_pred)
            except:
                pass
        
        if accuracy >= old_accuracy:
            self.current_model = model
            self.last_training_time = datetime.utcnow()
            logger.info(
                f"Model retrained. New accuracy: {accuracy:.4f} "
                f"(old: {old_accuracy:.4f})"
            )
        else:
            logger.warning(
                f"New model accuracy ({accuracy:.4f}) not better than old "
                f"({old_accuracy:.4f}). Keeping old model."
            )
        
        return {
            "update_type": "full_retrain",
            "samples_used": len(X_all),
            "training_time": training_time,
            "accuracy": float(accuracy),
            "f1_score": float(f1),
            "model_updated": accuracy >= old_accuracy,
            "status": "success",
        }
    
    def save_model_version(
        self,
        version: str,
        model: Any,
        accuracy: float,
        precision: float,
        recall: float,
        f1_score: float,
        training_samples: int,
        validation_samples: int,
        hyperparameters: Dict[str, Any],
        description: Optional[str] = None,
        is_production: bool = False,
    ) -> ModelVersion:
        """
        Save model version with metadata.
        
        Args:
            version: Version identifier
            model: Trained model
            accuracy: Model accuracy
            precision: Model precision
            recall: Model recall
            f1_score: F1 score
            training_samples: Number of training samples
            validation_samples: Number of validation samples
            hyperparameters: Model hyperparameters
            description: Optional description
            is_production: Whether this is production version
            
        Returns:
            ModelVersion instance
        """
        # Save model file
        model_filename = f"cache_prediction_{version}.pkl"
        model_path = self.model_dir / model_filename
        
        with open(model_path, 'wb') as f:
            pickle.dump(model, f)
        
        logger.info(f"Model saved to {model_path}")
        
        # Register version
        model_version = self.version_manager.register_version(
            version=version,
            model_path=str(model_path),
            accuracy=accuracy,
            precision=precision,
            recall=recall,
            f1_score=f1_score,
            training_samples=training_samples,
            validation_samples=validation_samples,
            hyperparameters=hyperparameters,
            description=description,
            is_production=is_production,
        )
        
        # Create symlink for current version
        current_link = self.model_dir / "cache_prediction_current.pkl"
        if current_link.exists():
            current_link.unlink()
        current_link.symlink_to(model_filename)
        
        return model_version
    
    def load_model_version(self, version: str) -> Optional[Any]:
        """
        Load model by version.
        
        Args:
            version: Version identifier
            
        Returns:
            Loaded model or None
        """
        model_path = self.version_manager.get_model_path(version)
        if model_path is None:
            logger.error(f"Version {version} not found")
            return None
        
        try:
            with open(model_path, 'rb') as f:
                model = pickle.load(f)
            logger.info(f"Model version {version} loaded from {model_path}")
            return model
        except Exception as exc:
            logger.error(f"Failed to load model version {version}: {exc}")
            return None
    
    def rollback_to_version(self, version: str) -> bool:
        """
        Rollback to a previous model version.
        
        Args:
            version: Version identifier to rollback to
            
        Returns:
            True if successful
        """
        model = self.load_model_version(version)
        if model is None:
            return False
        
        # Set as production
        success = self.version_manager.set_production(version)
        if success:
            self.current_model = model
            logger.info(f"Rolled back to version {version}")
        
        return success
    
    def compare_versions(
        self,
        v1: str,
        v2: str,
    ) -> Dict[str, Any]:
        """
        Compare two model versions.
        
        Args:
            v1: First version identifier
            v2: Second version identifier
            
        Returns:
            Comparison dictionary
        """
        version1 = self.version_manager.get_version(v1)
        version2 = self.version_manager.get_version(v2)
        
        if version1 is None or version2 is None:
            return {"error": "One or both versions not found"}
        
        comparison = {
            "version1": {
                "version": version1.version,
                "accuracy": version1.accuracy,
                "precision": version1.precision,
                "recall": version1.recall,
                "f1_score": version1.f1_score,
                "created_at": version1.created_at,
            },
            "version2": {
                "version": version2.version,
                "accuracy": version2.accuracy,
                "precision": version2.precision,
                "recall": version2.recall,
                "f1_score": version2.f1_score,
                "created_at": version2.created_at,
            },
            "differences": {
                "accuracy_diff": version2.accuracy - version1.accuracy,
                "precision_diff": version2.precision - version1.precision,
                "recall_diff": version2.recall - version1.recall,
                "f1_diff": version2.f1_score - version1.f1_score,
            },
            "better_version": v2 if version2.f1_score > version1.f1_score else v1,
        }
        
        return comparison
    
    def _get_base_model(self, model_type: str) -> Any:
        """Get base model instance by type."""
        if model_type == "random_forest":
            return RandomForestClassifier(random_state=42)
        elif model_type == "gradient_boosting":
            return GradientBoostingClassifier(random_state=42)
        elif model_type == "xgboost":
            if not XGBOOST_AVAILABLE:
                raise ImportError("xgboost is not installed")
            return xgb.XGBClassifier(random_state=42, eval_metric='mlogloss')
        elif model_type == "lightgbm":
            if not LIGHTGBM_AVAILABLE:
                raise ImportError("lightgbm is not installed")
            return lgb.LGBMClassifier(random_state=42, verbose=-1)
        else:
            raise ValueError(f"Unknown model type: {model_type}")
    
    def _get_default_param_grid(self, model_type: str) -> Dict[str, List[Any]]:
        """Get default parameter grid for model type."""
        if model_type == "random_forest":
            return {
                'n_estimators': [50, 100, 200],
                'max_depth': [5, 10, 15, 20, None],
                'min_samples_split': [2, 5, 10],
                'min_samples_leaf': [1, 2, 4],
            }
        elif model_type == "gradient_boosting":
            return {
                'n_estimators': [50, 100, 200],
                'max_depth': [3, 5, 7, 10],
                'learning_rate': [0.01, 0.1, 0.2],
                'min_samples_split': [2, 5, 10],
            }
        elif model_type == "xgboost":
            return {
                'n_estimators': [50, 100, 200],
                'max_depth': [3, 5, 7, 10],
                'learning_rate': [0.01, 0.1, 0.2],
                'subsample': [0.8, 0.9, 1.0],
            }
        elif model_type == "lightgbm":
            return {
                'n_estimators': [50, 100, 200],
                'max_depth': [3, 5, 7, 10],
                'learning_rate': [0.01, 0.1, 0.2],
                'num_leaves': [31, 50, 100],
            }
        else:
            return {}

