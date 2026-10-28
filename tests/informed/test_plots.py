"""Task 5.5: honest aggregation, visible failures and headless report export."""
import csv
import json

import pytest
from PIL import Image

from benchmark import plots
from benchmark.run import CSV_COLUMNS


def row(stage="g1_01", algorithm="bfs", **changes):
    result = dict(zip(CSV_COLUMNS, (
        stage, "G1", algorithm, "solved", "2", "2", "3", "0.0",
        "0.0;0.0", "4.0", "True", "abc123", "3.12.0", "test-machine",
    )))
    result.update(changes)
    return result


def write_csv(tmp_path, rows, name="input.csv"):
    path = tmp_path / name
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    return path


def test_summary_excludes_failed_solutions_and_counts_missing_pairs(tmp_path):
    path = write_csv(tmp_path, [
        row(time_ms_median="10", time_ms_all="9;11", peak_mem_kb="8"),
        row("g1_02", time_ms_median="30", time_ms_all="29;31", length="4", cost="8"),
        row("g1_03", status="timeout", verified="", time_ms_median="999", time_ms_all="999"),
        row("g1_04", verified="False", length="100", cost="100"),
        row(algorithm="ucs"),
    ])
    data = plots.load_results(path)
    summary = plots.summarize(data).set_index(["group", "algorithm"])
    bfs = summary.loc[("G1", "bfs")]
    assert bfs["total"] == 4 and bfs["solved"] == 2
    assert bfs["timeout"] == 1 and bfs["invalid"] == 1
    assert bfs["time_ms_median"] == 20
    assert bfs["length_mean"] == 3 and bfs["cost_mean"] == 5
    assert summary.loc[("G1", "ucs"), "missing"] == 3
    assert data.loc[0, "time_ms_median"] == 10


@pytest.mark.parametrize("changes", [
    {"time_ms_median": "NaN"}, {"peak_mem_kb": "-1"},
    {"expanded": "2.5"}, {"length": "oops"}, {"cost": "inf"},
    {"time_ms_all": "1;nan"}, {"status": "unknown"}, {"verified": "maybe"},
])
def test_rejects_malformed_measurements(tmp_path, changes):
    with pytest.raises(ValueError):
        plots.load_results(write_csv(tmp_path, [row(**changes)]))


def test_rejects_duplicate_stage_algorithm_and_mixed_environments(tmp_path):
    for rows in ([row(), row()], [row(), row("g1_02", commit="different")]):
        with pytest.raises(ValueError):
            plots.load_results(write_csv(tmp_path, rows))


def test_rejects_empty_csv_and_missing_columns(tmp_path):
    with pytest.raises(ValueError):
        plots.load_results(write_csv(tmp_path, []))
    path = tmp_path / "incomplete.csv"
    path.write_text("stage_id,algorithm\ng1_01,bfs\n", encoding="utf-8")
    with pytest.raises(ValueError):
        plots.load_results(path)


def test_zero_times_blank_memory_and_failures_stay_visible_on_log_plot(tmp_path):
    data = plots.load_results(write_csv(tmp_path, [
        row(), row("g1_02", status="timeout", verified="", peak_mem_kb=""),
        row("g1_03", status="unsolvable", verified="", peak_mem_kb=""),
    ]))
    figure = plots.metric_figure(data, "time_ms_median", "Test", "Time (ms)", log=True)
    try:
        axis = figure.axes[0]
        assert axis.get_yscale() == "log"
        assert [tick.get_text() for tick in axis.get_xticklabels()] == ["g1_01", "g1_02", "g1_03"]
        legend = [text.get_text() for text in axis.get_legend().get_texts()]
        assert "timeout" in legend and "unsolvable" in legend
        assert any("zero" in text.lower() for text in legend)
    finally:
        import matplotlib.pyplot as plt
        plt.close(figure)


def test_cli_exports_five_charts_tables_and_33_stage_appendix(tmp_path):
    path = write_csv(tmp_path, [
        row(algorithm=algo, expanded=str(expanded))
        for algo, expanded in (("bfs", 10), ("ucs", 10), ("astar", 5), ("astar_manhattan", 8))
    ])
    original = write_csv(tmp_path, [row(f"stage_{i:02d}") for i in range(1, 34)], "original.csv")
    out = tmp_path / "report"
    assert plots.main([str(path), "--out", str(out), "--original", str(original), "--label", "TEST DATA"]) == 0
    images = sorted((out / "figures").glob("*.png"))
    assert len(images) == 5
    for path in images:
        with Image.open(path) as picture:
            assert picture.width > 800 and picture.height > 500
            assert min(picture.info["dpi"]) >= 150
    for name in ("summary.csv", "summary.md", "details.csv", "details.md", "original.md", "observations.md"):
        assert (out / "tables" / name).is_file()
    appendix = (out / "tables" / "original.md").read_text(encoding="utf-8")
    assert "stage_33" in appendix and "33" in appendix
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["label"] == "TEST DATA"
    assert manifest["input"]["commit"] == "abc123"
    assert manifest["original"]["stages"] == 33
    observations = (out / "tables" / "observations.md").read_text(encoding="utf-8")
    assert "50.0%" in observations  # paired A* reduction relative to UCS


def test_cli_bad_input_does_not_create_partial_report(tmp_path):
    out = tmp_path / "report"
    assert plots.main([str(tmp_path / "missing.csv"), "--out", str(out)]) != 0
    assert not out.exists()


@pytest.mark.filterwarnings("error::FutureWarning")
def test_all_failed_group_has_no_fake_zero_statistics(tmp_path):
    data = plots.load_results(write_csv(tmp_path, [
        row(status="timeout", verified="", peak_mem_kb=""),
        row("g1_02", status="unsolvable", verified="", peak_mem_kb=""),
    ]))
    summary = plots.summarize(data).iloc[0]
    import pandas as pd
    assert summary["solved"] == 0 and summary["total"] == 2
    assert pd.isna(summary["time_ms_median"])
    assert pd.isna(summary["peak_mem_kb_median"])
    assert pd.isna(summary["length_mean"])
    assert "Không có lời giải đã xác minh" in plots.observations(data, "test")


def test_heuristic_comparison_uses_only_common_verified_stages(tmp_path):
    data = plots.load_results(write_csv(tmp_path, [
        row(algorithm="ucs", expanded="100"),
        row(algorithm="astar", expanded="50"),
        row("g1_02", algorithm="ucs", expanded="1000"),
        row("g1_02", algorithm="astar", expanded="1", verified="False"),
    ]))
    text = plots.observations(data, "test")
    assert "Trên 1 màn chung" in text and "50.0%" in text


def test_missing_memory_is_counted_separately_from_a_real_zero(tmp_path):
    data = plots.load_results(write_csv(tmp_path, [row(peak_mem_kb=""), row("g1_02", peak_mem_kb="0")]))
    summary = plots.summarize(data).iloc[0]
    assert summary["solved"] == 2 and summary["memory_samples"] == 1
    assert summary["peak_mem_kb_median"] == 0


def test_provenance_checksum_survives_git_line_ending_normalization(tmp_path):
    path = write_csv(tmp_path, [row()])
    data = plots.load_results(path)
    before = plots._provenance(path, data)["sha256"]
    path.write_bytes(path.read_bytes().replace(b"\r\n", b"\n"))
    after = plots._provenance(path, plots.load_results(path))["sha256"]
    assert before == after
