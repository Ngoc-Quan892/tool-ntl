"""
Advanced feature engineering for Baccarat prediction.

This module provides:
- Advanced statistical features
- Pattern detection features
- Roadmap-based features
- Card counting features (EOR-based)
- Time-series features
- Feature selection and importance
- Feature scaling and normalization
"""
from __future__ import annotations

import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from collections import Counter, deque
from datetime import datetime
import math

try:
    from sklearn.preprocessing import StandardScaler, MinMaxScaler, RobustScaler
    from sklearn.feature_selection import SelectKBest, f_classif, mutual_info_classif
    from sklearn.decomposition import PCA
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False


# ==================== STATISTICAL FEATURES ====================

class StatisticalFeatureExtractor:
    """
    Extract advanced statistical features from outcome sequences.
    """
    
    def __init__(self, window_sizes: List[int] = [10, 20, 50, 100]):
        """
        Initialize statistical feature extractor.
        
        Args:
            window_sizes: List of window sizes for rolling statistics
        """
        self.window_sizes = window_sizes
    
    def extract(self, outcomes: List[str]) -> np.ndarray:
        """
        Extract all statistical features.
        
        Args:
            outcomes: List of outcomes
            
        Returns:
            Feature array
        """
        features = []
        
        # Remove ties for some calculations
        no_ties = [o for o in outcomes if o != 'T']
        
        if len(outcomes) == 0:
            return np.zeros(50, dtype=np.float32)
        
        # Basic counts and proportions
        features.extend(self._extract_counts(outcomes))
        
        # Rolling statistics for different windows
        for window in self.window_sizes:
            features.extend(self._extract_rolling_stats(outcomes, window))
        
        # Streak features
        features.extend(self._extract_streak_features(outcomes))
        
        # Pattern features
        features.extend(self._extract_pattern_features(outcomes))
        
        # Variance and volatility
        features.extend(self._extract_volatility_features(outcomes))
        
        # Trend features
        features.extend(self._extract_trend_features(outcomes))
        
        # Alternation features
        features.extend(self._extract_alternation_features(no_ties))
        
        # Ensure fixed size
        while len(features) < 50:
            features.append(0.0)
        
        return np.array(features[:50], dtype=np.float32)
    
    def _extract_counts(self, outcomes: List[str]) -> List[float]:
        """Extract count-based features."""
        if not outcomes:
            return [0.0] * 5
        
        total = len(outcomes)
        banker_count = outcomes.count('B')
        player_count = outcomes.count('P')
        tie_count = outcomes.count('T')
        
        return [
            banker_count / total if total > 0 else 0.0,
            player_count / total if total > 0 else 0.0,
            tie_count / total if total > 0 else 0.0,
            banker_count - player_count,  # Difference
            (banker_count - player_count) / total if total > 0 else 0.0  # Normalized difference
        ]
    
    def _extract_rolling_stats(
        self,
        outcomes: List[str],
        window: int
    ) -> List[float]:
        """Extract rolling statistics."""
        if len(outcomes) < window:
            return [0.0] * 5
        
        recent = outcomes[-window:]
        no_ties = [o for o in recent if o != 'T']
        
        if not no_ties:
            return [0.0] * 5
        
        # Encode outcomes
        encoded = np.array([1.0 if o == 'B' else 0.0 for o in no_ties], dtype=np.float32)
        
        return [
            np.mean(encoded),  # Mean (proportion of banker)
            np.std(encoded),   # Standard deviation
            np.var(encoded),   # Variance
            np.min(encoded),   # Minimum
            np.max(encoded)    # Maximum
        ]
    
    def _extract_streak_features(self, outcomes: List[str]) -> List[float]:
        """Extract streak-related features."""
        if not outcomes:
            return [0.0] * 6
        
        no_ties = [o for o in outcomes if o != 'T']
        
        if not no_ties:
            return [0.0] * 6
        
        # Current streak
        current_streak = self._calculate_current_streak(no_ties)
        
        # Max streaks
        max_banker_streak = self._calculate_max_streak(no_ties, 'B')
        max_player_streak = self._calculate_max_streak(no_ties, 'P')
        
        # Average streak length
        avg_streak = self._calculate_avg_streak(no_ties)
        
        # Streak count
        streak_count = self._count_streaks(no_ties)
        
        return [
            current_streak / 10.0,  # Normalized
            max_banker_streak / 10.0,
            max_player_streak / 10.0,
            avg_streak / 10.0,
            streak_count / len(no_ties) if no_ties else 0.0,
            (max_banker_streak - max_player_streak) / 10.0  # Streak difference
        ]
    
    def _extract_pattern_features(self, outcomes: List[str]) -> List[float]:
        """Extract pattern detection features."""
        if len(outcomes) < 5:
            return [0.0] * 5
        
        no_ties = [o for o in outcomes if o != 'T']
        
        if len(no_ties) < 5:
            return [0.0] * 5
        
        # Pattern repetition
        pattern_score = self._detect_pattern_repetition(no_ties[-10:])
        
        # Alternation pattern
        alternation_score = self._calculate_alternation_score(no_ties[-10:])
        
        # Clustering score
        clustering_score = self._calculate_clustering_score(no_ties[-10:])
        
        # Run length distribution
        run_length_entropy = self._calculate_run_length_entropy(no_ties[-10:])
        
        # Pattern stability
        stability_score = self._calculate_stability_score(no_ties[-10:])
        
        return [
            pattern_score,
            alternation_score,
            clustering_score,
            run_length_entropy,
            stability_score
        ]
    
    def _extract_volatility_features(self, outcomes: List[str]) -> List[float]:
        """Extract volatility features."""
        if len(outcomes) < 10:
            return [0.0] * 4
        
        no_ties = [o for o in outcomes if o != 'T']
        
        if len(no_ties) < 10:
            return [0.0] * 4
        
        recent = no_ties[-20:]
        encoded = np.array([1.0 if o == 'B' else 0.0 for o in recent], dtype=np.float32)
        
        # Rolling variance
        rolling_var = np.var(encoded)
        
        # Coefficient of variation
        mean_val = np.mean(encoded)
        cv = rolling_var / (mean_val + 1e-10)
        
        # Range
        value_range = np.max(encoded) - np.min(encoded)
        
        # Autocorrelation (lag 1)
        if len(encoded) > 1:
            autocorr = np.corrcoef(encoded[:-1], encoded[1:])[0, 1]
            if np.isnan(autocorr):
                autocorr = 0.0
        else:
            autocorr = 0.0
        
        return [
            rolling_var,
            cv,
            value_range,
            autocorr
        ]
    
    def _extract_trend_features(self, outcomes: List[str]) -> List[float]:
        """Extract trend features."""
        if len(outcomes) < 5:
            return [0.0] * 4
        
        no_ties = [o for o in outcomes if o != 'T']
        
        if len(no_ties) < 5:
            return [0.0] * 4
        
        recent = no_ties[-10:]
        encoded = np.array([1.0 if o == 'B' else 0.0 for o in recent], dtype=np.float32)
        
        # Linear trend
        x = np.arange(len(encoded))
        if len(encoded) > 1:
            trend_slope = np.polyfit(x, encoded, 1)[0]
        else:
            trend_slope = 0.0
        
        # Recent vs earlier trend
        if len(encoded) >= 6:
            early_mean = np.mean(encoded[:len(encoded)//2])
            recent_mean = np.mean(encoded[len(encoded)//2:])
            trend_change = recent_mean - early_mean
        else:
            trend_change = 0.0
        
        # Momentum (rate of change)
        if len(encoded) >= 3:
            momentum = encoded[-1] - encoded[-3]
        else:
            momentum = 0.0
        
        # Acceleration (second derivative)
        if len(encoded) >= 3:
            acceleration = (encoded[-1] - encoded[-2]) - (encoded[-2] - encoded[-3])
        else:
            acceleration = 0.0
        
        return [
            trend_slope,
            trend_change,
            momentum,
            acceleration
        ]
    
    def _extract_alternation_features(self, no_ties: List[str]) -> List[float]:
        """Extract alternation pattern features."""
        if len(no_ties) < 2:
            return [0.0] * 3
        
        # Alternation rate
        alternations = sum(1 for i in range(1, len(no_ties)) if no_ties[i] != no_ties[i-1])
        alt_rate = alternations / (len(no_ties) - 1) if len(no_ties) > 1 else 0.0
        
        # Expected alternation (random would be ~0.5)
        expected_alt = 0.5
        alt_deviation = alt_rate - expected_alt
        
        # Alternation streak (how many consecutive alternations)
        alt_streak = 0
        for i in range(1, min(10, len(no_ties))):
            if no_ties[i] != no_ties[i-1]:
                alt_streak += 1
            else:
                break
        
        return [
            alt_rate,
            alt_deviation,
            alt_streak / 10.0
        ]
    
    # Helper methods
    def _calculate_current_streak(self, outcomes: List[str]) -> int:
        """Calculate current streak length."""
        if not outcomes:
            return 0
        
        last = outcomes[-1]
        streak = 1
        
        for i in range(len(outcomes) - 2, -1, -1):
            if outcomes[i] == last:
                streak += 1
            else:
                break
        
        return streak
    
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
    
    def _calculate_avg_streak(self, outcomes: List[str]) -> float:
        """Calculate average streak length."""
        if not outcomes:
            return 0.0
        
        streaks = []
        current_streak = 1
        
        for i in range(1, len(outcomes)):
            if outcomes[i] == outcomes[i-1]:
                current_streak += 1
            else:
                if current_streak > 0:
                    streaks.append(current_streak)
                current_streak = 1
        
        if current_streak > 0:
            streaks.append(current_streak)
        
        return np.mean(streaks) if streaks else 0.0
    
    def _count_streaks(self, outcomes: List[str]) -> int:
        """Count number of streaks."""
        if len(outcomes) < 2:
            return 0
        
        streak_count = 0
        for i in range(1, len(outcomes)):
            if outcomes[i] != outcomes[i-1]:
                streak_count += 1
        
        return streak_count
    
    def _detect_pattern_repetition(self, outcomes: List[str]) -> float:
        """Detect pattern repetition score."""
        if len(outcomes) < 4:
            return 0.0
        
        # Check for repeating patterns of length 2-4
        max_repetition = 0.0
        
        for pattern_len in [2, 3, 4]:
            if len(outcomes) >= pattern_len * 2:
                pattern = tuple(outcomes[-pattern_len:])
                count = 0
                
                for i in range(len(outcomes) - pattern_len * 2, -1, -pattern_len):
                    if tuple(outcomes[i:i+pattern_len]) == pattern:
                        count += 1
                    else:
                        break
                
                repetition_score = count / (len(outcomes) / pattern_len)
                max_repetition = max(max_repetition, repetition_score)
        
        return max_repetition
    
    def _calculate_alternation_score(self, outcomes: List[str]) -> float:
        """Calculate alternation pattern score."""
        if len(outcomes) < 2:
            return 0.0
        
        alternations = sum(1 for i in range(1, len(outcomes)) if outcomes[i] != outcomes[i-1])
        return alternations / (len(outcomes) - 1)
    
    def _calculate_clustering_score(self, outcomes: List[str]) -> float:
        """Calculate clustering score (how grouped outcomes are)."""
        if len(outcomes) < 3:
            return 0.0
        
        # Count transitions
        transitions = sum(1 for i in range(1, len(outcomes)) if outcomes[i] != outcomes[i-1])
        # Lower transitions = more clustering
        clustering = 1.0 - (transitions / (len(outcomes) - 1))
        
        return clustering
    
    def _calculate_run_length_entropy(self, outcomes: List[str]) -> float:
        """Calculate entropy of run lengths."""
        if not outcomes:
            return 0.0
        
        run_lengths = []
        current_run = 1
        
        for i in range(1, len(outcomes)):
            if outcomes[i] == outcomes[i-1]:
                current_run += 1
            else:
                run_lengths.append(current_run)
                current_run = 1
        
        run_lengths.append(current_run)
        
        if not run_lengths:
            return 0.0
        
        # Calculate entropy
        counts = Counter(run_lengths)
        total = sum(counts.values())
        entropy = -sum((count/total) * math.log2(count/total + 1e-10) for count in counts.values())
        
        return entropy / math.log2(len(set(run_lengths)) + 1)  # Normalized
    
    def _calculate_stability_score(self, outcomes: List[str]) -> float:
        """Calculate stability score (consistency)."""
        if len(outcomes) < 2:
            return 0.0
        
        # Variance of outcomes
        encoded = np.array([1.0 if o == 'B' else 0.0 for o in outcomes], dtype=np.float32)
        variance = np.var(encoded)
        
        # Stability is inverse of variance
        stability = 1.0 - variance
        
        return max(0.0, min(1.0, stability))


# ==================== ROADMAP FEATURES ====================

class RoadmapFeatureExtractor:
    """
    Extract features from Baccarat roadmaps (Big Road, Small Road, etc.).
    """
    
    def __init__(self):
        """Initialize roadmap feature extractor."""
        pass
    
    def extract(self, outcomes: List[str]) -> np.ndarray:
        """
        Extract roadmap-based features.
        
        Args:
            outcomes: List of outcomes
            
        Returns:
            Feature array
        """
        features = []
        
        if len(outcomes) < 3:
            return np.zeros(15, dtype=np.float32)
        
        no_ties = [o for o in outcomes if o != 'T']
        
        if len(no_ties) < 3:
            return np.zeros(15, dtype=np.float32)
        
        # Big Road features
        features.extend(self._extract_big_road_features(no_ties))
        
        # Small Road features
        features.extend(self._extract_small_road_features(no_ties))
        
        # Cockroach Pig features
        features.extend(self._extract_cockroach_pig_features(no_ties))
        
        return np.array(features[:15], dtype=np.float32)
    
    def _extract_big_road_features(self, outcomes: List[str]) -> List[float]:
        """Extract Big Road features."""
        if len(outcomes) < 2:
            return [0.0] * 5
        
        # Simulate Big Road (simplified)
        # Count consecutive same outcomes
        recent = outcomes[-20:] if len(outcomes) >= 20 else outcomes
        
        banker_columns = 0
        player_columns = 0
        max_column_height = 0
        current_column = 1
        last_outcome = recent[0] if recent else None
        
        for outcome in recent[1:]:
            if outcome == last_outcome:
                current_column += 1
                max_column_height = max(max_column_height, current_column)
            else:
                if last_outcome == 'B':
                    banker_columns += 1
                elif last_outcome == 'P':
                    player_columns += 1
                current_column = 1
                last_outcome = outcome
        
        # Add last column
        if last_outcome == 'B':
            banker_columns += 1
        elif last_outcome == 'P':
            player_columns += 1
        
        return [
            banker_columns / len(recent) if recent else 0.0,
            player_columns / len(recent) if recent else 0.0,
            max_column_height / 10.0,  # Normalized
            (banker_columns - player_columns) / len(recent) if recent else 0.0,
            current_column / 10.0  # Current column height
        ]
    
    def _extract_small_road_features(self, outcomes: List[str]) -> List[float]:
        """Extract Small Road features."""
        # Simplified Small Road (alternation pattern)
        if len(outcomes) < 4:
            return [0.0] * 5
        
        recent = outcomes[-15:] if len(outcomes) >= 15 else outcomes
        
        # Check for pairs
        pairs = 0
        for i in range(0, len(recent) - 1, 2):
            if i + 1 < len(recent) and recent[i] == recent[i+1]:
                pairs += 1
        
        # Alternation pattern
        alternations = sum(1 for i in range(1, len(recent)) if recent[i] != recent[i-1])
        alt_rate = alternations / (len(recent) - 1) if len(recent) > 1 else 0.0
        
        return [
            pairs / (len(recent) / 2) if recent else 0.0,
            alt_rate,
            0.0,  # Placeholder
            0.0,  # Placeholder
            0.0   # Placeholder
        ]
    
    def _extract_cockroach_pig_features(self, outcomes: List[str]) -> List[float]:
        """Extract Cockroach Pig features."""
        # Simplified Cockroach Pig (diagonal patterns)
        if len(outcomes) < 3:
            return [0.0] * 5
        
        recent = outcomes[-12:] if len(outcomes) >= 12 else outcomes
        
        # Check for diagonal patterns (simplified)
        diagonal_score = 0.0
        
        # Pattern detection would be more complex in real implementation
        # This is a simplified version
        
        return [
            diagonal_score,
            0.0,  # Placeholder
            0.0,  # Placeholder
            0.0,  # Placeholder
            0.0   # Placeholder
        ]


# ==================== CARD COUNTING FEATURES ====================

class CardCountingFeatureExtractor:
    """
    Extract card counting features based on EOR (Effect of Removal) values.
    """
    
    # EOR values for Baccarat (from research)
    EOR_BANKER = {
        'A': -0.5470, '2': -0.4012, '3': -0.4064, '4': +0.5638,
        '5': +0.7753, '6': +0.4518, '7': +0.3428, '8': +0.1811,
        '9': -0.2897, '10': +0.5224, 'J': +0.5224, 'Q': +0.5224, 'K': +0.5224
    }
    
    EOR_PLAYER = {
        'A': +0.5287, '2': +0.3962, '3': +0.3981, '4': -0.5649,
        '5': -0.7804, '6': -0.4586, '7': -0.3451, '8': -0.1798,
        '9': +0.2819, '10': -0.5198, 'J': -0.5198, 'Q': -0.5198, 'K': -0.5198
    }
    
    def __init__(self, decks: int = 8):
        """
        Initialize card counting feature extractor.
        
        Args:
            decks: Number of decks in shoe
        """
        self.decks = decks
        self.total_cards = decks * 52
    
    def extract(self, removed_cards: List[str]) -> np.ndarray:
        """
        Extract card counting features.
        
        Args:
            removed_cards: List of removed cards (e.g., ['A', 'K', '5', ...])
            
        Returns:
            Feature array
        """
        if not removed_cards:
            return np.zeros(10, dtype=np.float32)
        
        # Count cards
        card_counts = Counter(removed_cards)
        cards_remaining = self.total_cards - len(removed_cards)
        
        if cards_remaining == 0:
            return np.zeros(10, dtype=np.float32)
        
        # Calculate running count for banker
        banker_running_count = sum(
            self.EOR_BANKER.get(card, 0.0) * count
            for card, count in card_counts.items()
        )
        
        # Calculate running count for player
        player_running_count = sum(
            self.EOR_PLAYER.get(card, 0.0) * count
            for card, count in card_counts.items()
        )
        
        # True count (normalized by decks remaining)
        decks_remaining = cards_remaining / 52.0
        banker_true_count = banker_running_count / (decks_remaining + 1e-10)
        player_true_count = player_running_count / (decks_remaining + 1e-10)
        
        # Penetration
        penetration = len(removed_cards) / self.total_cards
        
        # Card composition
        high_cards = sum(card_counts.get(card, 0) for card in ['10', 'J', 'Q', 'K', 'A'])
        low_cards = sum(card_counts.get(card, 0) for card in ['2', '3', '4', '5', '6'])
        high_low_ratio = high_cards / (low_cards + 1e-10)
        
        return np.array([
            banker_running_count,
            player_running_count,
            banker_true_count,
            player_true_count,
            penetration,
            high_low_ratio,
            high_cards / len(removed_cards) if removed_cards else 0.0,
            low_cards / len(removed_cards) if removed_cards else 0.0,
            (banker_true_count - player_true_count),
            cards_remaining / self.total_cards
        ], dtype=np.float32)


# ==================== COMPREHENSIVE FEATURE ENGINEER ====================

class AdvancedFeatureEngineer:
    """
    Comprehensive feature engineering combining all feature types.
    """
    
    def __init__(
        self,
        sequence_length: int = 50,
        window_sizes: List[int] = [10, 20, 50, 100],
        decks: int = 8,
        use_statistical: bool = True,
        use_roadmap: bool = True,
        use_card_counting: bool = True
    ):
        """
        Initialize advanced feature engineer.
        
        Args:
            sequence_length: Length of sequence features
            window_sizes: Window sizes for rolling statistics
            decks: Number of decks
            use_statistical: Enable statistical features
            use_roadmap: Enable roadmap features
            use_card_counting: Enable card counting features
        """
        self.sequence_length = sequence_length
        self.stat_extractor = StatisticalFeatureExtractor(window_sizes) if use_statistical else None
        self.roadmap_extractor = RoadmapFeatureExtractor() if use_roadmap else None
        self.card_counting_extractor = CardCountingFeatureExtractor(decks) if use_card_counting else None
        
        # Feature scalers
        self.scaler = StandardScaler() if SKLEARN_AVAILABLE else None
        self.is_fitted = False
    
    def extract_features(
        self,
        outcomes: List[str],
        removed_cards: Optional[List[str]] = None
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Extract all features.
        
        Args:
            outcomes: List of outcomes
            removed_cards: Optional list of removed cards for counting
            
        Returns:
            Tuple of (sequence_features, statistical_features)
        """
        # Sequence features (encoded outcomes)
        seq_features = self._extract_sequence_features(outcomes)
        
        # Statistical features
        stat_features = []
        
        if self.stat_extractor:
            stat_features.extend(self.stat_extractor.extract(outcomes))
        
        if self.roadmap_extractor:
            roadmap_features = self.roadmap_extractor.extract(outcomes)
            stat_features.extend(roadmap_features)
        
        if self.card_counting_extractor and removed_cards:
            counting_features = self.card_counting_extractor.extract(removed_cards)
            stat_features.extend(counting_features)
        
        # Ensure fixed size
        while len(stat_features) < 80:
            stat_features.append(0.0)
        
        stat_features = np.array(stat_features[:80], dtype=np.float32)
        
        return seq_features, stat_features
    
    def _extract_sequence_features(self, outcomes: List[str]) -> np.ndarray:
        """Extract sequence features."""
        encoding = {'B': 1.0, 'P': 0.0, 'T': 0.5}
        encoded = np.array([encoding.get(o, 0.5) for o in outcomes], dtype=np.float32)
        
        # Pad or truncate
        if len(encoded) < self.sequence_length:
            padding = np.zeros(self.sequence_length - len(encoded), dtype=np.float32)
            encoded = np.concatenate([padding, encoded])
        else:
            encoded = encoded[-self.sequence_length:]
        
        return encoded[:self.sequence_length]
    
    def fit_scaler(self, X_stat: np.ndarray) -> None:
        """
        Fit feature scaler.
        
        Args:
            X_stat: Statistical features array
        """
        if self.scaler and SKLEARN_AVAILABLE:
            self.scaler.fit(X_stat)
            self.is_fitted = True
    
    def transform_features(self, X_stat: np.ndarray) -> np.ndarray:
        """
        Transform features using fitted scaler.
        
        Args:
            X_stat: Statistical features array
            
        Returns:
            Scaled features
        """
        if self.scaler and self.is_fitted:
            return self.scaler.transform(X_stat)
        return X_stat
    
    def fit_transform_features(self, X_stat: np.ndarray) -> np.ndarray:
        """
        Fit and transform features.
        
        Args:
            X_stat: Statistical features array
            
        Returns:
            Scaled features
        """
        if self.scaler and SKLEARN_AVAILABLE:
            return self.scaler.fit_transform(X_stat)
        return X_stat


# ==================== FEATURE SELECTION ====================

class FeatureSelector:
    """
    Feature selection for improving model performance.
    """
    
    def __init__(self, method: str = 'mutual_info', k: int = 50):
        """
        Initialize feature selector.
        
        Args:
            method: Selection method ('mutual_info', 'f_classif', 'pca')
            k: Number of features to select
        """
        self.method = method
        self.k = k
        self.selector = None
        self.is_fitted = False
    
    def fit(self, X: np.ndarray, y: np.ndarray) -> None:
        """
        Fit feature selector.
        
        Args:
            X: Feature matrix
            y: Labels
        """
        if not SKLEARN_AVAILABLE:
            return
        
        if self.method == 'mutual_info':
            self.selector = SelectKBest(
                score_func=mutual_info_classif,
                k=min(self.k, X.shape[1])
            )
        elif self.method == 'f_classif':
            self.selector = SelectKBest(
                score_func=f_classif,
                k=min(self.k, X.shape[1])
            )
        elif self.method == 'pca':
            self.selector = PCA(n_components=min(self.k, X.shape[1]))
        else:
            return
        
        self.selector.fit(X, y)
        self.is_fitted = True
    
    def transform(self, X: np.ndarray) -> np.ndarray:
        """
        Transform features.
        
        Args:
            X: Feature matrix
            
        Returns:
            Selected features
        """
        if self.selector and self.is_fitted:
            return self.selector.transform(X)
        return X
    
    def get_feature_importance(self) -> Optional[np.ndarray]:
        """
        Get feature importance scores.
        
        Returns:
            Importance scores
        """
        if self.selector and hasattr(self.selector, 'scores_'):
            return self.selector.scores_
        return None

