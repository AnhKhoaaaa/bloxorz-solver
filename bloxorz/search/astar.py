# Phụ trách: VT5 - Task 5.2
"""A* tối ưu tổng move_cost, với hai heuristic và thứ tự mở nhánh cố định."""
from __future__ import annotations

import heapq
from itertools import count
from math import inf

from bloxorz.engine import initial_state, is_goal, step
from bloxorz.model import Action, State
from bloxorz.stage import Stage
from .base import ORDERED_DIRECTIONS, SearchContext, reconstruct, register
from .cost import move_cost
from .heuristics import Heuristic, make_heuristic

_ACTIONS = tuple(Action(direction) for direction in ORDERED_DIRECTIONS)
_SPLIT_ACTIONS = tuple(Action(direction, cube) for cube in (0, 1) for direction in ORDERED_DIRECTIONS)


def best_first(stage: Stage, ctx: SearchContext, heuristic: Heuristic) -> tuple[Action, ...] | None:
    """Lazy deletion theo g_best; cho mở lại node khi tìm được g nhỏ hơn.

    Heap (f, counter, g, state) ưu tiên thứ tự sinh nếu f bằng nhau.
    State làm khóa giữ cả pose, hai vị trí cube và bridges_open.
    """
    start = initial_state(stage)
    if is_goal(start, stage):
        return ()
    serial = count()
    heap = [(heuristic(start), next(serial), 0.0, start)]
    g_best = {start: 0.0}
    parents: dict[State, tuple[State, Action] | None] = {start: None}
    while heap:
        _, _, cost, state = heapq.heappop(heap)
        if cost != g_best[state]:
            continue
        ctx.tick()
        if is_goal(state, stage):
            return reconstruct(parents, state)
        actions = _SPLIT_ACTIONS if state.pose is None else _ACTIONS
        for action in actions:
            nxt = step(state, action, stage)
            if nxt is None:
                continue
            candidate = cost + move_cost(state, action, nxt, stage)
            if candidate >= g_best.get(nxt, inf):
                continue
            estimate = heuristic(nxt)
            if estimate == inf:
                continue
            g_best[nxt] = candidate
            parents[nxt] = (state, action)
            heapq.heappush(heap, (candidate + estimate, next(serial), candidate, nxt))
    return None


@register("astar")
def astar(stage: Stage, ctx: SearchContext) -> tuple[Action, ...] | None:
    return best_first(stage, ctx, make_heuristic(stage, "relaxed"))


@register("astar_manhattan")
def astar_manhattan(stage: Stage, ctx: SearchContext) -> tuple[Action, ...] | None:
    return best_first(stage, ctx, make_heuristic(stage, "manhattan"))
