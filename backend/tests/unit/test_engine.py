"""
Unit tests for engine module.
"""
import pytest
from app.core.engine import EnhancedShoe, Outcome, Card, Suit


class TestEnhancedShoe:
    """Tests for EnhancedShoe."""
    
    def test_create_shoe(self):
        """Test creating a shoe."""
        shoe = EnhancedShoe(decks=8)
        assert shoe.decks == 8
        assert len(shoe.shoe) == 8 * 52
    
    def test_deal_card(self):
        """Test dealing a card."""
        shoe = EnhancedShoe(decks=1)
        initial_count = len(shoe.shoe)
        card = shoe.deal_card()
        
        assert card is not None
        assert len(shoe.shoe) == initial_count - 1
    
    def test_play_hand(self):
        """Test playing a hand."""
        shoe = EnhancedShoe(decks=1)
        hand = shoe.play_hand()
        
        assert hand is not None
        assert hand.result in [Outcome.BANKER, Outcome.PLAYER, Outcome.TIE]
        assert len(hand.banker_cards) >= 2
        assert len(hand.player_cards) >= 2
    
    def test_get_statistics(self):
        """Test getting statistics."""
        shoe = EnhancedShoe(decks=1)
        
        # Play some hands
        for _ in range(5):
            shoe.play_hand()
        
        stats = shoe.get_statistics()
        assert "total_hands" in stats
        assert stats["total_hands"] == 5
    
    def test_calculate_edge(self):
        """Test edge calculation."""
        shoe = EnhancedShoe(decks=1)
        edge = shoe.calculate_edge()
        
        assert "edge_banker_raw" in edge
        assert "edge_player" in edge
        assert "max_edge" in edge


class TestCard:
    """Tests for Card class."""
    
    def test_card_creation(self):
        """Test card creation."""
        card = Card(rank="A", suit=Suit.SPADES)
        assert card.rank == "A"
        assert card.suit == Suit.SPADES
    
    def test_card_value(self):
        """Test card value calculation."""
        from app.core.engine import CARD_VALUES
        
        card = Card(rank="A", suit=Suit.SPADES)
        assert CARD_VALUES[card.rank] == 1
        
        card = Card(rank="K", suit=Suit.HEARTS)
        assert CARD_VALUES[card.rank] == 0
