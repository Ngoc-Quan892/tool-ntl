"""Helpers for application-level state and statistics."""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import List


@dataclass
class AppState:
    shoe_number: int = 1
    hand_number: int = 0
    history: List[str] = field(default_factory=list)
    prediction_hits: int = 0
    totals: Counter = field(default_factory=Counter)

    def record(self, result: str, prediction_correct: bool) -> None:
        self.history.append(result)
        self.hand_number += 1
        if prediction_correct:
            self.prediction_hits += 1
        if result in ("B", "P", "T"):
            self.totals[result] += 1

    def reset(self) -> None:
        self.shoe_number = 1
        self.hand_number = 0
        self.history.clear()
        self.prediction_hits = 0
        self.totals.clear()


def _current_streak(history: List[str], target: str) -> int:
    streak = 0
    for result in reversed(history):
        if result == target:
            streak += 1
        elif result != "T":
            break
    return streak


def compute_stats(state: AppState) -> dict:
    total_hands = state.hand_number
    banker_wins = state.totals.get("B", 0)
    player_wins = state.totals.get("P", 0)
    ties = state.totals.get("T", 0)

    return {
        "total_hands": total_hands,
        "banker_wins": banker_wins,
        "player_wins": player_wins,
        "ties": ties,
        "banker_streak": _current_streak(state.history, "B"),
        "player_streak": _current_streak(state.history, "P"),
        "current_shoe": state.shoe_number,
        "accuracy": round((state.prediction_hits / total_hands) * 100, 2) if total_hands else 0.0,
    }
