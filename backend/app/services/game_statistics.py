"""
Advanced game statistics aggregation with query optimization, caching, and monitoring.
"""
from __future__ import annotations

import logging
import threading
import time
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from sqlalchemy import Float, case, cast, func
from sqlalchemy.orm import Session

from app.models.database import GameResult, db_manager
from app.services.error_recovery import CircuitBreaker, CircuitBreakerConfig

logger = logging.getLogger(__name__)


class EnhancedQueryOptimizer:
    """Builds efficient aggregate queries tailored to the current database dialect."""

    def __init__(self, session: Session):
        self.session = session
        self.dialect = (
            getattr(getattr(session, "bind", None), "dialect", None).name
            if getattr(session, "bind", None)
            else "generic"
        )

    def fetch_game_statistics(self, days: int) -> Dict[str, float]:
        """Return aggregated statistics for the requested rolling window."""
        cutoff = datetime.utcnow() - timedelta(days=days)

        confidence_expr = func.coalesce(
            cast(self._confidence_expr(), Float),
            0.0,
        )
        accuracy_expr = case(
            (self._recommend_expr() == GameResult.result, 1.0),
            else_=0.0,
        )

        query = (
            self.session.query(
                func.count(GameResult.id).label("total_games"),
                func.avg(accuracy_expr).label("win_rate"),
                func.avg(confidence_expr).label("avg_confidence"),
            )
            .filter(GameResult.timestamp >= cutoff)
        )

        row = query.one_or_none()
        if not row:
            return {"total_games": 0, "win_rate": 0.0, "avg_confidence": 0.0}

        total_games = int(row.total_games or 0)
        win_rate = float(row.win_rate or 0.0)
        avg_confidence = float(row.avg_confidence or 0.0)

        return {
            "total_games": total_games,
            "win_rate": round(win_rate, 4),
            "avg_confidence": round(avg_confidence, 2),
        }

    def _confidence_expr(self):
        if self.dialect == "sqlite":
            return func.json_extract(GameResult.prediction, "$.confidence")
        return GameResult.prediction["confidence"].astext

    def _recommend_expr(self):
        if self.dialect == "sqlite":
            return func.json_extract(GameResult.prediction, "$.recommend")
        return GameResult.prediction["recommend"].astext


class AdvancedCacheManager:
    """In-memory cache with TTL control and optional stale fallback."""

    def __init__(self, ttl_seconds: int = 3600):
        self.ttl_seconds = ttl_seconds
        self._store: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()

    def build_key(self, prefix: str, *parts: Any) -> str:
        key_parts = ":".join(str(part) for part in parts)
        return f"{prefix}:{key_parts}"

    def get(self, key: str, allow_stale: bool = False) -> Optional[Any]:
        with self._lock:
            entry = self._store.get(key)
            if not entry:
                return None

            if entry["expires_at"] >= time.time():
                return entry["value"]

            if allow_stale:
                return entry["value"]

            self._store.pop(key, None)
            return None

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            self._store[key] = {
                "value": value,
                "expires_at": time.time() + self.ttl_seconds,
            }


class AdvancedPerformanceMonitor:
    """Tracks execution metrics and cache efficiency."""

    def __init__(self):
        self.metrics: Dict[str, Dict[str, Any]] = {}

    def record(self, name: str, duration: float, success: bool, from_cache: bool) -> None:
        metric = self.metrics.setdefault(
            name,
            {
                "calls": 0,
                "errors": 0,
                "cache_hits": 0,
                "total_time": 0.0,
                "last_duration_ms": 0.0,
            },
        )
        metric["calls"] += 1
        metric["total_time"] += duration
        metric["last_duration_ms"] = round(duration * 1000, 2)
        if not success:
            metric["errors"] += 1
        if from_cache:
            metric["cache_hits"] += 1

    def summary(self) -> Dict[str, Any]:
        summary: Dict[str, Any] = {}
        for name, metric in self.metrics.items():
            avg = metric["total_time"] / metric["calls"] if metric["calls"] else 0.0
            summary[name] = {
                "calls": metric["calls"],
                "errors": metric["errors"],
                "cache_hits": metric["cache_hits"],
                "avg_duration_ms": round(avg * 1000, 2),
                "last_duration_ms": metric["last_duration_ms"],
            }
        return summary


_stats_cache = AdvancedCacheManager(ttl_seconds=3600)
_stats_monitor = AdvancedPerformanceMonitor()
_stats_circuit_breaker = CircuitBreaker(
    "game_statistics",
    CircuitBreakerConfig(failure_threshold=3, recovery_timeout=30),
)


def get_game_statistics(days: int = 30) -> Dict[str, float]:
    """
    Aggregate Baccarat game statistics with caching, monitoring, and resiliency.

    Returns:
        Dict containing total_games, win_rate, avg_confidence.
    """
    if days <= 0:
        raise ValueError("days must be a positive integer")

    start = time.perf_counter()
    cache_key = _stats_cache.build_key("game_stats", days)
    cached = _stats_cache.get(cache_key)
    if cached is not None:
        duration = time.perf_counter() - start
        _stats_monitor.record("get_game_statistics", duration, True, True)
        return cached

    def _compute() -> Dict[str, float]:
        with db_manager.get_session() as session:
            optimizer = EnhancedQueryOptimizer(session)
            return optimizer.fetch_game_statistics(days)

    try:
        stats = _stats_circuit_breaker.call(_compute)
        stats = _sanitize_stats(stats)
        _stats_cache.set(cache_key, stats)
        duration = time.perf_counter() - start
        _stats_monitor.record("get_game_statistics", duration, True, False)
        return stats
    except Exception as exc:
        logger.error("Failed to compute game statistics: %s", exc, exc_info=True)
        fallback = _stats_cache.get(cache_key, allow_stale=True)
        duration = time.perf_counter() - start
        _stats_monitor.record("get_game_statistics", duration, False, fallback is not None)
        if fallback is not None:
            return fallback
        return {"total_games": 0, "win_rate": 0.0, "avg_confidence": 0.0}


def _sanitize_stats(stats: Optional[Dict[str, Any]]) -> Dict[str, float]:
    if not stats:
        return {"total_games": 0, "win_rate": 0.0, "avg_confidence": 0.0}

    total_games = int(stats.get("total_games", 0) or 0)
    win_rate = float(stats.get("win_rate", 0.0) or 0.0)
    avg_confidence = float(stats.get("avg_confidence", 0.0) or 0.0)

    win_rate = min(max(win_rate, 0.0), 1.0)
    avg_confidence = min(max(avg_confidence, 0.0), 100.0)

    return {
        "total_games": total_games,
        "win_rate": round(win_rate, 4),
        "avg_confidence": round(avg_confidence, 2),
    }


def get_statistics_monitor() -> AdvancedPerformanceMonitor:
    """Expose internal monitor for diagnostics/tests."""
    return _stats_monitor


