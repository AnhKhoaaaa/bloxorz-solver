# Phụ trách: VT1 - Task 1.5
"""Thuật toán tìm kiếm theo chiều sâu (Depth-First Search - Graph search).

Quy ước toàn dự án & tương thích với VT5:
- Hướng duyệt chuẩn: ORDERED_DIRECTIONS = (UP, DOWN, LEFT, RIGHT).
- Do Stack hoạt động theo cơ chế LIFO, danh sách các hành động hợp lệ phải được
  đảo ngược (reversed) khi push vào stack để nhánh UP luôn được pop ra duyệt trước.
- Graph search: Dùng từ điển `parents` để chống chu trình vô tận.
- Goal check: Kiểm tra khi POP trạng thái ra khỏi stack.
"""

from __future__ import annotations

from bloxorz.model import Action, State
from bloxorz.stage import Stage
from bloxorz.engine import initial_state, is_goal, step
from .base import ORDERED_DIRECTIONS, SearchContext, reconstruct, register


def get_available_actions(state: State) -> tuple[Action, ...]:
    """Sinh danh sách hành động hợp lệ theo đúng quy ước ORDERED_DIRECTIONS.

    - Khối nguyên vẹn (state.pose is not None): duyệt 4 hướng theo ORDERED_DIRECTIONS.
    - Khối tách đôi (state.pose is None): duyệt cube 0 theo ORDERED_DIRECTIONS,
      sau đó đến cube 1 theo ORDERED_DIRECTIONS (đồng bộ với VT5 và BFS).
    """
    if state.pose is not None:
        return tuple(Action(d) for d in ORDERED_DIRECTIONS)
    return tuple(Action(d, cube=0) for d in ORDERED_DIRECTIONS) + tuple(
        Action(d, cube=1) for d in ORDERED_DIRECTIONS
    )


@register("dfs")
def dfs(stage: Stage, ctx: SearchContext) -> tuple[Action, ...] | None:
    """Thuật toán DFS Graph-Search tìm đường đi từ điểm xuất phát đến đích.

    Args:
        stage: Màn chơi (chứa bản đồ, vị trí ban đầu và đích).
        ctx: Ngữ cảnh điều phối tìm kiếm (đếm nút mở rộng, kiểm tra timeout/cancel).

    Returns:
        tuple[Action, ...] nếu tìm thấy đường đi, hoặc None nếu vô nghiệm/hết thời gian.
    """
    start = initial_state(stage)
    if is_goal(start, stage):
        return ()

    # Stack lưu trữ tuple: (state, parent_state, action_taken)
    stack: list[tuple[State, State | None, Action | None]] = [(start, None, None)]
    parents: dict[State, tuple[State, Action] | None] = {}

    while stack:
        s, parent, action = stack.pop()

        if s in parents:
            continue
        parents[s] = None if parent is None else (parent, action)

        if is_goal(s, stage):
            return reconstruct(parents, s)

        ctx.tick()

        # Đảo ngược thứ tự successor để nhánh UP được pop ra duyệt đầu tiên
        for act in reversed(get_available_actions(s)):
            nxt = step(s, act, stage)
            if nxt is None:
                continue
            if nxt not in parents:
                stack.append((nxt, s, act))

    return None
