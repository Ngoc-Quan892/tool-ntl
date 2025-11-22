"""Casino-accurate roadmap (road) generators for Baccarat."""
from __future__ import annotations

from functools import lru_cache
from typing import List, Optional

MAX_ROWS = 6


class RoadCell(dict):
    """Cell wrapper with helpers."""

    value: str
    ties: int


def _place(column: List[Optional[RoadCell]], row: int, cell: RoadCell) -> None:
    while len(column) <= row:
        column.append(None)
    column[row] = cell


def build_big_road(history: List[str]) -> List[List[Optional[RoadCell]]]:
    columns: List[List[Optional[RoadCell]]] = []
    if not history:
        return columns

    col_idx = -1
    row_idx = 0
    last_value: Optional[str] = None

    for result in history:
        if result == "T":
            if col_idx >= 0 and row_idx < len(columns[col_idx]) and columns[col_idx][row_idx]:
                columns[col_idx][row_idx]["ties"] = columns[col_idx][row_idx].get("ties", 0) + 1
            continue

        if last_value is None or result != last_value:
            col_idx += 1
            row_idx = 0
            columns.append([])
        else:
            proposed_row = row_idx + 1
            if proposed_row >= MAX_ROWS:
                col_idx += 1
                row_idx = 0
                columns.append([])
            else:
                next_cell_exists = proposed_row < len(columns[col_idx]) and columns[col_idx][proposed_row]
                if next_cell_exists:
                    col_idx += 1
                    row_idx = 0
                    columns.append([])
                else:
                    row_idx = proposed_row

        cell: RoadCell = {"value": result, "ties": 0}
        _place(columns[col_idx], row_idx, cell)
        last_value = result

    return columns


def _column_depth(columns: List[List[Optional[RoadCell]]], idx: int) -> int:
    if idx < 0 or idx >= len(columns):
        return 0
    return sum(1 for cell in columns[idx] if cell)


def _derived_color(big_road: List[List[Optional[RoadCell]]], col: int, row: int, gap: int) -> Optional[str]:
    ref_col = col - gap
    if ref_col < 0:
        return None

    if row == 0:
        left = ref_col - 1
        depth_ref = _column_depth(big_road, ref_col)
        depth_left = _column_depth(big_road, left)
        return "B" if depth_ref == depth_left else "R"

    if row >= len(big_road[ref_col]) or not big_road[ref_col][row]:
        return "R"
    return "B"


def _build_derived(big_road: List[List[Optional[RoadCell]]], gap: int) -> List[List[Optional[RoadCell]]]:
    derived: List[List[Optional[RoadCell]]] = []
    col_idx = -1
    row_idx = 0
    last_value: Optional[str] = None

    for c_idx, column in enumerate(big_road):
        for r_idx, cell in enumerate(column):
            if not cell:
                continue
            color = _derived_color(big_road, c_idx, r_idx, gap)
            if color is None:
                continue

            if last_value is None or color != last_value:
                col_idx += 1
                row_idx = 0
                derived.append([])
            else:
                proposed_row = row_idx + 1
                if proposed_row >= MAX_ROWS:
                    col_idx += 1
                    row_idx = 0
                    derived.append([])
                else:
                    next_cell_exists = proposed_row < len(derived[col_idx]) and derived[col_idx][proposed_row]
                    if next_cell_exists:
                        col_idx += 1
                        row_idx = 0
                        derived.append([])
                    else:
                        row_idx = proposed_row

            _place(derived[col_idx], row_idx, {"value": color})
            last_value = color

    return derived


def _to_matrix(columns: List[List[Optional[RoadCell]]]) -> List[List[Optional[RoadCell]]]:
    if not columns:
        return []
    width = len(columns)
    matrix: List[List[Optional[RoadCell]]] = [[None for _ in range(width)] for _ in range(MAX_ROWS)]
    for x, column in enumerate(columns):
        for y in range(MAX_ROWS):
            matrix[y][x] = column[y] if y < len(column) else None
    return matrix


@lru_cache(maxsize=64)
def generate_roadmaps(history_key: str) -> dict:
    history = list(history_key)
    big_road = build_big_road(history)
    big_eye = _build_derived(big_road, gap=1)
    small_road = _build_derived(big_road, gap=2)
    cockroach = _build_derived(big_road, gap=3)

    return {
        "big_road": _to_matrix(big_road),
        "big_eye_boy": _to_matrix(big_eye),
        "small_road": _to_matrix(small_road),
        "cockroach_pig": _to_matrix(cockroach),
    }
