"""
Advanced LSTM model with attention mechanism for Baccarat prediction

This module provides:
- PyTorch-based LSTM with multi-head attention
- Advanced feature extraction
- Ensemble prediction
- Confidence calibration
- Performance optimization
"""
from __future__ import annotations

import pickle
import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from datetime import datetime
import numpy as np

try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    # Fallback will be used

try:
    from scipy import stats
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False


@dataclass
class ModelConfig:
    """Model configuration"""
    input_size: int = 35  # Number of features
    hidden_size: int = 128
    num_layers: int = 3
    dropout: float = 0.3
    attention_heads: int = 8
    sequence_length: int = 30
    learning_rate: float = 0.001
    batch_size: int = 32
    epochs: int = 100
    early_stopping_patience: int = 10


if TORCH_AVAILABLE:
    class MultiHeadAttention(nn.Module):
        """
        Multi-head attention mechanism for sequence analysis
        """
        
        def __init__(self, hidden_size: int, num_heads: int = 8, dropout: float = 0.1):
            super().__init__()
            assert hidden_size % num_heads == 0
            
            self.hidden_size = hidden_size
            self.num_heads = num_heads
            self.head_dim = hidden_size // num_heads
            
            self.q_linear = nn.Linear(hidden_size, hidden_size)
            self.k_linear = nn.Linear(hidden_size, hidden_size)
            self.v_linear = nn.Linear(hidden_size, hidden_size)
            self.out_linear = nn.Linear(hidden_size, hidden_size)
            
            self.dropout = nn.Dropout(dropout)
            self.scale = torch.sqrt(torch.FloatTensor([self.head_dim]))
        
        def forward(self, query, key, value, mask=None):
            batch_size = query.shape[0]
            
            # Linear transformations in batch from hidden_size => h * head_dim
            Q = self.q_linear(query)
            K = self.k_linear(key)
            V = self.v_linear(value)
            
            # Reshape to batch_size * num_heads * seq_length * head_dim
            Q = Q.view(batch_size, -1, self.num_heads, self.head_dim).permute(0, 2, 1, 3)
            K = K.view(batch_size, -1, self.num_heads, self.head_dim).permute(0, 2, 1, 3)
            V = V.view(batch_size, -1, self.num_heads, self.head_dim).permute(0, 2, 1, 3)
            
            # Move scale to device
            if self.scale.device != query.device:
                self.scale = self.scale.to(query.device)
            
            # Attention
            attention = torch.matmul(Q, K.permute(0, 1, 3, 2)) / self.scale
            
            if mask is not None:
                attention = attention.masked_fill(mask == 0, -1e10)
            
            attention = F.softmax(attention, dim=-1)
            attention = self.dropout(attention)
            
            # Apply attention to values
            x = torch.matmul(attention, V)
            
            # Reshape back
            x = x.permute(0, 2, 1, 3).contiguous()
            x = x.view(batch_size, -1, self.hidden_size)
            
            x = self.out_linear(x)
            
            return x, attention
    
    
    class BaccaratLSTM(nn.Module):
        """
        Advanced LSTM model with attention for Baccarat prediction
        """
        
        def __init__(self, config: ModelConfig):
            super().__init__()
            self.config = config
            
            # Input projection
            self.input_projection = nn.Sequential(
                nn.Linear(config.input_size, config.hidden_size),
                nn.LayerNorm(config.hidden_size),
                nn.ReLU(),
                nn.Dropout(config.dropout)
            )
            
            # LSTM layers
            self.lstm = nn.LSTM(
                input_size=config.hidden_size,
                hidden_size=config.hidden_size,
                num_layers=config.num_layers,
                batch_first=True,
                dropout=config.dropout if config.num_layers > 1 else 0,
                bidirectional=True
            )
            
            # Attention mechanism
            self.attention = MultiHeadAttention(
                config.hidden_size * 2,  # Bidirectional
                config.attention_heads,
                config.dropout
            )
            
            # Position encoding
            self.position_encoding = self._create_position_encoding(
                config.sequence_length,
                config.hidden_size * 2
            )
            
            # Output layers
            self.output_layers = nn.Sequential(
                nn.Linear(config.hidden_size * 2, config.hidden_size),
                nn.LayerNorm(config.hidden_size),
                nn.ReLU(),
                nn.Dropout(config.dropout),
                nn.Linear(config.hidden_size, 64),
                nn.ReLU(),
                nn.Dropout(config.dropout),
                nn.Linear(64, 3)  # B, P, T probabilities
            )
            
            # Confidence estimation
            self.confidence_layer = nn.Sequential(
                nn.Linear(config.hidden_size * 2, 32),
                nn.ReLU(),
                nn.Linear(32, 1),
                nn.Sigmoid()
            )
        
        def _create_position_encoding(self, max_len: int, d_model: int):
            """Create sinusoidal position encoding"""
            position = torch.arange(max_len).unsqueeze(1).float()
            div_term = torch.exp(torch.arange(0, d_model, 2).float() * 
                                -(np.log(10000.0) / d_model))
            
            pe = torch.zeros(max_len, d_model)
            pe[:, 0::2] = torch.sin(position * div_term)
            pe[:, 1::2] = torch.cos(position * div_term)
            
            return pe.unsqueeze(0)
        
        def forward(self, x, return_attention=False):
            batch_size = x.shape[0]
            seq_len = x.shape[1]
            
            # Input projection
            x = self.input_projection(x)
            
            # LSTM processing
            lstm_out, (hidden, cell) = self.lstm(x)
            
            # Add position encoding
            if seq_len <= self.config.sequence_length:
                pe = self.position_encoding[:, :seq_len, :].to(x.device)
                lstm_out = lstm_out + pe
            
            # Self-attention
            attended, attention_weights = self.attention(lstm_out, lstm_out, lstm_out)
            
            # Residual connection
            lstm_out = lstm_out + attended
            
            # Take the last output for prediction
            final_output = lstm_out[:, -1, :]
            
            # Generate predictions
            predictions = self.output_layers(final_output)
            probabilities = F.softmax(predictions, dim=-1)
            
            # Estimate confidence
            confidence = self.confidence_layer(final_output)
            
            if return_attention:
                return probabilities, confidence, attention_weights
            
            return probabilities, confidence
else:
    # Fallback classes if PyTorch not available
    class MultiHeadAttention:
        def __init__(self, *args, **kwargs):
            raise ImportError("PyTorch is required for MultiHeadAttention")
    
    class BaccaratLSTM:
        def __init__(self, *args, **kwargs):
            raise ImportError("PyTorch is required for BaccaratLSTM")


# ==================== FEATURE EXTRACTOR ====================

class FeatureExtractor:
    """
    Advanced feature extraction for ML model
    """
    
    def extract_all_features(self, shoe_state: Dict, history: List[str]) -> np.ndarray:
        """Extract comprehensive feature set"""
        features = []
        
        # 1. Pattern features (10 features)
        features.extend(self._extract_pattern_features(history))
        
        # 2. Statistical features (8 features)
        features.extend(self._extract_statistical_features(history))
        
        # 3. Card counting features (6 features)
        features.extend(self._extract_counting_features(shoe_state))
        
        # 4. Composition features (6 features)
        features.extend(self._extract_composition_features(shoe_state))
        
        # 5. Temporal features (5 features)
        features.extend(self._extract_temporal_features(shoe_state, history))
        
        # Ensure we have exactly 35 features
        if len(features) < 35:
            features.extend([0.0] * (35 - len(features)))
        elif len(features) > 35:
            features = features[:35]
        
        # Create sequence for LSTM (use sliding window)
        sequence = self._create_sequence(features, history)
        
        return sequence
    
    def _extract_pattern_features(self, history: List[str]) -> List[float]:
        """Extract pattern-based features"""
        if len(history) < 5:
            return [0.0] * 10
        
        features = []
        no_tie = [h for h in history if h != 'T']
        
        # Recent win rates
        for window in [5, 10, 20]:
            if len(no_tie) >= window:
                banker_rate = sum(1 for h in no_tie[-window:] if h == 'B') / window
                features.append(banker_rate)
            else:
                features.append(0.4586)
        
        # Streak analysis
        current_streak = self._get_current_streak(no_tie)
        features.append(min(current_streak / 10, 1.0))
        
        # Pattern counts
        features.append(self._count_dragons(no_tie))
        features.append(self._count_pingpong(no_tie))
        features.append(self._count_doubles(no_tie))
        
        # Trend analysis
        features.append(self._calculate_trend(no_tie))
        
        # Volatility
        features.append(self._calculate_volatility(no_tie))
        
        # Momentum
        features.append(self._calculate_momentum(no_tie))
        
        return features[:10]
    
    def _extract_statistical_features(self, history: List[str]) -> List[float]:
        """Extract statistical features"""
        if len(history) < 10:
            return [0.5] * 8
        
        no_tie = [1 if h == 'B' else 0 for h in history if h != 'T']
        
        if len(no_tie) < 10:
            return [0.5] * 8
        
        features = []
        
        # Basic statistics
        features.append(np.mean(no_tie))
        features.append(np.std(no_tie))
        
        # Higher moments
        if SCIPY_AVAILABLE:
            features.append(stats.skew(no_tie))
            features.append(stats.kurtosis(no_tie))
        else:
            features.extend([0.0, 0.0])
        
        # Entropy
        features.append(self._calculate_entropy(history))
        
        # Autocorrelation
        features.append(self._calculate_autocorrelation(no_tie, 1))
        features.append(self._calculate_autocorrelation(no_tie, 2))
        
        # Hurst exponent (trend persistence)
        features.append(self._calculate_hurst_exponent(no_tie))
        
        return features[:8]
    
    def _extract_counting_features(self, shoe_state: Dict) -> List[float]:
        """Extract card counting features"""
        return [
            shoe_state.get("true_count_b", 0) / 10,
            shoe_state.get("true_count_p", 0) / 10,
            shoe_state.get("running_count_b", 0) / 100,
            shoe_state.get("running_count_p", 0) / 100,
            shoe_state.get("decks_remaining", 8) / 8,
            shoe_state.get("edge", {}).get("max_edge", 0) / 10
        ]
    
    def _extract_composition_features(self, shoe_state: Dict) -> List[float]:
        """Extract deck composition features"""
        composition = shoe_state.get("composition", {})
        
        features = []
        
        # Key card densities
        for rank in ['4', '5', '6', '9']:
            if rank in composition:
                density = composition[rank].get("density", 0.0769)
            else:
                density = 0.0769
            features.append(density * 10)  # Scale up
        
        # High/Low ratio
        features.append(shoe_state.get("high_low_ratio", 1.0))
        
        # Cards dealt ratio
        cards_dealt = shoe_state.get("cards_dealt", 0)
        total_cards = 52 * shoe_state.get("decks", 8)
        features.append(cards_dealt / total_cards if total_cards > 0 else 0)
        
        return features[:6]
    
    def _extract_temporal_features(self, shoe_state: Dict, history: List[str]) -> List[float]:
        """Extract time-based features"""
        features = []
        
        # Position in shoe
        hands_played = shoe_state.get("hands_played", 0)
        features.append(hands_played / 80)  # Normalize by typical shoe length
        
        # Recent change rate
        if len(history) >= 10:
            recent_changes = sum(1 for i in range(1, 10) if history[-i] != history[-i-1])
            features.append(recent_changes / 9)
        else:
            features.append(0.5)
        
        # Cyclic patterns (every 8 hands)
        features.append(np.sin(2 * np.pi * hands_played / 8))
        features.append(np.cos(2 * np.pi * hands_played / 8))
        
        # Shoe progress
        features.append(shoe_state.get("cards_remaining", 416) / 416)
        
        return features[:5]
    
    def _create_sequence(self, current_features: List[float], history: List[str]) -> np.ndarray:
        """Create sequence for LSTM input"""
        sequence_length = 30
        feature_dim = 35
        
        # Initialize with zeros
        sequence = np.zeros((sequence_length, feature_dim))
        
        # Fill with historical features (simplified - would be more complex in practice)
        # For now, just repeat current features with slight variations
        for i in range(sequence_length):
            if i == sequence_length - 1:
                sequence[i] = current_features
            else:
                # Add some noise to historical features
                noise = np.random.normal(0, 0.01, feature_dim)
                sequence[i] = np.array(current_features) + noise
        
        return sequence
    
    # Helper methods
    def _get_current_streak(self, history: List[str]) -> int:
        if not history:
            return 0
        
        streak = 1
        for i in range(len(history) - 1, 0, -1):
            if history[i] == history[i-1]:
                streak += 1
            else:
                break
        return streak
    
    def _count_dragons(self, history: List[str]) -> float:
        """Count dragon patterns (7+ consecutive)"""
        if len(history) < 7:
            return 0.0
        
        max_streak = 0
        current = 1
        
        for i in range(1, len(history)):
            if history[i] == history[i-1]:
                current += 1
                max_streak = max(max_streak, current)
            else:
                current = 1
        
        return 1.0 if max_streak >= 7 else 0.0
    
    def _count_pingpong(self, history: List[str]) -> float:
        """Count alternating patterns"""
        if len(history) < 2:
            return 0.0
        
        alternations = sum(1 for i in range(1, len(history)) 
                          if history[i] != history[i-1])
        return alternations / (len(history) - 1)
    
    def _count_doubles(self, history: List[str]) -> float:
        """Count double patterns (exactly 2 consecutive)"""
        if len(history) < 2:
            return 0.0
        
        doubles = 0
        i = 0
        while i < len(history) - 1:
            if history[i] == history[i+1]:
                if (i == 0 or history[i] != history[i-1]) and \
                   (i >= len(history) - 2 or history[i+1] != history[i+2] if i+2 < len(history) else True):
                    doubles += 1
                i += 2
            else:
                i += 1
        
        return doubles / max(len(history) / 2, 1)
    
    def _calculate_trend(self, history: List[str]) -> float:
        """Calculate trend direction"""
        if len(history) < 5:
            return 0.0
        
        # Convert to numeric (B=1, P=0)
        numeric = [1 if h == 'B' else 0 for h in history]
        
        # Simple linear regression slope
        x = np.arange(len(numeric))
        y = np.array(numeric)
        
        slope = np.polyfit(x, y, 1)[0]
        
        return np.tanh(slope * 10)  # Normalize to [-1, 1]
    
    def _calculate_volatility(self, history: List[str]) -> float:
        """Calculate outcome volatility"""
        if len(history) < 5:
            return 0.5
        
        numeric = [1 if h == 'B' else 0 for h in history]
        returns = np.diff(numeric)
        
        return np.std(returns) if len(returns) > 0 else 0.5
    
    def _calculate_momentum(self, history: List[str]) -> float:
        """Calculate momentum indicator"""
        if len(history) < 10:
            return 0.0
        
        recent = history[-5:]
        older = history[-10:-5]
        
        recent_b = sum(1 for h in recent if h == 'B') / 5
        older_b = sum(1 for h in older if h == 'B') / 5
        
        return recent_b - older_b
    
    def _calculate_entropy(self, history: List[str]) -> float:
        """Calculate Shannon entropy"""
        if not history:
            return 0.0
        
        counts = {}
        for outcome in history:
            counts[outcome] = counts.get(outcome, 0) + 1
        
        total = len(history)
        entropy = 0
        
        for count in counts.values():
            if count > 0:
                p = count / total
                entropy -= p * np.log2(p)
        
        # Normalize by maximum entropy
        max_entropy = np.log2(3)  # 3 possible outcomes
        
        return entropy / max_entropy if max_entropy > 0 else 0.0
    
    def _calculate_autocorrelation(self, series: List[int], lag: int) -> float:
        """Calculate autocorrelation at given lag"""
        if len(series) <= lag:
            return 0.0
        
        series = np.array(series)
        mean = np.mean(series)
        c0 = np.sum((series - mean) ** 2) / len(series)
        c_lag = np.sum((series[:-lag] - mean) * (series[lag:] - mean)) / len(series)
        
        return c_lag / c0 if c0 != 0 else 0.0
    
    def _calculate_hurst_exponent(self, series: List[int]) -> float:
        """Calculate Hurst exponent for trend persistence"""
        if len(series) < 10:
            return 0.5
        
        series = np.array(series)
        lags = range(2, min(20, len(series) // 2))
        tau = [np.sqrt(np.std(np.subtract(series[lag:], series[:-lag]))) for lag in lags]
        
        # Linear fit to log-log plot
        if len(tau) > 0 and all(t > 0 for t in tau):
            poly = np.polyfit(np.log(list(lags)), np.log(tau), 1)
            return poly[0] * 2.0
        
        return 0.5  # Random walk


# ==================== CONFIDENCE CALIBRATOR ====================

class ConfidenceCalibrator:
    """
    Calibrate model confidence to match actual accuracy
    """
    
    def __init__(self):
        self.calibration_map = {}
        self.history = []
    
    def calibrate(self, raw_confidence: float) -> float:
        """Calibrate raw confidence score"""
        # Platt scaling (simplified)
        # In practice, this would be trained on validation data
        
        # Sigmoid calibration
        a = 2.0  # Scale parameter
        b = -1.0  # Bias parameter
        
        calibrated = 1 / (1 + np.exp(-(a * raw_confidence + b)))
        
        # Ensure reasonable bounds
        calibrated = np.clip(calibrated, 0.01, 0.99)
        
        return calibrated
    
    def update(self, raw_confidence: float, was_correct: bool):
        """Update calibration with new result"""
        self.history.append({
            "raw": raw_confidence,
            "correct": was_correct
        })
        
        # Retrain calibration periodically
        if len(self.history) % 100 == 0:
            self._retrain()
    
    def _retrain(self):
        """Retrain calibration mapping"""
        if len(self.history) < 100:
            return
        
        # Group by confidence buckets
        buckets = {}
        for item in self.history:
            bucket = round(item["raw"], 1)
            if bucket not in buckets:
                buckets[bucket] = {"total": 0, "correct": 0}
            
            buckets[bucket]["total"] += 1
            if item["correct"]:
                buckets[bucket]["correct"] += 1
        
        # Update calibration map
        for bucket, stats in buckets.items():
            if stats["total"] >= 10:
                actual_accuracy = stats["correct"] / stats["total"]
                self.calibration_map[bucket] = actual_accuracy


# ==================== ADVANCED PREDICTOR ====================

class AdvancedPredictor:
    """
    Advanced prediction system with ensemble and calibration
    """
    
    def __init__(self, model_path: str = "./ml-training/models/"):
        if not TORCH_AVAILABLE:
            raise ImportError("PyTorch is required for AdvancedPredictor")
        
        self.model_path = Path(model_path)
        self.model_path.mkdir(parents=True, exist_ok=True)
        
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.models = {}  # Ensemble of models
        self.feature_extractor = FeatureExtractor()
        self.calibrator = ConfidenceCalibrator()
        
        # Performance tracking
        self.prediction_cache = {}
        self.performance_metrics = {
            "predictions_made": 0,
            "cache_hits": 0,
            "average_confidence": 0,
            "accuracy_buffer": []
        }
    
    def load_model(self, model_name: str = "latest"):
        """Load trained model"""
        model_file = self.model_path / f"baccarat_lstm_{model_name}.pth"
        
        if not model_file.exists():
            raise FileNotFoundError(f"Model {model_file} not found")
        
        config = ModelConfig()
        model = BaccaratLSTM(config).to(self.device)
        
        checkpoint = torch.load(model_file, map_location=self.device)
        model.load_state_dict(checkpoint['model_state_dict'])
        model.eval()
        
        self.models[model_name] = model
        
        # Load calibrator if exists
        calibrator_file = self.model_path / f"calibrator_{model_name}.pkl"
        if calibrator_file.exists():
            with open(calibrator_file, 'rb') as f:
                self.calibrator = pickle.load(f)
    
    def predict(self, shoe_state: Dict, history: List[str]) -> Dict:
        """
        Make prediction with ensemble and calibration
        """
        # Check cache
        cache_key = self._generate_cache_key(shoe_state, history)
        if cache_key in self.prediction_cache:
            self.performance_metrics["cache_hits"] += 1
            return self.prediction_cache[cache_key]
        
        # Extract features
        features = self.feature_extractor.extract_all_features(shoe_state, history)
        
        # Prepare input tensor
        x = torch.FloatTensor(features).unsqueeze(0).to(self.device)
        
        # Ensemble prediction
        all_predictions = []
        all_confidences = []
        
        with torch.no_grad():
            for model_name, model in self.models.items():
                probs, conf = model(x)
                all_predictions.append(probs.cpu().numpy())
                all_confidences.append(conf.cpu().numpy())
        
        # Aggregate predictions
        if all_predictions:
            # Weighted average based on confidence
            weights = np.array(all_confidences)
            weights = weights / weights.sum()
            
            final_probs = np.average(all_predictions, axis=0, weights=weights.flatten())[0]
            final_confidence = np.mean(all_confidences)
        else:
            # Fallback to statistical prediction
            final_probs = np.array([0.4586, 0.4462, 0.0952])
            final_confidence = 0.5
        
        # Calibrate confidence
        calibrated_confidence = self.calibrator.calibrate(final_confidence)
        
        # Determine recommendation
        outcomes = ['B', 'P', 'T']
        best_idx = np.argmax(final_probs)
        recommendation = outcomes[best_idx]
        
        # Calculate edge
        edge = self._calculate_edge(final_probs, shoe_state)
        
        # Build response
        prediction = {
            "recommendation": recommendation,
            "probabilities": {
                "B": float(final_probs[0]),
                "P": float(final_probs[1]),
                "T": float(final_probs[2])
            },
            "confidence": float(final_confidence),
            "calibrated_confidence": float(calibrated_confidence),
            "edge_pct": edge,
            "ensemble_size": len(self.models),
            "features_used": len(features[0]) if len(features) > 0 else 0,
            "cache_key": cache_key
        }
        
        # Cache result
        self.prediction_cache[cache_key] = prediction
        
        # Update metrics
        self.performance_metrics["predictions_made"] += 1
        self.performance_metrics["average_confidence"] = (
            (self.performance_metrics["average_confidence"] * 
             (self.performance_metrics["predictions_made"] - 1) +
             calibrated_confidence) / 
            self.performance_metrics["predictions_made"]
        )
        
        return prediction
    
    def _calculate_edge(self, probabilities: np.ndarray, shoe_state: Dict) -> float:
        """Calculate betting edge"""
        # Get card counting edge
        counting_edge = shoe_state.get("edge", {}).get("max_edge", 0)
        
        # Calculate probability edge
        theoretical = [0.4586, 0.4462, 0.0952]
        prob_edge = max(probabilities - theoretical) * 100
        
        # Combine edges
        total_edge = (counting_edge + prob_edge) / 2
        
        return round(total_edge, 3)
    
    def _generate_cache_key(self, shoe_state: Dict, history: List[str]) -> str:
        """Generate cache key for prediction"""
        # Use last 10 hands and key shoe state
        recent_history = ''.join(history[-10:])
        shoe_key = f"{shoe_state.get('cards_remaining', 0)}_{shoe_state.get('true_count_b', 0):.2f}"
        
        return f"{recent_history}_{shoe_key}"
    
    def update_accuracy(self, prediction: Dict, actual: str):
        """Update accuracy tracking"""
        was_correct = prediction["recommendation"] == actual
        
        self.performance_metrics["accuracy_buffer"].append(was_correct)
        
        # Keep last 1000 predictions
        if len(self.performance_metrics["accuracy_buffer"]) > 1000:
            self.performance_metrics["accuracy_buffer"].pop(0)
    
    def get_performance_stats(self) -> Dict:
        """Get performance statistics"""
        accuracy_buffer = self.performance_metrics["accuracy_buffer"]
        
        if accuracy_buffer:
            accuracy = sum(accuracy_buffer) / len(accuracy_buffer) * 100
        else:
            accuracy = 0
        
        cache_hit_rate = 0
        if self.performance_metrics["predictions_made"] > 0:
            cache_hit_rate = (self.performance_metrics["cache_hits"] / 
                            self.performance_metrics["predictions_made"] * 100)
        
        return {
            "predictions_made": self.performance_metrics["predictions_made"],
            "cache_hit_rate": round(cache_hit_rate, 2),
            "average_confidence": round(self.performance_metrics["average_confidence"], 2),
            "recent_accuracy": round(accuracy, 2),
            "models_loaded": len(self.models),
            "device": str(self.device)
        }
