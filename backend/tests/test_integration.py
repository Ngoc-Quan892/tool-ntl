"""
End-to-end integration tests for predictive cache warming components.

These tests ensure the ML analyzer, predictive warmer, and scheduling logic
work together correctly across realistic workflows.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch, call

import pytest

from app.services.predictive_cache_warmer import PredictiveCacheWarmer


@pytest.mark.asyncio
async def test_complete_cache_warming_workflow(trained_analyzer, mock_cache_warmer):
    """
    Validate the full workflow: predictions are generated and passed to the cache warmer.
    """
    warmer = PredictiveCacheWarmer(
        cache_warmer=mock_cache_warmer,
        analyzer=trained_analyzer,
        prediction_horizon=60,
        update_interval=1,
    )

    sample_predictions = [
        {"game_id": 11, "confidence": 0.92, "time_horizon": 60},
        {"game_id": 22, "confidence": 0.88, "time_horizon": 60},
    ]

    trained_analyzer.predict_next_access = AsyncMock(side_effect=[sample_predictions, []])

    async def fast_sleep(_):
        warmer.is_running = False

    warmer.is_running = True
    with patch("app.services.predictive_cache_warmer.asyncio.sleep", side_effect=fast_sleep):
        await warmer._warming_loop()

    assert mock_cache_warmer._warm_game_results.await_count == len(sample_predictions)
    warmed_ids = [call.args[0] for call in mock_cache_warmer._warm_game_results.await_args_list]
    assert warmed_ids == [11, 22]
    assert warmer.prediction_history, "Prediction history should record at least one entry"


@pytest.mark.asyncio
async def test_scheduled_cache_warming_creates_background_tasks(trained_analyzer, mock_cache_warmer):
    """
    Ensure start_predictive_warming schedules background loops and can stop cleanly.
    """
    warmer = PredictiveCacheWarmer(
        cache_warmer=mock_cache_warmer,
        analyzer=trained_analyzer,
        prediction_horizon=15,
        update_interval=1,
    )

    trained_analyzer._load_model = MagicMock(return_value=True)
    trained_analyzer.analyze_patterns = AsyncMock(return_value={})

    created_tasks = []

    class _DummyTask:
        def __init__(self, coro):
            self.coro = coro
            self.cancelled = False

        def cancel(self):
            self.cancelled = True

    def fake_create_task(coro):
        task = _DummyTask(coro)
        created_tasks.append(task)
        return task

    with patch("app.services.predictive_cache_warmer.asyncio.create_task", side_effect=fake_create_task):
        await warmer.start_predictive_warming()

    assert warmer.is_running is True
    assert len(created_tasks) == 2, "Should create warming and evaluation tasks"

    await warmer.stop_predictive_warming()
    assert warmer.is_running is False
    assert all(task.cancelled for task in created_tasks)


@pytest.mark.asyncio
async def test_data_pipeline_integration(analyzer):
    """
    Train the model end-to-end and ensure predictions are produced with expected structure.
    """
    result = await analyzer.train_prediction_model()
    assert result.get("status") == "success", f"Training failed: {result}"
    assert analyzer.model is not None
    assert analyzer.feature_scaler is not None

    predictions = await analyzer.predict_next_access(time_horizon=60, top_k=5)
    assert isinstance(predictions, list)
    assert predictions, "Prediction list should not be empty after successful training"
    assert all({"game_id", "confidence", "time_horizon"} <= set(pred.keys()) for pred in predictions)


@pytest.mark.asyncio
async def test_error_propagation_through_pipeline(analyzer):
    """
    Verify database errors propagate through training and prediction steps with clear signals.
    """

    async def raise_db_error(*_, **__):
        raise ConnectionError("DB unavailable")

    analyzer._get_access_logs = raise_db_error

    result = await analyzer.train_prediction_model()
    assert result["status"] == "error"
    assert "DB unavailable" in result.get("error", "")

    predictions = await analyzer.predict_next_access()
    assert predictions == [], "Prediction should return empty list when training cannot run"


@pytest.mark.asyncio
async def test_concurrent_predictions(trained_analyzer):
    """
    Ensure the analyzer can handle multiple concurrent prediction requests.
    """
    horizons = [15, 30, 60, 120, 240]
    tasks = [
        trained_analyzer.predict_next_access(time_horizon=h, top_k=3)
        for h in horizons
    ]

    results = await asyncio.gather(*tasks)

    assert len(results) == len(horizons)
    for predictions in results:
        assert isinstance(predictions, list)
        for prediction in predictions:
            assert prediction["time_horizon"] in horizons


@pytest.mark.asyncio
async def test_partial_cache_warming_failure(trained_analyzer, mock_cache_warmer):
    """
    Cache warming should continue even if some cache operations fail.
    """
    warmer = PredictiveCacheWarmer(
        cache_warmer=mock_cache_warmer,
        analyzer=trained_analyzer,
        prediction_horizon=30,
        update_interval=1,
    )

    failure_game_id = 42
    sample_predictions = [
        {"game_id": 10, "confidence": 0.95, "time_horizon": 30},
        {"game_id": failure_game_id, "confidence": 0.9, "time_horizon": 30},
        {"game_id": 77, "confidence": 0.85, "time_horizon": 30},
    ]

    async def warm_side_effect(game_id, limit=100):
        if game_id == failure_game_id:
            raise RuntimeError("Cache unavailable")
        return True

    mock_cache_warmer._warm_game_results.side_effect = warm_side_effect
    trained_analyzer.predict_next_access = AsyncMock(side_effect=[sample_predictions, []])

    async def fast_sleep(_):
        warmer.is_running = False

    warmer.is_running = True
    with patch("app.services.predictive_cache_warmer.asyncio.sleep", side_effect=fast_sleep):
        await warmer._warming_loop()

    assert mock_cache_warmer._warm_game_results.await_count == len(sample_predictions)
    failed_calls = [
        call for call in mock_cache_warmer._warm_game_results.await_args_list
        if call.args and call.args[0] == failure_game_id
    ]
    assert failed_calls, "Failing game should still be attempted"

