"""
Performance optimization utilities.

Features:
- Database query optimization
- Batch operations
- Async processing helpers
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable, List, Optional, TypeVar

from sqlalchemy.orm import Session
from sqlalchemy import func, select

from app.services.monitoring import track_query

logger = logging.getLogger(__name__)

T = TypeVar("T")


class BatchProcessor:
    """Utility for batch processing operations."""

    @staticmethod
    async def process_batch(
        items: List[Any],
        processor: Callable[[Any], Any],
        batch_size: int = 100,
        max_concurrent: int = 10,
    ) -> List[Any]:
        """
        Process items in batches with concurrency control.

        Args:
            items: List of items to process
            processor: Async function to process each item
            batch_size: Size of each batch
            max_concurrent: Maximum concurrent operations

        Returns:
            List of processed results
        """
        results = []
        semaphore = asyncio.Semaphore(max_concurrent)

        async def process_with_semaphore(item):
            async with semaphore:
                if asyncio.iscoroutinefunction(processor):
                    return await processor(item)
                else:
                    return processor(item)

        # Process in batches
        for i in range(0, len(items), batch_size):
            batch = items[i : i + batch_size]
            batch_results = await asyncio.gather(
                *[process_with_semaphore(item) for item in batch]
            )
            results.extend(batch_results)

        return results


class QueryOptimizer:
    """Database query optimization utilities."""

    @staticmethod
    def optimize_query(
        session: Session,
        query,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        use_index: bool = True,
    ):
        """
        Optimize a SQLAlchemy query.

        Args:
            session: Database session
            query: SQLAlchemy query
            limit: Limit results
            offset: Offset for pagination
            use_index: Whether to use indexes (hint for optimizer)

        Returns:
            Optimized query
        """
        if limit:
            query = query.limit(limit)
        if offset:
            query = query.offset(offset)

        return query

    @staticmethod
    def get_count_optimized(session: Session, model_class, filters: Optional[dict] = None) -> int:
        """
        Get count with optimization (uses COUNT(*) instead of loading all records).

        Args:
            session: Database session
            model_class: SQLAlchemy model class
            filters: Optional filter dictionary

        Returns:
            Count of records
        """
        with track_query("count"):
            query = session.query(func.count(model_class.id))
            
            if filters:
                for key, value in filters.items():
                    if hasattr(model_class, key):
                        query = query.filter(getattr(model_class, key) == value)
            
            return query.scalar() or 0

    @staticmethod
    def bulk_insert(
        session: Session,
        model_class,
        items: List[dict],
        batch_size: int = 1000,
    ) -> int:
        """
        Bulk insert records for better performance.

        Args:
            session: Database session
            model_class: SQLAlchemy model class
            items: List of dictionaries to insert
            batch_size: Batch size for inserts

        Returns:
            Number of records inserted
        """
        with track_query("bulk_insert"):
            inserted = 0
            for i in range(0, len(items), batch_size):
                batch = items[i : i + batch_size]
                session.bulk_insert_mappings(model_class, batch)
                inserted += len(batch)
            
            session.commit()
            return inserted

    @staticmethod
    def bulk_update(
        session: Session,
        model_class,
        items: List[dict],
        update_key: str = "id",
        batch_size: int = 1000,
    ) -> int:
        """
        Bulk update records for better performance.

        Args:
            session: Database session
            model_class: SQLAlchemy model class
            items: List of dictionaries to update
            update_key: Key to match records for update
            batch_size: Batch size for updates

        Returns:
            Number of records updated
        """
        with track_query("bulk_update"):
            updated = 0
            for i in range(0, len(items), batch_size):
                batch = items[i : i + batch_size]
                session.bulk_update_mappings(model_class, batch)
                updated += len(batch)
            
            session.commit()
            return updated


async def run_async(func: Callable, *args, **kwargs) -> Any:
    """
    Run a function asynchronously.

    Args:
        func: Function to run
        *args: Positional arguments
        **kwargs: Keyword arguments

    Returns:
        Function result
    """
    if asyncio.iscoroutinefunction(func):
        return await func(*args, **kwargs)
    else:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: func(*args, **kwargs))

