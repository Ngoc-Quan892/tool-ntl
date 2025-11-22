"""HTTP API routes for Baccarat Predictor backend."""
from __future__ import annotations

import csv
import io
from datetime import datetime
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..api.websocket import manager as ws_manager
from ..core.roadmap import generate_roadmaps
from ..models.database import GameResult, SimulationRun, db_manager, get_db
from ..models.schemas import (
    AddResultRequest,
    AddResultResponse,
    HistoryEntry,
    HistoryResponse,
    PredictionResponse,
    ResetResponse,
    RoadmapResponse,
    SimulationRequest,
    SimulationStatus,
    StatsResponse,
)
from ..utils.helpers import compute_stats
from ..utils.logger import get_logger

router = APIRouter()
logger = get_logger(__name__)


def _with_timestamp(payload: Dict[str, Any]) -> Dict[str, Any]:
    enriched = dict(payload)
    enriched["timestamp"] = datetime.utcnow().isoformat()
    return enriched


@router.post("/add", response_model=AddResultResponse)
async def add_result(
    request: Request,
    payload: AddResultRequest,
    db: Session = Depends(get_db),
) -> AddResultResponse:
    predictor = request.app.state.predictor
    app_state = request.app.state.app_state

    previous_prediction = predictor.predict()
    predictor.add(payload.result)
    app_state.record(payload.result, previous_prediction["recommend"] == payload.result)

    latest_prediction = _with_timestamp(predictor.predict())

    db_obj = GameResult(
        result=payload.result,
        prediction=latest_prediction,
        shoe_number=app_state.shoe_number,
        hand_number=app_state.hand_number,
        true_count=latest_prediction["true_count"],
        edge=latest_prediction["edge_pct"],
    )
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)

    await ws_manager.broadcast({"type": "prediction", "data": latest_prediction})

    return AddResultResponse(success=True, total_hands=app_state.hand_number, prediction=PredictionResponse(**latest_prediction))


@router.get("/predict", response_model=PredictionResponse)
async def get_prediction(request: Request) -> PredictionResponse:
    predictor = request.app.state.predictor
    prediction = _with_timestamp(predictor.predict())
    return PredictionResponse(**prediction)


@router.get("/history", response_model=HistoryResponse)
async def get_history(
    db: Session = Depends(get_db),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> HistoryResponse:
    total = db.query(func.count(GameResult.id)).scalar() or 0
    rows = (
        db.query(GameResult)
        .order_by(GameResult.timestamp.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    items = [
        HistoryEntry(
            id=row.id,
            result=row.result,
            prediction=row.prediction,
            shoe_number=row.shoe_number,
            hand_number=row.hand_number,
            timestamp=row.timestamp,
        )
        for row in rows
    ]

    return HistoryResponse(total=total, items=items)


@router.get("/roadmap", response_model=RoadmapResponse)
async def roadmap(request: Request) -> RoadmapResponse:
    app_state = request.app.state.app_state
    key = "".join(app_state.history)
    roads = generate_roadmaps(key)
    return RoadmapResponse(**roads)


@router.get("/stats", response_model=StatsResponse)
async def stats(request: Request) -> StatsResponse:
    app_state = request.app.state.app_state
    return StatsResponse(**compute_stats(app_state))


@router.post("/simulate", response_model=SimulationStatus)
async def start_simulation(request: Request, payload: SimulationRequest) -> SimulationStatus:
    manager = request.app.state.simulation_manager
    task = manager.start(payload.shoes, payload.hands_per_shoe)

    sim_row = SimulationRun(
        task_id=task.task_id,
        total_shoes=task.total_shoes,
        completed_shoes=task.completed_shoes,
        status=task.status,
    )
    with db_manager.get_session() as session:
        session.add(sim_row)
        session.commit()

    return SimulationStatus(
        task_id=task.task_id,
        status=task.status,
        total_shoes=task.total_shoes,
        completed_shoes=task.completed_shoes,
        results=task.results,
    )


@router.get("/simulate/{task_id}", response_model=SimulationStatus)
async def get_simulation_status(request: Request, task_id: str) -> SimulationStatus:
    manager = request.app.state.simulation_manager
    task = manager.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Simulation task not found")
    return SimulationStatus(
        task_id=task.task_id,
        status=task.status,
        total_shoes=task.total_shoes,
        completed_shoes=task.completed_shoes,
        results=task.results,
    )


@router.post("/reset", response_model=ResetResponse)
async def reset(request: Request, db: Session = Depends(get_db)) -> ResetResponse:
    predictor = request.app.state.predictor
    app_state = request.app.state.app_state
    predictor.reset()
    app_state.reset()
    db.query(GameResult).delete()
    db.commit()
    await ws_manager.broadcast({"type": "reset"})
    return ResetResponse(success=True)


@router.get("/export")
async def export_data(format: str = Query("json", pattern="^(csv|json)$"), db: Session = Depends(get_db)):
    rows = db.query(GameResult).order_by(GameResult.timestamp.asc()).all()
    if format == "json":
        payload = [
            {
                "id": row.id,
                "result": row.result,
                "prediction": row.prediction,
                "shoe_number": row.shoe_number,
                "hand_number": row.hand_number,
                "timestamp": row.timestamp,
            }
            for row in rows
        ]
        return JSONResponse(payload)

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["id", "result", "shoe_number", "hand_number", "timestamp", "true_count", "edge", "prediction"])
    for row in rows:
        writer.writerow([
            row.id,
            row.result,
            row.shoe_number,
            row.hand_number,
            row.timestamp.isoformat(),
            row.true_count,
            row.edge,
            row.prediction,
        ])
    buffer.seek(0)
    headers = {"Content-Disposition": "attachment; filename=history.csv"}
    return StreamingResponse(iter([buffer.getvalue()]), media_type="text/csv", headers=headers)
