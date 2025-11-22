import asyncio
import gc
import time
from datetime import datetime, timedelta
from statistics import mean
from typing import Any, Dict, List, Sequence

import pandas as pd
import pytest

from app.services.predictive_cache_warmer import PredictiveCacheWarmer

try:  # Optional dependency for memory assertions
    import psutil
except ImportError:  # pragma: no cover - psutil should be available via requirements
    psutil = None


def _generate_access_logs(
    length_minutes: int,
    step_minutes: int = 5,
    game_count: int = 50,
    user_count: int = 200,
) -> List[Dict[str, Any]]:
    """Generate synthetic access log entries with realistic fields."""
    start_time = datetime.utcnow() - timedelta(minutes=length_minutes)
    logs: List[Dict[str, Any]] = []

    for idx, minute_offset in enumerate(range(0, length_minutes, step_minutes)):
        timestamp = start_time + timedelta(minutes=minute_offset)
        logs.append(
            {
                "timestamp": timestamp,
                "game_id": (idx % game_count) + 1,
                "user_id": f"user_{idx % user_count}",
                "session_duration": float(300 + (idx % 900)),
                "access_count": (idx % 5) + 1,
            }
        )

    return logs


def _configure_analyzer_dataset(analyzer, monkeypatch, dataset: Sequence[Dict[str, Any]]):
    """Helper to make analyzer use in-memory dataset for all access log queries."""

    async def _fake_get_access_logs(start_date: datetime, end_date: datetime):
        # Provide coverage even if requested window misses synthetic timestamps
        if start_date is None or end_date is None:
            return list(dataset)

        filtered = [
            log
            for log in dataset
            if start_date <= log["timestamp"] <= end_date
        ]

        return filtered or list(dataset)

    monkeypatch.setattr(analyzer, "_get_access_logs", _fake_get_access_logs)


def _percentile(values: Sequence[float], quantile: float) -> float:
    """Compute percentile with basic interpolation."""
    if not values:
        return 0.0
    sorted_vals = sorted(values)
    index = min(len(sorted_vals) - 1, int(round(quantile * (len(sorted_vals) - 1))))
    return sorted_vals[index]


# Reusable datasets to avoid regenerating large payloads repeatedly
TRAINING_DATASET = _generate_access_logs(length_minutes=30 * 24 * 60, step_minutes=10, game_count=120, user_count=500)
RECENT_DATASET = _generate_access_logs(length_minutes=6 * 60, step_minutes=2, game_count=80, user_count=400)
BULK_DATASET = _generate_access_logs(length_minutes=12 * 60, step_minutes=1, game_count=60, user_count=600)


@pytest.mark.asyncio
@pytest.mark.slow
async def test_training_performance_large_dataset(analyzer, monkeypatch):
    """Training should finish within acceptable latency even on sizeable datasets."""
    _configure_analyzer_dataset(analyzer, monkeypatch, TRAINING_DATASET)

    start_time = time.perf_counter()
    train_result = await analyzer.train_prediction_model()
    elapsed = time.perf_counter() - start_time

    assert train_result.get("status") == "success"
    assert train_result.get("n_samples", 0) >= 100
    assert elapsed < 15, f"Training took {elapsed:.2f}s, expected < 15s"


@pytest.mark.asyncio
async def test_prediction_latency(trained_analyzer, monkeypatch):
    """Predictions should return quickly with consistent latency bounds."""
    _configure_analyzer_dataset(trained_analyzer, monkeypatch, RECENT_DATASET)

    latencies: List[float] = []
    for _ in range(50):
        start = time.perf_counter()
        predictions = await trained_analyzer.predict_next_access(top_k=10)
        latencies.append(time.perf_counter() - start)
        assert isinstance(predictions, list)

    avg_latency = mean(latencies)
    p95_latency = _percentile(latencies, 0.95)

    assert avg_latency < 0.08, f"Avg latency {avg_latency:.3f}s > 80ms"
    assert p95_latency < 0.12, f"P95 latency {p95_latency:.3f}s > 120ms"


@pytest.mark.asyncio
@pytest.mark.slow
async def test_memory_usage_training(analyzer, monkeypatch):
    """Training should not grow process RSS beyond the agreed threshold."""
    if psutil is None:
        pytest.skip("psutil not available for memory assertions")

    _configure_analyzer_dataset(analyzer, monkeypatch, TRAINING_DATASET)

    process = psutil.Process()
    gc.collect()
    baseline = process.memory_info().rss / (1024 * 1024)

    await analyzer.train_prediction_model()
    gc.collect()
    peak = process.memory_info().rss / (1024 * 1024)

    assert (peak - baseline) < 500, f"Memory increased by {(peak - baseline):.1f}MB (> 500MB)"


@pytest.mark.asyncio
async def test_concurrent_prediction_throughput(trained_analyzer, monkeypatch):
    """High concurrency prediction calls should sustain healthy throughput."""
    _configure_analyzer_dataset(trained_analyzer, monkeypatch, RECENT_DATASET)

    num_requests = 200
    start = time.perf_counter()
    tasks = [
        trained_analyzer.predict_next_access(time_horizon=60, top_k=5)
        for _ in range(num_requests)
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    elapsed = time.perf_counter() - start

    throughput = num_requests / elapsed
    errors = [r for r in results if isinstance(r, Exception)]

    assert not errors, f"Had {len(errors)} errors: {errors[:3]}"
    assert throughput > 100, f"Throughput {throughput:.1f} req/s < 100 req/s"


@pytest.mark.asyncio
async def test_cache_warming_performance(trained_analyzer, mock_cache_warmer, monkeypatch):
    """Warming predicted items should complete within the soft SLA."""
    _configure_analyzer_dataset(trained_analyzer, monkeypatch, RECENT_DATASET)

    predictions = [
        {"game_id": i, "confidence": 0.9, "time_horizon": 60}
        for i in range(1, 1001)
    ]

    async def _fake_predict_next_access(*args, **kwargs):
        return predictions

    monkeypatch.setattr(trained_analyzer, "predict_next_access", _fake_predict_next_access)

    warmer = PredictiveCacheWarmer(
        cache_warmer=mock_cache_warmer,
        analyzer=trained_analyzer,
        prediction_horizon=60,
        update_interval=1,
    )

    start = time.perf_counter()
    warmed = 0
    for prediction in predictions:
        success = await warmer.cache_warmer._warm_game_results(prediction["game_id"], limit=50)
        if success:
            warmed += 1
    elapsed = time.perf_counter() - start

    assert warmed == len(predictions)
    assert elapsed < 5, f"Cache warming took {elapsed:.2f}s for 1000 items"


@pytest.mark.asyncio
async def test_feature_extraction_performance(analyzer):
    """Feature extraction over large batches should stay performant."""
    recent_logs = pd.DataFrame(_generate_access_logs(length_minutes=12 * 60, step_minutes=1, game_count=40, user_count=120))
    historical_logs = pd.DataFrame(BULK_DATASET)

    recent_logs["timestamp"] = pd.to_datetime(recent_logs["timestamp"])
    historical_logs["timestamp"] = pd.to_datetime(historical_logs["timestamp"])

    start = time.perf_counter()
    features = analyzer._extract_features(recent_logs, historical_logs)
    elapsed = time.perf_counter() - start

    assert features is not None
    assert elapsed < 5, f"Feature extraction took {elapsed:.2f}s (>5s)"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_database_query_performance(test_db, monkeypatch, sample_results):
    """Database-backed access log queries should respond quickly."""
    from app.models.database import GameResult

    class _SessionContext:
        def __init__(self, session):
            self._session = session

        def __enter__(self):
            return self._session

        def __exit__(self, exc_type, exc, tb):
            return False

    class _TestDBManager:
        def __init__(self, session):
            self._session = session

        def get_session(self):
            return _SessionContext(self._session)

    # Populate extra rows to mimic 90 days of data
    now = datetime.utcnow()
    for day in range(30):
        record = GameResult(
            result="B",
            shoe_number=999,
            hand_number=day + 1,
            timestamp=now - timedelta(days=day),
            true_count=0.0,
            edge=0.0,
        )
        test_db.add(record)
    test_db.commit()

    from app.services import predictive_cache_warmer as pcw_module

    monkeypatch.setattr(pcw_module, "db_manager", _TestDBManager(test_db))

    analyzer = pcw_module.AccessPatternAnalyzer(lookback_days=90)

    start = time.perf_counter()
    logs = await analyzer._get_access_logs(
        start_date=datetime.utcnow() - timedelta(days=90),
        end_date=datetime.utcnow(),
    )
    elapsed = time.perf_counter() - start

    assert logs, "Should return data"
    assert elapsed < 2, f"Query took {elapsed:.2f}s (>2s)"


@pytest.mark.asyncio
async def test_batch_prediction_performance(trained_analyzer, monkeypatch):
    """Batching repeated predictions should provide tangible speedups."""
    _configure_analyzer_dataset(trained_analyzer, monkeypatch, RECENT_DATASET)

    num_batches = 20
    batch_size = 5

    start_individual = time.perf_counter()
    for _ in range(num_batches * batch_size):
        await trained_analyzer.predict_next_access(top_k=5)
    individual_time = time.perf_counter() - start_individual

    start_batch = time.perf_counter()
    for _ in range(num_batches):
        await trained_analyzer.predict_next_access(top_k=batch_size)
    batch_time = time.perf_counter() - start_batch

    speedup = individual_time / batch_time if batch_time else float("inf")
    assert speedup > 5, f"Batching only {speedup:.2f}x faster, expected > 5x"


@pytest.mark.asyncio
async def test_resource_cleanup_after_operations(trained_analyzer, monkeypatch):
    """Repeated operations should not leak an excessive number of Python objects."""
    _configure_analyzer_dataset(trained_analyzer, monkeypatch, TRAINING_DATASET)

    gc.collect()
    initial_objects = len(gc.get_objects())

    for _ in range(20):
        await trained_analyzer.train_prediction_model()
        await trained_analyzer.predict_next_access(top_k=5)

    trained_analyzer.user_clusters.clear()
    gc.collect()
    final_objects = len(gc.get_objects())

    growth = final_objects - initial_objects
    assert growth < 1000, f"Object count grew by {growth}, indicates potential leak"


@pytest.mark.asyncio
@pytest.mark.slow
async def test_system_stability_under_stress(trained_analyzer, monkeypatch):
    """The analyzer should remain stable under continuous predictive load."""
    _configure_analyzer_dataset(trained_analyzer, monkeypatch, RECENT_DATASET)

    duration = 10  # seconds
    start_time = time.perf_counter()
    request_count = 0
    errors: List[Exception] = []

    while time.perf_counter() - start_time < duration:
        try:
            await trained_analyzer.predict_next_access(top_k=5)
            request_count += 1
        except Exception as exc:  # pragma: no cover - guardrail
            errors.append(exc)
        await asyncio.sleep(0.01)

    error_rate = (len(errors) / request_count) if request_count else 1

    assert request_count > 500, f"Only processed {request_count} requests"
    assert error_rate < 0.01, f"Error rate {error_rate:.3%} > 1%"

