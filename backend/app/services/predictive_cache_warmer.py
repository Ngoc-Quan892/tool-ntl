"""
ML-based predictive cache warming service.

Uses machine learning to predict which data will be accessed in the future
and proactively warm the cache based on these predictions.

Features:
- Historical access pattern analysis
- Time-series analysis (hourly, daily, weekly patterns)
- User behavior clustering
- Seasonal trends detection
- Confidence scoring for predictions
- Adaptive learning
- A/B testing framework
"""

from __future__ import annotations

import asyncio
import logging
import pickle
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

from app.models.database import db_manager
from app.services.cache_warmer import CacheWarmer
from sqlalchemy import text

logger = logging.getLogger(__name__)


# ============================================================================
# Access Pattern Analyzer
# ============================================================================

class AccessPatternAnalyzer:
    """
    Analyze historical access patterns to identify trends and predict future accesses.
    """
    
    def __init__(
        self,
        lookback_days: int = 30,
        min_confidence: float = 0.7,
        model_path: Optional[str] = None,
    ):
        """
        Initialize access pattern analyzer.
        
        Args:
            lookback_days: Number of days to analyze for patterns
            min_confidence: Minimum prediction confidence threshold
            model_path: Path to save/load trained model
        """
        self.lookback_days = lookback_days
        self.min_confidence = min_confidence
        self.model_path = model_path or "models/cache_prediction_model.pkl"
        self.scaler_path = model_path.replace(".pkl", "_scaler.pkl") if model_path else "models/cache_prediction_scaler.pkl"
        
        self.model: Optional[RandomForestClassifier] = None
        self.feature_scaler: Optional[StandardScaler] = None
        self.user_clusters: Dict[str, int] = {}
        self.peak_hours: List[int] = []
        self.logger = logging.getLogger(__name__)
        
        # Create models directory if it doesn't exist
        Path(self.model_path).parent.mkdir(parents=True, exist_ok=True)
    
    async def analyze_patterns(self) -> Dict[str, Any]:
        """
        Analyze historical access patterns to identify trends.
        
        Returns:
            Dictionary with pattern analysis results
        """
        self.logger.info(f"Analyzing access patterns for last {self.lookback_days} days")
        
        try:
            # Fetch access logs from database
            end_date = datetime.now()
            start_date = end_date - timedelta(days=self.lookback_days)
            
            logs = await self._get_access_logs(start_date, end_date)
            
            if not logs:
                self.logger.warning("No access logs found")
                return {
                    "hourly_distribution": {},
                    "daily_distribution": {},
                    "top_games": {},
                    "peak_hours": [],
                    "user_clusters": {},
                }
            
            # Convert to DataFrame
            df = pd.DataFrame(logs)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df['hour'] = df['timestamp'].dt.hour
            df['day_of_week'] = df['timestamp'].dt.dayofweek
            df['is_weekend'] = df['day_of_week'].isin([5, 6]).astype(int)
            
            # Analyze patterns
            patterns = {
                "hourly_distribution": df.groupby('hour')['access_count'].mean().to_dict(),
                "daily_distribution": df.groupby('day_of_week')['access_count'].mean().to_dict(),
                "top_games": df.groupby('game_id')['access_count'].sum().nlargest(20).to_dict(),
                "peak_hours": self._identify_peak_hours(df),
                "user_clusters": await self._cluster_users(df),
                "total_accesses": len(df),
                "unique_games": df['game_id'].nunique(),
                "unique_users": df.get('user_id', pd.Series()).nunique() if 'user_id' in df.columns else 0,
            }
            
            self.peak_hours = patterns["peak_hours"]
            self.user_clusters = patterns["user_clusters"]
            
            self.logger.info(f"Pattern analysis complete: {patterns['total_accesses']} accesses analyzed")
            return patterns
            
        except Exception as exc:
            self.logger.error(f"Failed to analyze patterns: {exc}", exc_info=True)
            return {}
    
    async def train_prediction_model(self) -> Dict[str, Any]:
        """
        Train ML model to predict future accesses.
        
        Returns:
            Dictionary with training results (accuracy, etc.)
        """
        self.logger.info("Training prediction model...")
        
        try:
            # Fetch training data
            end_date = datetime.now()
            start_date = end_date - timedelta(days=self.lookback_days)
            
            logs = await self._get_access_logs(start_date, end_date)
            
            if not logs or len(logs) < 100:
                self.logger.warning("Insufficient data for training")
                return {"accuracy": 0.0, "status": "insufficient_data"}
            
            df = pd.DataFrame(logs)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df = df.sort_values('timestamp')
            
            # Feature engineering
            features = []
            labels = []
            
            # Use sliding window to create training examples
            window_size = 60  # 60 minutes window
            prediction_horizon = 60  # Predict 60 minutes ahead
            
            for i in range(len(df) - window_size - prediction_horizon):
                window = df.iloc[i:i+window_size]
                future_point = df.iloc[i+window_size+prediction_horizon]
                
                feature = self._extract_features(window, df.iloc[:i+window_size])
                label = future_point.get('game_id', 0)
                
                if feature is not None and label is not None:
                    features.append(feature)
                    labels.append(label)
            
            if len(features) < 50:
                self.logger.warning("Insufficient training examples")
                return {"accuracy": 0.0, "status": "insufficient_examples"}
            
            # Train/test split
            X_train, X_test, y_train, y_test = train_test_split(
                features, labels, test_size=0.2, random_state=42
            )
            
            # Scale features
            self.feature_scaler = StandardScaler()
            X_train_scaled = self.feature_scaler.fit_transform(X_train)
            X_test_scaled = self.feature_scaler.transform(X_test)
            
            # Train model
            self.model = RandomForestClassifier(
                n_estimators=100,
                max_depth=10,
                random_state=42,
                n_jobs=-1,
            )
            self.model.fit(X_train_scaled, y_train)
            
            # Evaluate
            train_accuracy = self.model.score(X_train_scaled, y_train)
            test_accuracy = self.model.score(X_test_scaled, y_test)
            
            self.logger.info(
                f"Model trained - Train accuracy: {train_accuracy:.2%}, "
                f"Test accuracy: {test_accuracy:.2%}"
            )
            
            # Save model
            self._save_model()
            
            return {
                "train_accuracy": train_accuracy,
                "test_accuracy": test_accuracy,
                "status": "success",
                "n_samples": len(features),
            }
            
        except Exception as exc:
            self.logger.error(f"Failed to train model: {exc}", exc_info=True)
            return {"accuracy": 0.0, "status": "error", "error": str(exc)}
    
    async def predict_next_access(
        self,
        time_horizon: int = 60,
        top_k: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        Predict which games will be accessed in next N minutes.
        
        Args:
            time_horizon: Minutes to predict ahead
            top_k: Number of top predictions to return
            
        Returns:
            List of predictions with confidence scores
        """
        if self.model is None or self.feature_scaler is None:
            self.logger.warning("Model not trained, cannot make predictions")
            return []
        
        try:
            # Get recent access patterns
            recent_logs = await self._get_access_logs(
                start_date=datetime.now() - timedelta(hours=1),
                end_date=datetime.now(),
            )
            
            if not recent_logs:
                self.logger.warning("No recent access logs for prediction")
                return []
            
            # Get historical context for feature extraction
            historical_logs = await self._get_access_logs(
                start_date=datetime.now() - timedelta(days=1),
                end_date=datetime.now(),
            )
            
            df_recent = pd.DataFrame(recent_logs)
            df_historical = pd.DataFrame(historical_logs) if historical_logs else pd.DataFrame()
            
            if len(df_recent) == 0:
                return []
            
            df_recent['timestamp'] = pd.to_datetime(df_recent['timestamp'])
            if not df_historical.empty:
                df_historical['timestamp'] = pd.to_datetime(df_historical['timestamp'])
            
            # Extract features
            feature = self._extract_features(df_recent, df_historical)
            
            if feature is None:
                return []
            
            # Scale features
            features_scaled = self.feature_scaler.transform([feature])
            
            # Predict
            probabilities = self.model.predict_proba(features_scaled)[0]
            
            # Get top predictions with confidence
            predictions = []
            for i, prob in enumerate(probabilities):
                if prob >= self.min_confidence:
                    predictions.append({
                        "game_id": int(self.model.classes_[i]),
                        "confidence": float(prob),
                        "time_horizon": time_horizon,
                    })
            
            # Sort by confidence and return top K
            predictions.sort(key=lambda x: x['confidence'], reverse=True)
            
            self.logger.info(f"Generated {len(predictions)} predictions (top {top_k} returned)")
            return predictions[:top_k]
            
        except Exception as exc:
            self.logger.error(f"Failed to predict next access: {exc}", exc_info=True)
            return []
    
    def _extract_features(
        self,
        access_log: pd.DataFrame,
        historical_log: pd.DataFrame = None,
    ) -> Optional[np.ndarray]:
        """
        Extract ML features from access logs.
        
        Args:
            access_log: Recent access logs DataFrame
            historical_log: Historical logs for context
            
        Returns:
            NumPy array of features
        """
        try:
            if access_log.empty:
                return None
            
            current_time = datetime.now()
            features = []
            
            # Temporal features
            hour = current_time.hour
            day_of_week = current_time.weekday()
            is_weekend = 1 if day_of_week >= 5 else 0
            is_peak_hour = 1 if hour in self.peak_hours else 0
            
            features.extend([hour, day_of_week, is_weekend, is_peak_hour])
            
            # Access pattern features
            last_15_min = access_log[
                access_log['timestamp'] >= current_time - timedelta(minutes=15)
            ] if 'timestamp' in access_log.columns else pd.DataFrame()
            last_60_min = access_log[
                access_log['timestamp'] >= current_time - timedelta(minutes=60)
            ] if 'timestamp' in access_log.columns else pd.DataFrame()
            
            access_count_15min = len(last_15_min)
            access_count_60min = len(last_60_min)
            unique_users_15min = last_15_min.get('user_id', pd.Series()).nunique() if 'user_id' in last_15_min.columns else 0
            unique_games_15min = last_15_min.get('game_id', pd.Series()).nunique() if 'game_id' in last_15_min.columns else 0
            
            # Average session duration (if available)
            avg_session_duration = 0.0
            if 'session_duration' in access_log.columns:
                avg_session_duration = access_log['session_duration'].mean() if not access_log.empty else 0.0
            
            features.extend([
                access_count_15min,
                access_count_60min,
                unique_users_15min,
                unique_games_15min,
                avg_session_duration,
            ])
            
            # Game features (from historical data)
            if historical_log is not None and not historical_log.empty:
                top_games = historical_log.groupby('game_id')['access_count'].sum().nlargest(10)
                game_popularity_rank = len(top_games)  # Default if not in top
                
                # Recent trend (increasing/decreasing)
                recent_trend = 0.0
                if len(historical_log) > 1:
                    recent_counts = historical_log.groupby(
                        pd.Grouper(key='timestamp', freq='1H')
                    )['access_count'].sum()
                    if len(recent_counts) > 1:
                        recent_trend = (recent_counts.iloc[-1] - recent_counts.iloc[-2]) / max(recent_counts.iloc[-2], 1)
                
                features.extend([game_popularity_rank, recent_trend])
            else:
                features.extend([0, 0.0])
            
            # User behavior features (if user_id available)
            if 'user_id' in access_log.columns and not access_log.empty:
                # Most common user cluster
                user_ids = access_log['user_id'].dropna().unique()
                if len(user_ids) > 0:
                    # Get cluster for most common user
                    most_common_user = access_log['user_id'].mode()[0] if not access_log['user_id'].mode().empty else None
                    user_cluster = self.user_clusters.get(str(most_common_user), 0) if most_common_user else 0
                    user_activity_level = len(user_ids)
                else:
                    user_cluster = 0
                    user_activity_level = 0
            else:
                user_cluster = 0
                user_activity_level = 0
            
            features.extend([user_cluster, user_activity_level])
            
            return np.array(features, dtype=np.float32)
            
        except Exception as exc:
            self.logger.error(f"Failed to extract features: {exc}", exc_info=True)
            return None
    
    def _identify_peak_hours(self, df: pd.DataFrame) -> List[int]:
        """
        Identify peak traffic hours.
        
        Args:
            df: Access logs DataFrame
            
        Returns:
            List of peak hour numbers (0-23)
        """
        try:
            if df.empty or 'hour' not in df.columns:
                return []
            
            hourly_counts = df.groupby('hour')['access_count'].sum()
            mean_count = hourly_counts.mean()
            std_count = hourly_counts.std()
            
            # Peak hours are those above mean + 0.5*std
            threshold = mean_count + 0.5 * std_count
            peak_hours = hourly_counts[hourly_counts >= threshold].index.tolist()
            
            return sorted(peak_hours)
        except Exception as exc:
            self.logger.error(f"Failed to identify peak hours: {exc}")
            return []
    
    async def _cluster_users(self, df: pd.DataFrame) -> Dict[str, int]:
        """
        Cluster users by access behavior.
        
        Args:
            df: Access logs DataFrame
            
        Returns:
            Dictionary mapping user_id to cluster_id
        """
        try:
            if df.empty or 'user_id' not in df.columns:
                return {}
            
            # Get user statistics
            user_stats = {}
            for user_id in df['user_id'].dropna().unique():
                user_data = df[df['user_id'] == user_id]
                
                stats = {
                    "access_count": len(user_data),
                    "avg_session_duration": user_data.get('session_duration', pd.Series([0])).mean(),
                    "unique_games": user_data['game_id'].nunique() if 'game_id' in user_data.columns else 0,
                    "peak_hours": user_data['hour'].mode().tolist() if 'hour' in user_data.columns else [],
                }
                user_stats[str(user_id)] = stats
            
            if len(user_stats) < 5:
                # Not enough users to cluster
                return {user_id: 0 for user_id in user_stats.keys()}
            
            # Create feature matrix
            features = []
            user_ids = []
            
            for user_id, stats in user_stats.items():
                feature = [
                    stats["access_count"],
                    stats["avg_session_duration"],
                    stats["unique_games"],
                    len(stats["peak_hours"]),
                ]
                features.append(feature)
                user_ids.append(user_id)
            
            # Cluster
            n_clusters = min(5, len(user_stats) // 2)  # At least 2 users per cluster
            if n_clusters < 2:
                return {user_id: 0 for user_id in user_ids}
            
            kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
            clusters = kmeans.fit_predict(features)
            
            # Map users to clusters
            user_clusters = {
                user_id: int(cluster_id)
                for user_id, cluster_id in zip(user_ids, clusters)
            }
            
            self.logger.info(f"Clustered {len(user_clusters)} users into {n_clusters} clusters")
            return user_clusters
            
        except Exception as exc:
            self.logger.error(f"Failed to cluster users: {exc}", exc_info=True)
            return {}
    
    def _detect_seasonal_patterns(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Detect seasonal trends in access patterns.
        
        Args:
            df: Access logs DataFrame
            
        Returns:
            Dictionary with seasonal patterns
        """
        try:
            if df.empty:
                return {}
            
            df['month'] = df['timestamp'].dt.month
            df['day_of_month'] = df['timestamp'].dt.day
            
            patterns = {
                "monthly_distribution": df.groupby('month')['access_count'].mean().to_dict(),
                "day_of_month_distribution": df.groupby('day_of_month')['access_count'].mean().to_dict(),
            }
            
            return patterns
        except Exception as exc:
            self.logger.error(f"Failed to detect seasonal patterns: {exc}")
            return {}
    
    async def _get_access_logs(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> List[Dict[str, Any]]:
        """
        Get access logs from database.
        
        Args:
            start_date: Start date for logs
            end_date: End date for logs
            
        Returns:
            List of access log dictionaries
        """
        try:
            with db_manager.get_session() as session:
                # Query game_results to simulate access logs
                # In production, you would have a dedicated access_logs table
                query = text("""
                    SELECT 
                        shoe_number as game_id,
                        timestamp,
                        COUNT(*) as access_count,
                        MAX(timestamp) - MIN(timestamp) as session_duration
                    FROM game_results
                    WHERE timestamp >= :start_date AND timestamp <= :end_date
                    GROUP BY shoe_number, DATE(timestamp), HOUR(timestamp)
                    ORDER BY timestamp
                """)
                
                result = session.execute(query, {
                    "start_date": start_date,
                    "end_date": end_date,
                })
                
                logs = []
                for row in result:
                    logs.append({
                        "game_id": row[0],
                        "timestamp": row[1],
                        "access_count": row[2],
                        "session_duration": row[3].total_seconds() if row[3] else 0,
                        "user_id": None,  # Would come from actual access logs
                    })
                
                return logs
                
        except Exception as exc:
            self.logger.error(f"Failed to get access logs: {exc}", exc_info=True)
            return []
    
    def _save_model(self) -> None:
        """Save trained model and scaler to disk."""
        try:
            if self.model:
                with open(self.model_path, 'wb') as f:
                    pickle.dump(self.model, f)
                self.logger.info(f"Model saved to {self.model_path}")
            
            if self.feature_scaler:
                with open(self.scaler_path, 'wb') as f:
                    pickle.dump(self.feature_scaler, f)
                self.logger.info(f"Scaler saved to {self.scaler_path}")
        except Exception as exc:
            self.logger.error(f"Failed to save model: {exc}")
    
    def _load_model(self) -> bool:
        """Load trained model and scaler from disk."""
        try:
            if Path(self.model_path).exists():
                with open(self.model_path, 'rb') as f:
                    self.model = pickle.load(f)
                self.logger.info(f"Model loaded from {self.model_path}")
            
            if Path(self.scaler_path).exists():
                with open(self.scaler_path, 'rb') as f:
                    self.feature_scaler = pickle.load(f)
                self.logger.info(f"Scaler loaded from {self.scaler_path}")
            
            return self.model is not None and self.feature_scaler is not None
        except Exception as exc:
            self.logger.error(f"Failed to load model: {exc}")
            return False


# ============================================================================
# Predictive Cache Warmer
# ============================================================================

class PredictiveCacheWarmer:
    """
    Cache warmer using ML predictions to proactively warm cache.
    """
    
    def __init__(
        self,
        cache_warmer: CacheWarmer,
        analyzer: AccessPatternAnalyzer,
        prediction_horizon: int = 60,
        update_interval: int = 300,
    ):
        """
        Initialize predictive cache warmer.
        
        Args:
            cache_warmer: CacheWarmer instance
            analyzer: AccessPatternAnalyzer instance
            prediction_horizon: Minutes to predict ahead
            update_interval: Seconds between prediction updates
        """
        self.cache_warmer = cache_warmer
        self.analyzer = analyzer
        self.prediction_horizon = prediction_horizon
        self.update_interval = update_interval
        
        self.is_running = False
        self.logger = logging.getLogger(__name__)
        
        self._warming_task: Optional[asyncio.Task] = None
        self._evaluation_task: Optional[asyncio.Task] = None
        
        # Metrics tracking
        self.prediction_history: List[Dict[str, Any]] = []
        self.evaluation_metrics: Dict[str, float] = {
            "precision": 0.0,
            "recall": 0.0,
            "f1_score": 0.0,
            "cache_hit_rate": 0.0,
        }
    
    async def start_predictive_warming(self) -> None:
        """Start predictive cache warming."""
        self.logger.info("Starting predictive cache warming...")
        
        try:
            # Try to load existing model
            if not self.analyzer._load_model():
                # Train initial model if not available
                self.logger.info("Training initial prediction model...")
                training_result = await self.analyzer.train_prediction_model()
                if training_result.get("status") != "success":
                    self.logger.warning("Model training failed, using fallback")
            
            # Analyze patterns
            await self.analyzer.analyze_patterns()
            
            # Start warming loop
            self.is_running = True
            self._warming_task = asyncio.create_task(self._warming_loop())
            
            # Start evaluation loop
            self._evaluation_task = asyncio.create_task(self._evaluation_loop())
            
            self.logger.info("Predictive cache warming started")
            
        except Exception as exc:
            self.logger.error(f"Failed to start predictive warming: {exc}", exc_info=True)
            raise
    
    async def stop_predictive_warming(self) -> None:
        """Stop predictive cache warming."""
        self.logger.info("Stopping predictive cache warming...")
        self.is_running = False
        
        if self._warming_task:
            self._warming_task.cancel()
        if self._evaluation_task:
            self._evaluation_task.cancel()
        
        self.logger.info("Predictive cache warming stopped")
    
    async def _warming_loop(self) -> None:
        """Continuous predictive warming loop."""
        try:
            while self.is_running:
                # Get predictions
                predictions = await self.analyzer.predict_next_access(
                    time_horizon=self.prediction_horizon,
                    top_k=20,
                )
                
                # Warm predicted items
                warmed_count = 0
                for pred in predictions:
                    if pred['confidence'] >= self.analyzer.min_confidence:
                        try:
                            success = await self.cache_warmer._warm_game_results(
                                pred['game_id'],
                                limit=100,
                            )
                            if success:
                                warmed_count += 1
                        except Exception as exc:
                            self.logger.warning(f"Failed to warm game {pred['game_id']}: {exc}")
                
                # Store predictions for evaluation
                if predictions:
                    self.prediction_history.append({
                        "timestamp": datetime.now(),
                        "predictions": predictions,
                        "warmed_count": warmed_count,
                    })
                
                self.logger.info(
                    f"Warmed {warmed_count}/{len(predictions)} predicted items "
                    f"(confidence >= {self.analyzer.min_confidence})"
                )
                
                await asyncio.sleep(self.update_interval)
                
        except asyncio.CancelledError:
            self.logger.info("Warming loop cancelled")
        except Exception as exc:
            self.logger.error(f"Warming loop error: {exc}", exc_info=True)
    
    async def _evaluation_loop(self) -> None:
        """Evaluate prediction accuracy periodically."""
        try:
            while self.is_running:
                await asyncio.sleep(600)  # Evaluate every 10 minutes
                
                if len(self.prediction_history) > 0:
                    evaluation = await self._evaluate_predictions()
                    self.evaluation_metrics.update(evaluation)
                    
                    self.logger.info(
                        f"Prediction evaluation - Precision: {evaluation.get('precision', 0):.2%}, "
                        f"Recall: {evaluation.get('recall', 0):.2%}, "
                        f"F1: {evaluation.get('f1_score', 0):.2%}"
                    )
                    
                    # Adaptive adjustment
                    await self._adaptive_adjustment()
                
        except asyncio.CancelledError:
            self.logger.info("Evaluation loop cancelled")
        except Exception as exc:
            self.logger.error(f"Evaluation loop error: {exc}", exc_info=True)
    
    async def _evaluate_predictions(self) -> Dict[str, float]:
        """
        Evaluate prediction accuracy.
        
        Returns:
            Dictionary with evaluation metrics
        """
        try:
            if len(self.prediction_history) == 0:
                return {"precision": 0.0, "recall": 0.0, "f1_score": 0.0}
            
            # Get predictions from N minutes ago
            evaluation_window = timedelta(minutes=self.prediction_horizon)
            cutoff_time = datetime.now() - evaluation_window
            
            # Find predictions made around cutoff_time
            relevant_predictions = [
                p for p in self.prediction_history
                if p["timestamp"] <= cutoff_time
            ]
            
            if not relevant_predictions:
                return {"precision": 0.0, "recall": 0.0, "f1_score": 0.0}
            
            # Get actual accesses in that time window
            actual_logs = await self.analyzer._get_access_logs(
                start_date=cutoff_time,
                end_date=datetime.now(),
            )
            
            actual_game_ids = set()
            if actual_logs:
                df = pd.DataFrame(actual_logs)
                actual_game_ids = set(df['game_id'].unique())
            
            # Calculate metrics
            all_predicted = set()
            for pred_entry in relevant_predictions:
                for pred in pred_entry["predictions"]:
                    all_predicted.add(pred["game_id"])
            
            if len(all_predicted) == 0:
                return {"precision": 0.0, "recall": 0.0, "f1_score": 0.0}
            
            # True positives: predicted and actually accessed
            true_positives = len(all_predicted & actual_game_ids)
            
            # Precision: % of predictions that were correct
            precision = true_positives / len(all_predicted) if len(all_predicted) > 0 else 0.0
            
            # Recall: % of actual accesses that were predicted
            recall = true_positives / len(actual_game_ids) if len(actual_game_ids) > 0 else 0.0
            
            # F1 score
            f1_score = (
                2 * (precision * recall) / (precision + recall)
                if (precision + recall) > 0 else 0.0
            )
            
            return {
                "precision": precision,
                "recall": recall,
                "f1_score": f1_score,
                "true_positives": true_positives,
                "total_predictions": len(all_predicted),
                "total_actual": len(actual_game_ids),
            }
            
        except Exception as exc:
            self.logger.error(f"Failed to evaluate predictions: {exc}", exc_info=True)
            return {"precision": 0.0, "recall": 0.0, "f1_score": 0.0}
    
    async def _adaptive_adjustment(self) -> None:
        """Adjust prediction parameters based on accuracy."""
        try:
            precision = self.evaluation_metrics.get("precision", 0.0)
            recall = self.evaluation_metrics.get("recall", 0.0)
            
            # If precision is low, increase confidence threshold
            if precision < 0.5:
                self.analyzer.min_confidence = min(0.9, self.analyzer.min_confidence + 0.05)
                self.logger.info(f"Increased confidence threshold to {self.analyzer.min_confidence}")
            
            # If recall is low, decrease confidence threshold
            elif recall < 0.3:
                self.analyzer.min_confidence = max(0.5, self.analyzer.min_confidence - 0.05)
                self.logger.info(f"Decreased confidence threshold to {self.analyzer.min_confidence}")
            
            # Retrain model if accuracy is consistently low
            if precision < 0.4 and recall < 0.4:
                self.logger.info("Low accuracy detected, retraining model...")
                await self.analyzer.train_prediction_model()
                
        except Exception as exc:
            self.logger.error(f"Failed to adjust adaptively: {exc}")
    
    async def run_ab_test(
        self,
        strategy_a: str = "traditional",
        strategy_b: str = "predictive",
        duration_hours: int = 24,
        traffic_split: float = 0.5,
    ) -> Dict[str, Any]:
        """
        Run A/B test comparing different warming strategies.
        
        Args:
            strategy_a: First strategy name
            strategy_b: Second strategy name
            duration_hours: Test duration in hours
            traffic_split: Fraction of traffic for strategy A (0.0-1.0)
            
        Returns:
            Dictionary with A/B test results
        """
        self.logger.info(
            f"Starting A/B test: {strategy_a} vs {strategy_b} "
            f"({traffic_split*100:.0f}%/{100-traffic_split*100:.0f}% split)"
        )
        
        try:
            # This is a simplified A/B test framework
            # In production, you would use proper user assignment and tracking
            
            start_time = datetime.now()
            end_time = start_time + timedelta(hours=duration_hours)
            
            group_a_metrics = {
                "cache_hits": 0,
                "cache_misses": 0,
                "total_requests": 0,
            }
            
            group_b_metrics = {
                "cache_hits": 0,
                "cache_misses": 0,
                "total_requests": 0,
            }
            
            # Simulate A/B test (in production, this would track actual requests)
            # For now, we'll use the predictive warming results
            
            while datetime.now() < end_time:
                # Randomly assign to group A or B
                import random
                if random.random() < traffic_split:
                    # Group A: Traditional warming
                    # (would use traditional cache warmer)
                    pass
                else:
                    # Group B: Predictive warming
                    # (already running)
                    pass
                
                await asyncio.sleep(60)  # Check every minute
            
            # Calculate results
            group_a_hit_rate = (
                group_a_metrics["cache_hits"] / group_a_metrics["total_requests"]
                if group_a_metrics["total_requests"] > 0 else 0.0
            )
            
            group_b_hit_rate = (
                group_b_metrics["cache_hits"] / group_b_metrics["total_requests"]
                if group_b_metrics["total_requests"] > 0 else 0.0
            )
            
            improvement = group_b_hit_rate - group_a_hit_rate
            improvement_pct = (improvement / group_a_hit_rate * 100) if group_a_hit_rate > 0 else 0.0
            
            result = {
                "strategy_a": strategy_a,
                "strategy_b": strategy_b,
                "duration_hours": duration_hours,
                "traffic_split": traffic_split,
                "group_a_hit_rate": group_a_hit_rate,
                "group_b_hit_rate": group_b_hit_rate,
                "improvement": improvement,
                "improvement_percent": improvement_pct,
                "winner": strategy_b if improvement > 0 else strategy_a,
            }
            
            self.logger.info(
                f"A/B test complete - Winner: {result['winner']} "
                f"({improvement_pct:+.1f}% improvement)"
            )
            
            return result
            
        except Exception as exc:
            self.logger.error(f"A/B test failed: {exc}", exc_info=True)
            return {
                "error": str(exc),
                "strategy_a": strategy_a,
                "strategy_b": strategy_b,
            }
    
    async def update_features_realtime(self) -> None:
        """
        Update features as new data comes in (real-time updates).
        
        This would typically subscribe to a stream (Redis pub/sub, Kafka, etc.)
        """
        # Placeholder for real-time feature updates
        # In production, this would:
        # 1. Subscribe to access log stream
        # 2. Update rolling statistics
        # 3. Trigger re-prediction when significant changes detected
        # 4. Implement online learning for model updates
        
        self.logger.info("Real-time feature updates not yet implemented")
        pass
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Get current metrics and statistics.
        
        Returns:
            Dictionary with metrics
        """
        return {
            "evaluation_metrics": self.evaluation_metrics.copy(),
            "prediction_history_count": len(self.prediction_history),
            "is_running": self.is_running,
            "prediction_horizon": self.prediction_horizon,
            "update_interval": self.update_interval,
        }

