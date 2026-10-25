"""Đối chiếu chi phí và số node; thời gian run() gồm tiền xử lý heuristic.

Chạy từ repo: python -m tools.validate_astar [stages/original]
Không có tham số: dùng fixtures và bench. CSV in ra stdout để lưu nếu cần.
"""
from __future__ import annotations

import csv
from pathlib import Path
import sys

from bloxorz.engine import initial_state, is_goal, step
from bloxorz.loader import load_stage
from bloxorz.search.base import Limits, run


def main() -> int:
    directories = [Path(arg) for arg in sys.argv[1:]] or [Path("stages/fixtures"), Path("stages/bench")]
    paths = sorted({path for directory in directories for path in directory.rglob("*.json")})
    writer = csv.writer(sys.stdout, lineterminator="\n")
    writer.writerow(("stage", "algorithm", "status", "cost", "length", "expanded", "time_s"))
    failed = not paths
    for path in paths:
        stage = load_stage(path)
        reference = None
        for algorithm in ("ucs", "astar", "astar_manhattan"):
            result = run(algorithm, stage, Limits(timeout_s=5.0))
            writer.writerow((stage.id, algorithm, result.status, result.cost,
                             result.length, result.expanded, f"{result.time_s:.6f}"))
            sys.stdout.flush()
            if reference is None:
                reference = result
            failed |= result.status not in ("solved", "unsolvable")
            failed |= (result.status, result.cost) != (reference.status, reference.cost)
            if result.status == "solved":
                state = initial_state(stage)
                for action in result.actions:
                    state = step(state, action, stage)
                    if state is None:
                        break
                failed |= state is None or not is_goal(state, stage)
            if algorithm == "astar" and "bench" in path.parts:
                failed |= result.expanded > reference.expanded
    return int(failed)


if __name__ == "__main__":
    raise SystemExit(main())
