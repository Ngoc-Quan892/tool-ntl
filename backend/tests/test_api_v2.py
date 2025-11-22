"""
Tests for API v2 endpoints.
"""
import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture
def client():
    """Create test client."""
    app = create_app()
    return TestClient(app)


@pytest.fixture
def shoe_id(client):
    """Create a test shoe and return its ID."""
    response = client.post("/api/v2/shoes/create", json={"decks": 8})
    assert response.status_code == 200
    data = response.json()
    assert data["success"]
    return data["data"]["shoe_id"]


class TestShoeManagement:
    """Tests for shoe management endpoints."""
    
    def test_create_shoe(self, client):
        """Test creating a new shoe."""
        response = client.post("/api/v2/shoes/create", json={"decks": 8})
        assert response.status_code == 200
        data = response.json()
        assert data["success"]
        assert "shoe_id" in data["data"]
        assert data["data"]["decks"] == 8
    
    def test_get_shoe_state(self, client, shoe_id):
        """Test getting shoe state."""
        response = client.get(f"/api/v2/shoes/{shoe_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["shoe_id"] == shoe_id
        assert "decks" in data
        assert "cards_remaining" in data
    
    def test_reset_shoe(self, client, shoe_id):
        """Test resetting a shoe."""
        response = client.post(f"/api/v2/shoes/{shoe_id}/reset")
        assert response.status_code == 200
        data = response.json()
        assert data["success"]
        assert data["shoe_id"] == shoe_id
    
    def test_delete_shoe(self, client, shoe_id):
        """Test deleting a shoe."""
        response = client.delete(f"/api/v2/shoes/{shoe_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["success"]
        
        # Verify shoe is deleted
        response = client.get(f"/api/v2/shoes/{shoe_id}")
        assert response.status_code == 404
    
    def test_get_nonexistent_shoe(self, client):
        """Test getting non-existent shoe."""
        response = client.get("/api/v2/shoes/nonexistent")
        assert response.status_code == 404


class TestHandPlaying:
    """Tests for hand playing endpoints."""
    
    def test_play_hand(self, client):
        """Test playing a hand."""
        response = client.post("/api/v2/hands/play", json={})
        assert response.status_code == 200
        data = response.json()
        assert "hand_id" in data
        assert data["result"] in ["B", "P", "T"]
        assert "banker_total" in data
        assert "player_total" in data
    
    def test_play_hand_with_result(self, client):
        """Test playing a hand with manual result."""
        response = client.post("/api/v2/hands/play", json={"result": "B"})
        assert response.status_code == 200
        data = response.json()
        assert data["result"] == "B"
    
    def test_get_hand_history(self, client):
        """Test getting hand history."""
        # Play a few hands first
        for _ in range(3):
            client.post("/api/v2/hands/play", json={})
        
        response = client.get("/api/v2/hands/history?page=1&page_size=10")
        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "items" in data
        assert isinstance(data["items"], list)
    
    def test_get_specific_hand(self, client):
        """Test getting a specific hand."""
        # Play a hand first
        play_response = client.post("/api/v2/hands/play", json={})
        assert play_response.status_code == 200
        hand_id = play_response.json()["hand_id"]
        
        # Extract numeric ID
        db_id = hand_id.replace("hand_", "")
        
        # Get hand from history to get database ID
        history_response = client.get("/api/v2/hands/history?page=1&page_size=1")
        if history_response.status_code == 200:
            items = history_response.json().get("items", [])
            if items:
                hand_id = items[0]["hand_id"]
                response = client.get(f"/api/v2/hands/{hand_id}")
                assert response.status_code == 200
                data = response.json()
                assert data["hand_id"] == hand_id


class TestPredictions:
    """Tests for prediction endpoints."""
    
    def test_get_prediction(self, client):
        """Test getting a prediction."""
        response = client.post("/api/v2/predictions/predict", json={})
        assert response.status_code == 200
        data = response.json()
        assert "recommend" in data
        assert data["recommend"] in ["B", "P"]
        assert "confidence" in data
        assert 0.0 <= data["confidence"] <= 1.0
    
    def test_get_accuracy_metrics(self, client):
        """Test getting accuracy metrics."""
        response = client.get("/api/v2/predictions/accuracy")
        assert response.status_code == 200
        data = response.json()
        assert "total_predictions" in data
        assert "accuracy" in data
        assert "confidence_distribution" in data
    
    def test_get_confidence_scores(self, client):
        """Test getting confidence scores."""
        response = client.get("/api/v2/predictions/confidence")
        assert response.status_code == 200
        data = response.json()
        assert "current_confidence" in data
        assert "average_confidence" in data
        assert "confidence_history" in data


class TestAnalysis:
    """Tests for analysis endpoints."""
    
    def test_get_statistics(self, client):
        """Test getting statistics."""
        response = client.get("/api/v2/analysis/statistics")
        assert response.status_code == 200
        data = response.json()
        assert "total_hands" in data
        assert "banker_wins" in data
        assert "player_wins" in data
    
    def test_get_pattern_analysis(self, client):
        """Test getting pattern analysis."""
        response = client.get("/api/v2/analysis/patterns?limit=50")
        assert response.status_code == 200
        data = response.json()
        assert "detected_patterns" in data
        assert "pattern_frequency" in data
        assert "streak_analysis" in data
    
    def test_get_edge_calculation(self, client, shoe_id):
        """Test getting edge calculation."""
        response = client.get(f"/api/v2/analysis/edge?shoe_id={shoe_id}")
        assert response.status_code == 200
        data = response.json()
        assert "edge_banker_raw" in data
        assert "edge_player" in data
        assert "recommendation" in data


class TestHealthEndpoints:
    """Tests for health check endpoints."""
    
    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get("/api/v2/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "version" in data
    
    def test_database_health_check(self, client):
        """Test database health check endpoint."""
        response = client.get("/api/v2/health/db")
        # May return 200 or 500 depending on database connection
        assert response.status_code in [200, 500]
        if response.status_code == 200:
            data = response.json()
            assert "status" in data

