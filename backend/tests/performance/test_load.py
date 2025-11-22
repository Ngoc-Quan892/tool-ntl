"""
Load and performance tests.
"""
import pytest
import time
from fastapi.testclient import TestClient
from app.main import create_app


@pytest.fixture
def client():
    """Create test client."""
    app = create_app()
    return TestClient(app)


class TestPerformance:
    """Performance tests."""
    
    def test_prediction_response_time(self, client):
        """Test prediction endpoint response time."""
        start = time.time()
        response = client.post("/api/v2/predictions/predict", json={})
        elapsed = time.time() - start
        
        assert response.status_code in [200, 404]
        assert elapsed < 1.0  # Should respond within 1 second
    
    def test_statistics_response_time(self, client):
        """Test statistics endpoint response time."""
        start = time.time()
        response = client.get("/api/v2/analysis/statistics")
        elapsed = time.time() - start
        
        assert response.status_code == 200
        assert elapsed < 0.5  # Should respond within 500ms
    
    def test_concurrent_requests(self, client):
        """Test handling concurrent requests."""
        import concurrent.futures
        
        def make_request():
            return client.get("/api/v2/analysis/statistics")
        
        start = time.time()
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request) for _ in range(20)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]
        elapsed = time.time() - start
        
        # All should succeed
        assert all(r.status_code == 200 for r in results)
        # Should complete within reasonable time
        assert elapsed < 5.0
    
    def test_large_data_handling(self, client):
        """Test handling large amounts of data."""
        # Create many hands
        for i in range(100):
            client.post(
                "/api/v2/hands/play",
                json={"result": "B" if i % 2 == 0 else "P"}
            )
        
        # Get history
        start = time.time()
        response = client.get("/api/v2/hands/history", params={"limit": 1000})
        elapsed = time.time() - start
        
        assert response.status_code == 200
        assert elapsed < 2.0  # Should handle large datasets efficiently


class TestMemoryUsage:
    """Memory usage tests."""
    
    def test_memory_leak_detection(self, client):
        """Test for memory leaks."""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Make many requests
        for _ in range(100):
            client.get("/api/v2/analysis/statistics")
        
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable (< 50MB)
        assert memory_increase < 50


@pytest.mark.slow
class TestStressTest:
    """Stress tests (marked as slow)."""
    
    def test_sustained_load(self, client):
        """Test sustained load over time."""
        import concurrent.futures
        
        def make_request():
            return client.get("/api/v2/analysis/statistics")
        
        start = time.time()
        request_count = 0
        
        # Run for 10 seconds
        while time.time() - start < 10:
            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                futures = [executor.submit(make_request) for _ in range(10)]
                results = [f.result() for f in concurrent.futures.as_completed(futures)]
                request_count += len(results)
                time.sleep(0.1)
        
        # Should handle sustained load
        assert request_count > 0
        assert all(r.status_code == 200 for r in results)

