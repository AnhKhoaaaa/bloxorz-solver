# Phụ trách: VT5 - Task 5.1
"""Thuật toán tìm kiếm chi phí đều (Uniform-Cost Search).

UCS tối ưu tổng chi phí C(P) = Σ c(s, s') theo hàm chi phí đã thống nhất
trong bloxorz_ucs_astar_design.md §1-2. UCS có thể chọn đường dài hơn BFS
nếu đường đó tránh được nhiều ô dễ vỡ F.

Cài đặt:
- Hàng đợi ưu tiên (min-heap) sắp xếp theo g(s) — tổng chi phí thực tế.
- Tập closed (visited) lưu trạng thái đã được MỞ RỘNG với chi phí tối ưu.
- Khi pop một trạng thái khỏi heap:
    * Nếu trạng thái đã mở rộng → bỏ qua (lazy deletion).
    * Nếu là trạng thái đích → tái tạo và trả về đường đi.
    * Sinon → mở rộng, sinh các trạng thái kế tiếp.
- Kết quả: tuple[Action, ...] hoặc None nếu không có lời giải.

Khối nguyên vẹn và hai cube sau khi tách đều được xử lý qua engine.step.
Khi tách, mỗi cube được xét đủ bốn hướng; engine tự xử lý việc ghép khối.
"""

from __future__ import annotations

import heapq
from typing import Optional

from bloxorz.engine import initial_state, is_goal, step
from bloxorz.model import Action, State
from bloxorz.stage import Stage

from .base import ORDERED_DIRECTIONS, SearchContext, register, reconstruct
from .cost import move_cost

# Bốn hướng di chuyển chuẩn; cube=None → khối nguyên vẹn
_ACTIONS: tuple[Action, ...] = tuple(Action(direction) for direction in ORDERED_DIRECTIONS)

# Xét đủ các hướng chuẩn của cube 0 trước, rồi đến cube 1.
_SPLIT_ACTIONS: tuple[Action, ...] = tuple(
    Action(direction, cube=cube)
    for cube in (0, 1)
    for direction in ORDERED_DIRECTIONS
)


@register("ucs")
def ucs(stage: Stage, ctx: SearchContext) -> tuple[Action, ...] | None:
    """Giải màn chơi bằng Uniform-Cost Search.

    Args:
        stage: Bản đồ màn chơi (bất biến).
        ctx  : Ngữ cảnh tìm kiếm (đếm node mở rộng, kiểm tra timeout).

    Returns:
        Tuple các Action tối ưu chi phí dẫn tới đích, hoặc None nếu
        không tồn tại lời giải hoặc bị giới hạn (timeout/cancel).
    """
    start: State = initial_state(stage)

    # Trạng thái đích ngay tại xuất phát
    if is_goal(start, stage):
        return ()

    # priority_queue: (g_cost, tie_breaker, state)
    # tie_breaker đảm bảo heap không cố so sánh hai State với nhau
    counter: int = 0
    heap: list[tuple[float, int, State]] = [(0.0, counter, start)]

    # parents[state] = (parent_state, action) hoặc None nếu là trạng thái gốc
    parents: dict[State, Optional[tuple[State, Action]]] = {start: None}

    # g_best[state] = chi phí tốt nhất đã biết đến state
    g_best: dict[State, float] = {start: 0.0}

    # Tập trạng thái đã được mở rộng (closed set)
    closed: set[State] = set()

    while heap:
        g, _, state = heapq.heappop(heap)

        # Lazy deletion: bỏ qua nếu đã mở rộng với chi phí tốt hơn
        if state in closed:
            continue

        # Mở rộng node
        ctx.tick()
        closed.add(state)

        # Kiểm tra đích
        if is_goal(state, stage):
            return reconstruct(parents, state)

        # Sinh các trạng thái kế tiếp
        actions = _SPLIT_ACTIONS if state.pose is None else _ACTIONS
        for action in actions:
            next_state: State | None = step(state, action, stage)
            if next_state is None:
                continue  # Bước đi không hợp lệ (rơi vực, gạch vỡ, v.v.)

            edge_cost: float = move_cost(state, action, next_state, stage)
            new_g: float = g + edge_cost

            # Chỉ thêm vào heap nếu tìm được đường tốt hơn
            if next_state in closed:
                continue
            if new_g < g_best.get(next_state, float("inf")):
                g_best[next_state] = new_g
                parents[next_state] = (state, action)
                counter += 1
                heapq.heappush(heap, (new_g, counter, next_state))

    # Hàng đợi rỗng → không có lời giải
    return None
