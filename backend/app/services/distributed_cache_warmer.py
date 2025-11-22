"""
Distributed cache warming coordinator.

Coordinates cache warming across multiple application instances with:
- Distributed locking to prevent duplicate work
- Work queue for task distribution
- Leader election for coordination
- Health checking and failure handling
- Progress aggregation
"""

from __future__ import annotations

import asyncio
import json
import logging
import random
import time
import uuid
from typing import Any, Dict, List, Optional, Set
from uuid import uuid4

try:
    from redis.asyncio import Redis
    HAS_REDIS_ASYNC = True
except ImportError:
    HAS_REDIS_ASYNC = False
    Redis = None

from app.services.cache_warmer import CacheWarmer
from app.services.performance_optimizer import OptimizationStack

logger = logging.getLogger(__name__)


# ============================================================================
# Distributed Lock
# ============================================================================

class DistributedLock:
    """Distributed locking mechanism using Redis."""
    
    def __init__(
        self,
        redis_client: Any,
        lock_name: str,
        timeout: int = 300,
        retry_interval: float = 0.1,
    ):
        """
        Initialize distributed lock.
        
        Args:
            redis_client: Redis client (async)
            lock_name: Lock identifier
            timeout: Lock expiration time in seconds (default: 5 minutes)
            retry_interval: Retry interval when acquiring lock
        """
        self.redis = redis_client
        self.lock_name = f"lock:{lock_name}"
        self.timeout = timeout
        self.retry_interval = retry_interval
        self.lock_value: Optional[str] = None
        self.instance_id = str(uuid4())
    
    async def acquire(self, blocking: bool = True, timeout: Optional[float] = None) -> bool:
        """
        Try to acquire lock.
        
        Args:
            blocking: If True, wait until lock is acquired
            timeout: Maximum time to wait (None = wait forever)
            
        Returns:
            True if lock acquired, False otherwise
        """
        start_time = time.time()
        
        while True:
            # Try to acquire lock using SETNX
            lock_value = f"{self.instance_id}:{time.time()}"
            acquired = await self.redis.set(
                self.lock_name,
                lock_value,
                nx=True,  # Only set if not exists
                ex=self.timeout,  # Expire after timeout
            )
            
            if acquired:
                self.lock_value = lock_value
                logger.debug(f"Lock acquired: {self.lock_name}")
                return True
            
            if not blocking:
                return False
            
            if timeout and (time.time() - start_time) >= timeout:
                return False
            
            await asyncio.sleep(self.retry_interval)
    
    async def release(self) -> bool:
        """
        Release lock.
        
        Returns:
            True if released, False otherwise
        """
        if not self.lock_value:
            return False
        
        # Use Lua script for atomic check-and-delete
        lua_script = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("del", KEYS[1])
        else
            return 0
        end
        """
        
        try:
            result = await self.redis.eval(
                lua_script,
                1,
                self.lock_name,
                self.lock_value,
            )
            if result:
                self.lock_value = None
                logger.debug(f"Lock released: {self.lock_name}")
                return True
            return False
        except Exception as exc:
            logger.error(f"Failed to release lock: {exc}")
            return False
    
    async def extend(self, additional_time: int = 60) -> bool:
        """
        Extend lock timeout.
        
        Args:
            additional_time: Additional seconds to extend
            
        Returns:
            True if extended, False otherwise
        """
        if not self.lock_value:
            return False
        
        # Use Lua script for atomic extend
        lua_script = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("expire", KEYS[1], ARGV[2])
        else
            return 0
        end
        """
        
        try:
            result = await self.redis.eval(
                lua_script,
                1,
                self.lock_name,
                self.lock_value,
                str(self.timeout + additional_time),
            )
            return bool(result)
        except Exception as exc:
            logger.error(f"Failed to extend lock: {exc}")
            return False
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.acquire()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.release()


# ============================================================================
# Work Queue
# ============================================================================

class WorkQueue:
    """Distributed work queue for warming tasks."""
    
    def __init__(
        self,
        redis_client: Any,
        queue_name: str = "cache_warming_queue",
    ):
        """
        Initialize work queue.
        
        Args:
            redis_client: Redis client (async)
            queue_name: Queue identifier
        """
        self.redis = redis_client
        self.queue_name = queue_name
        self.pending_key = f"{queue_name}:pending"
        self.processing_key = f"{queue_name}:processing"
        self.completed_key = f"{queue_name}:completed"
        self.failed_key = f"{queue_name}:failed"
        self.stats_key = f"{queue_name}:stats"
    
    async def enqueue(self, task: Dict[str, Any]) -> bool:
        """
        Add task to queue.
        
        Args:
            task: Task dictionary with at least "id" key
            
        Returns:
            True if enqueued, False otherwise
        """
        try:
            task_json = json.dumps(task)
            await self.redis.lpush(self.pending_key, task_json)
            logger.debug(f"Task enqueued: {task.get('id')}")
            return True
        except Exception as exc:
            logger.error(f"Failed to enqueue task: {exc}")
            return False
    
    async def dequeue(self, worker_id: str, timeout: int = 30) -> Optional[Dict[str, Any]]:
        """
        Get next task from queue.
        
        Args:
            worker_id: Worker instance identifier
            timeout: Blocking timeout in seconds
            
        Returns:
            Task dictionary or None if timeout
        """
        try:
            # Blocking pop from queue
            result = await self.redis.brpop(self.pending_key, timeout=timeout)
            
            if not result:
                return None
            
            _, task_json = result
            task = json.loads(task_json)
            
            # Move to processing
            task_id = task.get("id")
            processing_data = {
                "worker_id": worker_id,
                "start_time": str(time.time()),
                "task": task_json,
            }
            await self.redis.hset(self.processing_key, task_id, json.dumps(processing_data))
            await self.redis.expire(self.processing_key, 600)  # 10 minute timeout
            
            logger.debug(f"Task dequeued: {task_id} by worker {worker_id}")
            return task
            
        except Exception as exc:
            logger.error(f"Failed to dequeue task: {exc}")
            return None
    
    async def mark_completed(self, task_id: str) -> bool:
        """
        Mark task as completed.
        
        Args:
            task_id: Task identifier
            
        Returns:
            True if marked, False otherwise
        """
        try:
            # Remove from processing
            await self.redis.hdel(self.processing_key, task_id)
            
            # Add to completed set
            await self.redis.sadd(self.completed_key, task_id)
            
            # Update stats
            await self.redis.hincrby(self.stats_key, "completed", 1)
            
            logger.debug(f"Task completed: {task_id}")
            return True
        except Exception as exc:
            logger.error(f"Failed to mark task completed: {exc}")
            return False
    
    async def mark_failed(self, task_id: str, error: str) -> bool:
        """
        Mark task as failed.
        
        Args:
            task_id: Task identifier
            error: Error message
            
        Returns:
            True if marked, False otherwise
        """
        try:
            # Remove from processing
            await self.redis.hdel(self.processing_key, task_id)
            
            # Add to failed hash
            await self.redis.hset(self.failed_key, task_id, error)
            
            # Update stats
            await self.redis.hincrby(self.stats_key, "failed", 1)
            
            logger.warning(f"Task failed: {task_id} - {error}")
            return True
        except Exception as exc:
            logger.error(f"Failed to mark task failed: {exc}")
            return False
    
    async def requeue_stale_tasks(self, stale_timeout: int = 300) -> int:
        """
        Requeue tasks stuck in processing state.
        
        Args:
            stale_timeout: Time in seconds to consider task stale
            
        Returns:
            Number of tasks requeued
        """
        try:
            all_processing = await self.redis.hgetall(self.processing_key)
            requeued = 0
            current_time = time.time()
            
            for task_id, processing_data_json in all_processing.items():
                try:
                    processing_data = json.loads(processing_data_json)
                    start_time = float(processing_data.get("start_time", 0))
                    
                    if current_time - start_time > stale_timeout:
                        # Requeue task
                        task = json.loads(processing_data.get("task", "{}"))
                        await self.enqueue(task)
                        await self.redis.hdel(self.processing_key, task_id)
                        requeued += 1
                        logger.warning(f"Requeued stale task: {task_id}")
                except Exception as exc:
                    logger.error(f"Error processing stale task {task_id}: {exc}")
            
            return requeued
        except Exception as exc:
            logger.error(f"Failed to requeue stale tasks: {exc}")
            return 0
    
    async def get_queue_stats(self) -> Dict[str, int]:
        """
        Get queue statistics.
        
        Returns:
            Dictionary with queue statistics
        """
        try:
            pending = await self.redis.llen(self.pending_key)
            processing = await self.redis.hlen(self.processing_key)
            completed = await self.redis.scard(self.completed_key)
            failed = await self.redis.hlen(self.failed_key)
            
            return {
                "pending": pending,
                "processing": processing,
                "completed": completed,
                "failed": failed,
            }
        except Exception as exc:
            logger.error(f"Failed to get queue stats: {exc}")
            return {
                "pending": 0,
                "processing": 0,
                "completed": 0,
                "failed": 0,
            }


# ============================================================================
# Distributed Cache Warmer
# ============================================================================

class DistributedCacheWarmer:
    """
    Coordinate cache warming across multiple application instances.
    
    Features:
    - Distributed locking to prevent duplicate work
    - Work queue for task distribution
    - Leader election for coordination
    - Health checking and failure handling
    - Progress aggregation
    """
    
    def __init__(
        self,
        redis_url: str,
        cache_warmer: CacheWarmer,
        instance_id: Optional[str] = None,
        coordinator_mode: bool = False,
        heartbeat_interval: int = 30,
        coordinator_interval: int = 10,
    ):
        """
        Initialize distributed cache warmer.
        
        Args:
            redis_url: Redis connection URL
            cache_warmer: Local CacheWarmer instance
            instance_id: Unique instance identifier (auto-generated if None)
            coordinator_mode: Whether this instance should try to be coordinator
            heartbeat_interval: Heartbeat interval in seconds
            coordinator_interval: Coordinator loop interval in seconds
        """
        if not HAS_REDIS_ASYNC:
            raise ImportError("redis[asyncio] is required for distributed cache warming")
        
        self.redis_url = redis_url
        self.cache_warmer = cache_warmer
        self.instance_id = instance_id or str(uuid4())
        self.coordinator_mode = coordinator_mode
        self.heartbeat_interval = heartbeat_interval
        self.coordinator_interval = coordinator_interval
        
        self.redis: Optional[Redis] = None
        self.work_queue: Optional[WorkQueue] = None
        self.coordinator_lock: Optional[DistributedLock] = None
        
        self.is_running = False
        self.start_time = time.time()
        self.tasks_processed = 0
        self.logger = logging.getLogger(__name__)
        
        self._coordinator_task: Optional[asyncio.Task] = None
        self._worker_task: Optional[asyncio.Task] = None
        self._heartbeat_task: Optional[asyncio.Task] = None
    
    async def start(self) -> None:
        """Start distributed cache warming system."""
        try:
            # Connect to Redis
            self.redis = await Redis.from_url(
                self.redis_url,
                decode_responses=True,
            )
            
            # Initialize work queue
            self.work_queue = WorkQueue(self.redis)
            
            # Register this instance
            await self._register_instance()
            
            # Try to become coordinator if in coordinator mode
            if self.coordinator_mode:
                self.coordinator_lock = DistributedLock(
                    self.redis,
                    "cache_warmer:coordinator",
                    timeout=60,
                )
                
                acquired = await self.coordinator_lock.acquire(blocking=False)
                if acquired:
                    self.logger.info(f"Instance {self.instance_id} elected as coordinator")
                    self._coordinator_task = asyncio.create_task(self._coordinator_loop())
                else:
                    self.logger.info(f"Instance {self.instance_id} running as worker (coordinator exists)")
                    self.coordinator_mode = False
            
            # Start worker loop
            self._worker_task = asyncio.create_task(self._worker_loop())
            
            # Start heartbeat
            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
            
            self.is_running = True
            self.logger.info(f"Distributed cache warmer started: instance={self.instance_id}")
            
        except Exception as exc:
            self.logger.error(f"Failed to start distributed cache warmer: {exc}", exc_info=True)
            raise
    
    async def stop(self) -> None:
        """Stop distributed cache warming system."""
        self.logger.info("Stopping distributed cache warmer...")
        self.is_running = False
        
        # Cancel tasks
        if self._coordinator_task:
            self._coordinator_task.cancel()
        if self._worker_task:
            self._worker_task.cancel()
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
        
        # Release coordinator lock
        if self.coordinator_lock:
            await self.coordinator_lock.release()
        
        # Unregister instance
        if self.redis:
            await self.redis.delete(f"cache_warmer:instances:{self.instance_id}")
            await self.redis.close()
        
        self.logger.info("Distributed cache warmer stopped")
    
    async def _register_instance(self) -> None:
        """Register this instance in Redis."""
        key = f"cache_warmer:instances:{self.instance_id}"
        data = {
            "instance_id": self.instance_id,
            "last_heartbeat": str(time.time()),
            "status": "active",
            "tasks_processed": "0",
            "uptime": "0",
        }
        await self.redis.hset(key, mapping=data)
        await self.redis.expire(key, self.heartbeat_interval * 3)
    
    async def _coordinator_loop(self) -> None:
        """Main coordinator loop - distributes work and monitors progress."""
        self.logger.info("Coordinator loop started")
        
        try:
            while self.is_running:
                # Check if still holding coordinator lock
                if self.coordinator_lock:
                    if not await self.coordinator_lock.extend():
                        self.logger.warning("Lost coordinator lock, switching to worker mode")
                        self.coordinator_mode = False
                        break
                
                # Get healthy workers
                workers = await self._get_healthy_workers()
                self.logger.debug(f"Healthy workers: {len(workers)}")
                
                # Check if warming is needed
                queue_stats = await self.work_queue.get_queue_stats()
                
                # Generate and distribute tasks if queue is empty
                if queue_stats["pending"] == 0:
                    tasks = await self._generate_warming_tasks()
                    if tasks:
                        for task in tasks:
                            await self.work_queue.enqueue(task)
                        self.logger.info(f"Distributed {len(tasks)} warming tasks")
                
                # Monitor progress
                progress = await self._aggregate_progress()
                if progress["total_tasks"] > 0:
                    self.logger.info(
                        f"Progress: {progress['completed']}/{progress['total_tasks']} "
                        f"({progress['completed']/progress['total_tasks']*100:.1f}%)"
                    )
                
                # Requeue stale tasks
                requeued = await self.work_queue.requeue_stale_tasks()
                if requeued > 0:
                    self.logger.warning(f"Requeued {requeued} stale tasks")
                
                await asyncio.sleep(self.coordinator_interval)
                
        except asyncio.CancelledError:
            self.logger.info("Coordinator loop cancelled")
        except Exception as exc:
            self.logger.error(f"Coordinator loop error: {exc}", exc_info=True)
        finally:
            if self.coordinator_lock:
                await self.coordinator_lock.release()
    
    async def _worker_loop(self) -> None:
        """Main worker loop - processes warming tasks."""
        self.logger.info("Worker loop started")
        
        try:
            while self.is_running:
                # Try to dequeue task
                task = await self.work_queue.dequeue(self.instance_id, timeout=30)
                
                if task is None:
                    continue  # Timeout, no work available
                
                # Process task
                try:
                    result = await self._process_warming_task(task)
                    
                    if result:
                        await self.work_queue.mark_completed(task["id"])
                        self.tasks_processed += 1
                    else:
                        await self.work_queue.mark_failed(task["id"], "Processing failed")
                except Exception as exc:
                    self.logger.error(f"Task {task.get('id')} failed: {exc}", exc_info=True)
                    await self.work_queue.mark_failed(task["id"], str(exc))
                
                # Update worker metrics
                await self._update_worker_metrics(task, result)
                
        except asyncio.CancelledError:
            self.logger.info("Worker loop cancelled")
        except Exception as exc:
            self.logger.error(f"Worker loop error: {exc}", exc_info=True)
    
    async def _process_warming_task(self, task: Dict[str, Any]) -> bool:
        """
        Process a single warming task.
        
        Args:
            task: Task dictionary
            
        Returns:
            True if successful, False otherwise
        """
        task_type = task.get("type")
        
        try:
            if task_type == "warm_game":
                game_id = task.get("game_id")
                limit = task.get("limit", 100)
                return await self.cache_warmer._warm_game_results(game_id, limit=limit)
            
            elif task_type == "warm_pattern":
                pattern = task.get("pattern")
                days = task.get("days", 7)
                return await self.cache_warmer._warm_pattern_statistics(pattern, days)
            
            elif task_type == "warm_aggregation":
                days = task.get("days", 30)
                # This would need to be implemented in cache_warmer
                # For now, return False
                return False
            
            else:
                self.logger.warning(f"Unknown task type: {task_type}")
                return False
                
        except Exception as exc:
            self.logger.error(f"Error processing task {task.get('id')}: {exc}")
            return False
    
    async def _heartbeat_loop(self) -> None:
        """Send periodic heartbeat to Redis."""
        try:
            while self.is_running:
                await self._send_heartbeat()
                await asyncio.sleep(self.heartbeat_interval)
        except asyncio.CancelledError:
            pass
        except Exception as exc:
            self.logger.error(f"Heartbeat loop error: {exc}")
    
    async def _send_heartbeat(self) -> None:
        """Send heartbeat to Redis."""
        try:
            key = f"cache_warmer:instances:{self.instance_id}"
            uptime = time.time() - self.start_time
            data = {
                "instance_id": self.instance_id,
                "last_heartbeat": str(time.time()),
                "status": "active",
                "tasks_processed": str(self.tasks_processed),
                "uptime": str(uptime),
            }
            await self.redis.hset(key, mapping=data)
            await self.redis.expire(key, self.heartbeat_interval * 3)
        except Exception as exc:
            self.logger.error(f"Failed to send heartbeat: {exc}")
    
    async def _get_healthy_workers(self) -> List[str]:
        """
        Get list of healthy worker instances.
        
        Returns:
            List of healthy instance IDs
        """
        try:
            pattern = "cache_warmer:instances:*"
            keys = await self.redis.keys(pattern)
            
            healthy_workers = []
            current_time = time.time()
            
            for key in keys:
                try:
                    info = await self.redis.hgetall(key)
                    last_heartbeat = float(info.get("last_heartbeat", 0))
                    
                    # Consider healthy if heartbeat within 90 seconds
                    if current_time - last_heartbeat < 90:
                        healthy_workers.append(info.get("instance_id"))
                except Exception as exc:
                    self.logger.warning(f"Error checking worker health: {exc}")
            
            return healthy_workers
        except Exception as exc:
            self.logger.error(f"Failed to get healthy workers: {exc}")
            return []
    
    async def _generate_warming_tasks(self) -> List[Dict[str, Any]]:
        """
        Generate warming tasks based on strategy.
        
        Returns:
            List of task dictionaries
        """
        tasks = []
        strategy = self.cache_warmer.strategy
        
        try:
            from app.models.database import db_manager
            from sqlalchemy import text
            
            with db_manager.get_session() as session:
                # P0: Active games
                query = text("""
                    SELECT DISTINCT shoe_number
                    FROM game_results
                    WHERE timestamp >= CURRENT_TIMESTAMP - INTERVAL '1 hour'
                    GROUP BY shoe_number
                    ORDER BY MAX(timestamp) DESC
                    LIMIT 5
                """)
                result = session.execute(query)
                active_games = [row[0] for row in result.fetchall()]
                
                if not active_games:
                    # Fallback
                    fallback_query = text("""
                        SELECT DISTINCT shoe_number
                        FROM game_results
                        GROUP BY shoe_number
                        ORDER BY MAX(timestamp) DESC
                        LIMIT 5
                    """)
                    result = session.execute(fallback_query)
                    active_games = [row[0] for row in result.fetchall()]
                
                for game_id in active_games:
                    tasks.append({
                        "id": str(uuid4()),
                        "type": "warm_game",
                        "priority": 0,
                        "game_id": game_id,
                        "limit": 100,
                    })
                
                # P1: Popular games (if not minimal)
                if strategy != "minimal":
                    limit = 50 if strategy == "moderate" else 200
                    query = text("""
                        SELECT shoe_number, COUNT(*) as access_count
                        FROM game_results
                        WHERE timestamp >= CURRENT_TIMESTAMP - INTERVAL '7 days'
                        GROUP BY shoe_number
                        ORDER BY access_count DESC
                        LIMIT :limit
                    """)
                    result = session.execute(query, {"limit": limit})
                    popular_games = [row[0] for row in result.fetchall()]
                    
                    for game_id in popular_games:
                        tasks.append({
                            "id": str(uuid4()),
                            "type": "warm_game",
                            "priority": 1,
                            "game_id": game_id,
                            "limit": 100,
                        })
                
                # P2: Pattern statistics
                patterns = ["B", "P", "T", "all"]
                time_ranges = [7, 30] if strategy == "moderate" else [7, 14, 30, 90]
                
                for pattern in patterns[:min(10, len(patterns))]:
                    for days in time_ranges:
                        tasks.append({
                            "id": str(uuid4()),
                            "type": "warm_pattern",
                            "priority": 2,
                            "pattern": pattern,
                            "days": days,
                        })
            
            # Shuffle tasks for fair distribution
            random.shuffle(tasks)
            
            return tasks
            
        except Exception as exc:
            self.logger.error(f"Failed to generate warming tasks: {exc}", exc_info=True)
            return []
    
    async def _aggregate_progress(self) -> Dict[str, Any]:
        """
        Aggregate progress from all worker instances.
        
        Returns:
            Dictionary with aggregated statistics
        """
        try:
            # Get queue stats
            queue_stats = await self.work_queue.get_queue_stats()
            
            # Get worker stats
            workers = await self._get_healthy_workers()
            worker_stats = {}
            
            for worker_id in workers:
                key = f"cache_warmer:instances:{worker_id}"
                info = await self.redis.hgetall(key)
                worker_stats[worker_id] = {
                    "instance_id": worker_id,
                    "status": info.get("status", "unknown"),
                    "tasks_processed": int(info.get("tasks_processed", 0)),
                    "uptime": float(info.get("uptime", 0)),
                    "last_heartbeat": info.get("last_heartbeat"),
                }
            
            total_tasks = (
                queue_stats["pending"] +
                queue_stats["processing"] +
                queue_stats["completed"] +
                queue_stats["failed"]
            )
            
            return {
                "total_tasks": total_tasks,
                "completed": queue_stats["completed"],
                "failed": queue_stats["failed"],
                "pending": queue_stats["pending"],
                "processing": queue_stats["processing"],
                "active_workers": len(workers),
                "worker_stats": worker_stats,
            }
        except Exception as exc:
            self.logger.error(f"Failed to aggregate progress: {exc}")
            return {
                "total_tasks": 0,
                "completed": 0,
                "failed": 0,
                "pending": 0,
                "processing": 0,
                "active_workers": 0,
                "worker_stats": {},
            }
    
    async def _update_worker_metrics(self, task: Dict[str, Any], result: bool) -> None:
        """
        Update worker metrics after processing task.
        
        Args:
            task: Task that was processed
            result: Success/failure result
        """
        try:
            key = f"cache_warmer:worker_stats:{self.instance_id}"
            await self.redis.hincrby(key, "tasks_processed", 1)
            if result:
                await self.redis.hincrby(key, "tasks_succeeded", 1)
            else:
                await self.redis.hincrby(key, "tasks_failed", 1)
            await self.redis.expire(key, 3600)  # 1 hour TTL
        except Exception as exc:
            self.logger.warning(f"Failed to update worker metrics: {exc}")
    
    async def get_status(self) -> Dict[str, Any]:
        """
        Get current status of distributed warming system.
        
        Returns:
            Dictionary with system status
        """
        try:
            # Get coordinator
            coordinator_lock = DistributedLock(self.redis, "cache_warmer:coordinator")
            coordinator_id = None
            if await coordinator_lock.acquire(blocking=False):
                coordinator_id = self.instance_id
                await coordinator_lock.release()
            else:
                # Try to get coordinator info from lock value
                lock_value = await self.redis.get("lock:cache_warmer:coordinator")
                if lock_value:
                    coordinator_id = lock_value.split(":")[0] if ":" in lock_value else "unknown"
            
            # Get queue stats
            queue_stats = await self.work_queue.get_queue_stats()
            
            # Get workers
            workers = await self._get_healthy_workers()
            worker_details = []
            
            for worker_id in workers:
                key = f"cache_warmer:instances:{worker_id}"
                info = await self.redis.hgetall(key)
                worker_details.append({
                    "instance_id": worker_id,
                    "status": info.get("status", "unknown"),
                    "tasks_processed": int(info.get("tasks_processed", 0)),
                    "uptime": float(info.get("uptime", 0)),
                    "last_heartbeat": info.get("last_heartbeat"),
                })
            
            return {
                "coordinator": coordinator_id,
                "active_workers": len(workers),
                "queue": queue_stats,
                "workers": worker_details,
                "this_instance": {
                    "instance_id": self.instance_id,
                    "is_coordinator": self.coordinator_mode,
                    "tasks_processed": self.tasks_processed,
                    "uptime": time.time() - self.start_time,
                },
            }
        except Exception as exc:
            self.logger.error(f"Failed to get status: {exc}")
            return {
                "error": str(exc),
            }

