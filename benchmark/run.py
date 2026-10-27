# Phụ trách: VT1 - Task 1.6
"""Runner tự động chạy đo thời gian và bộ nhớ các thuật toán (Benchmark Runner).

Mục tiêu:
- Một lệnh chạy mọi màn × mọi thuật toán và ghi kết quả ra file CSV.
- VT5 dùng file này để vẽ bảng và biểu đồ (Task 5.5 plots.py).
- Tuyệt đối không mở cửa sổ giao diện, chạy headless hoàn toàn.

Quy cách đo:
- Đo thời gian: Lặp lại repeat lần (mặc định 5 lần) với measure_memory=False, lấy trung vị (median).
- Đo bộ nhớ: Chạy thêm 1 lần riêng biệt với measure_memory=True để lấy bộ nhớ đỉnh (tracemalloc).
- Kiểm tra tính đúng đắn: Lời giải 'solved' được kiểm tra qua verify_solution.
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
import platform
import statistics
import subprocess
import sys
from typing import Any, Sequence

from bloxorz.loader import load_stage, load_stages
from bloxorz.search import Limits, run
from bloxorz.stage import Stage
from bloxorz.verify import verify_solution

CSV_COLUMNS: list[str] = [
    "stage_id",
    "group",
    "algorithm",
    "status",
    "length",
    "cost",
    "expanded",
    "time_ms_median",
    "time_ms_all",
    "peak_mem_kb",
    "verified",
    "commit",
    "python",
    "machine",
]

DEFAULT_ALGOS: list[str] = ["bfs", "dfs", "ucs", "astar", "astar_manhattan"]


def get_git_commit() -> str:
    """Lấy mã commit hash ngắn hiện tại qua git rev-parse --short HEAD."""
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
        return out
    except Exception:
        return "unknown"


def get_machine_info() -> str:
    """Lấy thông tin vi xử lý/phần cứng hệ thống."""
    proc = platform.processor().strip()
    return proc if proc else platform.machine()


def load_all_stages(stage_paths: Sequence[str | Path]) -> list[Stage]:
    """Tải tất cả màn chơi từ danh sách đường dẫn thư mục hoặc file JSON."""
    stages: list[Stage] = []
    seen_ids: set[str] = set()

    for path_item in stage_paths:
        p = Path(path_item)
        if not p.exists():
            raise FileNotFoundError(f"Đường dẫn màn chơi không tồn tại: {path_item}")

        loaded: list[Stage] = load_stages(p) if p.is_dir() else [load_stage(p)]
        for st in loaded:
            if st.id not in seen_ids:
                stages.append(st)
                seen_ids.add(st.id)

    return stages


def benchmark_stage_algo(
    stage: Stage,
    algo: str,
    repeat: int = 5,
    timeout_s: float = 60.0,
    commit: str = "",
    python_ver: str = "",
    machine: str = "",
) -> dict[str, Any]:
    """Thực hiện đo đạc cho 1 cặp (màn chơi, thuật toán)."""
    limits = Limits(timeout_s=timeout_s)
    times_ms: list[float] = []
    last_res = None

    # 1. Đo thời gian repeat lần
    for _ in range(repeat):
        res = run(algo, stage, limits, measure_memory=False)
        last_res = res
        time_ms = res.time_s * 1000.0
        times_ms.append(time_ms)

        # Các thuật toán của dự án là đơn định (deterministic).
        # Nếu đã timeout/cancelled/error ở lần đầu, không cần lặp lại để tránh lãng phí thời gian.
        if res.status in ("timeout", "cancelled", "error"):
            while len(times_ms) < repeat:
                times_ms.append(time_ms)
            break

    assert last_res is not None
    time_ms_median = round(statistics.median(times_ms), 1)
    time_ms_all = ";".join(f"{t:.1f}" for t in times_ms)

    # 2. Đo bộ nhớ đỉnh (chỉ chạy 1 lần khi kết quả là solved hoặc unsolvable)
    peak_mem_kb: float | str = ""
    if last_res.status in ("solved", "unsolvable"):
        res_mem = run(algo, stage, limits, measure_memory=True)
        if res_mem.peak_mem_bytes is not None:
            peak_mem_kb = round(res_mem.peak_mem_bytes / 1024.0, 1)

    # 3. Kiểm tra tính đúng đắn (Verification)
    verified: bool | str = ""
    if last_res.status == "solved":
        try:
            ok, _ = verify_solution(stage, last_res.actions)
            verified = ok
        except Exception:
            verified = False

    return {
        "stage_id": stage.id,
        "group": stage.group or "",
        "algorithm": algo,
        "status": last_res.status,
        "length": last_res.length,
        "cost": last_res.cost,
        "expanded": last_res.expanded,
        "time_ms_median": time_ms_median,
        "time_ms_all": time_ms_all,
        "peak_mem_kb": peak_mem_kb,
        "verified": verified,
        "commit": commit,
        "python": python_ver,
        "machine": machine,
    }


def run_benchmark(
    stages: Sequence[Stage],
    algos: Sequence[str],
    repeat: int = 5,
    timeout: float = 60.0,
    out_path: str | Path = "results/run.csv",
) -> list[dict[str, Any]]:
    """Chạy toàn bộ ma trận (stages × algos), ghi file CSV và in tiến độ ra console."""
    out_file = Path(out_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)

    commit = get_git_commit()
    python_ver = platform.python_version()
    machine = get_machine_info()

    total_tasks = len(stages) * len(algos)
    current_idx = 0
    results: list[dict[str, Any]] = []

    with open(out_file, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        f.flush()

        for stage in stages:
            for algo in algos:
                current_idx += 1
                row = benchmark_stage_algo(
                    stage=stage,
                    algo=algo,
                    repeat=repeat,
                    timeout_s=timeout,
                    commit=commit,
                    python_ver=python_ver,
                    machine=machine,
                )
                writer.writerow(row)
                f.flush()
                results.append(row)

                # In tiến độ: ví dụ [12/68] g3_02 astar solved 23 moves 41.2 ms
                status = row["status"]
                length = row["length"]
                t_median = row["time_ms_median"]
                print(
                    f"[{current_idx}/{total_tasks}] {stage.id} {algo} {status} {length} moves {t_median} ms",
                    flush=True,
                )

    return results


def build_parser() -> argparse.ArgumentParser:
    """Xây dựng bộ phân tích cú pháp tham số dòng lệnh CLI."""
    parser = argparse.ArgumentParser(
        description="Bloxorz Solver Benchmark Runner: Tự động chạy đo hiệu năng mọi màn × mọi thuật toán.",
    )
    parser.add_argument(
        "--stages",
        nargs="+",
        default=["stages/bench"],
        help="Đường dẫn đến một hoặc nhiều thư mục / file JSON màn chơi (mặc định: stages/bench).",
    )
    parser.add_argument(
        "--algos",
        nargs="+",
        default=DEFAULT_ALGOS,
        help=f"Danh sách thuật toán cần đo (mặc định: {' '.join(DEFAULT_ALGOS)}).",
    )
    parser.add_argument(
        "--repeat",
        type=int,
        default=5,
        help="Số lần lặp đo thời gian để lấy trung vị (mặc định: 5).",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=60.0,
        help="Thời gian tối đa (giây) cho mỗi lần chạy thuật toán (mặc định: 60).",
    )
    parser.add_argument(
        "--out",
        type=str,
        default="results/run.csv",
        help="Đường dẫn file CSV xuất kết quả (mặc định: results/run.csv).",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Hàm thực thi chính khi gọi từ CLI."""
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        stages = load_all_stages(args.stages)
    except Exception as e:
        print(f"Lỗi khi đọc màn chơi: {e}", file=sys.stderr)
        return 1

    if not stages:
        print("Cảnh báo: Không tìm thấy màn chơi nào hợp lệ để đo.", file=sys.stderr)
        return 1

    print(
        f"Bắt đầu Benchmark: {len(stages)} màn × {len(args.algos)} thuật toán (repeat={args.repeat}, timeout={args.timeout}s)..."
    )
    print(f"File kết quả: {args.out}")

    run_benchmark(
        stages=stages,
        algos=args.algos,
        repeat=args.repeat,
        timeout=args.timeout,
        out_path=args.out,
    )

    print("Benchmark hoàn tất thành công!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
