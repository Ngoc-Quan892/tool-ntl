"""
Cache management API endpoints.

Provides endpoints for cache warming and cache management operations.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Dict, Optional
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel

from app.api.v2.base import get_database_session
from app.services.cache_warmer import CacheWarmer, WARMING_STRATEGIES
from app.services.performance_optimizer import OptimizationStack

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/cache", tags=["cache"])

# In-memory storage for warming task status
_warming_tasks: Dict[str, Dict] = {}


class WarmingTaskResponse(BaseModel):
    """Response model for cache warming task."""
    task_id: str
    status: str
    message: str


class WarmingStatusResponse(BaseModel):
    """Response model for cache warming status."""
    task_id: str
    status: str
    strategy: Optional[str] = None
    progress: Optional[Dict] = None
    result: Optional[Dict] = None
    error: Optional[str] = None


def get_optimizer(request: Request) -> OptimizationStack:
    """
    Get OptimizationStack from app state.
    
    Args:
        request: FastAPI request object
        
    Returns:
        OptimizationStack instance
        
    Raises:
        HTTPException: If optimizer is not available
    """
    optimizer = getattr(request.app.state, "optimizer", None)
    if optimizer is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="OptimizationStack is not available"
        )
    return optimizer


@router.post("/warm", response_model=WarmingTaskResponse)
async def trigger_cache_warming(
    request: Request,
    background_tasks: BackgroundTasks,
    strategy: str = Query("moderate", description="Warming strategy: minimal, moderate, or aggressive"),
    max_concurrent: int = Query(10, ge=1, le=50, description="Maximum concurrent warming tasks"),
) -> WarmingTaskResponse:
    """
    Trigger cache warming in background.
    
    This endpoint starts cache warming asynchronously and returns immediately
    with a task ID. Use GET /cache/warm/{task_id} to check status.
    
    Args:
        request: FastAPI request object
        background_tasks: FastAPI background tasks
        strategy: Warming strategy (minimal, moderate, aggressive)
        max_concurrent: Maximum concurrent warming tasks
        
    Returns:
        Task ID and initial status
    """
    if strategy not in WARMING_STRATEGIES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid strategy: {strategy}. Must be one of {list(WARMING_STRATEGIES.keys())}"
        )
    
    optimizer = get_optimizer(request)
    task_id = str(uuid4())
    
    # Initialize task status
    _warming_tasks[task_id] = {
        "status": "running",
        "strategy": strategy,
        "progress": None,
        "result": None,
        "error": None,
    }
    
    # Start warming in background
    async def warm_cache_task():
        try:
            warmer = CacheWarmer(
                optimizer=optimizer,
                strategy=strategy,
                max_concurrent=max_concurrent,
            )
            
            result = await warmer.warm_cache()
            
            _warming_tasks[task_id]["status"] = "completed"
            _warming_tasks[task_id]["result"] = result
            
        except Exception as exc:
            logger.error(f"Cache warming task {task_id} failed: {exc}", exc_info=True)
            _warming_tasks[task_id]["status"] = "failed"
            _warming_tasks[task_id]["error"] = str(exc)
    
    # Run in background
    asyncio.create_task(warm_cache_task())
    
    return WarmingTaskResponse(
        task_id=task_id,
        status="running",
        message=f"Cache warming started with strategy: {strategy}"
    )


@router.get("/warm/{task_id}", response_model=WarmingStatusResponse)
async def get_warming_status(
    task_id: str,
) -> WarmingStatusResponse:
    """
    Get status of a cache warming task.
    
    Args:
        task_id: Task ID returned from POST /cache/warm
        
    Returns:
        Current status and result (if completed)
        
    Raises:
        HTTPException: If task ID not found
    """
    if task_id not in _warming_tasks:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found"
        )
    
    task_info = _warming_tasks[task_id]
    
    return WarmingStatusResponse(
        task_id=task_id,
        status=task_info["status"],
        strategy=task_info.get("strategy"),
        progress=task_info.get("progress"),
        result=task_info.get("result"),
        error=task_info.get("error"),
    )


@router.get("/warm", response_model=Dict)
async def list_warming_tasks() -> Dict:
    """
    List all cache warming tasks.
    
    Returns:
        Dictionary with task IDs and their statuses
    """
    return {
        "tasks": {
            task_id: {
                "status": info["status"],
                "strategy": info.get("strategy"),
            }
            for task_id, info in _warming_tasks.items()
        },
        "total": len(_warming_tasks),
    }


@router.delete("/warm/{task_id}")
async def delete_warming_task(task_id: str) -> Dict:
    """
    Delete a warming task from history.
    
    Args:
        task_id: Task ID to delete
        
    Returns:
        Success message
    """
    if task_id not in _warming_tasks:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found"
        )
    
    del _warming_tasks[task_id]
    
    return {"message": f"Task {task_id} deleted"}


@router.get("/stats")
async def get_cache_stats(
    request: Request,
) -> Dict:
    """
    Get current cache statistics.
    
    Args:
        request: FastAPI request object
        
    Returns:
        Cache statistics including hit rates and sizes
    """
    optimizer = get_optimizer(request)
    cache_manager = optimizer.get_cache_manager()
    
    stats = cache_manager.get_stats()
    
    return {
        "cache_stats": stats,
        "local_cache_size": stats.get("local_cache_size", 0),
        "local_hit_rate": stats.get("local_hit_rate", 0),
        "redis_hit_rate": stats.get("redis_hit_rate", 0),
    }

