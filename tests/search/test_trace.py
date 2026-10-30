"""Benchmark Visualizer: vết tìm kiếm (bloxorz/search/trace.py) khớp với solver thật."""
from pathlib import Path

import pytest

from bloxorz.loader import load_stage
from bloxorz.search import run
from bloxorz.search.trace import collect_trace

FIXTURES = Path(__file__).resolve().parents[2] / "stages" / "fixtures"


@pytest.mark.parametrize("algorithm", ["bfs", "dfs", "ucs", "astar", "astar_manhattan"])
def test_trace_matches_real_search(algorithm):
    stage = load_stage(FIXTURES / "basic.json")
    trace = collect_trace(algorithm, stage)
    result = run(algorithm, stage)
    assert trace["status"] == result.status == "solved"
    assert not trace["truncated"]
    assert len(trace["events"]) == trace["stats"]["expanded"] == result.expanded  # 1 sự kiện / nút mở rộng
    assert trace["events"][0]["cells"] == [list(stage.start)]                       # nút đầu tiên là xuất phát
    assert trace["path"][0] == [list(stage.start)] and trace["path"][-1] == [list(stage.goal)]
    assert len(trace["path"]) == result.length + 1


def test_astar_trace_has_heuristic_field_and_h():
    stage = load_stage(FIXTURES / "basic.json")
    trace = collect_trace("astar", stage)
    field = trace["heuristic_field"]
    assert field[f"{stage.goal[0]},{stage.goal[1]}"] == 0
    assert all(f"{r},{c}" in field for r, row in enumerate(stage.grid) for c, ch in enumerate(row) if ch != ".")
    assert all(ev["h"] is not None and ev["g"] is not None and ev["f"] == round(ev["g"] + ev["h"], 2)
               for ev in trace["events"])


def test_uninformed_trace_has_no_heuristic():
    trace = collect_trace("bfs", load_stage(FIXTURES / "basic.json"))
    assert trace["heuristic_field"] is None
    assert all(ev["h"] is None for ev in trace["events"])


def test_split_trace_records_two_cubes():
    trace = collect_trace("bfs", load_stage(FIXTURES / "split.json"))
    assert trace["status"] == "solved"
    def apart(cells):  # 2 cube rời nhau, không phải khối nằm
        return len(cells) == 2 and abs(cells[0][0] - cells[1][0]) + abs(cells[0][1] - cells[1][1]) > 1

    assert any(apart(ev["cells"]) for ev in trace["events"])
    assert trace["switches"] and trace["switches"][0]["kind"] == "split"


def test_unknown_algorithm_is_rejected():
    with pytest.raises(ValueError):
        collect_trace("nope", load_stage(FIXTURES / "basic.json"))
