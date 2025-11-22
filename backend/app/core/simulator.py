"""Mass simulation utilities for Baccarat shoes."""
from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict

from .predictor import Predictor


@dataclass
class SimulationTask:
    task_id: str
    total_shoes: int
    hands_per_shoe: int
    status: str = "running"
    completed_shoes: int = 0
    results: Dict[str, Any] = field(default_factory=dict)
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None


class SimulationManager:
    def __init__(self, app=None) -> None:
        self.app = app
        self.tasks: Dict[str, SimulationTask] = {}

    def start(self, shoes: int, hands: int) -> SimulationTask:
        task_id = f"sim-{uuid.uuid4().hex[:8]}"
        task = SimulationTask(task_id=task_id, total_shoes=shoes, hands_per_shoe=hands)
        self.tasks[task_id] = task
        asyncio.create_task(self._run(task))
        return task

    async def _run(self, task: SimulationTask) -> None:
        predictor = Predictor()
        banker_wins = player_wins = ties = 0
        prediction_hits = 0

        try:
            for shoe in range(task.total_shoes):
                predictor.reset()
                for _ in range(task.hands_per_shoe):
                    result = self._simulate_hand()
                    predictor.add(result)
                    prediction = predictor.predict()
                    if prediction["recommend"] == result:
                        prediction_hits += 1
                    if result == "B":
                        banker_wins += 1
                    elif result == "P":
                        player_wins += 1
                    else:
                        ties += 1
                task.completed_shoes = shoe + 1
                await asyncio.sleep(0)

            task.results = {
                "banker_wins": banker_wins,
                "player_wins": player_wins,
                "ties": ties,
                "accuracy": round(prediction_hits / max(1, task.total_shoes * task.hands_per_shoe) * 100, 2),
            }
            task.status = "completed"
        except Exception as exc:  # pragma: no cover - best effort logging
            task.status = "failed"
            task.results = {"error": str(exc)}
        finally:
            task.completed_at = datetime.utcnow()

    def _simulate_hand(self) -> str:
        from random import choices

        return choices(["B", "P", "T"], weights=[0.4586, 0.4462, 0.0952])[0]

    def get(self, task_id: str) -> SimulationTask | None:
        return self.tasks.get(task_id)
