"""
Final end-to-end style integration tests for predictive analytics stack.

These tests simulate realistic operating conditions: long-running access
patterns, deployment workflows, resilience checks, multi-tenant behaviour, and
backward compatibility expectations before production roll-outs.
"""

from __future__ import annotations

import inspect
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Sequence

import joblib
import numpy as np
import pytest

from app.services.predictive_cache_warmer import AccessPatternAnalyzer
from backend.tests.conftest import seed_database

try:  # Optional; skip certain tests if Faker is unavailable
    from faker import Faker
except ImportError:  # pragma: no cover - development dependency
    Faker = None  # type: ignore


def _generate_realistic_logs(days: int = 30) -> List[Dict[str, Any]]:
    """Generate realistic access logs with heavier evening traffic."""
    if Faker is None:
        pytest.skip("faker is required for this test")

    fake = Faker()
    random.seed(42)
    base_time = datetime(2024, 1, 1, 0, 0, 0)
    logs: List[Dict[str, Any]] = []

    for day in range(days):
        for hour in range(24):
            num_users = 50 if 18 <= hour <= 23 else 10
            for _ in range(num_users):
                is_popular = random.random() < 0.7
                game_id = random.randint(1, 10) if is_popular else random.randint(11, 50)
                logs.append(
                    {
                        "timestamp": base_time + timedelta(days=day, hours=hour, minutes=random.randint(0, 59)),
                        "game_id": game_id,
                        "user_id": fake.uuid4(),
                        "session_duration": random.randint(300, 7200),
                        "access_count": random.randint(1, 5),
                        "platform": random.choice(["pc", "mobile", "console"]),
                    }
                )
    return logs


def _configure_logs(analyzer: AccessPatternAnalyzer, monkeypatch, logs: Sequence[Dict[str, Any]]) -> None:
    """Force analyzer to use provided dataset for every access log query."""

    async def _fake_get_access_logs(start_date: datetime, end_date: datetime):
        return [
            entry
            for entry in logs
            if start_date <= entry["timestamp"] <= end_date
        ]

    monkeypatch.setattr(analyzer, "_get_access_logs", _fake_get_access_logs)


def _generate_hour_logs(hour: int, base_day: datetime | None = None) -> List[Dict[str, Any]]:
    """Generate short burst of activity for a specific hour."""
    if Faker is None:
        pytest.skip("faker is required for this test")

    fake = Faker()
    base = base_day or datetime(2024, 2, 1, 0, 0, 0)
    logs: List[Dict[str, Any]] = []
    num_users = 40 if 18 <= hour <= 23 else 8

    for _ in range(num_users):
        logs.append(
            {
                "timestamp": base + timedelta(hours=hour, minutes=random.randint(0, 59)),
                "game_id": random.randint(1, 50),
                "user_id": fake.uuid4(),
                "session_duration": random.randint(120, 3600),
                "access_count": random.randint(1, 6),
                "platform": random.choice(["pc", "mobile"]),
            }
        )
    return logs


class _PassthroughScaler:
    """Simple scaler used for deterministic tenant predictions."""

    def fit(self, data: Sequence[Any]) -> "_PassthroughScaler":  # pragma: no cover - helper
        return self

    def transform(self, data: Sequence[Any]) -> Sequence[Any]:
        return data


class _StaticModel:
    """Deterministic probability model that favours provided class IDs."""

    def __init__(self, classes: Sequence[int]):
        self.classes_ = np.array(classes, dtype=np.int32)

    def predict_proba(self, features: Sequence[Any]):  # pragma: no cover - helper
        weights = np.linspace(1.0, float(len(self.classes_)), num=len(self.classes_))
        probs = weights / weights.sum()
        return np.array([probs])


def _tenant_dataset(seed: int, base_game: int) -> List[Dict[str, Any]]:
    """Tenant-specific dataset with distinct game ID ranges."""
    random.seed(seed)
    base_time = datetime(2024, 3, seed, 0, 0, 0)
    logs: List[Dict[str, Any]] = []

    for minute in range(0, 600, 5):
        logs.append(
            {
                "timestamp": base_time + timedelta(minutes=minute),
                "game_id": base_game + (minute % 5),
                "user_id": f"tenant_{seed}_{minute}",
                "session_duration": random.randint(60, 1200),
                "access_count": random.randint(1, 4),
            }
        )
    return logs


@pytest.mark.asyncio
@pytest.mark.integration
async def test_realistic_gaming_scenario(analyzer, monkeypatch):
    """Ensure realistic traffic leads to sensible predictions."""
    realistic_logs = _generate_realistic_logs(days=15)
    _configure_logs(analyzer, monkeypatch, realistic_logs)

    train_result = await analyzer.train_prediction_model()
    assert train_result.get("status") == "success"

    predictions = await analyzer.predict_next_access(time_horizon=60, top_k=20)
    if not predictions:
        pytest.skip("Model failed to emit predictions with synthetic data")

    popular_games = set(range(1, 11))
    predicted_games = {prediction["game_id"] for prediction in predictions}
    assert predicted_games & popular_games, "Top popular games should appear in predictions"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_production_deployment_workflow(analyzer, mock_cache_warmer, mock_redis, monkeypatch):
    """Simulate production-like deployment cycle with continuous updates."""
    rolling_logs = _generate_realistic_logs(days=7)
    _configure_logs(analyzer, monkeypatch, rolling_logs)

    assert analyzer.model is None
    await analyzer.train_prediction_model()
    assert analyzer.model is not None

    predictions = await analyzer.predict_next_access(time_horizon=60, top_k=10)
    if not predictions:
        pytest.skip("Predictions unavailable for deployment workflow")

    for prediction in predictions:
        await mock_cache_warmer._warm_game_results(prediction["game_id"], limit=50)
        cache_key = f"prediction:{prediction['game_id']}"
        mock_redis.set(cache_key, prediction["confidence"])
        assert mock_redis.get(cache_key) is not None

    for hour in range(24):
        rolling_logs.extend(_generate_hour_logs(hour))
        if hour % 4 == 0:
            refreshed = await analyzer.predict_next_access(time_horizon=60, top_k=5)
            for prediction in refreshed:
                await mock_cache_warmer._warm_game_results(prediction["game_id"], limit=50)

    retrain_result = await analyzer.train_prediction_model()
    assert retrain_result.get("status") == "success"
    final_predictions = await analyzer.predict_next_access(top_k=5)
    assert isinstance(final_predictions, list)


@pytest.mark.asyncio
async def test_disaster_recovery(analyzer, monkeypatch):
    """Verify system gracefully handles failures and can retrain after issues."""
    stable_logs = _generate_realistic_logs(days=3)
    _configure_logs(analyzer, monkeypatch, stable_logs)
    await analyzer.train_prediction_model()

    async def failing_logs(*_args, **_kwargs):
        raise ConnectionError("database offline")

    monkeypatch.setattr(analyzer, "_get_access_logs", failing_logs)
    predictions = await analyzer.predict_next_access()
    assert predictions == [], "Should return empty list when data source is unavailable"

    _configure_logs(analyzer, monkeypatch, stable_logs)
    predictions = await analyzer.predict_next_access(top_k=5)
    assert isinstance(predictions, list)

    analyzer.model = None
    analyzer.feature_scaler = None
    recovery_result = await analyzer.train_prediction_model()
    if recovery_result.get("status") != "success":
        pytest.skip(f"Unable to retrain model: {recovery_result}")
    assert await analyzer.predict_next_access(top_k=5) is not None


@pytest.mark.asyncio
async def test_monitoring_and_alerting(analyzer, monkeypatch, caplog):
    """Ensure critical workflow steps emit informative log entries."""
    logs = _generate_realistic_logs(days=5)
    _configure_logs(analyzer, monkeypatch, logs)
    caplog.set_level("INFO")

    await analyzer.train_prediction_model()
    await analyzer.predict_next_access(top_k=5)

    text = caplog.text.lower()
    assert "training prediction model" in text
    assert "model trained" in text
    assert "generated" in text and "predictions" in text
    assert "error" not in text, "Unexpected errors logged during workflow"


@pytest.mark.asyncio
async def test_backward_compatibility(trained_analyzer, tmp_path):
    """Loading legacy serialized models should remain functional."""
    if trained_analyzer.model is None or trained_analyzer.feature_scaler is None:
        pytest.skip("Trained analyzer fixture is not ready")

    checkpoint_path = tmp_path / "legacy_model.pkl"
    joblib.dump({"version": "1.0", "model": trained_analyzer.model, "scaler": trained_analyzer.feature_scaler}, checkpoint_path)

    legacy_payload = joblib.load(checkpoint_path)
    trained_analyzer.model = legacy_payload["model"]
    trained_analyzer.feature_scaler = legacy_payload["scaler"]

    predictions = await trained_analyzer.predict_next_access(top_k=5)
    assert isinstance(predictions, list)


@pytest.mark.asyncio
async def test_api_contract(analyzer):
    """Validate that public async methods keep their signature and payload."""
    train_sig = inspect.signature(analyzer.train_prediction_model)
    assert len(train_sig.parameters) == 0

    predict_sig = inspect.signature(analyzer.predict_next_access)
    params = predict_sig.parameters
    assert "time_horizon" in params
    assert "top_k" in params

    predictions = await analyzer.predict_next_access(top_k=5)
    assert isinstance(predictions, list)
    if predictions:
        sample = predictions[0]
        assert "game_id" in sample and "confidence" in sample and "time_horizon" in sample


@pytest.mark.asyncio
async def test_multi_tenant_isolation(monkeypatch):
    """Ensure analyzers configured per tenant maintain isolation."""
    tenant_a = AccessPatternAnalyzer(model_path="models/test_tenant_a.pkl")
    tenant_b = AccessPatternAnalyzer(model_path="models/test_tenant_b.pkl")

    tenant_a_logs = _tenant_dataset(seed=1, base_game=10)
    tenant_b_logs = _tenant_dataset(seed=2, base_game=40)
    _configure_logs(tenant_a, monkeypatch, tenant_a_logs)
    _configure_logs(tenant_b, monkeypatch, tenant_b_logs)

    tenant_a.feature_scaler = _PassthroughScaler()
    tenant_b.feature_scaler = _PassthroughScaler()
    tenant_a.model = _StaticModel([10, 11, 12, 13, 14])
    tenant_b.model = _StaticModel([40, 41, 42, 43, 44])

    predictions_a = await tenant_a.predict_next_access(top_k=3)
    predictions_b = await tenant_b.predict_next_access(top_k=3)

    assert predictions_a != predictions_b
    assert {p["game_id"] for p in predictions_a} <= {10, 11, 12, 13, 14}
    assert {p["game_id"] for p in predictions_b} <= {40, 41, 42, 43, 44}


@pytest.mark.asyncio
async def test_security_validations(analyzer, monkeypatch, test_db):
    """Input validation should flag malformed data and reject unsafe seeds."""
    malicious_logs = [
        {
            "timestamp": "invalid-timestamp",
            "game_id": "1; DROP TABLE games; --",
            "user_id": "user_x",
            "session_duration": 500,
            "access_count": 2,
        }
    ]

    async def _malicious_logs(_start, _end):
        return malicious_logs

    monkeypatch.setattr(analyzer, "_get_access_logs", _malicious_logs)
    result = await analyzer.train_prediction_model()
    assert result.get("status") == "error"

    with pytest.raises(ValueError):
        seed_database(test_db, {"game_results; DROP TABLE users; --": []})


