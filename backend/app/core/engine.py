"""
Core Baccarat Engine with exact card tracking and comprehensive counting
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from enum import Enum
import random
import uuid
from collections import Counter


# ==================== CONSTANTS ====================

# Effect of Removal (EOR) values for card counting
# Research-backed values from "The Theory of Blackjack" adapted for Baccarat
CARD_EOR_BANKER = {
    'A': -0.5470, '2': -0.4012, '3': -0.4064, '4': +0.5638, 
    '5': +0.7753, '6': +0.4518, '7': +0.3428, '8': +0.1811, 
    '9': -0.2897, '10': +0.5224, 'J': +0.5224, 'Q': +0.5224, 'K': +0.5224
}

CARD_EOR_PLAYER = {
    'A': +0.5287, '2': +0.3962, '3': +0.3981, '4': -0.5649,
    '5': -0.7804, '6': -0.4586, '7': -0.3451, '8': -0.1798,
    '9': +0.2819, '10': -0.5198, 'J': -0.5198, 'Q': -0.5198, 'K': -0.5198
}

# Theoretical probabilities (for reference)
THEORETICAL_PROB = {
    'BANKER': 0.458597,
    'PLAYER': 0.446247,
    'TIE': 0.095156
}

# Card values in Baccarat (mod 10)
CARD_VALUES = {
    'A': 1, '2': 2, '3': 3, '4': 4, '5': 5,
    '6': 6, '7': 7, '8': 8, '9': 9,
    '10': 0, 'J': 0, 'Q': 0, 'K': 0
}


# ==================== ENUMS ====================

class Outcome(str, Enum):
    """Hand outcome"""
    BANKER = "B"
    PLAYER = "P"
    TIE = "T"


class Suit(str, Enum):
    """Card suits"""
    SPADES = "♠"
    HEARTS = "♥"
    DIAMONDS = "♦"
    CLUBS = "♣"


# ==================== DATA CLASSES ====================

@dataclass(frozen=True)
class Card:
    """
    Immutable card representation
    """
    rank: str  # A, 2-10, J, Q, K
    suit: Suit
    
    @property
    def value(self) -> int:
        """Baccarat value (0-9)"""
        return CARD_VALUES[self.rank]
    
    def __str__(self) -> str:
        return f"{self.rank}{self.suit.value}"
    
    def __repr__(self) -> str:
        return f"Card({self.rank}{self.suit.value})"


@dataclass
class Hand:
    """
    Complete hand information
    """
    hand_id: str
    shoe_id: str
    hand_number: int
    
    # Cards
    banker_cards: List[Card]
    player_cards: List[Card]
    
    # Outcome
    result: Outcome
    
    # Metadata
    timestamp: datetime
    is_natural: bool
    dealing_time_ms: Optional[int] = None
    
    # Card counting state at this hand
    running_count_b: float = 0.0
    running_count_p: float = 0.0
    true_count_b: float = 0.0
    true_count_p: float = 0.0
    decks_remaining: float = 0.0
    
    @property
    def banker_total(self) -> int:
        """Banker final total (mod 10)"""
        return sum(c.value for c in self.banker_cards) % 10
    
    @property
    def player_total(self) -> int:
        """Player final total (mod 10)"""
        return sum(c.value for c in self.player_cards) % 10
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization"""
        return {
            "hand_id": self.hand_id,
            "shoe_id": self.shoe_id,
            "hand_number": self.hand_number,
            "banker_cards": [str(c) for c in self.banker_cards],
            "player_cards": [str(c) for c in self.player_cards],
            "banker_total": self.banker_total,
            "player_total": self.player_total,
            "result": self.result.value,
            "is_natural": self.is_natural,
            "timestamp": self.timestamp.isoformat(),
            "running_count_b": round(self.running_count_b, 4),
            "running_count_p": round(self.running_count_p, 4),
            "true_count_b": round(self.true_count_b, 4),
            "true_count_p": round(self.true_count_p, 4),
            "decks_remaining": round(self.decks_remaining, 2)
        }


# ==================== MAIN SHOE CLASS ====================

class EnhancedShoe:
    """
    Enhanced 8-deck shoe with exact card tracking and professional card counting
    """
    
    def __init__(self, decks: int = 8, shoe_id: Optional[str] = None,
                 reshuffle_point: int = 20):
        """
        Initialize shoe
        
        Args:
            decks: Number of decks (1-8)
            shoe_id: Unique identifier (auto-generated if None)
            reshuffle_point: Cards remaining when reshuffling
        """
        self.decks = decks
        self.shoe_id = shoe_id or str(uuid.uuid4())
        self.reshuffle_point = reshuffle_point
        
        # State
        self.cards: List[Card] = []
        self.hand_history: List[Hand] = []
        
        # Card counting
        self.running_count_b: float = 0.0
        self.running_count_p: float = 0.0
        self.cards_dealt: int = 0
        
        # Exact composition tracking
        self.cards_by_rank: Dict[str, int] = {}
        
        # Metadata
        self.created_at: datetime = datetime.now()
        self.reshuffled_count: int = 0
        
        # Initialize
        self.reset()
    
    def reset(self) -> None:
        """Reset shoe to fresh state"""
        ranks = ['A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K']
        suits = list(Suit)
        
        # Create all cards
        self.cards = []
        for _ in range(self.decks):
            for suit in suits:
                for rank in ranks:
                    self.cards.append(Card(rank=rank, suit=suit))
        
        # Shuffle
        random.shuffle(self.cards)
        
        # Reset counts
        self.running_count_b = 0.0
        self.running_count_p = 0.0
        self.cards_dealt = 0
        
        # Reset composition tracking
        self.cards_by_rank = {rank: 4 * self.decks for rank in ranks}
        
        # Clear history
        self.hand_history = []
        
        # Increment reshuffle counter
        if hasattr(self, 'reshuffled_count'):
            self.reshuffled_count += 1
        else:
            self.reshuffled_count = 0
    
    def draw_card(self) -> Card:
        """
        Draw one card and update all counts
        
        Returns:
            Card drawn
        
        Raises:
            ValueError: If shoe needs reshuffling
        """
        if len(self.cards) < self.reshuffle_point:
            raise ValueError(f"Shoe needs reshuffling (< {self.reshuffle_point} cards)")
        
        card = self.cards.pop()
        self.cards_dealt += 1
        
        # Update rank composition
        self.cards_by_rank[card.rank] -= 1
        
        # Update running counts
        self.running_count_b += CARD_EOR_BANKER[card.rank]
        self.running_count_p += CARD_EOR_PLAYER[card.rank]
        
        return card
    
    def get_true_counts(self) -> Tuple[float, float]:
        """
        Calculate true counts for both sides
        
        Returns:
            (true_count_banker, true_count_player)
        """
        decks_remaining = max(len(self.cards) / 52, 0.5)
        
        tc_b = self.running_count_b / decks_remaining
        tc_p = self.running_count_p / decks_remaining
        
        return tc_b, tc_p
    
    def calculate_edge(self) -> Dict:
        """
        Calculate current edge for both bets
        
        Returns:
            Dictionary with edge calculations
        """
        tc_b, tc_p = self.get_true_counts()
        
        # Conservative edge estimates (0.4-0.5% per true count unit)
        edge_b_raw = -0.0106 + (tc_b * 0.0045)
        edge_b_commission = edge_b_raw - 0.0053  # After 5% commission
        edge_p = -0.0124 + (tc_p * 0.0042)
        
        # Determine recommendation
        max_edge = max(edge_b_commission, edge_p)
        
        if max_edge <= 0:
            recommendation = "NO BET"
            reason = "Both sides have negative expectation"
        elif max_edge < 0.005:  # Less than 0.5%
            recommendation = "MARGINAL"
            reason = "Edge too small (< 0.5%)"
        elif edge_b_commission > edge_p:
            recommendation = "BANKER"
            reason = f"Positive edge: {edge_b_commission*100:.3f}%"
        else:
            recommendation = "PLAYER"
            reason = f"Positive edge: {edge_p*100:.3f}%"
        
        return {
            "edge_banker_raw": round(edge_b_raw * 100, 4),
            "edge_banker_after_commission": round(edge_b_commission * 100, 4),
            "edge_player": round(edge_p * 100, 4),
            "max_edge": round(max_edge * 100, 4),
            "has_positive_edge": max_edge > 0,
            "recommendation": recommendation,
            "reason": reason,
            "true_count_b": round(tc_b, 3),
            "true_count_p": round(tc_p, 3)
        }
    
    def play_hand(self) -> Hand:
        """
        Play one complete hand following Baccarat Tableau rules
        
        Returns:
            Complete Hand object
        
        Raises:
            ValueError: If shoe needs reshuffling
        """
        start_time = datetime.now()
        
        # Check if reshuffle needed
        if len(self.cards) < self.reshuffle_point:
            self.reset()
        
        # Initial deal (P-B-P-B)
        player_cards = [self.draw_card(), self.draw_card()]
        banker_cards = [self.draw_card(), self.draw_card()]
        
        # Calculate initial totals
        player_total = sum(c.value for c in player_cards) % 10
        banker_total = sum(c.value for c in banker_cards) % 10
        
        # Natural check (8 or 9)
        is_natural = False
        if player_total >= 8 or banker_total >= 8:
            is_natural = True
        else:
            # Apply Tableau rules for third card
            player_third_value = None
            
            # Player draws third card if total <= 5
            if player_total <= 5:
                player_third = self.draw_card()
                player_cards.append(player_third)
                player_third_value = player_third.value
                player_total = sum(c.value for c in player_cards) % 10
            
            # Banker draws based on player's third card (or lack thereof)
            if player_third_value is None:
                # Player stood, banker draws if <= 5
                if banker_total <= 5:
                    banker_cards.append(self.draw_card())
                    banker_total = sum(c.value for c in banker_cards) % 10
            else:
                # Player drew third card, use complex rules
                if self._banker_draws_third(banker_total, player_third_value):
                    banker_cards.append(self.draw_card())
                    banker_total = sum(c.value for c in banker_cards) % 10
        
        # Determine outcome
        if banker_total > player_total:
            result = Outcome.BANKER
        elif player_total > banker_total:
            result = Outcome.PLAYER
        else:
            result = Outcome.TIE
        
        # Calculate dealing time
        dealing_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
        
        # Get current counts
        tc_b, tc_p = self.get_true_counts()
        decks_remaining = len(self.cards) / 52
        
        # Create hand object
        hand = Hand(
            hand_id=str(uuid.uuid4()),
            shoe_id=self.shoe_id,
            hand_number=len(self.hand_history) + 1,
            banker_cards=banker_cards,
            player_cards=player_cards,
            result=result,
            timestamp=datetime.now(),
            is_natural=is_natural,
            dealing_time_ms=dealing_time_ms,
            running_count_b=self.running_count_b,
            running_count_p=self.running_count_p,
            true_count_b=tc_b,
            true_count_p=tc_p,
            decks_remaining=decks_remaining
        )
        
        # Add to history
        self.hand_history.append(hand)
        
        return hand
    
    def _banker_draws_third(self, banker_total: int, player_third: int) -> bool:
        """
        Determine if banker draws third card based on Tableau rules
        
        Args:
            banker_total: Banker's two-card total
            player_third: Value of player's third card (0-9)
        
        Returns:
            True if banker should draw
        """
        if banker_total <= 2:
            return True
        elif banker_total == 3:
            return player_third != 8
        elif banker_total == 4:
            return player_third in [2, 3, 4, 5, 6, 7]
        elif banker_total == 5:
            return player_third in [4, 5, 6, 7]
        elif banker_total == 6:
            return player_third in [6, 7]
        else:
            return False
    
    def get_state(self) -> Dict:
        """
        Get complete shoe state
        
        Returns:
            Dictionary with all state information
        """
        tc_b, tc_p = self.get_true_counts()
        edge = self.calculate_edge()
        
        # Composition analysis
        total_cards = sum(self.cards_by_rank.values())
        composition = {
            rank: {
                "remaining": count,
                "density": round(count / total_cards, 4) if total_cards > 0 else 0
            }
            for rank, count in self.cards_by_rank.items()
        }
        
        # Calculate high/low card ratios
        high_cards = sum(self.cards_by_rank[r] for r in ['7', '8', '9', '10', 'J', 'Q', 'K'])
        low_cards = sum(self.cards_by_rank[r] for r in ['A', '2', '3', '4', '5', '6'])
        
        return {
            "shoe_id": self.shoe_id,
            "decks": self.decks,
            "cards_remaining": len(self.cards),
            "cards_dealt": self.cards_dealt,
            "decks_remaining": round(len(self.cards) / 52, 2),
            "hands_played": len(self.hand_history),
            "reshuffled_count": self.reshuffled_count,
            
            # Counts
            "running_count_b": round(self.running_count_b, 4),
            "running_count_p": round(self.running_count_p, 4),
            "true_count_b": round(tc_b, 4),
            "true_count_p": round(tc_p, 4),
            
            # Edge
            "edge": edge,
            
            # Composition
            "composition": composition,
            "high_card_count": high_cards,
            "low_card_count": low_cards,
            "high_low_ratio": round(high_cards / low_cards, 3) if low_cards > 0 else 0,
            
            # Metadata
            "created_at": self.created_at.isoformat(),
            "needs_reshuffle": len(self.cards) < self.reshuffle_point
        }
    
    def get_statistics(self) -> Dict:
        """
        Get statistical summary of shoe history
        
        Returns:
            Dictionary with statistics
        """
        if not self.hand_history:
            return {
                "total_hands": 0,
                "message": "No hands played yet"
            }
        
        results = [h.result for h in self.hand_history]
        
        # Count outcomes
        banker_wins = sum(1 for r in results if r == Outcome.BANKER)
        player_wins = sum(1 for r in results if r == Outcome.PLAYER)
        ties = sum(1 for r in results if r == Outcome.TIE)
        
        total = len(results)
        no_tie = banker_wins + player_wins
        
        # Calculate streaks
        max_banker_streak = self._calculate_max_streak(results, Outcome.BANKER)
        max_player_streak = self._calculate_max_streak(results, Outcome.PLAYER)
        
        # Natural frequency
        naturals = sum(1 for h in self.hand_history if h.is_natural)
        
        return {
            "total_hands": total,
            
            # Win counts
            "banker_wins": banker_wins,
            "player_wins": player_wins,
            "ties": ties,
            
            # Percentages
            "banker_pct": round(banker_wins / no_tie * 100, 2) if no_tie > 0 else 0,
            "player_pct": round(player_wins / no_tie * 100, 2) if no_tie > 0 else 0,
            "tie_pct": round(ties / total * 100, 2) if total > 0 else 0,
            
            # Streaks
            "max_banker_streak": max_banker_streak,
            "max_player_streak": max_player_streak,
            
            # Naturals
            "natural_count": naturals,
            "natural_pct": round(naturals / total * 100, 2) if total > 0 else 0,
            
            # Deviation from theoretical
            "banker_deviation": round(banker_wins / no_tie - THEORETICAL_PROB['BANKER'], 4) if no_tie > 0 else 0,
            "player_deviation": round(player_wins / no_tie - THEORETICAL_PROB['PLAYER'], 4) if no_tie > 0 else 0
        }
    
    def _calculate_max_streak(self, results: List[Outcome], target: Outcome) -> int:
        """Calculate maximum streak length for a specific outcome"""
        max_streak = 0
        current_streak = 0
        
        for result in results:
            if result == target:
                current_streak += 1
                max_streak = max(max_streak, current_streak)
            else:
                current_streak = 0
        
        return max_streak


class Shoe(EnhancedShoe):
    """
    Backward-compatible alias for legacy references.
    """
    pass


class BaccaratEngine:
    """
    High-level facade that exposes the essential engine APIs used by other
    modules (maintains compatibility with earlier versions that imported a
    BaccaratEngine class).
    """

    def __init__(
        self,
        decks: int = 8,
        shoe: Optional[EnhancedShoe] = None,
        reshuffle_point: int = 20,
    ):
        self.shoe = shoe or Shoe(decks=decks, reshuffle_point=reshuffle_point)

    def play_hand(self) -> Hand:
        """Proxy to the underlying shoe implementation."""
        return self.shoe.play_hand()

    def get_state(self) -> Dict:
        return self.shoe.get_state()

    def get_statistics(self) -> Dict:
        return self.shoe.get_statistics()

    def calculate_edge(self) -> Dict:
        return self.shoe.calculate_edge()

    def reset(self) -> None:
        self.shoe.reset()


# ==================== TESTING CODE ====================

if __name__ == "__main__":
    """Test the engine"""
    print("🧪 Testing Enhanced Baccarat Engine\n")
    
    # Create shoe
    shoe = EnhancedShoe(decks=8)
    print(f"✅ Created shoe: {shoe.shoe_id}")
    print(f"   Cards: {len(shoe.cards)}")
    print(f"   Decks: {shoe.decks}\n")
    
    # Play 20 hands
    print("🎲 Playing 20 hands...\n")
    for i in range(20):
        hand = shoe.play_hand()
        edge = shoe.calculate_edge()
        
        print(f"Hand {hand.hand_number}: {hand.result.value} "
              f"(B:{hand.banker_total} vs P:{hand.player_total}) "
              f"{'🌟' if hand.is_natural else ''}")
        
        if i == 19:  # Last hand
            print(f"\n   TC Banker: {edge['true_count_b']}")
            print(f"   TC Player: {edge['true_count_p']}")
            print(f"   Edge: {edge['max_edge']:.4f}%")
            print(f"   Recommendation: {edge['recommendation']}")
    
    # Statistics
    stats = shoe.get_statistics()
    print(f"\n📊 Shoe Statistics:")
    print(f"   Banker: {stats['banker_wins']} ({stats['banker_pct']:.1f}%)")
    print(f"   Player: {stats['player_wins']} ({stats['player_pct']:.1f}%)")
    print(f"   Ties: {stats['ties']} ({stats['tie_pct']:.1f}%)")
    print(f"   Naturals: {stats['natural_count']} ({stats['natural_pct']:.1f}%)")
    
    print("\n✅ Engine test complete!")


# Note: Predictor is now in predictor.py module
# Import here for backward compatibility
try:
    from .predictor import Predictor
except ImportError:
    # Fallback if predictor.py doesn't exist yet
    pass
