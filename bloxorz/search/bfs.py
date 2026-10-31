# Phụ trách: VT1 - Task 1.4
"""Thuật toán tìm kiếm theo chiều rộng (Breadth-First Search)."""

from __future__ import annotations
from collections import deque
from bloxorz.model import Action, State
from bloxorz.stage import Stage
from bloxorz.engine import initial_state, is_goal, step
from .base import ORDERED_DIRECTIONS, SearchContext, reconstruct, register


def get_available_actions(state: State) -> tuple[Action, ...]:
    """
    Sinh danh sách các hành động hợp lệ tùy theo trạng thái khối theo thứ tự ORDERED_DIRECTIONS:
    - Khối nguyên vẹn (pose is not None): các hướng trong ORDERED_DIRECTIONS.
    - Khối phân tách (pose is None): các hướng trong ORDERED_DIRECTIONS cho cube 0 rồi cube 1.
    """
    if state.pose is not None:
        return tuple(Action(d) for d in ORDERED_DIRECTIONS)
    return tuple(Action(d, cube=0) for d in ORDERED_DIRECTIONS) + tuple(
        Action(d, cube=1) for d in ORDERED_DIRECTIONS
    )


@register("bfs")
def bfs(stage: Stage, ctx: SearchContext) -> tuple[Action, ...] | None:
    """Thuật toán BFS tìm đường đi có số bước ngắn nhất từ start đến goal."""
    start = initial_state(stage)
    if is_goal(start, stage):
        return ()

    frontier = deque([start])
    parents: dict[State, tuple[State, Action] | None] = {start: None}

    while frontier:
        curr = frontier.popleft()
        ctx.tick()
        ctx.observe(curr, len(frontier))

        for action in get_available_actions(curr):
            nxt = step(curr, action, stage)
            if nxt is None:
                continue
            if nxt not in parents:
                parents[nxt] = (curr, action)
                if is_goal(nxt, stage):
                    return reconstruct(parents, nxt)
                frontier.append(nxt)

    return None
