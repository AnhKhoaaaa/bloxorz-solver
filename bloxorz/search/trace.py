# Phụ trách: Benchmark Visualizer
"""Ghi lại từng bước mở rộng của solver để trình visualizer (bloxorz/gui/web/bench.js) phát lại.

- TraceContext: SearchContext ghi mỗi lần mở rộng (ô khối chiếm, kích thước frontier, h nếu có).
  Thuật toán chỉ cần gọi ctx.observe(state, len(frontier)) sau ctx.tick(); SearchContext gốc bỏ qua.
- collect_trace(): chạy 1 lượt có ghi vết + 1 lượt search.run() để lấy số đo thật
  (thời gian không bị lẫn chi phí ghi vết).
"""
from __future__ import annotations

from math import inf
from typing import Any

from bloxorz.engine import get_block_cells, initial_state, step
from bloxorz.model import Pose, State
from bloxorz.stage import Stage
from .base import ALGORITHMS, Limits, SearchAborted, SearchContext, run
from .heuristics import Heuristic, make_heuristic

MAX_EVENTS = 20000  # đủ cho các màn trong repo; quá thì cắt và báo "truncated"
HEURISTIC_OF = {"astar": "relaxed", "astar_manhattan": "manhattan"}


def cells_of(state: State) -> list[list[int]]:
    """Các ô khối đang chiếm: 1-2 ô khi nguyên khối, 2 cube khi tách."""
    if state.pose is None:
        return [list(state.pos), list(state.cube2)]
    return [list(p) for p in get_block_cells(state.pose, state.pos)]


def _number(value: float) -> float | None:
    return None if value == inf else value


class TraceContext(SearchContext):
    def __init__(self, limits: Limits | None = None, heuristic: Heuristic | None = None):
        super().__init__(limits)
        self.heuristic = heuristic
        self.events: list[dict[str, Any]] = []

    def observe(self, state: State, frontier: int, g: float | None = None) -> None:
        if len(self.events) >= MAX_EVENTS:
            return
        h = _number(self.heuristic(state)) if self.heuristic else None
        g_val = round(g, 2) if g is not None else None
        h_val = round(h, 2) if h is not None else None
        f_val = round(g_val + h_val, 2) if g_val is not None and h_val is not None else None
        self.events.append({"cells": cells_of(state), "frontier": frontier, "g": g_val, "h": h_val, "f": f_val})


def heuristic_field(stage: Stage, heuristic: Heuristic) -> dict[str, float | None]:
    """h của khối đứng thẳng trên từng ô sàn: "trường hấp dẫn" kéo về lỗ đích."""
    bridges = stage.initial_bridges_open()
    field = {}
    for r, row in enumerate(stage.grid):
        for c, ch in enumerate(row):
            if ch != ".":
                field[f"{r},{c}"] = _number(heuristic(State(Pose.STANDING, (r, c), bridges_open=bridges)))
    return field


def solution_cells(stage: Stage, actions) -> list[list[list[int]]]:
    """Ô khối chiếm sau từng bước của lời giải, bắt đầu từ vị trí xuất phát."""
    state = initial_state(stage)
    path = [cells_of(state)]
    for action in actions:
        state = step(state, action, stage)
        if state is None:
            break
        path.append(cells_of(state))
    return path


def collect_trace(algorithm: str, stage: Stage, limits: Limits | None = None) -> dict[str, Any]:
    if algorithm not in ALGORITHMS:
        raise ValueError(f"Algorithm '{algorithm}' is not registered")
    limits = limits or Limits(timeout_s=10.0)
    name = HEURISTIC_OF.get(algorithm)
    heuristic = make_heuristic(stage, name) if name else None

    ctx = TraceContext(limits, heuristic)
    try:
        ALGORITHMS[algorithm](stage, ctx)
    except SearchAborted:
        pass  # trạng thái cuối lấy từ search.run bên dưới

    result = run(algorithm, stage, limits)
    return {
        "algorithm": algorithm,
        "stage_id": stage.id,
        "status": result.status,
        "grid": list(stage.grid),
        "goal": list(stage.goal),
        "switches": [{"pos": list(s.pos), "kind": s.kind} for s in stage.switches],
        "events": ctx.events,
        "truncated": ctx.expanded > len(ctx.events),
        "heuristic_field": heuristic_field(stage, heuristic) if heuristic else None,
        "path": solution_cells(stage, result.actions) if result.status == "solved" else [],
        "stats": {
            "expanded": result.expanded,
            "length": result.length,
            "cost": result.cost,
            "time_ms": round(result.time_s * 1000, 3),
        },
    }
