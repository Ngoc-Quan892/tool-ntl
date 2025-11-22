"""
LSTM-based ML model for Baccarat prediction.

This module provides:
- LSTM neural network implementation
- Feature engineering pipeline
- Model architecture definition
"""
from __future__ import annotations

import os
import pickle
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import numpy as np

try:
    import tensorflow as tf
    from tensorflow import keras
    from tensorflow.keras import layers, models, callbacks
    TENSORFLOW_AVAILABLE = True
except ImportError:
    TENSORFLOW_AVAILABLE = False
    # Fallback will be used

try:
    from sklearn.preprocessing import StandardScaler, LabelEncoder
    from sklearn.model_selection import train_test_split
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False


# ==================== FEATURE ENGINEERING ====================

class FeatureEngineer:
    """
    Feature engineering for Baccarat sequences.
    
    Extracts features from historical outcomes including:
    - Sequence patterns
    - Streak indicators
    - Statistical features
    - Roadmap features
    """
    
    def __init__(self, sequence_length: int = 30):
        """
        Initialize feature engineer.
        
        Args:
            sequence_length: Length of sequence to use for features
        """
        self.sequence_length = sequence_length
        self.scaler = StandardScaler() if SKLEARN_AVAILABLE else None
    
    def encode_outcomes(self, outcomes: List[str]) -> np.ndarray:
        """
        Encode outcomes to numeric values.
        
        Args:
            outcomes: List of outcomes ('B', 'P', 'T')
            
        Returns:
            Encoded array (B=1, P=0, T=0.5)
        """
        encoding = {'B': 1.0, 'P': 0.0, 'T': 0.5}
        return np.array([encoding.get(o, 0.5) for o in outcomes], dtype=np.float32)
    
    def extract_sequence_features(self, outcomes: List[str]) -> np.ndarray:
        """
        Extract sequence-based features.
        
        Args:
            outcomes: List of outcomes
            
        Returns:
            Feature array
        """
        if len(outcomes) < 2:
            return np.zeros((self.sequence_length,), dtype=np.float32)
        
        # Encode outcomes
        encoded = self.encode_outcomes(outcomes[-self.sequence_length:])
        
        # Pad if necessary
        if len(encoded) < self.sequence_length:
            padding = np.zeros(self.sequence_length - len(encoded), dtype=np.float32)
            encoded = np.concatenate([padding, encoded])
        
        return encoded[:self.sequence_length]
    
    def extract_statistical_features(self, outcomes: List[str]) -> np.ndarray:
        """
        Extract statistical features from recent history.
        
        Args:
            outcomes: List of outcomes
            
        Returns:
            Statistical feature array
        """
        if not outcomes:
            return np.zeros(10, dtype=np.float32)
        
        recent = outcomes[-50:] if len(outcomes) >= 50 else outcomes
        no_ties = [o for o in recent if o != 'T']
        
        features = []
        
        # Counts
        banker_count = recent.count('B')
        player_count = recent.count('P')
        tie_count = recent.count('T')
        total = len(recent)
        
        if total > 0:
            features.extend([
                banker_count / total,
                player_count / total,
                tie_count / total,
            ])
        else:
            features.extend([0.0, 0.0, 0.0])
        
        # Streaks
        max_banker_streak = self._calculate_max_streak(recent, 'B')
        max_player_streak = self._calculate_max_streak(recent, 'P')
        features.extend([
            max_banker_streak / 10.0,  # Normalize
            max_player_streak / 10.0,
        ])
        
        # Recent trend (last 5)
        if len(no_ties) >= 5:
            last_5 = no_ties[-5:]
            banker_trend = last_5.count('B') / 5.0
            features.append(banker_trend)
        else:
            features.append(0.5)
        
        # Alternation rate
        if len(no_ties) >= 2:
            alternations = sum(1 for i in range(1, len(no_ties)) if no_ties[i] != no_ties[i-1])
            alt_rate = alternations / (len(no_ties) - 1) if len(no_ties) > 1 else 0.0
            features.append(alt_rate)
        else:
            features.append(0.0)
        
        # Variance in recent outcomes
        if len(no_ties) >= 10:
            encoded_recent = self.encode_outcomes(no_ties[-10:])
            variance = np.var(encoded_recent)
            features.append(variance)
        else:
            features.append(0.0)
        
        # Mean of recent outcomes
        if len(no_ties) >= 10:
            encoded_recent = self.encode_outcomes(no_ties[-10:])
            mean_val = np.mean(encoded_recent)
            features.append(mean_val)
        else:
            features.append(0.5)
        
        # Ensure we have exactly 10 features
        while len(features) < 10:
            features.append(0.0)
        
        return np.array(features[:10], dtype=np.float32)
    
    def extract_features(self, outcomes: List[str]) -> Tuple[np.ndarray, np.ndarray]:
        """
        Extract all features from outcomes.
        
        Args:
            outcomes: List of outcomes
            
        Returns:
            Tuple of (sequence_features, statistical_features)
        """
        seq_features = self.extract_sequence_features(outcomes)
        stat_features = self.extract_statistical_features(outcomes)
        
        return seq_features, stat_features
    
    def _calculate_max_streak(self, outcomes: List[str], target: str) -> int:
        """Calculate maximum streak length."""
        max_streak = 0
        current_streak = 0
        
        for outcome in outcomes:
            if outcome == target:
                current_streak += 1
                max_streak = max(max_streak, current_streak)
            else:
                current_streak = 0
        
        return max_streak


# ==================== LSTM MODEL ====================

class LSTMPredictor:
    """
    LSTM-based predictor for Baccarat outcomes.
    
    Uses bidirectional LSTM to learn patterns from sequences.
    """
    
    def __init__(
        self,
        sequence_length: int = 30,
        lstm_units: int = 64,
        dense_units: int = 32,
        dropout_rate: float = 0.2,
        learning_rate: float = 0.001
    ):
        """
        Initialize LSTM model.
        
        Args:
            sequence_length: Length of input sequences
            lstm_units: Number of LSTM units
            dense_units: Number of dense layer units
            dropout_rate: Dropout rate
            learning_rate: Learning rate for optimizer
        """
        self.sequence_length = sequence_length
        self.lstm_units = lstm_units
        self.dense_units = dense_units
        self.dropout_rate = dropout_rate
        self.learning_rate = learning_rate
        
        self.model: Optional[Any] = None
        self.feature_engineer = FeatureEngineer(sequence_length=sequence_length)
        self.is_compiled = False
    
    def build_model(self) -> None:
        """Build the LSTM model architecture."""
        if not TENSORFLOW_AVAILABLE:
            raise ImportError("TensorFlow is required for LSTM model")
        
        # Input for sequence features
        sequence_input = keras.Input(
            shape=(self.sequence_length, 1),
            name='sequence_input'
        )
        
        # Bidirectional LSTM layers
        lstm1 = layers.Bidirectional(
            layers.LSTM(self.lstm_units, return_sequences=True)
        )(sequence_input)
        lstm1 = layers.Dropout(self.dropout_rate)(lstm1)
        
        lstm2 = layers.Bidirectional(
            layers.LSTM(self.lstm_units // 2, return_sequences=False)
        )(lstm1)
        lstm2 = layers.Dropout(self.dropout_rate)(lstm2)
        
        # Input for statistical features
        stat_input = keras.Input(shape=(10,), name='statistical_input')
        stat_dense = layers.Dense(self.dense_units, activation='relu')(stat_input)
        stat_dense = layers.Dropout(self.dropout_rate)(stat_dense)
        
        # Concatenate LSTM output with statistical features
        concatenated = layers.concatenate([lstm2, stat_dense])
        
        # Dense layers
        dense1 = layers.Dense(self.dense_units, activation='relu')(concatenated)
        dense1 = layers.Dropout(self.dropout_rate)(dense1)
        
        dense2 = layers.Dense(self.dense_units // 2, activation='relu')(dense1)
        dense2 = layers.Dropout(self.dropout_rate)(dense2)
        
        # Output layer (2 classes: Banker or Player)
        output = layers.Dense(2, activation='softmax', name='prediction')(dense2)
        
        # Create model
        self.model = models.Model(
            inputs=[sequence_input, stat_input],
            outputs=output
        )
        
        # Compile model
        optimizer = keras.optimizers.Adam(learning_rate=self.learning_rate)
        self.model.compile(
            optimizer=optimizer,
            loss='categorical_crossentropy',
            metrics=['accuracy', 'precision', 'recall']
        )
        
        self.is_compiled = True
    
    def prepare_training_data(
        self,
        sequences: List[List[str]],
        labels: List[str]
    ) -> Tuple[Tuple[np.ndarray, np.ndarray], np.ndarray]:
        """
        Prepare training data from sequences and labels.
        
        Args:
            sequences: List of outcome sequences
            labels: List of labels ('B' or 'P')
            
        Returns:
            Tuple of (X_sequence, X_stat), y
        """
        X_sequence = []
        X_stat = []
        y = []
        
        for seq, label in zip(sequences, labels):
            seq_feat, stat_feat = self.feature_engineer.extract_features(seq)
            
            # Reshape sequence for LSTM input
            seq_feat = seq_feat.reshape(-1, 1)
            
            X_sequence.append(seq_feat)
            X_stat.append(stat_feat)
            
            # Encode label (B=1, P=0)
            if label == 'B':
                y.append([1.0, 0.0])
            else:
                y.append([0.0, 1.0])
        
        return (
            (np.array(X_sequence), np.array(X_stat)),
            np.array(y, dtype=np.float32)
        )
    
    def train(
        self,
        X_sequence: np.ndarray,
        X_stat: np.ndarray,
        y: np.ndarray,
        validation_split: float = 0.2,
        epochs: int = 50,
        batch_size: int = 32,
        verbose: int = 1
    ) -> Dict[str, Any]:
        """
        Train the LSTM model.
        
        Args:
            X_sequence: Sequence features
            X_stat: Statistical features
            y: Labels
            validation_split: Validation split ratio
            epochs: Number of training epochs
            batch_size: Batch size
            verbose: Verbosity level
            
        Returns:
            Training history
        """
        if self.model is None:
            self.build_model()
        
        # Callbacks
        callbacks_list = [
            callbacks.EarlyStopping(
                monitor='val_loss',
                patience=10,
                restore_best_weights=True
            ),
            callbacks.ReduceLROnPlateau(
                monitor='val_loss',
                factor=0.5,
                patience=5,
                min_lr=1e-6
            ),
            callbacks.ModelCheckpoint(
                filepath='best_model.h5',
                monitor='val_loss',
                save_best_only=True,
                verbose=0
            )
        ]
        
        # Train
        history = self.model.fit(
            [X_sequence, X_stat],
            y,
            validation_split=validation_split,
            epochs=epochs,
            batch_size=batch_size,
            callbacks=callbacks_list,
            verbose=verbose
        )
        
        return {
            'loss': history.history.get('loss', []),
            'accuracy': history.history.get('accuracy', []),
            'val_loss': history.history.get('val_loss', []),
            'val_accuracy': history.history.get('val_accuracy', []),
        }
    
    def predict(
        self,
        outcomes: List[str]
    ) -> Tuple[str, float, np.ndarray]:
        """
        Make prediction from outcomes.
        
        Args:
            outcomes: List of historical outcomes
            
        Returns:
            Tuple of (prediction, confidence, probabilities)
        """
        if self.model is None:
            raise ValueError("Model not built or loaded")
        
        # Extract features
        seq_feat, stat_feat = self.feature_engineer.extract_features(outcomes)
        
        # Reshape for model input
        seq_feat = seq_feat.reshape(1, self.sequence_length, 1)
        stat_feat = stat_feat.reshape(1, -1)
        
        # Predict
        probabilities = self.model.predict([seq_feat, stat_feat], verbose=0)[0]
        
        # Get prediction and confidence
        banker_prob = probabilities[0]
        player_prob = probabilities[1]
        
        if banker_prob > player_prob:
            prediction = 'B'
            confidence = float(banker_prob)
        else:
            prediction = 'P'
            confidence = float(player_prob)
        
        return prediction, confidence, probabilities
    
    def save(self, filepath: str) -> None:
        """
        Save model and feature engineer.
        
        Args:
            filepath: Path to save model
        """
        if self.model is None:
            raise ValueError("No model to save")
        
        # Create directory if needed
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        
        # Save model
        model_path = f"{filepath}.h5"
        self.model.save(model_path)
        
        # Save feature engineer and metadata
        metadata = {
            'sequence_length': self.sequence_length,
            'lstm_units': self.lstm_units,
            'dense_units': self.dense_units,
            'dropout_rate': self.dropout_rate,
            'learning_rate': self.learning_rate,
            'feature_engineer': self.feature_engineer,
        }
        
        metadata_path = f"{filepath}_metadata.pkl"
        with open(metadata_path, 'wb') as f:
            pickle.dump(metadata, f)
    
    def load(self, filepath: str) -> None:
        """
        Load model and feature engineer.
        
        Args:
            filepath: Path to load model from
        """
        if not TENSORFLOW_AVAILABLE:
            raise ImportError("TensorFlow is required to load model")
        
        # Load model
        model_path = f"{filepath}.h5"
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model file not found: {model_path}")
        
        self.model = keras.models.load_model(model_path)
        self.is_compiled = True
        
        # Load metadata
        metadata_path = f"{filepath}_metadata.pkl"
        if os.path.exists(metadata_path):
            with open(metadata_path, 'rb') as f:
                metadata = pickle.load(f)
            
            self.sequence_length = metadata.get('sequence_length', 30)
            self.lstm_units = metadata.get('lstm_units', 64)
            self.dense_units = metadata.get('dense_units', 32)
            self.dropout_rate = metadata.get('dropout_rate', 0.2)
            self.learning_rate = metadata.get('learning_rate', 0.001)
            self.feature_engineer = metadata.get('feature_engineer', FeatureEngineer())
        else:
            # Default feature engineer
            self.feature_engineer = FeatureEngineer(sequence_length=self.sequence_length)


# ==================== MODEL FACTORY ====================

def create_model(
    sequence_length: int = 30,
    lstm_units: int = 64,
    dense_units: int = 32,
    dropout_rate: float = 0.2,
    learning_rate: float = 0.001
) -> LSTMPredictor:
    """
    Factory function to create LSTM model.
    
    Args:
        sequence_length: Length of input sequences
        lstm_units: Number of LSTM units
        dense_units: Number of dense layer units
        dropout_rate: Dropout rate
        learning_rate: Learning rate
        
    Returns:
        LSTMPredictor instance
    """
    model = LSTMPredictor(
        sequence_length=sequence_length,
        lstm_units=lstm_units,
        dense_units=dense_units,
        dropout_rate=dropout_rate,
        learning_rate=learning_rate
    )
    model.build_model()
    return model

