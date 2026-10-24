# Phụ trách: VT1 - Task 1.4
"""Thuật toán tìm kiếm theo chiều rộng (Breadth-First Search)."""

from __future__ import annotations
from collections import deque
from bloxorz.model import Action, Direction, State
from bloxorz.stage import Stage
from bloxorz.engine import initial_state, is_goal, step
from .base import register, reconstruct, SearchContext

DIRECTIONS = (Direction.UP, Direction.DOWN, Direction.LEFT, Direction.RIGHT)

def get_available_actions(state: State) -> tuple[Action, ...]:
    """
    Sinh danh sách các hành động hợp lệ tùy theo trạng thái khối:
    - Khối nguyên vẹn (pose is not None): 4 hướng di chuyển (UP, DOWN, LEFT, RIGHT).
    - Khối phân tách thành 2 cube 1x1 (pose is None): 4 hướng cho cube 0 và 4 hướng cho cube 1.
    """
    if state.pose is not None:
        return (
            Action(Direction.UP),
            Action(Direction.DOWN),
            Action(Direction.LEFT),
            Action(Direction.RIGHT),
        )
    return (
        Action(Direction.UP, cube=0),
        Action(Direction.DOWN, cube=0),
        Action(Direction.LEFT, cube=0),
        Action(Direction.RIGHT, cube=0),
        Action(Direction.UP, cube=1),
        Action(Direction.DOWN, cube=1),
        Action(Direction.LEFT, cube=1),
        Action(Direction.RIGHT, cube=1),
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

        for action in get_available_actions(curr):
            nxt = step (curr, action, stage)
            if nxt is None:
                continue
            if nxt not in parents:
                parents[nxt] = (curr, action)
                if is_goal(nxt, stage):
                    return reconstruct(parents, nxt)
                frontier.append(nxt)
                
    return None

