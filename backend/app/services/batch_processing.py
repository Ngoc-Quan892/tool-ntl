"""
Batch processing service with validation, circuit breaker protection, and caching.
"""
from __future__ import annotations

import logging
import threading
import time
from datetime import datetime
from typing import Any, Dict, List, Tuple

from sqlalchemy import text

from app.models.database import db_manager
from app.services.error_recovery import CircuitBreaker, CircuitBreakerConfig

logger = logging.getLogger(__name__)


class _TTLCache:
    """Simple thread-safe TTL cache."""

    def __init__(self, ttl_seconds: int):
        self.ttl = ttl_seconds
        self._data: Dict[str, Tuple[float, Any]] = {}
        self._lock = threading.Lock()

    def get(self, key: str) -> Any:
        with self._lock:
            payload = self._data.get(key)
            if not payload:
                return None
            expires_at, value = payload
            if expires_at < time.time():
                self._data.pop(key, None)
                return None
            return value

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            self._data[key] = (time.time() + self.ttl, value)


_cache = _TTLCache(ttl_seconds=3600)
_circuit_breaker = CircuitBreaker(
    "database_batch_processor",
    CircuitBreakerConfig(failure_threshold=5, recovery_timeout=60),
)


def process_batch(items: List[Dict]) -> Dict:
    """
    Process items in batches of 50 with DB circuit breaker protection and caching.

    Returns:
        Dict summarizing processed results and cache hits.
    """
    _validate_items(items)

    cached_results: List[Dict[str, Any]] = []
    pending: List[Tuple[str, Dict[str, Any]]] = []

    for item in items:
        cache_key = _build_cache_key(item["id"])
        cached = _cache.get(cache_key)
        if cached:
            cached_results.append(cached)
            continue
        pending.append((cache_key, item))

    processed_results: List[Dict[str, Any]] = []
    if pending:
        for chunk_start in range(0, len(pending), 50):
            chunk = pending[chunk_start : chunk_start + 50]
            logger.debug("Processing batch chunk size=%s", len(chunk))

            def _chunk_job() -> List[Dict[str, Any]]:
                with db_manager.get_session() as session:
                    return _process_chunk(session, chunk)

            chunk_results = _circuit_breaker.call(_chunk_job)
            for cache_key, result in chunk_results:
                _cache.set(cache_key, result)
                processed_results.append(result)

    results = processed_results + cached_results
    return {
        "request_count": len(items),
        "processed_count": len(processed_results),
        "cache_hits": len(cached_results),
        "results": results,
    }


def _process_chunk(session, chunk: List[Tuple[str, Dict[str, Any]]]) -> List[Tuple[str, Dict[str, Any]]]:
    """Persist chunk via DB session and return enriched results."""
    responses: List[Tuple[str, Dict[str, Any]]] = []

    for cache_key, item in chunk:
        # Minimal DB touch to ensure connection is healthy; replace with real work later.
        session.execute(text("SELECT 1"))

        result = {
            "id": item["id"],
            "payload": item["payload"],
            "status": "processed",
            "processed_at": datetime.utcnow().isoformat() + "Z",
        }
        responses.append((cache_key, result))

    return responses


def _validate_items(items: List[Dict[str, Any]]) -> None:
    if not items:
        raise ValueError("items must not be empty")

    for idx, item in enumerate(items):
        if not isinstance(item, dict):
            raise ValueError(f"Item at index {idx} must be a dict")
        if "id" not in item:
            raise ValueError(f"Item at index {idx} missing required field 'id'")
        if "payload" not in item:
            raise ValueError(f"Item {item['id']} missing required field 'payload'")


def _build_cache_key(item_id: Any) -> str:
    return f"batch:{item_id}"


