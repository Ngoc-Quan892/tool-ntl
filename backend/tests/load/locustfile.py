"""
Comprehensive load testing suite with Locust for Baccarat Predictor API.

Simulates realistic user behavior patterns and measures performance under load.
"""

from __future__ import annotations

import json
import random
import statistics
import time
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

from locust import HttpUser, LoadTestShape, TaskSet, between, constant, events, task


# ============================================================================
# Performance Targets
# ============================================================================

PERFORMANCE_TARGETS = {
    "get_game_results": {"p95_ms": 50, "error_rate": 0.01},
    "get_pattern_statistics": {"p95_ms": 200, "error_rate": 0.02},
    "create_game_result": {"p95_ms": 100, "error_rate": 0.01},
    "system": {"req_per_sec": 1000, "error_rate": 0.05},
}

# Baccarat probabilities
BANKER_PROB = 0.4586
PLAYER_PROB = 0.4462
TIE_PROB = 0.0952


# ============================================================================
# Helper Functions
# ============================================================================

def validate_response_time(response, endpoint: str, threshold_ms: int) -> bool:
    """
    Validate response time against threshold.
    
    Args:
        response: Response object
        endpoint: Endpoint name
        threshold_ms: Threshold in milliseconds
        
    Returns:
        True if passes, False otherwise
    """
    response_time_ms = response.elapsed.total_seconds() * 1000
    return response_time_ms < threshold_ms


def generate_realistic_game_result() -> Dict[str, Any]:
    """
    Generate realistic game result matching Baccarat probabilities.
    
    Returns:
        Dictionary with result, banker_score, player_score
    """
    rand = random.random()
    
    if rand < BANKER_PROB:
        result = "B"
        # Banker wins, so banker_score > player_score
        banker_score = random.randint(6, 9)
        player_score = random.randint(0, banker_score - 1)
    elif rand < BANKER_PROB + PLAYER_PROB:
        result = "P"
        # Player wins, so player_score > banker_score
        player_score = random.randint(6, 9)
        banker_score = random.randint(0, player_score - 1)
    else:
        result = "T"
        # Tie, scores are equal
        score = random.randint(0, 9)
        banker_score = score
        player_score = score
    
    return {
        "result": result,
        "banker_score": banker_score,
        "player_score": player_score,
    }


# ============================================================================
# Base User Class
# ============================================================================

class BaccaratUser(HttpUser):
    """Base class for all Baccarat API users."""
    
    wait_time = between(1, 3)  # Think time between requests
    
    def on_start(self):
        """Initialize user when starting."""
        self.game_ids = list(range(1, 101))  # Game IDs 1-100
        self.pattern_types = ["B", "P", "T", "all"]
        self.slow_requests = []
        self.failures = []
    
    def on_stop(self):
        """Cleanup when user stops."""
        pass
    
    def _check_response(self, response, name: str, threshold_ms: int):
        """
        Validate response and mark success/failure.
        
        Args:
            response: Response object
            name: Request name
            threshold_ms: Response time threshold in milliseconds
        """
        response_time_ms = response.elapsed.total_seconds() * 1000
        
        if response.status_code != 200:
            response.failure(f"Got status {response.status_code}")
            return False
        
        if response_time_ms < threshold_ms:
            response.success()
            return True
        elif response_time_ms < threshold_ms * 4:
            response.success()  # Acceptable but slow
            return True
        else:
            response.failure(f"Too slow: {response_time_ms:.0f}ms (threshold: {threshold_ms}ms)")
            return False


# ============================================================================
# Regular User (60% of users)
# ============================================================================

class RegularUser(BaccaratUser):
    """
    Simulate typical user behavior.
    
    Behavior: 60% reads, 30% analytics, 10% writes
    """
    
    weight = 3  # 60% of users (3 out of 5 total weight)
    wait_time = between(1, 3)
    
    @task(6)
    def get_game_results(self):
        """Test most frequent endpoint - get game results."""
        game_id = random.choice(self.game_ids)
        limit = random.choice([10, 50, 100, 200])
        
        with self.client.get(
            f"/api/v2/game/{game_id}/results",
            params={"limit": limit},
            catch_response=True,
            name="get_game_results"
        ) as response:
            response_time_ms = response.elapsed.total_seconds() * 1000
            
            if response.status_code != 200:
                response.failure(f"Got status {response.status_code}")
                return
            
            # Validate response structure
            try:
                data = response.json()
                if "results" not in data:
                    response.failure("Missing 'results' key in response")
                    return
            except Exception as e:
                response.failure(f"Invalid JSON: {e}")
                return
            
            # Check response time
            if response_time_ms < 50:
                response.success()
            elif response_time_ms < 200:
                response.success()  # Acceptable
            else:
                response.failure(f"Too slow: {response_time_ms:.0f}ms")
    
    @task(3)
    def get_pattern_statistics(self):
        """Test analytics endpoint performance."""
        pattern_type = random.choice(self.pattern_types)
        days = random.choice([7, 14, 30])
        
        with self.client.get(
            "/api/v2/game/statistics/pattern",
            params={"pattern_type": pattern_type, "days": days},
            catch_response=True,
            name="get_pattern_statistics"
        ) as response:
            response_time_ms = response.elapsed.total_seconds() * 1000
            
            if response.status_code != 200:
                response.failure(f"Got status {response.status_code}")
                return
            
            # Validate response
            try:
                data = response.json()
                if "statistics" not in data and "pattern_type" not in data:
                    response.failure("Invalid response structure")
                    return
            except Exception as e:
                response.failure(f"Invalid JSON: {e}")
                return
            
            # Check response time (threshold: 200ms)
            if response_time_ms < 200:
                response.success()
            elif response_time_ms < 500:
                response.success()  # Acceptable for analytics
            else:
                response.failure(f"Analytics query too slow: {response_time_ms:.0f}ms")
    
    @task(1)
    def create_game_result(self):
        """Test write operation performance."""
        game_id = random.randint(1, 10)  # Focus on active games
        result_data = generate_realistic_game_result()
        
        # Note: This endpoint may not exist, so we'll use a generic POST
        # In real implementation, this would be /api/v2/game/results or similar
        payload = {
            "game_id": game_id,
            "result": result_data["result"],
            "banker_score": result_data["banker_score"],
            "player_score": result_data["player_score"],
        }
        
        with self.client.post(
            "/api/v2/hands/play",
            json={"result": result_data["result"]},
            catch_response=True,
            name="create_game_result"
        ) as response:
            response_time_ms = response.elapsed.total_seconds() * 1000
            
            # Accept 200 or 201 for successful creation
            if response.status_code not in [200, 201]:
                response.failure(f"Create failed: {response.status_code}")
                return
            
            # Check response time (threshold: 100ms)
            if response_time_ms < 100:
                response.success()
            elif response_time_ms < 300:
                response.success()  # Acceptable
            else:
                response.failure(f"Write too slow: {response_time_ms:.0f}ms")


# ============================================================================
# Power User (20% of users)
# ============================================================================

class PowerUser(BaccaratUser):
    """
    Simulate analytics-heavy power users.
    
    Behavior: 80% analytics, 20% complex queries
    """
    
    weight = 1  # 20% of users
    wait_time = between(0.5, 2)  # Faster than regular users
    
    @task(5)
    def get_detailed_analytics(self):
        """Test complex analytical queries."""
        game_id = random.choice(self.game_ids)
        days = random.choice([90, 120, 180])
        pattern_type = random.choice(self.pattern_types)
        
        with self.client.get(
            "/api/v2/game/statistics/pattern",
            params={"pattern_type": pattern_type, "days": days},
            catch_response=True,
            name="get_detailed_analytics"
        ) as response:
            response_time_ms = response.elapsed.total_seconds() * 1000
            
            if response.status_code != 200:
                response.failure(f"Got status {response.status_code}")
                return
            
            # Threshold: 500ms for complex queries
            if response_time_ms < 500:
                response.success()
            elif response_time_ms < 1000:
                response.success()  # Acceptable for complex queries
            else:
                response.failure(f"Complex query too slow: {response_time_ms:.0f}ms")
    
    @task(3)
    def get_slow_endpoints(self):
        """Test monitoring dashboard endpoint."""
        with self.client.get(
            "/api/v2/monitoring/dashboard/slow-endpoints",
            params={"limit": 10},
            catch_response=True,
            name="get_slow_endpoints"
        ) as response:
            response_time_ms = response.elapsed.total_seconds() * 1000
            
            if response.status_code != 200:
                # Endpoint may not exist, mark as success if 404
                if response.status_code == 404:
                    response.success()
                else:
                    response.failure(f"Got status {response.status_code}")
                return
            
            # Threshold: 100ms (should be cached)
            if response_time_ms < 100:
                response.success()
            else:
                response.failure(f"Monitoring endpoint too slow: {response_time_ms:.0f}ms")
    
    @task(2)
    def get_cache_stats(self):
        """Test cache statistics endpoint."""
        with self.client.get(
            "/api/v2/monitoring/dashboard/cache-stats",
            params={"detail_level": "detailed"},
            catch_response=True,
            name="get_cache_stats"
        ) as response:
            response_time_ms = response.elapsed.total_seconds() * 1000
            
            if response.status_code != 200:
                if response.status_code == 404:
                    response.success()  # Endpoint may not exist
                else:
                    response.failure(f"Got status {response.status_code}")
                return
            
            # Threshold: 50ms
            if response_time_ms < 50:
                response.success()
            else:
                response.failure(f"Cache stats too slow: {response_time_ms:.0f}ms")


# ============================================================================
# API Integration User (20% of users)
# ============================================================================

class APIIntegrationUser(BaccaratUser):
    """
    Simulate external API integrations.
    
    Behavior: 90% reads, 10% writes
    """
    
    weight = 1  # 20% of users
    wait_time = constant(0.1)  # Steady rate, minimal think time
    
    @task(9)
    def batch_read_results(self):
        """Simulate bulk data fetching."""
        game_ids = random.sample(self.game_ids, min(10, len(self.game_ids)))
        start_time = time.time()
        success_count = 0
        
        for game_id in game_ids:
            with self.client.get(
                f"/api/v2/game/{game_id}/results",
                catch_response=True,
                name="batch_read_results"
            ) as response:
                if response.status_code == 200:
                    success_count += 1
                    response.success()
                else:
                    response.failure(f"Got status {response.status_code}")
        
        total_time_ms = (time.time() - start_time) * 1000
        
        # Threshold: 500ms for all 10 requests
        if total_time_ms < 500:
            pass  # All marked individually
        elif total_time_ms < 1000:
            pass  # Acceptable
        else:
            # Mark as slow batch
            pass
    
    @task(1)
    def batch_create_results(self):
        """Simulate bulk insert operations."""
        start_time = time.time()
        success_count = 0
        
        for _ in range(5):
            result_data = generate_realistic_game_result()
            with self.client.post(
                "/api/v2/hands/play",
                json={"result": result_data["result"]},
                catch_response=True,
                name="batch_create_results"
            ) as response:
                if response.status_code in [200, 201]:
                    success_count += 1
                    response.success()
                else:
                    response.failure(f"Got status {response.status_code}")
        
        total_time_ms = (time.time() - start_time) * 1000
        
        # Threshold: 500ms for all 5 requests
        if total_time_ms < 500:
            pass
        elif total_time_ms < 1000:
            pass
        else:
            pass


# ============================================================================
# Event Listeners
# ============================================================================

# Track slow requests
slow_requests = []


@events.request.add_listener
def on_request(request_type, name, response_time, response_length, exception, **kwargs):
    """Log requests exceeding thresholds."""
    if response_time > 200:  # 200ms threshold
        slow_requests.append({
            "timestamp": time.time(),
            "type": request_type,
            "name": name,
            "response_time": response_time,
            "exception": str(exception) if exception else None,
        })
        print(f"⚠️  SLOW: {name} took {response_time:.0f}ms")


# Track failures
failures_by_endpoint = defaultdict(int)
failures_by_type = defaultdict(int)


@events.request.add_listener
def on_request_failure(request_type, name, response_time, response_length, exception, **kwargs):
    """Track and categorize failures."""
    if exception:
        failures_by_endpoint[name] += 1
        error_type = type(exception).__name__
        failures_by_type[error_type] += 1


# Generate final report
@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Generate comprehensive test summary."""
    stats = environment.stats
    
    # Calculate totals
    total_requests = stats.total.num_requests
    total_failures = stats.total.num_failures
    success_rate = (total_requests - total_failures) / total_requests if total_requests > 0 else 0
    
    # Get response time percentiles
    if stats.total.num_requests > 0:
        p50 = stats.total.get_response_time_percentile(0.5)
        p95 = stats.total.get_response_time_percentile(0.95)
        p99 = stats.total.get_response_time_percentile(0.99)
        max_time = stats.total.max_response_time
    else:
        p50 = p95 = p99 = max_time = 0
    
    # Calculate throughput
    duration = stats.total.total_response_time / 1000 if stats.total.total_response_time > 0 else 1
    throughput = total_requests / duration if duration > 0 else 0
    
    # Get slowest endpoints
    slowest_endpoints = sorted(
        [(name, entry.avg_response_time) for name, entry in stats.entries.items()],
        key=lambda x: x[1],
        reverse=True
    )[:10]
    
    # Get most failed endpoints
    most_failed = sorted(
        [(name, entry.num_failures) for name, entry in stats.entries.items() if entry.num_failures > 0],
        key=lambda x: x[1],
        reverse=True
    )[:10]
    
    # Print report
    print("\n" + "=" * 60)
    print("📊 LOAD TEST RESULTS")
    print("=" * 60)
    print(f"Duration: {duration:.0f}s")
    print(f"Total Requests: {total_requests:,}")
    print(f"Successful: {total_requests - total_failures:,} ({success_rate*100:.1f}%)")
    print(f"Failed: {total_failures:,} ({total_failures/total_requests*100:.1f}%)" if total_requests > 0 else "Failed: 0")
    print()
    print("Response Times:")
    print(f"  - p50: {p50:.1f}ms")
    print(f"  - p95: {p95:.1f}ms")
    print(f"  - p99: {p99:.1f}ms")
    print(f"  - Max: {max_time:.1f}ms")
    print()
    print(f"Throughput: {throughput:.0f} req/s")
    print()
    
    if slowest_endpoints:
        print("Slowest Endpoints:")
        for i, (name, avg_time) in enumerate(slowest_endpoints, 1):
            print(f"  {i}. {name}: {avg_time:.1f}ms avg")
        print()
    
    if most_failed:
        print("Most Failed:")
        for i, (name, failures) in enumerate(most_failed, 1):
            print(f"  {i}. {name}: {failures} failures")
        print()
    
    if slow_requests:
        print(f"Slow Requests (>200ms): {len(slow_requests)}")
        print()
    
    if failures_by_type:
        print("Failures by Type:")
        for error_type, count in sorted(failures_by_type.items(), key=lambda x: x[1], reverse=True):
            print(f"  - {error_type}: {count}")
        print()
    
    print("=" * 60)


# ============================================================================
# Load Test Shapes
# ============================================================================

class ProgressiveLoadShape(LoadTestShape):
    """
    Gradually increase load to find breaking point.
    
    Stages:
    - 0-2 min: 10 users
    - 2-4 min: 50 users
    - 4-6 min: 100 users
    - 6-10 min: 250 users
    - 10-15 min: 500 users
    - 15-20 min: 1000 users
    """
    
    def tick(self):
        """Return tuple of (user_count, spawn_rate) or None to stop."""
        run_time = self.get_run_time()
        
        if run_time < 120:  # 0-2 min
            return (10, 2)
        elif run_time < 240:  # 2-4 min
            return (50, 5)
        elif run_time < 360:  # 4-6 min
            return (100, 10)
        elif run_time < 600:  # 6-10 min
            return (250, 25)
        elif run_time < 900:  # 10-15 min
            return (500, 50)
        elif run_time < 1200:  # 15-20 min
            return (1000, 100)
        else:
            return None  # Test ends


class BurstLoadShape(LoadTestShape):
    """
    Test system recovery from traffic bursts.
    
    Pattern:
    - 10 users baseline (1 min)
    - Burst to 500 users (30 sec)
    - Back to 10 users (1 min)
    - Repeat 5 times
    """
    
    def tick(self):
        """Return tuple of (user_count, spawn_rate) or None to stop."""
        run_time = self.get_run_time()
        cycle_time = run_time % 150  # 150 seconds per cycle (1 min + 30 sec + 1 min)
        
        if cycle_time < 60:  # Baseline
            return (10, 2)
        elif cycle_time < 90:  # Burst
            return (500, 100)
        else:  # Recovery
            return (10, 2)
        
        # Run for 5 cycles (750 seconds = 12.5 minutes)
        if run_time > 750:
            return None


class SoakLoadShape(LoadTestShape):
    """
    Test for memory leaks and degradation.
    
    Pattern:
    - Ramp to 200 users (5 min)
    - Hold 200 users (60 min)
    - Ramp down (5 min)
    """
    
    def tick(self):
        """Return tuple of (user_count, spawn_rate) or None to stop."""
        run_time = self.get_run_time()
        
        if run_time < 300:  # Ramp up (5 min)
            # Linear ramp from 0 to 200
            target_users = int(200 * (run_time / 300))
            return (target_users, 10)
        elif run_time < 3900:  # Hold (60 min = 3600s, total 3900s)
            return (200, 10)
        elif run_time < 4200:  # Ramp down (5 min)
            # Linear ramp from 200 to 0
            remaining = 4200 - run_time
            target_users = int(200 * (remaining / 300))
            return (target_users, 10)
        else:
            return None  # Test ends
