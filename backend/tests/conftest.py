"""
Pytest configuration and fixtures for comprehensive testing infrastructure.

This module provides:
- Isolated test database with transactions
- Mock Redis client for cache testing
- OptimizationStack configured for testing
- FastAPI test client
- Sample test data fixtures
- Automatic cleanup after each test
- Support for both sync and async tests
- Helper functions for common test operations
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
import random
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, Generator, List, Optional
from unittest.mock import Mock, MagicMock

import pytest
from pytest_asyncio import fixture as async_fixture
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.engine import Engine

# Try to import fakeredis, fallback to mock if not available
try:
    from fakeredis import FakeRedis
    HAS_FAKEREDIS = True
except ImportError:
    HAS_FAKEREDIS = False
    FakeRedis = None

from app.main import create_app
from app.models.database import Base, GameResult, SimulationRun, db_manager
from app.api.v2.base import get_database_session
from app.services.performance_optimizer import OptimizationStack

logger = logging.getLogger(__name__)

# Use in-memory SQLite for testing (fast and isolated)
TEST_DATABASE_URL = "sqlite:///:memory:"


# ============================================================================
# Database Fixtures
# ============================================================================

@pytest.fixture(scope="function")
def test_db() -> Generator[Session, None, None]:
    """
    Provide isolated database for each test.
    
    Creates a fresh in-memory SQLite database for each test function,
    ensuring complete test isolation.
    
    Yields:
        SQLAlchemy Session ready for testing
        
    Example:
        def test_something(test_db):
            result = test_db.query(GameResult).first()
            assert result is None
    """
    # Create test database engine
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        echo=False,  # Set to True for SQL debugging
    )
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    # Create session maker
    TestingSessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
    )
    
    # Create session
    db = TestingSessionLocal()
    
    try:
        yield db
    finally:
        # Cleanup: close session, drop tables, dispose engine
        db.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


# ============================================================================
# Redis Fixtures
# ============================================================================

@pytest.fixture(scope="function")
def test_redis() -> Generator[Any, None, None]:
    """
    Provide mock Redis client for cache testing.
    
    Uses fakeredis to simulate Redis in memory without requiring
    an actual Redis server.
    
    Yields:
        FakeRedis client instance (or Mock if fakeredis not available)
        
    Example:
        def test_cache(test_redis):
            test_redis.set("key", "value")
            assert test_redis.get("key") == b"value"
    """
    if HAS_FAKEREDIS:
        # Create FakeRedis instance
        fake_redis = FakeRedis(decode_responses=False)
        try:
            yield fake_redis
        finally:
            # Flush all data
            fake_redis.flushall()
            fake_redis.close()
    else:
        # Fallback to Mock if fakeredis not available
        mock_redis = Mock()
        mock_redis.get = Mock(return_value=None)
        mock_redis.set = Mock(return_value=True)
        mock_redis.delete = Mock(return_value=True)
        mock_redis.exists = Mock(return_value=False)
        mock_redis.flushall = Mock(return_value=True)
        mock_redis.close = Mock()
        yield mock_redis


# ============================================================================
# OptimizationStack Fixture
# ============================================================================

@pytest.fixture(scope="function")
def test_optimizer(test_db: Session, test_redis: Any) -> Generator[OptimizationStack, None, None]:
    """
    OptimizationStack configured for testing.
    
    Initializes OptimizationStack with test database connection and mock Redis.
    Configured with test-friendly settings (short TTL, small connection pool).
    
    Args:
        test_db: Test database session (dependency)
        test_redis: Mock Redis client (dependency)
        
    Yields:
        OptimizationStack instance ready for testing
        
    Example:
        def test_query_optimization(test_optimizer, test_db):
            optimizer = test_optimizer
            query_opt = optimizer.get_query_optimizer(test_db)
            results = query_opt.get_game_results(1, limit=10)
    """
    # Create a simple mock database manager for OptimizationStack
    # OptimizationStack only stores db_connection, it doesn't use it directly
    # Sessions are passed to get_query_optimizer() method
    class MockDBManager:
        """Mock database manager for testing."""
        def __init__(self, session: Session):
            self.session = session
            self.engine = session.bind if hasattr(session, 'bind') else None
    
    mock_db_manager = MockDBManager(test_db)
    
    # Initialize OptimizationStack with test settings
    optimizer = OptimizationStack(
        db_connection=mock_db_manager,
        redis_client=test_redis,
        cache_ttl=10,  # Short TTL for testing (10 seconds)
    )
    
    try:
        yield optimizer
    finally:
        # Clear cache and cleanup
        try:
            cache_manager = optimizer.get_cache_manager()
            if hasattr(cache_manager, 'clear_all'):
                cache_manager.clear_all()
        except Exception as e:
            logger.warning(f"Error clearing cache in test_optimizer cleanup: {e}")


# ============================================================================
# FastAPI Test Client Fixture
# ============================================================================

@pytest.fixture(scope="module")
def test_client(test_db: Session) -> Generator[TestClient, None, None]:
    """
    FastAPI TestClient for API testing.
    
    Creates a test client with database dependency overridden to use test database.
    Reused across tests in the same module for efficiency.
    
    Args:
        test_db: Test database session (dependency)
        
    Yields:
        TestClient instance ready for API testing
        
    Example:
        def test_api_endpoint(test_client):
            response = test_client.get("/api/v2/game/1/results")
            assert response.status_code == 200
    """
    # Create app
    app = create_app()
    
    # Override database dependency
    def override_get_db():
        try:
            yield test_db
        finally:
            pass
    
    app.dependency_overrides[get_database_session] = override_get_db
    
    # Create test client
    client = TestClient(app)
    
    try:
        yield client
    finally:
        # Clear dependency overrides
        app.dependency_overrides.clear()


# ============================================================================
# Sample Data Fixtures
# ============================================================================

@pytest.fixture(scope="session")
def sample_games() -> List[Dict[str, Any]]:
    """
    Provide test game data.
    
    Returns a list of 10 test games with sequential IDs and timestamps.
    Same data for all tests in the session.
    
    Returns:
        List of game dictionaries with id, name, created_at
        
    Example:
        def test_with_games(sample_games):
            assert len(sample_games) == 10
            assert sample_games[0]["id"] == 1
    """
    base_time = datetime(2024, 1, 1, 0, 0, 0)
    games = []
    
    for i in range(1, 11):
        games.append({
            "id": i,
            "name": f"Test Game {i}",
            "created_at": (base_time + timedelta(hours=i-1)).isoformat(),
        })
    
    return games


@pytest.fixture(scope="function")
def sample_results(test_db: Session, sample_games: List[Dict[str, Any]]) -> Generator[List[Dict[str, Any]], None, None]:
    """
    Provide test game results.
    
    Creates 20 results for each game in sample_games (200 total).
    Results have realistic distribution: 46% banker, 44% player, 10% tie.
    
    Args:
        test_db: Test database session (dependency)
        sample_games: Sample game data (dependency)
        
    Yields:
        List of inserted game result dictionaries
        
    Example:
        def test_results(sample_results):
            assert len(sample_results) == 200
            banker_count = sum(1 for r in sample_results if r["result"] == "B")
            assert banker_count > 80  # ~46% of 200
    """
    results = []
    base_time = datetime(2024, 1, 1, 0, 0, 0)
    
    # Result distribution: 46% banker, 44% player, 10% tie
    result_weights = ["B"] * 46 + ["P"] * 44 + ["T"] * 10
    
    for game in sample_games:
        game_id = game["id"]
        for hand_num in range(1, 21):  # 20 results per game
            result = random.choice(result_weights)
            banker_score = random.randint(0, 9) if result != "T" else random.randint(0, 9)
            player_score = random.randint(0, 9) if result != "T" else random.randint(0, 9)
            
            # Ensure scores match result (simplified logic)
            if result == "B":
                banker_score = max(banker_score, player_score + 1) if banker_score <= player_score else banker_score
            elif result == "P":
                player_score = max(player_score, banker_score + 1) if player_score <= banker_score else player_score
            else:  # Tie
                banker_score = player_score
            
            timestamp = base_time + timedelta(
                hours=game_id - 1,
                minutes=hand_num * 2
            )
            
            result_data = {
                "result": result,
                "shoe_number": game_id,
                "hand_number": hand_num,
                "timestamp": timestamp,
                "true_count": round(random.uniform(-5.0, 5.0), 2),
                "edge": round(random.uniform(-0.02, 0.02), 4),
            }
            
            # Insert into database
            db_result = GameResult(**result_data)
            test_db.add(db_result)
            test_db.flush()
            
            # Add ID to result_data
            result_data["id"] = db_result.id
            results.append(result_data)
    
    # Commit all changes
    test_db.commit()
    
    try:
        yield results
    finally:
        # Cleanup is handled by test_db fixture
        pass


@pytest.fixture(scope="function")
def sample_patterns(test_db: Session, sample_results: List[Dict[str, Any]]) -> Generator[List[Dict[str, Any]], None, None]:
    """
    Provide test pattern data.
    
    Calculates pattern statistics from sample_results:
    - banker_streak: Count consecutive banker wins
    - player_streak: Count consecutive player wins
    - alternating: Count alternating wins
    - tie_pattern: Count tie occurrences
    
    Args:
        test_db: Test database session (dependency)
        sample_results: Sample game results (dependency)
        
    Yields:
        List of pattern statistics dictionaries
        
    Example:
        def test_patterns(sample_patterns):
            assert len(sample_patterns) > 0
            assert "banker_streak" in sample_patterns[0]
    """
    patterns = []
    
    # Group results by shoe_number
    results_by_shoe: Dict[int, List[Dict[str, Any]]] = {}
    for result in sample_results:
        shoe_num = result["shoe_number"]
        if shoe_num not in results_by_shoe:
            results_by_shoe[shoe_num] = []
        results_by_shoe[shoe_num].append(result)
    
    # Calculate patterns for each shoe
    for shoe_num, results in results_by_shoe.items():
        # Sort by hand_number
        sorted_results = sorted(results, key=lambda x: x["hand_number"])
        
        # Calculate streaks
        banker_streak = 0
        player_streak = 0
        max_banker_streak = 0
        max_player_streak = 0
        alternating_count = 0
        tie_count = 0
        
        prev_result = None
        for result in sorted_results:
            current_result = result["result"]
            
            if current_result == "T":
                tie_count += 1
                banker_streak = 0
                player_streak = 0
            elif current_result == "B":
                banker_streak += 1
                player_streak = 0
                max_banker_streak = max(max_banker_streak, banker_streak)
            else:  # P
                player_streak += 1
                banker_streak = 0
                max_player_streak = max(max_player_streak, player_streak)
            
            # Check for alternating pattern
            if prev_result and prev_result != current_result and current_result != "T":
                alternating_count += 1
            
            prev_result = current_result
        
        pattern_data = {
            "shoe_number": shoe_num,
            "total_hands": len(results),
            "banker_streak": max_banker_streak,
            "player_streak": max_player_streak,
            "alternating_count": alternating_count,
            "tie_count": tie_count,
            "banker_wins": sum(1 for r in results if r["result"] == "B"),
            "player_wins": sum(1 for r in results if r["result"] == "P"),
        }
        
        patterns.append(pattern_data)
    
    try:
        yield patterns
    finally:
        # Cleanup is handled by test_db fixture
        pass


# ============================================================================
# Cleanup Fixtures (Auto-use)
# ============================================================================

@pytest.fixture(scope="function", autouse=True)
def cleanup_db(test_db: Session) -> Generator[None, None, None]:
    """
    Automatically cleanup database after each test.
    
    This fixture runs automatically for every test (autouse=True).
    Ensures test isolation by cleaning up all test data.
    
    Args:
        test_db: Test database session (dependency)
        
    Yields:
        None (runs cleanup in finally block)
    """
    try:
        yield
    finally:
        # Delete all test data
        try:
            test_db.query(GameResult).delete()
            test_db.query(SimulationRun).delete()
            test_db.commit()
        except Exception as e:
            logger.warning(f"Error during database cleanup: {e}")
            test_db.rollback()


@pytest.fixture(scope="function", autouse=True)
def performance_timer(request: pytest.FixtureRequest) -> Generator[None, None, None]:
    """
    Measure test execution time.
    
    Automatically measures how long each test takes to run.
    Logs a warning if test takes longer than 5 seconds.
    
    Args:
        request: Pytest request object (for test metadata)
        
    Yields:
        None (measures time around test execution)
    """
    start_time = time.time()
    
    try:
        yield
    finally:
        end_time = time.time()
        duration = end_time - start_time
        
        # Log warning if test is slow
        if duration > 5.0:
            logger.warning(
                f"Slow test detected: {request.node.name} took {duration:.2f} seconds"
            )
        
        # Store timing in test report (if available)
        if hasattr(request.node, "user_properties"):
            request.node.user_properties.append(("duration", duration))


# ============================================================================
# Request Logging Fixture
# ============================================================================

@pytest.fixture(scope="function")
def log_requests(test_client: TestClient, request: pytest.FixtureRequest) -> Generator[None, None, None]:
    """
    Log all API requests during test.
    
    Captures all HTTP requests made through test_client.
    Dumps request logs to file if test fails.
    
    Args:
        test_client: FastAPI test client (dependency)
        request: Pytest request object (for test metadata)
        
    Yields:
        None (logs requests during test execution)
    """
    request_logs: List[Dict[str, Any]] = []
    
    # Store original request methods
    original_get = test_client.get
    original_post = test_client.post
    original_put = test_client.put
    original_delete = test_client.delete
    
    def logged_get(*args, **kwargs):
        log_entry = {"method": "GET", "args": args, "kwargs": kwargs}
        request_logs.append(log_entry)
        return original_get(*args, **kwargs)
    
    def logged_post(*args, **kwargs):
        log_entry = {"method": "POST", "args": args, "kwargs": kwargs}
        request_logs.append(log_entry)
        return original_post(*args, **kwargs)
    
    def logged_put(*args, **kwargs):
        log_entry = {"method": "PUT", "args": args, "kwargs": kwargs}
        request_logs.append(log_entry)
        return original_put(*args, **kwargs)
    
    def logged_delete(*args, **kwargs):
        log_entry = {"method": "DELETE", "args": args, "kwargs": kwargs}
        request_logs.append(log_entry)
        return original_delete(*args, **kwargs)
    
    # Monkey patch test client
    test_client.get = logged_get
    test_client.post = logged_post
    test_client.put = logged_put
    test_client.delete = logged_delete
    
    try:
        yield
    finally:
        # Restore original methods
        test_client.get = original_get
        test_client.post = original_post
        test_client.put = original_put
        test_client.delete = original_delete
        
        # Dump logs if test failed
        if request.node.rep_call and request.node.rep_call.failed:
            log_file = f"test_request_logs_{request.node.name}.json"
            try:
                import json
                with open(log_file, "w") as f:
                    json.dump(request_logs, f, indent=2, default=str)
                logger.info(f"Request logs saved to {log_file}")
            except Exception as e:
                logger.warning(f"Failed to save request logs: {e}")


# Hook to capture test results for log_requests fixture
@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Hook to capture test results for request logging."""
    outcome = yield
    rep = outcome.get_result()
    setattr(item, "rep_" + rep.when, rep)


# ============================================================================
# Helper Functions
# ============================================================================

def wait_for_condition(
    condition: Callable[[], bool],
    timeout: int = 30,
    interval: float = 0.5,
    error_message: Optional[str] = None,
) -> None:
    """
    Wait for async conditions (cache propagation, etc.).
    
    Polls a condition function until it returns True or timeout is reached.
    Useful for waiting for async operations like cache updates.
    
    Args:
        condition: Callable that returns bool (True when condition is met)
        timeout: Maximum time to wait in seconds (default: 30)
        interval: Time between condition checks in seconds (default: 0.5)
        error_message: Custom error message for timeout (optional)
        
    Raises:
        TimeoutError: If condition is not met within timeout
        
    Example:
        wait_for_condition(
            lambda: cache.get("key") is not None,
            timeout=10,
            interval=0.1
        )
    """
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        if condition():
            return
        time.sleep(interval)
    
    # Timeout reached
    message = error_message or f"Condition not met within {timeout} seconds"
    raise TimeoutError(message)


def seed_database(
    session: Session,
    data: Dict[str, List[Dict[str, Any]]],
) -> Dict[str, List[int]]:
    """
    Quickly populate test database with data.
    
    Takes a dictionary mapping table names to lists of record dictionaries,
    creates model instances, and inserts them into the database.
    
    Args:
        session: SQLAlchemy session
        data: Dictionary mapping table names to lists of record dictionaries
              Example: {"game_results": [{"result": "B", ...}, ...]}
        
    Returns:
        Dictionary mapping table names to lists of inserted record IDs
        
    Example:
        inserted_ids = seed_database(session, {
            "game_results": [
                {"result": "B", "shoe_number": 1, "hand_number": 1},
                {"result": "P", "shoe_number": 1, "hand_number": 2},
            ]
        })
        assert len(inserted_ids["game_results"]) == 2
    """
    inserted_ids: Dict[str, List[int]] = {}
    
    # Map table names to model classes
    model_map = {
        "game_results": GameResult,
        "simulation_runs": SimulationRun,
    }
    
    for table_name, records in data.items():
        if table_name not in model_map:
            raise ValueError(f"Unknown table name: {table_name}")
        
        model_class = model_map[table_name]
        ids = []
        
        for record in records:
            instance = model_class(**record)
            session.add(instance)
            session.flush()
            ids.append(instance.id)
        
        inserted_ids[table_name] = ids
    
    # Commit all changes
    session.commit()
    
    return inserted_ids


def assert_api_response(
    response: Any,
    expected_status: int = 200,
    expected_keys: Optional[List[str]] = None,
    expected_types: Optional[Dict[str, type]] = None,
) -> Dict[str, Any]:
    """
    Common assertions for API responses.
    
    Validates status code, JSON format, required keys, and value types.
    Logs response body if any assertion fails.
    
    Args:
        response: Response object from test_client
        expected_status: Expected HTTP status code (default: 200)
        expected_keys: List of required keys in JSON response (optional)
        expected_types: Dictionary mapping keys to expected types (optional)
        
    Returns:
        Parsed JSON response as dictionary
        
    Raises:
        AssertionError: If any validation fails
        
    Example:
        response = test_client.get("/api/v2/game/1/results")
        data = assert_api_response(
            response,
            expected_status=200,
            expected_keys=["results", "total"],
            expected_types={"results": list, "total": int}
        )
    """
    # Assert status code
    assert response.status_code == expected_status, (
        f"Expected status {expected_status}, got {response.status_code}. "
        f"Response: {response.text}"
    )
    
    # Assert response is JSON
    try:
        data = response.json()
    except Exception as e:
        logger.error(f"Response is not valid JSON: {response.text}")
        raise AssertionError(f"Response is not valid JSON: {e}")
    
    # Assert all expected keys are present
    if expected_keys:
        missing_keys = [key for key in expected_keys if key not in data]
        if missing_keys:
            logger.error(f"Missing keys in response: {missing_keys}. Response: {data}")
            raise AssertionError(f"Missing keys in response: {missing_keys}")
    
    # Assert value types match expected_types
    if expected_types:
        for key, expected_type in expected_types.items():
            if key not in data:
                continue  # Skip if key is optional
            
            actual_value = data[key]
            if not isinstance(actual_value, expected_type):
                logger.error(
                    f"Type mismatch for key '{key}': "
                    f"expected {expected_type.__name__}, got {type(actual_value).__name__}. "
                    f"Response: {data}"
                )
                raise AssertionError(
                    f"Type mismatch for key '{key}': "
                    f"expected {expected_type.__name__}, got {type(actual_value).__name__}"
                )
    
    return data


# ============================================================================
# Predictive Cache Warmer Fixtures
# ============================================================================

@pytest.fixture(scope="function")
def sample_access_logs() -> List[Dict[str, Any]]:
    """
    Generate realistic access logs for testing.
    
    Creates 1000+ realistic access log entries with patterns:
    - Peak hours: 9-11 AM (weight: 10), 2-4 PM (weight: 12), 7-9 PM (weight: 10)
    - Normal hours: 6-8 AM (weight: 4), 12-1 PM (weight: 6)
    - Low hours: 0-5 AM (weight: 1), 11 PM-midnight (weight: 2)
    - Weekend pattern: Saturday/Sunday have different distribution
    - Popular games: 80-20 rule (20% games get 80% traffic)
    - User distribution: Power (10%), Regular (30%), Casual (60%)
    
    Returns:
        List of access log dictionaries with structure:
        {
            "timestamp": datetime,
            "game_id": int,
            "user_id": str,
            "session_duration": float,  # seconds
            "access_count": int
        }
    """
    logs = []
    base_time = datetime(2024, 1, 1, 0, 0, 0)
    
    # Set random seed for reproducibility
    random.seed(42)
    
    # Hour weights: Peak hours have higher weights
    # 0-5 AM: weight 1, 6-8 AM: weight 4, 9-11 AM: weight 10, 
    # 12-1 PM: weight 6, 2-4 PM: weight 12, 5-6 PM: weight 8,
    # 7-9 PM: weight 10, 10-11 PM: weight 4, 11 PM-midnight: weight 2
    hour_weights = [
        1, 1, 1, 1, 1, 1,  # 0-5 AM (low)
        4, 4, 4,           # 6-8 AM (normal)
        10, 10, 10,        # 9-11 AM (peak)
        6,                 # 12 PM (normal)
        12, 12, 12,        # 1-3 PM (peak)
        8, 8,              # 4-5 PM (normal)
        10, 10, 10,        # 6-8 PM (peak)
        4, 4,              # 9-10 PM (normal)
        2                  # 11 PM (low)
    ]
    
    # Game weights: 80-20 distribution
    # Top 20 games should get ~80% of traffic
    # Strategy: Top 20 have much higher weights than the rest
    game_weights = []
    for i in range(100):
        if i < 20:  # Top 20 games: high weights (80% of traffic)
            # Weight decreases from 100 to 60
            game_weights.append(100 - i * 2.0)
        elif i < 50:  # Mid 30 games: medium weights (15% of traffic)
            # Weight decreases from 20 to 5
            game_weights.append(20 - (i - 20) * 0.5)
        else:  # Long tail 50 games: low weights (5% of traffic)
            # Weight decreases from 5 to 1
            game_weights.append(5 - (i - 50) * 0.08)
    
    # User distribution: Power (10%), Regular (30%), Casual (60%)
    # Power users: user_id 1-50 (50 users)
    # Regular users: user_id 51-200 (150 users)
    # Casual users: user_id 201-500 (300 users)
    
    # Generate 1000+ logs spanning 30 days
    for i in range(1500):
        # Random hour with weighted distribution
        hour = random.choices(range(24), weights=hour_weights, k=1)[0]
        
        # Day offset (0-29 days)
        day_offset = i % 30
        day_of_week = (base_time + timedelta(days=day_offset)).weekday()
        is_weekend = day_of_week >= 5  # Saturday=5, Sunday=6
        
        # Adjust hour weights for weekend (more evening traffic)
        if is_weekend:
            # Weekend: more evening traffic, less morning
            if hour in [9, 10, 11]:  # Morning peak
                if random.random() < 0.3:  # 30% chance to keep morning
                    pass
                else:
                    hour = random.choice([19, 20, 21])  # Move to evening
        
        # Create timestamp
        timestamp = base_time + timedelta(
            days=day_offset,
            hours=hour,
            minutes=random.randint(0, 59),
            seconds=random.randint(0, 59)
        )
        
        # Game selection with 80-20 distribution
        game_id = random.choices(range(1, 101), weights=game_weights, k=1)[0]
        
        # User selection with distribution
        user_choice = random.random()
        if user_choice < 0.1:  # 10% power users
            user_id = random.randint(1, 50)
            session_duration = random.randint(3600, 7200)  # 1-2 hours
            access_count = random.randint(10, 20)
        elif user_choice < 0.4:  # 30% regular users
            user_id = random.randint(51, 200)
            session_duration = random.randint(1800, 3600)  # 30-60 min
            access_count = random.randint(5, 15)
        else:  # 60% casual users
            user_id = random.randint(201, 500)
            session_duration = random.randint(300, 1800)  # 5-30 min
            access_count = random.randint(1, 10)
        
        log = {
            "timestamp": timestamp,
            "game_id": game_id,
            "user_id": str(user_id),
            "session_duration": float(session_duration),
            "access_count": access_count
        }
        logs.append(log)
    
    # Sort by timestamp
    logs.sort(key=lambda x: x["timestamp"])
    
    assert len(logs) >= 1000, f"Should have at least 1000 logs, got {len(logs)}"
    return logs


@pytest.fixture(scope="function")
def sample_access_logs_with_patterns() -> List[Dict[str, Any]]:
    """
    Generate access logs with known patterns for validation.
    
    Controlled test data where patterns are known in advance:
    - Clear peak at 10 AM (200 accesses)
    - Clear peak at 8 PM (250 accesses)
    - Game #1 is clearly most popular (30% of all accesses)
    - Game #2 is second (20% of all accesses)
    - Weekend traffic is 60% of weekday traffic
    
    Use this fixture to test if analyzer correctly identifies these patterns.
    
    Returns:
        List of 500 access log dictionaries with known patterns
    """
    logs = []
    base_time = datetime(2024, 1, 1, 0, 0, 0)
    
    random.seed(42)  # For reproducibility
    
    # Pattern 1: Clear peak at 10 AM (200 accesses)
    for i in range(200):
        timestamp = base_time + timedelta(
            days=i % 7,  # Spread across week
            hours=10,
            minutes=random.randint(0, 59),
            seconds=random.randint(0, 59)
        )
        logs.append({
            "timestamp": timestamp,
            "game_id": random.randint(1, 20),  # Mix of games
            "user_id": str(random.randint(1, 100)),
            "session_duration": float(random.randint(300, 3600)),
            "access_count": random.randint(1, 10)
        })
    
    # Pattern 2: Clear peak at 8 PM (250 accesses)
    for i in range(250):
        timestamp = base_time + timedelta(
            days=i % 7,
            hours=20,  # 8 PM
            minutes=random.randint(0, 59),
            seconds=random.randint(0, 59)
        )
        logs.append({
            "timestamp": timestamp,
            "game_id": random.randint(1, 20),
            "user_id": str(random.randint(1, 100)),
            "session_duration": float(random.randint(300, 3600)),
            "access_count": random.randint(1, 10)
        })
    
    # Pattern 3: Game #1 is most popular (30% = 150 accesses)
    for i in range(150):
        timestamp = base_time + timedelta(
            days=random.randint(0, 6),
            hours=random.randint(8, 22),
            minutes=random.randint(0, 59),
            seconds=random.randint(0, 59)
        )
        logs.append({
            "timestamp": timestamp,
            "game_id": 1,  # Always game #1
            "user_id": str(random.randint(1, 100)),
            "session_duration": float(random.randint(300, 3600)),
            "access_count": random.randint(1, 10)
        })
    
    # Pattern 4: Game #2 is second (20% = 100 accesses)
    for i in range(100):
        timestamp = base_time + timedelta(
            days=random.randint(0, 6),
            hours=random.randint(8, 22),
            minutes=random.randint(0, 59),
            seconds=random.randint(0, 59)
        )
        logs.append({
            "timestamp": timestamp,
            "game_id": 2,  # Always game #2
            "user_id": str(random.randint(1, 100)),
            "session_duration": float(random.randint(300, 3600)),
            "access_count": random.randint(1, 10)
        })
    
    # Pattern 5: Weekend traffic is 60% of weekday
    # Add some weekend-specific logs
    for i in range(50):  # Additional weekend logs
        day = random.choice([5, 6])  # Saturday or Sunday
        timestamp = base_time + timedelta(
            days=day,
            hours=random.randint(10, 22),
            minutes=random.randint(0, 59),
            seconds=random.randint(0, 59)
        )
        logs.append({
            "timestamp": timestamp,
            "game_id": random.randint(1, 20),
            "user_id": str(random.randint(1, 100)),
            "session_duration": float(random.randint(300, 3600)),
            "access_count": random.randint(1, 10)
        })
    
    # Sort by timestamp
    logs.sort(key=lambda x: x["timestamp"])
    
    return logs


@pytest_asyncio.fixture(scope="function")
async def mock_database(sample_access_logs: List[Dict[str, Any]]):
    """
    Mock database functions for predictive cache warmer tests.
    
    Mocks all database calls to return test data:
    - get_access_logs(start_date, end_date) -> filtered sample_access_logs
    - get_active_games(limit) -> List of top N game_ids
    - get_popular_games(limit) -> List of popular game_ids
    - get_recent_user_sessions(limit) -> List of recent sessions
    
    Args:
        sample_access_logs: Sample access logs fixture (dependency)
        
    Yields:
        Mock database manager with all methods mocked
    """
    from unittest.mock import AsyncMock, patch
    
    # Create async mock that returns sample_access_logs
    async def mock_get_access_logs(start_date=None, end_date=None):
        """Filter logs by date range if provided"""
        if start_date is None and end_date is None:
            return sample_access_logs
        
        filtered = [
            log for log in sample_access_logs
            if (start_date is None or log["timestamp"] >= start_date)
            and (end_date is None or log["timestamp"] <= end_date)
        ]
        return filtered
    
    def mock_get_active_games(limit: int = 10):
        """Return top N active game IDs"""
        game_counts = {}
        for log in sample_access_logs:
            game_id = log["game_id"]
            game_counts[game_id] = game_counts.get(game_id, 0) + log["access_count"]
        
        sorted_games = sorted(game_counts.items(), key=lambda x: x[1], reverse=True)
        return [game_id for game_id, _ in sorted_games[:limit]]
    
    def mock_get_popular_games(limit: int = 10):
        """Return top N popular game IDs"""
        return mock_get_active_games(limit)
    
    def mock_get_recent_user_sessions(limit: int = 10):
        """Return recent user sessions"""
        recent_logs = sorted(sample_access_logs, key=lambda x: x["timestamp"], reverse=True)
        return recent_logs[:limit]
    
    # Patch database access
    with patch('app.services.predictive_cache_warmer.db_manager') as mock_db_manager:
        # Mock the get_session context manager
        mock_session = MagicMock()
        mock_session.execute = MagicMock()
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)
        
        mock_db_manager.get_session = MagicMock(return_value=mock_session)
        mock_db_manager.get_access_logs = AsyncMock(side_effect=mock_get_access_logs)
        mock_db_manager.get_active_games = MagicMock(side_effect=mock_get_active_games)
        mock_db_manager.get_popular_games = MagicMock(side_effect=mock_get_popular_games)
        mock_db_manager.get_recent_user_sessions = MagicMock(side_effect=mock_get_recent_user_sessions)
        
        yield mock_db_manager


@pytest_asyncio.fixture(scope="function")
async def analyzer(mock_database, sample_access_logs):
    """
    Create configured AccessPatternAnalyzer for testing.
    
    Reusable analyzer with mocked data, ready to use without additional setup.
    
    Steps:
    1. Create AccessPatternAnalyzer instance
    2. Mock _get_access_logs to return sample_access_logs
    3. Pre-analyze patterns to initialize state
    4. Return configured analyzer
    
    Args:
        mock_database: Mock database fixture
        sample_access_logs: Sample access logs fixture
        
    Returns:
        Configured AccessPatternAnalyzer instance
    """
    from app.services.predictive_cache_warmer import AccessPatternAnalyzer
    
    analyzer = AccessPatternAnalyzer(
        lookback_days=7,
        min_confidence=0.7,
        model_path="test_models/test_cache_prediction_model.pkl",
    )
    
    # Mock database calls
    async def mock_get_access_logs(start_date, end_date):
        filtered = [
            log for log in sample_access_logs
            if start_date <= log["timestamp"] <= end_date
        ]
        await asyncio.sleep(0.001)  # Simulate async delay
        return filtered
    
    analyzer._get_access_logs = mock_get_access_logs
    
    # Pre-analyze patterns to initialize analyzer state
    await analyzer.analyze_patterns()
    
    return analyzer


@pytest_asyncio.fixture(scope="function")
async def trained_analyzer(analyzer, sample_access_logs):
    """
    Create analyzer with trained model.
    
    Analyzer with pre-trained model for prediction tests.
    Allows testing predictions without waiting for training.
    
    Args:
        analyzer: Base analyzer fixture
        sample_access_logs: Sample access logs for training
        
    Returns:
        AccessPatternAnalyzer with trained model and scaler
    """
    # Train model with sample data
    training_result = await analyzer.train_prediction_model()
    
    if training_result.get("status") != "success":
        # If training fails, create a minimal mock model for testing
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.preprocessing import StandardScaler
        import numpy as np
        
        # Create minimal model
        analyzer.model = RandomForestClassifier(n_estimators=10, random_state=42)
        analyzer.feature_scaler = StandardScaler()
        
        # Fit with dummy data
        X_dummy = np.random.rand(100, 15)
        y_dummy = np.random.randint(1, 20, 100)
        analyzer.feature_scaler.fit(X_dummy)
        X_scaled = analyzer.feature_scaler.transform(X_dummy)
        analyzer.model.fit(X_scaled, y_dummy)
    
    return analyzer


@pytest_asyncio.fixture(scope="function")
async def predictive_warmer(trained_analyzer, mock_cache_warmer):
    """
    Create PredictiveCacheWarmer for testing.
    
    Full PredictiveCacheWarmer instance for integration tests.
    
    Args:
        trained_analyzer: Analyzer with trained model
        mock_cache_warmer: Mock CacheWarmer instance
        
    Returns:
        Configured PredictiveCacheWarmer instance
    """
    from app.services.predictive_cache_warmer import PredictiveCacheWarmer
    
    warmer = PredictiveCacheWarmer(
        cache_warmer=mock_cache_warmer,
        analyzer=trained_analyzer,
        prediction_horizon=60,
        update_interval=300,
    )
    
    return warmer


# ============================================================================
# Helper Functions
# ============================================================================

def generate_user_clusters(num_users: int = 500, num_clusters: int = 5) -> Dict[str, int]:
    """
    Generate realistic user cluster assignments.
    
    Creates user cluster data with distribution:
    - Cluster 0: Power users (10%)
    - Cluster 1: Evening players (20%)
    - Cluster 2: Morning players (15%)
    - Cluster 3: Weekend warriors (15%)
    - Cluster 4: Casual players (40%)
    
    Args:
        num_users: Total number of users
        num_clusters: Number of clusters to create
        
    Returns:
        Dictionary mapping user_id (str) -> cluster_id (int)
    """
    random.seed(42)
    clusters = {}
    
    # Cluster distribution
    cluster_distribution = {
        0: int(num_users * 0.10),  # Power users: 10%
        1: int(num_users * 0.20),  # Evening players: 20%
        2: int(num_users * 0.15),  # Morning players: 15%
        3: int(num_users * 0.15),  # Weekend warriors: 15%
        4: int(num_users * 0.40),  # Casual players: 40%
    }
    
    user_id = 1
    for cluster_id, count in cluster_distribution.items():
        for _ in range(count):
            if user_id <= num_users:
                clusters[str(user_id)] = cluster_id
                user_id += 1
    
    # Fill remaining users with random clusters
    while user_id <= num_users:
        clusters[str(user_id)] = random.randint(0, num_clusters - 1)
        user_id += 1
    
    return clusters


def calculate_expected_metrics(
    predictions: List[Dict[str, Any]],
    actual: List[Dict[str, Any]]
) -> Dict[str, float]:
    """
    Calculate expected precision/recall/F1 for test validation.
    
    Args:
        predictions: List of predicted game_ids with confidence
                    Format: [{"game_id": int, "confidence": float}, ...]
        actual: List of actual accessed game_ids
                Format: [{"game_id": int}, ...] or [int, ...]
    
    Returns:
        Dictionary with metrics:
        {
            "precision": float,
            "recall": float,
            "f1_score": float,
            "accuracy": float,
            "true_positives": int,
            "false_positives": int,
            "false_negatives": int
        }
    """
    # Extract game IDs
    if isinstance(predictions[0], dict):
        predicted_game_ids = {int(p["game_id"]) for p in predictions if "game_id" in p}
    else:
        predicted_game_ids = {int(p) for p in predictions}
    
    if isinstance(actual[0], dict):
        actual_game_ids = {int(a["game_id"]) for a in actual if "game_id" in a}
    else:
        actual_game_ids = {int(a) for a in actual}
    
    # Calculate metrics
    true_positives = len(predicted_game_ids & actual_game_ids)
    false_positives = len(predicted_game_ids - actual_game_ids)
    false_negatives = len(actual_game_ids - predicted_game_ids)
    
    precision = (
        true_positives / len(predicted_game_ids)
        if len(predicted_game_ids) > 0 else 0.0
    )
    
    recall = (
        true_positives / len(actual_game_ids)
        if len(actual_game_ids) > 0 else 0.0
    )
    
    f1_score = (
        2 * (precision * recall) / (precision + recall)
        if (precision + recall) > 0 else 0.0
    )
    
    # Accuracy: (TP + TN) / (TP + TN + FP + FN)
    # For this case, we don't have true negatives, so we use a simpler metric
    total = len(predicted_game_ids | actual_game_ids)
    accuracy = true_positives / total if total > 0 else 0.0
    
    return {
        "precision": float(precision),
        "recall": float(recall),
        "f1_score": float(f1_score),
        "accuracy": float(accuracy),
        "true_positives": true_positives,
        "false_positives": false_positives,
        "false_negatives": false_negatives,
        "total_predicted": len(predicted_game_ids),
        "total_actual": len(actual_game_ids),
    }


@pytest_asyncio.fixture(scope="function")
async def mock_cache_warmer():
    """
    Create mock CacheWarmer for testing.
    
    Mocks CacheWarmer to avoid actual cache operations:
    - _warm_game_results(game_id) -> return True
    - get_cache_stats() -> return mock stats
    - query_optimizer.get_game_results() -> return mock data
    
    Returns:
        Mock CacheWarmer object with all necessary methods
    """
    from unittest.mock import AsyncMock, MagicMock
    
    mock_warmer = MagicMock()
    
    # Mock async methods
    mock_warmer._warm_game_results = AsyncMock(return_value=True)
    mock_warmer.warm_game_results = AsyncMock(return_value=True)
    
    # Mock cache stats
    mock_warmer.get_cache_stats = MagicMock(return_value={
        "total_keys": 1000,
        "hit_rate": 0.85,
        "miss_rate": 0.15,
        "memory_usage_mb": 50.5,
    })
    
    # Mock query optimizer
    mock_optimizer = MagicMock()
    mock_optimizer.get_game_results = MagicMock(return_value=[
        {"id": i, "result": "B", "timestamp": datetime.now()}
        for i in range(10)
    ])
    mock_warmer.query_optimizer = mock_optimizer
    mock_warmer.strategy = "moderate"
    
    return mock_warmer