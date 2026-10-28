"""Kiểm thử công cụ Benchmark Runner (Task 1.6) - benchmark/run.py."""

import csv
from pathlib import Path
import pytest
from bloxorz.loader import load_stages
from benchmark.run import (
    CSV_COLUMNS,
    build_parser,
    load_all_stages,
    main,
    run_benchmark,
)


def test_bench_parser_defaults():
    """Kiểm tra giá trị mặc định của bộ phân tích tham số CLI."""
    parser = build_parser()
    args = parser.parse_args([])
    assert args.stages == ["stages/bench"]
    assert "bfs" in args.algos
    assert "dfs" in args.algos
    assert args.repeat == 5
    assert args.timeout == 60.0
    assert args.out == "results/run.csv"


def test_bench_no_ursina_dependency():
    """Đảm bảo gói benchmark chạy headless hoàn toàn, không có import ursina."""
    bench_dir = Path("benchmark")
    for py_file in bench_dir.glob("*.py"):
        content = py_file.read_text(encoding="utf-8")
        assert "ursina" not in content.lower(), f"Phát hiện import ursina trong {py_file}!"


def test_bench_load_all_stages_fixtures():
    """Kiểm tra load_all_stages với thư mục fixtures và file đơn lẻ."""
    stages = load_all_stages(["stages/fixtures"])
    assert len(stages) >= 3
    stage_ids = {s.id for s in stages}
    assert "fixture_basic" in stage_ids or "basic" in stage_ids or len(stage_ids) >= 3

    # Load 1 file cụ thể
    single = load_all_stages(["stages/fixtures/basic.json"])
    assert len(single) == 1


def test_bench_run_fixtures_csv(tmp_path):
    """Kiểm tra chạy benchmark trên fixtures với BFS và repeat 2, xuất CSV đủ cột."""
    out_csv = tmp_path / "test_run.csv"
    fixtures = load_stages("stages/fixtures")

    results = run_benchmark(
        stages=fixtures,
        algos=["bfs"],
        repeat=2,
        timeout=10.0,
        out_path=out_csv,
    )

    assert len(results) == len(fixtures)
    assert out_csv.exists()

    with open(out_csv, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        assert reader.fieldnames == CSV_COLUMNS

        rows = list(reader)
        assert len(rows) == len(fixtures)

        for row in rows:
            assert row["algorithm"] == "bfs"
            assert row["status"] == "solved"
            assert row["verified"] == "True"
            assert int(row["length"]) > 0
            assert float(row["time_ms_median"]) >= 0.0
            # time_ms_all phải có 2 giá trị nối bằng dấu ;
            times = row["time_ms_all"].split(";")
            assert len(times) == 2
            assert row["commit"] != ""
            assert row["python"] != ""


def test_bench_main_cli_execution(tmp_path):
    """Kiểm tra gọi main() mô phỏng lệnh CLI: python -m benchmark.run."""
    out_csv = tmp_path / "cli_run.csv"
    ret = main([
        "--stages", "stages/fixtures/basic.json",
        "--algos", "bfs", "dfs",
        "--repeat", "2",
        "--timeout", "5",
        "--out", str(out_csv),
    ])

    assert ret == 0
    assert out_csv.exists()

    with open(out_csv, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        assert len(rows) == 2  # 1 màn × 2 thuật toán
        algos_in_csv = {r["algorithm"] for r in rows}
        assert algos_in_csv == {"bfs", "dfs"}
        for r in rows:
            assert r["status"] == "solved"
            assert r["verified"] == "True"


def test_bench_invalid_repeat():
    """Kiểm tra parser từ chối repeat < 1 hoặc sai kiểu dữ liệu."""
    parser = build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["--repeat", "0"])

    with pytest.raises(SystemExit):
        parser.parse_args(["--repeat", "-3"])

    with pytest.raises(SystemExit):
        parser.parse_args(["--repeat", "invalid"])


def test_bench_invalid_timeout():
    """Kiểm tra parser từ chối timeout âm, vô cùng hoặc NaN."""
    parser = build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["--timeout", "-0.1"])

    with pytest.raises(SystemExit):
        parser.parse_args(["--timeout", "inf"])

    with pytest.raises(SystemExit):
        parser.parse_args(["--timeout", "nan"])


def test_bench_invalid_algo(tmp_path):
    """Kiểm tra CLI từ chối thuật toán không hợp lệ (typo) trước khi chạy và trả mã khác 0."""
    out_csv = tmp_path / "typo_run.csv"
    ret = main([
        "--stages", "stages/fixtures/basic.json",
        "--algos", "bfs", "typo_algo",
        "--out", str(out_csv),
    ])
    assert ret == 2
    assert not out_csv.exists()


def test_bench_timeout_no_fake_padding(tmp_path):
    """Kiểm tra khi timeout, runner dừng sớm và chỉ ghi đúng số lần chạy thực tế (không đệm giả)."""
    from bloxorz.stage import Stage

    # Tạo stage lớn với timeout_s = 0.0 để kích hoạt timeout ngay lần đầu
    large_grid = tuple("#" * 40 for _ in range(40))
    stage = Stage(
        id="timeout_stage",
        group="test",
        grid=large_grid,
        start=(20, 20),
        goal=(0, 0),
    )

    out_csv = tmp_path / "timeout_run.csv"
    results = run_benchmark(
        stages=[stage],
        algos=["bfs"],
        repeat=5,
        timeout=0.0,
        out_path=out_csv,
    )

    assert len(results) == 1
    row = results[0]
    assert row["status"] == "timeout"
    # Chỉ ghi nhận đúng 1 lần chạy thực tế, không nhân bản thành 5 lần
    times = row["time_ms_all"].split(";")
    assert len(times) == 1
