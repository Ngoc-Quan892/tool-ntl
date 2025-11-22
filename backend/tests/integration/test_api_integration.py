"""
Integration tests for API endpoints.
"""
import pytest
from fastapi.testclient import TestClient
from app.main import create_app


@pytest.fixture
def client():
    """Create test client."""
    app = create_app()
    return TestClient(app)


class TestPredictionEndpoints:
    """Tests for prediction endpoints."""
    
    def test_predict_endpoint(self, client):
        """Test prediction endpoint."""
        response = client.post("/api/v2/predictions/predict", json={})
        assert response.status_code in [200, 404]  # May not have data
    
    def test_predict_with_ml(self, client):
        """Test prediction with ML."""
        response = client.post(
            "/api/v2/predictions/predict",
            json={},
            params={"use_ml": True}
        )
        assert response.status_code in [200, 404]
    
    def test_accuracy_endpoint(self, client):
        """Test accuracy endpoint."""
        response = client.get("/api/v2/predictions/accuracy")
        assert response.status_code == 200
        data = response.json()
        assert "total_predictions" in data
        assert "accuracy" in data


class TestHandEndpoints:
    """Tests for hand endpoints."""
    
    def test_play_hand(self, client):
        """Test playing a hand."""
        response = client.post(
            "/api/v2/hands/play",
            json={"result": "B"}
        )
        assert response.status_code in [200, 201]
    
    def test_hand_history(self, client):
        """Test getting hand history."""
        response = client.get("/api/v2/hands/history")
        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "items" in data


class TestShoeEndpoints:
    """Tests for shoe endpoints."""
    
    def test_create_shoe(self, client):
        """Test creating a shoe."""
        response = client.post(
            "/api/v2/shoes/create",
            json={"decks": 8}
        )
        assert response.status_code in [200, 201]
        if response.status_code == 200:
            data = response.json()
            assert "shoe_id" in data or "data" in data
    
    def test_get_shoe_state(self, client):
        """Test getting shoe state."""
        # First create a shoe
        create_response = client.post(
            "/api/v2/shoes/create",
            json={"decks": 8}
        )
        if create_response.status_code == 200:
            shoe_id = create_response.json().get("data", {}).get("shoe_id")
            if shoe_id:
                response = client.get(f"/api/v2/shoes/{shoe_id}")
                assert response.status_code == 200


class TestAnalysisEndpoints:
    """Tests for analysis endpoints."""
    
    def test_statistics_endpoint(self, client):
        """Test statistics endpoint."""
        response = client.get("/api/v2/analysis/statistics")
        assert response.status_code == 200
        data = response.json()
        assert "total_hands" in data
    
    def test_pattern_analysis(self, client):
        """Test pattern analysis endpoint."""
        response = client.get("/api/v2/analysis/patterns")
        assert response.status_code == 200
        data = response.json()
        assert "detected_patterns" in data
    
    def test_edge_calculation(self, client):
        """Test edge calculation endpoint."""
        response = client.get("/api/v2/analysis/edge")
        assert response.status_code == 200
    
    def test_shoe_analysis(self, client):
        """Test comprehensive shoe analysis."""
        response = client.post(
            "/api/v2/analysis/analyze/shoe",
            json={}
        )
        assert response.status_code == 200
        data = response.json()
        assert "total_samples" in data
        assert "tests" in data


class TestHypothesisTestEndpoints:
    """Tests for hypothesis test endpoints."""
    
    def test_hypothesis_test_chi_square(self, client):
        """Test chi-square hypothesis test."""
        response = client.get(
            "/api/v2/analysis/hypothesis/test",
            params={"test_type": "chi_square"}
        )
        assert response.status_code in [200, 400]
    
    def test_hypothesis_test_runs(self, client):
        """Test runs test."""
        response = client.get(
            "/api/v2/analysis/hypothesis/test",
            params={"test_type": "runs"}
        )
        assert response.status_code in [200, 400]
    
    def test_pattern_significance(self, client):
        """Test pattern significance endpoint."""
        response = client.get(
            "/api/v2/analysis/patterns/significance",
            params={"pattern_type": "streak"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "p_value" in data
        assert "significant" in data


class TestEndToEndFlow:
    """End-to-end flow tests."""
    
    def test_create_shoe_play_hands_flow(self, client):
        """Test complete flow: create shoe → play hands → get predictions."""
        # Create shoe
        create_response = client.post(
            "/api/v2/shoes/create",
            json={"decks": 8}
        )
        assert create_response.status_code in [200, 201]
        
        # Play some hands
        for result in ["B", "P", "B", "B"]:
            play_response = client.post(
                "/api/v2/hands/play",
                json={"result": result}
            )
            assert play_response.status_code in [200, 201]
        
        # Get prediction
        predict_response = client.post("/api/v2/predictions/predict", json={})
        assert predict_response.status_code in [200, 404]
        
        # Get statistics
        stats_response = client.get("/api/v2/analysis/statistics")
        assert stats_response.status_code == 200
        
        # Get roadmap
        roadmap_response = client.get("/api/roadmap")
        assert roadmap_response.status_code in [200, 404]

