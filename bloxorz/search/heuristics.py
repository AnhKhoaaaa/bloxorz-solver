# Phụ trách: VT5 - Task 5.2
"""Hai cận dưới cho A*: relaxed 3D BFS và Manhattan theo ô trên-trái.

Relaxed giữ biên chữ nhật và bảng lăn, bỏ mọi loại ô/cầu/công tắc.
Khoảng cách tới công tắc tách được cộng cận phần đường sau dịch chuyển:
2 nếu hai cube chưa kề nhau, 1 nếu chúng ghép ngay khi xuất hiện.
Split cần ít nhất một bước ghép và một bước đứng lên goal nên h = 2.
"""
from __future__ import annotations

from collections import deque
from collections.abc import Callable, Iterable
from math import inf

from bloxorz.engine import get_block_cells, is_goal, roll_transition
from bloxorz.model import Pose, Pos, State
from bloxorz.stage import Stage
from .base import ORDERED_DIRECTIONS

Geometry = tuple[Pose, Pos]
Heuristic = Callable[[State], float]


def manhattan(first: Pos, second: Pos) -> int:
    return abs(first[0] - second[0]) + abs(first[1] - second[1])


def split_switch_positions(stage: Stage) -> tuple[Pos, ...]:
    return tuple(switch.pos for switch in stage.switches if switch.kind == "split")


def relaxed_distances(stage: Stage, targets: Iterable[Pos]) -> dict[Geometry, int]:
    """BFS nhiều nguồn đứng thẳng; cạnh lăn đảo được trên bàn trống.

    Chỉ yêu cầu mọi ô khối chiếm nằm trong rows x cols, kể cả ô khuyết của
    hàng ngắn. Không dùng engine.step vì nó áp luật ô và kích hoạt switch.
    """
    rows, cols = stage.rows, stage.cols
    distances: dict[Geometry, int] = {}
    queue: deque[Geometry] = deque()
    for target in targets:
        key = (Pose.STANDING, target)
        if 0 <= target[0] < rows and 0 <= target[1] < cols and key not in distances:
            distances[key] = 0
            queue.append(key)
    while queue:
        key = queue.popleft()
        for direction in ORDERED_DIRECTIONS:
            nxt = roll_transition(*key, direction)
            if nxt in distances:
                continue
            if all(0 <= r < rows and 0 <= c < cols for r, c in get_block_cells(*nxt)):
                distances[nxt] = distances[key] + 1
                queue.append(nxt)
    return distances


def make_heuristic(stage: Stage, name: str = "relaxed") -> Heuristic:
    """Tiền tính một lần mỗi lần chạy solver; không cache bằng stage.id.

    Manhattan dùng pos trên-trái; mỗi lần lăn dịch pos tối đa 2 ô.
    max(1, ...) ở trạng thái chưa thắng bảo đảm cạnh split -> ghép
    consistent: 2 <= 1 + h(khối nằm). Goal luôn có giá trị 0.
    """
    if name not in ("relaxed", "manhattan"):
        raise ValueError(f"Unknown heuristic: {name!r}")

    split_targets: dict[int, list[Pos]] = {1: [], 2: []}
    for switch in stage.switches:
        if switch.kind == "split":
            targets = switch.targets
            tail = 1 if targets is not None and manhattan(*targets) == 1 else 2
            split_targets[tail].append(switch.pos)

    if name == "relaxed":
        d_goal = relaxed_distances(stage, [stage.goal])
        d_split = [(relaxed_distances(stage, positions), tail)
                   for tail, positions in split_targets.items() if positions]

        def relaxed(state: State) -> float:
            if state.pose is None:
                return 2.0
            key = (state.pose, state.pos)
            best = d_goal.get(key, inf)
            for distances, tail in d_split:
                best = min(best, distances.get(key, inf) + tail)
            return float(best)

        return relaxed

    def baseline(state: State) -> float:
        if state.pose is None:
            return 2.0
        if is_goal(state, stage):
            return 0.0
        best = manhattan(state.pos, stage.goal) / 2
        for tail, positions in split_targets.items():
            for pos in positions:
                best = min(best, manhattan(state.pos, pos) / 2 + tail)
        return max(1.0, best)

    return baseline
