# Phụ trách: VT5 - Task 5.5
"""Headless tables and charts from the Task 1.6 CSV (Task 5.5).

    python -m benchmark.plots results/final/results.csv --out results
    python -m benchmark.plots bench.csv --original original.csv --out results

Only solved, verified rows contribute to solution statistics. Failed and missing
pairs remain visible on the charts; zero rounded timings are never replaced by
invented positive measurements on logarithmic axes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import sys
from typing import Sequence

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
import numpy as np
import pandas as pd

from benchmark.run import CSV_COLUMNS

COLORS = {
    "bfs": "#2563EB", "dfs": "#DC2626", "ucs": "#D97706",
    "astar": "#059669", "astar_manhattan": "#7C3AED",
}
NAMES = {"bfs": "BFS", "dfs": "DFS", "ucs": "UCS", "astar": "A* relaxed",
         "astar_manhattan": "A* Manhattan"}
MARKERS = {"timeout": "X", "unsolvable": "v", "cancelled": "s", "error": "P",
           "invalid": "D", "unverified": "*", "missing": "x", "no RAM": "+", "zero": "o"}
STATUSES = ("solved", "timeout", "unsolvable", "cancelled", "error", "invalid", "unverified")
NUMERIC = ("length", "cost", "expanded", "time_ms_median", "peak_mem_kb")


def _natural(value: str) -> tuple:
    return tuple(int(part) if part.isdigit() else part for part in re.split(r"(\d+)", value))


def _algorithms(data: pd.DataFrame) -> list[str]:
    return sorted(data.algorithm.unique(), key=lambda name: (list(COLORS).index(name)
                  if name in COLORS else len(COLORS), name))


def _stages(data: pd.DataFrame) -> list[str]:
    return sorted(data.stage_id.unique(), key=_natural)


def _color(algorithm: str) -> str:
    return COLORS.get(algorithm, "#64748B")


def load_results(path: str | Path) -> pd.DataFrame:
    """Validate one run/environment; never silently combine duplicate trials."""
    data = pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    missing = set(CSV_COLUMNS) - set(data.columns)
    if missing:
        raise ValueError(f"Missing CSV columns: {', '.join(sorted(missing))}")
    if data.empty:
        raise ValueError("CSV contains no results")
    data = data[CSV_COLUMNS].copy()
    for name in CSV_COLUMNS:
        data[name] = data[name].str.strip()
    for name in ("stage_id", "group", "algorithm", "commit", "python", "machine"):
        if (data[name] == "").any():
            raise ValueError(f"Empty {name}")
    for name in ("commit", "python", "machine"):
        if data[name].nunique() != 1:
            raise ValueError(f"Mixed {name} values: use a separate report for each environment/run")
    if data.duplicated(["stage_id", "algorithm"]).any():
        raise ValueError("Duplicate stage_id/algorithm pair; select a single benchmark run")
    if (data.groupby("stage_id")["group"].nunique() != 1).any():
        raise ValueError("A stage belongs to multiple groups")
    if not data.status.isin(STATUSES[:5]).all():
        raise ValueError("Unknown result status")
    verification = data.verified.str.lower()
    if not verification.isin(("true", "false", "")).all():
        raise ValueError("verified must be True, False or blank")
    for name in NUMERIC:
        text = data[name].replace("", np.nan) if name == "peak_mem_kb" else data[name]
        values = pd.to_numeric(text, errors="raise")
        valid = values.dropna() if name == "peak_mem_kb" else values
        if not np.isfinite(valid).all() or (valid < 0).any():
            raise ValueError(f"{name} must contain finite, nonnegative measurements")
        if name in ("length", "expanded") and (values % 1 != 0).any():
            raise ValueError(f"{name} must contain integers")
        data[name] = values
    samples = []
    for text in data.time_ms_all:
        try:
            times = [float(value) for value in text.split(";")]
        except ValueError as error:
            raise ValueError("Invalid time_ms_all sample") from error
        if not all(math.isfinite(value) and value >= 0 for value in times):
            raise ValueError("time_ms_all samples must be finite and nonnegative")
        samples.append(len(times))
    data["samples"] = samples
    data["result"] = data.status
    data.loc[(data.status == "solved") & (verification == "false"), "result"] = "invalid"
    data.loc[(data.status == "solved") & (verification == ""), "result"] = "unverified"
    data["usable"] = (data.status == "solved") & (verification == "true")
    data["verified"] = verification.map({"true": True, "false": False, "": None})
    return data.sort_values(["group", "stage_id", "algorithm"]).reset_index(drop=True)


def summarize(data: pd.DataFrame) -> pd.DataFrame:
    """Per-group medians/means over verified solutions, with explicit denominators."""
    records = []
    for group in sorted(data.group.unique(), key=_natural):
        cohort = data[data.group == group]
        total = cohort.stage_id.nunique()
        for algo in _algorithms(data):
            subset = cohort[cohort.algorithm == algo]
            solved = subset[subset.usable]
            record = {"group": group, "algorithm": algo, "solved": len(solved), "total": total,
                      "missing": total - len(subset)}
            record.update({status: int((subset.result == status).sum()) for status in STATUSES[1:]})
            record.update({
                "time_ms_median": solved.time_ms_median.median(),
                "peak_mem_kb_median": solved.peak_mem_kb.median() if solved.peak_mem_kb.notna().any() else np.nan,
                "memory_samples": int(solved.peak_mem_kb.notna().sum()),
                "expanded_median": solved.expanded.median(),
                "length_mean": solved.length.mean(), "cost_mean": solved.cost.mean(),
            })
            records.append(record)
    return pd.DataFrame(records)


def _draw_metric(axis, data: pd.DataFrame, metric: str, algorithms: list[str], log: bool) -> None:
    stages = _stages(data)
    index = data.set_index(["stage_id", "algorithm"])
    width = 0.8 / max(len(algorithms), 1)
    present_markers = set()
    for offset, algo in enumerate(algorithms):
        for position, stage in enumerate(stages):
            x = position - 0.4 + width * (offset + 0.5)
            key = (stage, algo)
            marker = None
            if key not in index.index:
                marker = "missing"
            else:
                row = index.loc[key]
                if not row.usable:
                    marker = row.result
                elif pd.isna(row[metric]):
                    marker = "no RAM"
                elif row[metric] == 0:
                    marker = "zero"
                else:
                    axis.bar(x, row[metric], width=width * 0.92, color=_color(algo), zorder=3)
            if marker:
                present_markers.add(marker)
                # A symbol in axis coordinates is a status label, not a numeric measurement.
                axis.plot(x, 0.025, marker=MARKERS[marker], color=_color(algo),
                          markerfacecolor="none" if marker == "zero" else _color(algo),
                          markersize=6, linestyle="none", transform=axis.get_xaxis_transform(), zorder=5)
    if log:
        axis.set_yscale("log")
        positive = data.loc[data.usable & (data[metric] > 0), metric]
        if positive.empty:
            axis.set_ylim(0.1, 10)
        else:
            axis.set_ylim(positive.min() / 2, max(positive.max() * 2, positive.min() * 4))
    else:
        axis.set_ylim(bottom=0)
    axis.set_xticks(range(len(stages)), stages, rotation=55, ha="right", fontsize=8)
    axis.set_xlim(-0.65, len(stages) - 0.35)
    axis.set_xlabel("Stage ID")
    axis.grid(axis="y", alpha=0.2, zorder=0)
    axis.spines[["top", "right"]].set_visible(False)
    handles = [Patch(color=_color(algo), label=NAMES.get(algo, algo)) for algo in algorithms]
    handles += [Line2D([], [], color="#334155", marker=MARKERS[status], linestyle="none",
                       markerfacecolor="none" if status == "zero" else "#334155",
                       label="zero (rounded/input)" if status == "zero" else status)
                for status in MARKERS if status in present_markers]
    if handles:
        axis.legend(handles=handles, loc="upper left", bbox_to_anchor=(0, 1.16),
                    ncols=min(5, len(handles)), fontsize=8, frameon=False)


def metric_figure(data: pd.DataFrame, metric: str, title: str, ylabel: str,
                  *, log: bool = False, algorithms: list[str] | None = None):
    """Create a grouped stage chart including status markers for failed/missing pairs."""
    figure, axis = plt.subplots(figsize=(max(12, min(26, len(_stages(data)) * 0.75)), 6.5))
    _draw_metric(axis, data, metric, algorithms or _algorithms(data), log)
    axis.set_ylabel(ylabel)
    figure.suptitle(title, fontsize=14, fontweight="bold", y=0.99)
    figure.text(0.01, 0.015, "Bars: solved + verified only. Bottom symbols: status / missing / zero; not measured heights.", fontsize=8)
    figure.subplots_adjust(left=0.075, right=0.99, bottom=0.19, top=0.78)
    return figure


def _length_cost_figure(data: pd.DataFrame, label: str):
    algorithms = ["bfs", "ucs", "astar"]
    figure, axes = plt.subplots(2, 1, figsize=(max(12, min(26, len(_stages(data)) * 0.75)), 11))
    for axis, metric, unit in zip(axes, ("length", "cost"), ("Solution length (moves)", "Path cost (cost units)")):
        _draw_metric(axis, data, metric, algorithms, False)
        axis.set_ylabel(unit)
    figure.suptitle(f"BFS / UCS / A*: length versus cost\n{label}", fontsize=14, fontweight="bold")
    figure.text(0.01, 0.01, "BFS minimizes moves; UCS/A* minimize weighted cost. Failure symbols are not zero-length solutions.", fontsize=8)
    figure.subplots_adjust(left=0.075, right=0.99, bottom=0.13, top=0.84, hspace=0.85)
    return figure


def _format(value) -> str:
    if pd.isna(value):
        return "—"
    if isinstance(value, (float, np.floating)):
        return f"{value:.3f}".rstrip("0").rstrip(".")
    return str(value).replace("|", "\\|").replace("\n", " ")


def _markdown(data: pd.DataFrame) -> str:
    lines = ["| " + " | ".join(data.columns) + " |", "| " + " | ".join("---" for _ in data.columns) + " |"]
    lines += ["| " + " | ".join(_format(value) for value in values) + " |"
              for values in data.itertuples(index=False, name=None)]
    return "\n".join(lines) + "\n"


def _provenance(path: str | Path, data: pd.DataFrame) -> dict:
    # The repository enforces LF on checkout; hash content consistently across OSes.
    content = Path(path).read_bytes().replace(b"\r\n", b"\n")
    return {"path": Path(path).as_posix(), "sha256": hashlib.sha256(content).hexdigest(),
            "rows": len(data), "stages": data.stage_id.nunique(),
            **{name: data.iloc[0][name] for name in ("commit", "python", "machine")}}


def _write_tables(data: pd.DataFrame, out: Path, label: str) -> None:
    summary = summarize(data)
    summary.to_csv(out / "summary.csv", index=False, encoding="utf-8")
    heading = (f"# Bảng tổng hợp — {label}\n\n"
               "Chỉ `solved` + `verified=True` được tính vào trung vị/trung bình. "
               "`total` là số màn khác nhau trong nhóm, kể cả cặp thuật toán bị thiếu. "
               "Các thuật toán có thể có tập màn thành công khác nhau; không suy ra speedup từ hai trung vị nhóm.\n\n"
               "Đơn vị: time_ms_median = ms; peak_mem_kb_median = KB (bytes/1024); "
               "expanded_median = nút; length_mean = bước; cost_mean = đơn vị chi phí. "
               "memory_samples là số dòng thành công có đo RAM; ô trống/— không phải 0.\n\n")
    (out / "summary.md").write_text(heading + _markdown(summary), encoding="utf-8")
    details = data.drop(columns="usable")
    details.to_csv(out / "details.csv", index=False, encoding="utf-8")
    columns = ["stage_id", "group", "algorithm", "result", "length", "cost", "expanded", "time_ms_median", "peak_mem_kb", "samples"]
    (out / "details.md").write_text(f"# Chi tiết — {label}\n\n" + _markdown(details[columns]), encoding="utf-8")


def observations(data: pd.DataFrame, label: str) -> str:
    """Draft statements grounded in verified rows; paired comparisons use common stages."""
    good = data[data.usable]
    lines = [f"# Nhận xét nháp — {label}", "Nhận xét chỉ áp dụng cho CSV và môi trường trong manifest.json; nếu đang dùng dữ liệu mẫu, cần thay bằng CSV chính thức 1.7 trước khi chốt báo cáo."]
    lines.append(f"1. CSV có {data.stage_id.nunique()} màn, {data.algorithm.nunique()} thuật toán; "
                 f"{len(good)}/{len(data)} dòng giải thành công đã xác minh; "
                 f"{len(data) - len(good)} dòng thất bại/chưa xác minh được giữ riêng.")
    if not good.empty:
        medians = good.groupby("algorithm").expanded.median()
        winner = medians.idxmax()
        lines.append(f"2. {NAMES.get(winner, winner)} có trung vị expanded lớn nhất trên tập thành công của từng thuật toán ({medians.max():g} nút); tập màn có thể khác nhau.")
    else:
        lines.append("2. Không có lời giải đã xác minh để so sánh hiệu năng.")
    paired = good.pivot(index="stage_id", columns="algorithm", values="expanded")
    for number, reference in ((3, "ucs"), (4, "astar_manhattan")):
        if {"astar", reference}.issubset(paired.columns):
            common = paired[["astar", reference]].dropna()
            common = common[common[reference] > 0]
        else:
            common = pd.DataFrame()
        if not common.empty:
            reduction = (1 - common.astar / common[reference]) * 100
            lines.append(f"{number}. Trên {len(common)} màn chung đã xác minh có expanded tham chiếu > 0, "
                         f"trung vị giảm expanded của A* relaxed so với {NAMES.get(reference, reference)} là {reduction.median():.1f}% "
                         "(tính tỷ lệ từng màn rồi lấy trung vị; giá trị âm nghĩa là tăng).")
        else:
            lines.append(f"{number}. Chưa đủ cặp màn thành công chung A* relaxed / {reference} để tính mức giảm expanded.")
    lengths = good.pivot(index="stage_id", columns="algorithm", values="length")
    if {"bfs", "dfs"}.issubset(lengths.columns):
        common = lengths[["bfs", "dfs"]].dropna()
        lines.append(f"5. DFS dài hơn BFS trên {int((common.dfs > common.bfs).sum())}/{len(common)} màn chung; DFS ưu tiên đi sâu và không tối ưu độ dài lời giải.")
    else:
        lines.append("5. BFS tối ưu số bước, UCS/A* tối ưu chi phí có phạt F; cần có cả hai kết quả trên cùng màn để đối chiếu độ dài và chi phí.")
    lines.append("6. Thời gian A* bao gồm tạo heuristic ở đầu mỗi lần chạy; ít expanded hơn chưa bảo đảm tổng thời gian nhỏ hơn. RAM đo riêng bằng tracemalloc, không phải toàn bộ RAM của tiến trình.")
    lines.append("7. Các thống kê thời gian dùng trung vị từng dòng từ runner; số mẫu thực tế nằm ở cột samples. Thời gian 0 ms có thể do runner làm tròn 0.1 ms và được đánh dấu riêng trên trục log.")
    lines.append("8. Expanded được giữ nguyên như solver báo: BFS kiểm tra goal khi sinh successor, còn DFS/UCS/A* kiểm tra khi pop; vì vậy cần lưu ý khác biệt cách đếm nút đích khi diễn giải chênh lệch nhỏ.")
    return "\n\n".join(lines) + "\n"


def create_report(csv_path: str | Path, out: str | Path = "results", *,
                  original: str | Path | None = None, label: str = "Benchmark results") -> list[Path]:
    data = load_results(csv_path)
    original_data = load_results(original) if original else None
    output = Path(out)
    figures, tables = output / "figures", output / "tables"
    figures.mkdir(parents=True, exist_ok=True)
    tables.mkdir(parents=True, exist_ok=True)
    _write_tables(data, tables, label)
    (tables / "observations.md").write_text(observations(data, label), encoding="utf-8")
    if original_data is not None:
        columns = ["stage_id", "group", "algorithm", "result", "length", "cost", "expanded", "time_ms_median", "peak_mem_kb"]
        original_data.drop(columns="usable").to_csv(tables / "original.csv", index=False, encoding="utf-8")
        stages = set(original_data.stage_id)
        expected = {f"stage_{number:02d}" for number in range(1, 34)}
        missing = sorted(expected - stages)
        text = (f"# Phụ lục màn gốc — {label}\n\n{len(stages)} màn, {len(original_data)} dòng. "
                + ("Đủ 33 id stage_01–stage_33.\n\n" if not missing else f"Chưa đủ 33 màn; còn thiếu: {', '.join(missing)}.\n\n"))
        (tables / "original.md").write_text(text + _markdown(original_data[columns]), encoding="utf-8")
    else:
        (tables / "original.md").write_text("# Phụ lục màn gốc\n\nChưa có CSV 33 màn gốc. Chạy lại với `--original <csv>`; không suy diễn từ bộ G1–G5.\n", encoding="utf-8")
        # Do not leave a previous appendix CSV next to the explicit 'missing' notice.
        (tables / "original.csv").unlink(missing_ok=True)
    jobs = [
        ("expanded", "expanded", "Expanded states by stage", "Expanded (nodes)", True, None),
        ("time", "time_ms_median", "Solver time including heuristic preparation", "Median time (ms)", True, None),
        ("memory", "peak_mem_kb", "Peak traced search memory", "Peak memory (KB = bytes / 1024)", False, None),
        ("heuristics", "expanded", "A* heuristic comparison", "Expanded (nodes)", True,
         ["astar", "astar_manhattan"]),
    ]
    paths = []
    for name, metric, title, ylabel, log, algorithms in jobs:
        # An absent heuristic pair is explicit, rather than silently plotting other solvers.
        if name == "heuristics" and not set(algorithms).intersection(data.algorithm):
            figure, axis = plt.subplots(figsize=(12, 6.5))
            axis.text(0.5, 0.5, "No A* heuristic results in input CSV", ha="center", transform=axis.transAxes)
            axis.set(xlabel="Stage ID", ylabel=ylabel, title=f"{title}\n{label}")
        else:
            figure = metric_figure(data, metric, f"{title}\n{label}", ylabel, log=log, algorithms=algorithms)
        path = figures / f"{name}.png"
        try:
            figure.savefig(path, dpi=180, facecolor="white")
        finally:
            plt.close(figure)
        paths.append(path)
    figure = _length_cost_figure(data, label)
    try:
        figure.savefig(figures / "length_cost.png", dpi=180, facecolor="white")
    finally:
        plt.close(figure)
    paths.append(figures / "length_cost.png")
    manifest = {"label": label, "input": _provenance(csv_path, data),
                "hash_normalization": "file bytes with CRLF normalized to LF before SHA-256",
                "original": _provenance(original, original_data) if original_data is not None else None,
                "figures": [path.name for path in paths],
                "statistics": "solved and verified=True only; failures retained as bottom symbols",
                "time": "median of runner timings, including heuristic preparation; sample count retained",
                "memory": "separate tracemalloc peak in KB (bytes/1024), not process RSS"}
    (output / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return paths


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv", type=Path, help="Task 1.6 CSV")
    parser.add_argument("--out", type=Path, default=Path("results"))
    parser.add_argument("--original", type=Path, help="Separate CSV for the 33 original stages")
    parser.add_argument("--label", default="Benchmark results", help="Dataset label printed on charts/tables")
    args = parser.parse_args(argv)
    try:
        paths = create_report(args.csv, args.out, original=args.original, label=args.label)
    except (OSError, ValueError) as error:
        print(f"Report error: {error}", file=sys.stderr)
        return 1
    print(f"Exported {len(paths)} figures, tables and manifest to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
