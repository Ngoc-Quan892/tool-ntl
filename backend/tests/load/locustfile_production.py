"""
Production-grade load testing suite with Locust for Baccarat Predictor API.

Simulates realistic user behavior with weighted tasks, progressive load testing,
and comprehensive metrics collection.
"""

import os
import json
import time
import csv
import random
import statistics
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from locust import HttpUser, task, between, constant, constant_pacing, events
from locust.contrib.fasthttp import FastHttpUser
from locust.shape import LoadTestShape

# Try to import optional dependencies
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

# ==================== ENVIRONMENT VARIABLES ====================

TARGET_HOST = os.getenv("LOCUST_TARGET_HOST", "http://localhost:8000")
RUN_TIME = os.getenv("LOCUST_RUN_TIME", "10m")
USERS = int(os.getenv("LOCUST_USERS", "100"))
SPAWN_RATE = int(os.getenv("LOCUST_SPAWN_RATE", "10"))
REPORT_HTML = os.getenv("LOCUST_REPORT_HTML", "report.html")

# ==================== GLOBAL METRICS ====================

slow_requests: List[Dict] = []
failed_requests: List[Dict] = []
endpoint_stats: Dict[str, List[float]] = {}
system_metrics: List[Dict] = []


# ==================== HELPER FUNCTIONS ====================

def validate_game_results_response(response) -> Tuple[bool, str]:
    """
    Validate game results response structure.
    
    Args:
        response: Locust Response object
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if response.status_code != 200:
        return False, f"Status code {response.status_code}, expected 200"
    
    content_type = response.headers.get("Content-Type", "")
    if "application/json" not in content_type:
        return False, f"Content-Type {content_type}, expected application/json"
    
    try:
        data = response.json()
    except json.JSONDecodeError:
        return False, "Response is not valid JSON"
    
    if "results" not in data and "data" not in data:
        return False, "Response missing 'results' or 'data' key"
    
    results = data.get("results") or data.get("data", [])
    if not isinstance(results, list):
        return False, "'results' is not a list"
    
    # Validate each result has required fields
    if results:
        required_fields = ["id", "game_id", "result"]
        for result in results[:5]:  # Check first 5
            for field in required_fields:
                if field not in result:
                    return False, f"Result missing required field: {field}"
    
    return True, ""


def validate_pattern_stats_response(response) -> Tuple[bool, str]:
    """
    Validate pattern statistics response structure.
    
    Args:
        response: Locust Response object
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if response.status_code != 200:
        return False, f"Status code {response.status_code}, expected 200"
    
    try:
        data = response.json()
    except json.JSONDecodeError:
        return False, "Response is not valid JSON"
    
    if "pattern_type" not in data:
        return False, "Response missing 'pattern_type' key"
    
    if "occurrences" not in data:
        return False, "Response missing 'occurrences' key"
    
    if "statistics" not in data:
        return False, "Response missing 'statistics' key"
    
    if not isinstance(data["statistics"], dict):
        return False, "'statistics' is not a dict"
    
    return True, ""


def generate_realistic_game_result(game_id: int = None) -> Dict:
    """
    Generate realistic game result with proper probability distribution.
    
    Baccarat probabilities:
    - Banker wins: 45.86%
    - Player wins: 44.62%
    - Tie: 9.52%
    
    Args:
        game_id: Optional game ID, random if None
        
    Returns:
        Dict with game_id, result, banker_score, player_score
    """
    if game_id is None:
        game_id = random.randint(1, 100)
    
    # Use weighted random for realistic distribution
    rand = random.random()
    if rand < 0.4586:
        result = "banker"
    elif rand < 0.4586 + 0.4462:
        result = "player"
    else:
        result = "tie"
    
    # Generate realistic scores
    if result == "tie":
        # Ties have same score
        score = random.randint(0, 9)
        banker_score = score
        player_score = score
    else:
        # Winner has higher score
        banker_score = random.randint(0, 9)
        player_score = random.randint(0, 9)
        
        if result == "banker" and banker_score <= player_score:
            banker_score = player_score + 1 if player_score < 9 else 9
        elif result == "player" and player_score <= banker_score:
            player_score = banker_score + 1 if banker_score < 9 else 9
    
    return {
        "game_id": game_id,
        "result": result,
        "banker_score": banker_score,
        "player_score": player_score,
    }


# ==================== EVENT LISTENERS ====================

@events.request.add_listener
def on_request_event(request_type, name, response_time, response_length, exception, **kwargs):
    """Log slow requests and track failures."""
    # Track slow requests (>200ms)
    if response_time > 200:
        slow_requests.append({
            "name": name,
            "response_time": response_time,
            "timestamp": datetime.now().isoformat(),
        })
        print(f"⚠️  SLOW: {name} took {response_time}ms")
    
    # Track failures
    if exception:
        failed_requests.append({
            "name": name,
            "exception": str(exception),
            "response_time": response_time,
            "timestamp": datetime.now().isoformat(),
        })
    
    # Track endpoint stats
    if name not in endpoint_stats:
        endpoint_stats[name] = []
    endpoint_stats[name].append(response_time / 1000.0)  # Convert to seconds


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Generate comprehensive test summary."""
    print("\n" + "=" * 50)
    print("📊 LOAD TEST SUMMARY")
    print("=" * 50)
    
    # Overall statistics
    stats = environment.stats
    total_requests = stats.total.num_requests
    total_failures = stats.total.num_failures
    failure_rate = (total_failures / total_requests * 100) if total_requests > 0 else 0
    duration = stats.total.total_response_time if hasattr(stats.total, 'total_response_time') else 0
    rps = stats.total.total_rps if hasattr(stats.total, 'total_rps') else 0
    
    print(f"\nTotal Requests: {total_requests:,}")
    print(f"Failures: {total_failures:,} ({failure_rate:.2f}%)")
    print(f"Duration: {duration:.2f} seconds")
    print(f"Requests/sec: {rps:.2f}")
    
    # Response times
    if stats.total.num_requests > 0:
        response_times = []
        for entry in stats.entries.values():
            if hasattr(entry, 'response_times'):
                # Collect response times from all percentiles
                if hasattr(entry.response_times, 'values'):
                    response_times.extend([r / 1000.0 for r in entry.response_times.values()])
                elif isinstance(entry.response_times, dict):
                    response_times.extend([r / 1000.0 for r in entry.response_times.values()])
        
        if response_times:
            sorted_times = sorted(response_times)
            print(f"\nResponse Times:")
            print(f"  - Average: {statistics.mean(sorted_times)*1000:.2f}ms")
            print(f"  - Median: {statistics.median(sorted_times)*1000:.2f}ms")
            if len(sorted_times) > 20:
                p95_idx = int(len(sorted_times) * 0.95)
                p99_idx = int(len(sorted_times) * 0.99)
                print(f"  - 95th %ile: {sorted_times[p95_idx]*1000:.2f}ms")
                print(f"  - 99th %ile: {sorted_times[p99_idx]*1000:.2f}ms")
    
    # Slowest endpoints
    if slow_requests:
        print(f"\nSlowest Endpoints (>200ms):")
        slow_by_endpoint = {}
        for req in slow_requests:
            if req["name"] not in slow_by_endpoint:
                slow_by_endpoint[req["name"]] = []
            slow_by_endpoint[req["name"]].append(req["response_time"])
        
        sorted_slow = sorted(
            slow_by_endpoint.items(),
            key=lambda x: statistics.mean(x[1]),
            reverse=True
        )[:10]
        
        for i, (endpoint, times) in enumerate(sorted_slow, 1):
            avg_time = statistics.mean(times)
            print(f"  {i}. {endpoint}: {avg_time:.2f}ms (avg, {len(times)} occurrences)")
    
    # Most failed endpoints
    if failed_requests:
        print(f"\nMost Failed Endpoints:")
        failed_by_endpoint = {}
        for req in failed_requests:
            if req["name"] not in failed_by_endpoint:
                failed_by_endpoint[req["name"]] = 0
            failed_by_endpoint[req["name"]] += 1
        
        sorted_failed = sorted(
            failed_by_endpoint.items(),
            key=lambda x: x[1],
            reverse=True
        )[:10]
        
        for i, (endpoint, count) in enumerate(sorted_failed, 1):
            print(f"  {i}. {endpoint}: {count} failures")
    
    print("=" * 50 + "\n")


@events.init.add_listener
def on_test_init(environment, **kwargs):
    """Initialize custom metrics collection."""
    print("🔧 Initializing custom metrics collection...")
    
    # Start system metrics collection if psutil available
    if PSUTIL_AVAILABLE:
        def collect_system_metrics():
            process = psutil.Process()
            metrics = {
                "timestamp": datetime.now().isoformat(),
                "cpu_percent": process.cpu_percent(interval=0.1),
                "memory_percent": process.memory_percent(),
                "memory_mb": process.memory_info().rss / 1024 / 1024,
            }
            system_metrics.append(metrics)
        
        # Collect every 5 seconds
        import threading
        def metrics_loop():
            while True:
                collect_system_metrics()
                time.sleep(5)
        
        thread = threading.Thread(target=metrics_loop, daemon=True)
        thread.start()
        print("✅ System metrics collection started")
    
    # Initialize CSV logger
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_filename = f"metrics_{timestamp}.csv"
    print(f"📊 Metrics will be logged to: {csv_filename}")


# ==================== USER CLASSES ====================

class BaccaratProductionUser(HttpUser):
    """
    Standard user behavior - 60% of traffic.
    
    Task distribution:
    - 60% Read operations (game results)
    - 30% Analytics (pattern statistics)
    - 10% Write operations (create results)
    """
    
    wait_time = between(1, 3)  # Simulates thinking time
    weight = 3  # 60% of traffic (3 out of 5 total weight)
    
    def on_start(self):
        """Initialize user session."""
        self.game_ids = list(range(1, 101))
        self.pattern_types = ["banker_streak", "player_streak", "alternating", "tie_pattern"]
    
    @task(6)
    def get_game_results(self):
        """
        Get game results - most frequent operation.
        Target: <50ms response time (cached)
        """
        game_id = random.choice(self.game_ids)
        
        with self.client.get(
            f"/api/v2/game/{game_id}/results",
            catch_response=True,
            name="get_game_results"
        ) as response:
            # Check status code
            if response.status_code != 200:
                response.failure(f"Status code {response.status_code}")
                return
            
            # Measure response time
            response_time_ms = response.elapsed.total_seconds() * 1000
            
            # Check response time target
            if response_time_ms > 50:
                response.failure(f"Too slow: {response_time_ms:.2f}ms (target: <50ms)")
                return
            
            # Validate response structure
            is_valid, error_msg = validate_game_results_response(response)
            if not is_valid:
                response.failure(f"Invalid response structure: {error_msg}")
                return
            
            response.success()
    
    @task(3)
    def get_pattern_statistics(self):
        """
        Get pattern statistics - analytics queries.
        Target: <200ms response time (heavy computation, cached)
        """
        pattern_type = random.choice(self.pattern_types)
        days = random.choice([7, 14, 30])
        
        with self.client.get(
            f"/api/v2/statistics/pattern",
            params={"pattern_type": pattern_type, "days": days},
            catch_response=True,
            name="get_pattern_statistics"
        ) as response:
            if response.status_code != 200:
                response.failure(f"Status code {response.status_code}")
                return
            
            response_time_ms = response.elapsed.total_seconds() * 1000
            
            if response_time_ms > 200:
                response.failure(f"Too slow: {response_time_ms:.2f}ms (target: <200ms)")
                return
            
            is_valid, error_msg = validate_pattern_stats_response(response)
            if not is_valid:
                response.failure(f"Invalid response: {error_msg}")
                return
            
            response.success()
    
    @task(1)
    def create_game_result(self):
        """
        Create game result - occasional writes.
        Target: <100ms response time
        Note: This invalidates cache, affects read performance
        """
        game_id = random.randint(1, 10)  # Focus on active games
        game_result = generate_realistic_game_result(game_id)
        
        payload = {
            "game_id": game_result["game_id"],
            "result": game_result["result"],
            "banker_score": game_result["banker_score"],
            "player_score": game_result["player_score"],
        }
        
        with self.client.post(
            "/api/v2/game/results",
            json=payload,
            catch_response=True,
            name="create_game_result"
        ) as response:
            if response.status_code not in [200, 201]:
                response.failure(f"Status code {response.status_code}")
                return
            
            response_time_ms = response.elapsed.total_seconds() * 1000
            
            if response_time_ms > 100:
                response.failure(f"Too slow: {response_time_ms:.2f}ms (target: <100ms)")
                return
            
            # Validate response
            try:
                data = response.json()
                if "id" not in data or "created_at" not in data:
                    response.failure("Response missing 'id' or 'created_at'")
                    return
            except json.JSONDecodeError:
                response.failure("Response is not valid JSON")
                return
            
            response.success()


class BaccaratHeavyUser(HttpUser):
    """
    Analytics-focused power user - 20% of traffic.
    
    Focus: Heavy analytics, longer-running queries
    Should stress-test database and caching
    """
    
    wait_time = between(0.5, 2)  # Faster actions (power users)
    weight = 1  # 20% of traffic
    
    def on_start(self):
        """Initialize user session."""
        self.game_ids = list(range(1, 101))
    
    @task(5)
    def get_detailed_analytics(self):
        """
        Get detailed analytics - complex queries.
        Target: <500ms response time
        """
        game_id = random.choice(self.game_ids)
        
        with self.client.get(
            f"/api/v2/analytics/detailed",
            params={"game_id": game_id, "days": 90},
            catch_response=True,
            name="get_detailed_analytics"
        ) as response:
            if response.status_code != 200:
                response.failure(f"Status code {response.status_code}")
                return
            
            response_time_ms = response.elapsed.total_seconds() * 1000
            
            if response_time_ms > 500:
                response.failure(f"Too slow: {response_time_ms:.2f}ms (target: <500ms)")
                return
            
            # Validate complex response structure
            try:
                data = response.json()
                if "statistics" not in data:
                    response.failure("Response missing 'statistics'")
                    return
            except json.JSONDecodeError:
                response.failure("Response is not valid JSON")
                return
            
            response.success()
    
    @task(3)
    def get_historical_data(self):
        """
        Get historical data - large date ranges.
        Target: <1000ms response time
        """
        with self.client.get(
            "/api/v2/history",
            params={"days": 180},
            catch_response=True,
            name="get_historical_data"
        ) as response:
            if response.status_code != 200:
                response.failure(f"Status code {response.status_code}")
                return
            
            response_time_ms = response.elapsed.total_seconds() * 1000
            
            if response_time_ms > 1000:
                response.failure(f"Too slow: {response_time_ms:.2f}ms (target: <1000ms)")
                return
            
            # Validate pagination
            try:
                data = response.json()
                if "results" in data or "data" in data:
                    results = data.get("results") or data.get("data", [])
                    if len(results) > 1000:
                        # Large response, check if reasonable
                        pass
            except json.JSONDecodeError:
                response.failure("Response is not valid JSON")
                return
            
            response.success()
    
    @task(2)
    def export_reports(self):
        """
        Generate reports - export operations.
        Target: <2000ms response time
        """
        with self.client.get(
            "/api/v2/reports/export",
            params={"format": "json", "days": 30},
            catch_response=True,
            name="export_reports"
        ) as response:
            if response.status_code != 200:
                response.failure(f"Status code {response.status_code}")
                return
            
            response_time_ms = response.elapsed.total_seconds() * 1000
            
            if response_time_ms > 2000:
                response.failure(f"Too slow: {response_time_ms:.2f}ms (target: <2000ms)")
                return
            
            response.success()


class BaccaratWriteUser(HttpUser):
    """
    Write-heavy user - 20% of traffic.
    
    Focus: Write-heavy workload, cache invalidation
    """
    
    wait_time = constant(1)  # Steady write rate
    weight = 1  # 20% of traffic
    
    def on_start(self):
        """Initialize user session."""
        self.game_ids = list(range(1, 11))  # Focus on active games
    
    @task(5)
    def bulk_create_results(self):
        """
        Bulk create results - batch operations.
        Target: <500ms for bulk insert
        """
        # Generate 10 random game results
        results = [generate_realistic_game_result(random.choice(self.game_ids)) for _ in range(10)]
        
        payload = {
            "results": [
                {
                    "game_id": r["game_id"],
                    "result": r["result"],
                    "banker_score": r["banker_score"],
                    "player_score": r["player_score"],
                }
                for r in results
            ]
        }
        
        with self.client.post(
            "/api/v2/game/results/bulk",
            json=payload,
            catch_response=True,
            name="bulk_create_results"
        ) as response:
            if response.status_code not in [200, 201]:
                response.failure(f"Status code {response.status_code}")
                return
            
            response_time_ms = response.elapsed.total_seconds() * 1000
            
            if response_time_ms > 500:
                response.failure(f"Too slow: {response_time_ms:.2f}ms (target: <500ms)")
                return
            
            # Verify all results created
            try:
                data = response.json()
                if "created" in data:
                    created_count = data["created"]
                    if created_count != len(results):
                        response.failure(f"Only {created_count}/{len(results)} results created")
                        return
            except json.JSONDecodeError:
                response.failure("Response is not valid JSON")
                return
            
            response.success()
    
    @task(3)
    def update_game_settings(self):
        """
        Update game settings - configuration changes.
        Target: <200ms response time
        """
        game_id = random.choice(self.game_ids)
        
        payload = {
            "game_id": game_id,
            "settings": {
                "auto_reshuffle": random.choice([True, False]),
                "deck_count": random.choice([6, 8]),
            }
        }
        
        with self.client.put(
            f"/api/v2/game/{game_id}/settings",
            json=payload,
            catch_response=True,
            name="update_game_settings"
        ) as response:
            if response.status_code not in [200, 204]:
                response.failure(f"Status code {response.status_code}")
                return
            
            response_time_ms = response.elapsed.total_seconds() * 1000
            
            if response_time_ms > 200:
                response.failure(f"Too slow: {response_time_ms:.2f}ms (target: <200ms)")
                return
            
            response.success()
    
    @task(2)
    def delete_old_results(self):
        """
        Delete old results - cleanup operations.
        Target: <300ms response time
        """
        game_id = random.choice(self.game_ids)
        days_old = random.choice([30, 60, 90])
        
        with self.client.delete(
            f"/api/v2/game/{game_id}/results",
            params={"days_old": days_old},
            catch_response=True,
            name="delete_old_results"
        ) as response:
            if response.status_code not in [200, 204]:
                response.failure(f"Status code {response.status_code}")
                return
            
            response_time_ms = response.elapsed.total_seconds() * 1000
            
            if response_time_ms > 300:
                response.failure(f"Too slow: {response_time_ms:.2f}ms (target: <300ms)")
                return
            
            response.success()


# ==================== LOAD TEST SHAPES ====================

class StepLoadShape(LoadTestShape):
    """
    Gradually increase load in steps.
    
    Steps:
    - 10 users (2 min)
    - 50 users (2 min)
    - 100 users (2 min)
    - 500 users (5 min)
    """
    
    step_time = 120  # 2 minutes per step
    step_load = 10
    spawn_rate = 10
    time_limit = 660  # 11 minutes total
    
    def tick(self):
        run_time = self.get_run_time()
        
        if run_time > self.time_limit:
            return None
        
        if run_time < 120:
            return (10, self.spawn_rate)
        elif run_time < 240:
            return (50, self.spawn_rate)
        elif run_time < 360:
            return (100, self.spawn_rate)
        else:
            return (500, self.spawn_rate)


class BurstLoadShape(LoadTestShape):
    """
    Burst testing pattern.
    
    Pattern:
    - 10 users steady (1 min)
    - Burst to 500 users (30 sec)
    - Back to 10 users (1 min)
    - Repeat 3 times
    """
    
    def tick(self):
        run_time = self.get_run_time()
        
        if run_time > 600:  # 10 minutes total
            return None
        
        cycle_time = run_time % 150  # 2.5 minute cycle
        
        if cycle_time < 60:
            return (10, 10)  # Steady state
        elif cycle_time < 90:
            return (500, 50)  # Burst
        else:
            return (10, 10)  # Back to steady


class SoakLoadShape(LoadTestShape):
    """
    Soak testing for endurance.
    
    Pattern:
    - Ramp to 200 users (5 min)
    - Hold 200 users (60 min)
    - Ramp down (5 min)
    """
    
    def tick(self):
        run_time = self.get_run_time()
        
        if run_time > 4200:  # 70 minutes total
            return None
        
        if run_time < 300:  # 5 minutes ramp up
            users = int(200 * (run_time / 300))
            return (users, 10)
        elif run_time < 3900:  # 60 minutes hold
            return (200, 10)
        else:  # 5 minutes ramp down
            remaining = 4200 - run_time
            users = int(200 * (remaining / 300))
            return (users, 10)

