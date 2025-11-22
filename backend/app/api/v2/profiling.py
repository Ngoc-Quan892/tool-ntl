"""
Performance profiling API endpoints.

Provides endpoints for on-demand profiling and profile analysis.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Dict, Optional
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, Request, status

from app.services.performance_profiler import PerformanceProfiler

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/profiling", tags=["profiling"])

# In-memory storage for active profiling sessions
_profiling_sessions: Dict[str, Dict] = {}


@router.post("/start")
async def start_profiling(
    request: Request,
    mode: str = Query("cpu", description="Profiling mode: cpu/memory/database/cache/full"),
    duration: int = Query(60, ge=1, le=3600, description="Duration in seconds"),
) -> Dict:
    """
    Start profiling for specified duration.
    
    Returns:
        Session ID for tracking profiling session
    """
    if mode not in ["cpu", "memory", "database", "cache", "full"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid mode: {mode}. Must be one of: cpu, memory, database, cache, full"
        )
    
    session_id = str(uuid4())
    
    # Create profiler
    profiler = PerformanceProfiler(mode=mode, output_dir="profiles")
    profiler.start()
    
    # Store session
    _profiling_sessions[session_id] = {
        "profiler": profiler,
        "start_time": time.time(),
        "duration": duration,
        "mode": mode,
        "status": "running",
    }
    
    # Schedule stop
    async def stop_profiling():
        await asyncio.sleep(duration)
        if session_id in _profiling_sessions:
            _profiling_sessions[session_id]["profiler"].stop()
            _profiling_sessions[session_id]["status"] = "completed"
    
    asyncio.create_task(stop_profiling())
    
    return {
        "session_id": session_id,
        "status": "started",
        "mode": mode,
        "duration": duration,
    }


@router.post("/stop/{session_id}")
async def stop_profiling(session_id: str) -> Dict:
    """
    Stop profiling session early.
    
    Args:
        session_id: Profiling session ID
        
    Returns:
        Status message
    """
    if session_id not in _profiling_sessions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found"
        )
    
    session = _profiling_sessions[session_id]
    if session["status"] != "running":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Session {session_id} is not running"
        )
    
    session["profiler"].stop()
    session["status"] = "completed"
    
    return {
        "session_id": session_id,
        "status": "stopped",
    }


@router.get("/{session_id}")
async def get_profile(session_id: str) -> Dict:
    """
    Get profiling results.
    
    Args:
        session_id: Profiling session ID
        
    Returns:
        Profiling report
    """
    if session_id not in _profiling_sessions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found"
        )
    
    session = _profiling_sessions[session_id]
    
    if session["status"] == "running":
        return {
            "session_id": session_id,
            "status": "running",
            "elapsed_seconds": time.time() - session["start_time"],
        }
    
    # Generate report
    report = session["profiler"].generate_report()
    report["session_id"] = session_id
    
    return report


@router.get("/")
async def list_profiling_sessions() -> Dict:
    """
    List all profiling sessions.
    
    Returns:
        Dictionary with session IDs and their statuses
    """
    sessions = {}
    for session_id, session in _profiling_sessions.items():
        sessions[session_id] = {
            "mode": session["mode"],
            "status": session["status"],
            "start_time": session["start_time"],
        }
    
    return {
        "sessions": sessions,
        "total": len(sessions),
    }


@router.delete("/{session_id}")
async def delete_profiling_session(session_id: str) -> Dict:
    """
    Delete profiling session.
    
    Args:
        session_id: Session ID to delete
        
    Returns:
        Success message
    """
    if session_id not in _profiling_sessions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found"
        )
    
    del _profiling_sessions[session_id]
    
    return {
        "message": f"Session {session_id} deleted",
    }

