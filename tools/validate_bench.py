"""BFS tham chiếu và replay cho bộ màn 5.3; không đăng ký/thay solver của VT1.

Chạy: python -m tools.validate_bench
In CSV: BFS tối thiểu số bước; UCS/A* tối thiểu chi phí, không đồng nhất hai số.
"""
from __future__ import annotations

from collections import deque
import argparse
import csv
from pathlib import Path
import sys
import time

from bloxorz.engine import initial_state, is_goal, step
from bloxorz.loader import load_stages
from bloxorz.model import Action, State
from bloxorz.search.base import ORDERED_DIRECTIONS, Limits, reconstruct, run
from bloxorz.search.cost import move_cost
from bloxorz.stage import Stage


def reference_bfs(stage: Stage, timeout_s: float = 60.0) -> tuple[Action, ...] | None:
    """Graph BFS độc lập, dùng cùng engine và thứ tự hướng chuẩn của dự án."""
    start = initial_state(stage)
    queue = deque([start])
    parents: dict[State, tuple[State, Action] | None] = {start: None}
    deadline = time.perf_counter() + timeout_s
    while queue:
        if time.perf_counter() >= deadline:
            raise TimeoutError(f"Reference BFS timed out: {stage.id}")
        state = queue.popleft()
        if is_goal(state, stage):
            return reconstruct(parents, state)
        for cube in ((0, 1) if state.pose is None else (None,)):
            for direction in ORDERED_DIRECTIONS:
                action = Action(direction, cube)
                nxt = step(state, action, stage)
                if nxt is not None and nxt not in parents:
                    parents[nxt] = (state, action)
                    queue.append(nxt)
    return None


def replay(stage: Stage, actions: tuple[Action, ...]) -> tuple[float, tuple[State, ...]]:
    """Kiểm tra từng bước hợp lệ và trạng thái cuối thắng, đồng thời tính cost."""
    state = initial_state(stage)
    states = [state]
    cost = 0.0
    for index, action in enumerate(actions):
        nxt = step(state, action, stage)
        if nxt is None:
            raise ValueError(f"{stage.id}: invalid action {index}: {action}")
        cost += move_cost(state, action, nxt, stage)
        states.append(nxt)
        state = nxt
    if not is_goal(state, stage):
        raise ValueError(f"{stage.id}: replay did not reach goal")
    return cost, tuple(states)


def action_text(actions: tuple[Action, ...]) -> str:
    return " ".join(a.direction.value + (str(a.cube) if a.cube is not None else "") for a in actions)


def main(output=sys.stdout) -> int:
    stages = load_stages(Path(__file__).parents[1] / "stages" / "bench")
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(("stage", "group", "bfs_length", "bfs_cost", "ucs_length", "ucs_cost",
                     "ucs_expanded", "astar_expanded", "bfs_actions", "ucs_actions"))
    failed = not stages
    for stage in stages:
        actions = reference_bfs(stage)
        if actions is None:
            raise ValueError(f"{stage.id}: reference BFS found no solution")
        bfs_cost, _ = replay(stage, actions)
        ucs = run("ucs", stage, Limits(timeout_s=60))
        if ucs.status != "solved":
            raise ValueError(f"{stage.id}: UCS returned {ucs.status}")
        replay(stage, ucs.actions)
        results = [run(name, stage, Limits(timeout_s=60)) for name in ("astar", "astar_manhattan")]
        for result in results:
            if result.status != "solved":
                raise ValueError(f"{stage.id}: {result.algorithm} returned {result.status}")
            replay(stage, result.actions)
            failed |= result.cost != ucs.cost
        failed |= results[0].expanded > ucs.expanded
        writer.writerow((stage.id, stage.group, len(actions), bfs_cost, ucs.length, ucs.cost,
                         ucs.expanded, results[0].expanded, action_text(actions), action_text(ucs.actions)))
    return int(failed)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="Lưu CSV UTF-8; mặc định in ra stdout")
    args = parser.parse_args()
    if args.output:
        with args.output.open("w", encoding="utf-8", newline="") as output:
            exit_code = main(output)
    else:
        exit_code = main()
    raise SystemExit(exit_code)
