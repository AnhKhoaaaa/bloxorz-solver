"""Nghiệm thu tự động bộ màn 5.3; chơi tay được ghi riêng trong README."""
from collections import Counter
import json
from pathlib import Path

import pytest

from bloxorz.engine import get_block_cells
from bloxorz.gui.controller import GameController
from bloxorz.loader import load_stage, load_stages
from bloxorz.search.base import Limits, run
from tools.validate_bench import reference_bfs, replay

BENCH = Path(__file__).parents[2] / "stages" / "bench"
IDS = [f"g{group}_{index:02d}" for group, size in ((1, 4), (2, 3), (3, 4), (4, 3), (5, 3))
       for index in range(1, size + 1)]


def test_benchmark_has_exactly_17_stages_in_required_groups():
    stages = load_stages(BENCH)
    assert Counter(stage.group for stage in stages) == {"G1": 4, "G2": 3, "G3": 4, "G4": 3, "G5": 3}
    assert {stage.id for stage in stages} == {
        f"g{group}_{index:02d}" for group, size in ((1, 4), (2, 3), (3, 4), (4, 3), (5, 3))
        for index in range(1, size + 1)
    }


@pytest.mark.parametrize("stage_id", IDS)
def test_each_stage_is_solved_by_bfs_within_60_seconds_and_replays(stage_id):
    stage = load_stage(BENCH / f"{stage_id}.json")
    actions = reference_bfs(stage, timeout_s=60)
    assert actions is not None
    bfs_cost, states = replay(stage, actions)
    ucs = run("ucs", stage, Limits(timeout_s=60))
    assert ucs.status == "solved"
    cost, _ = replay(stage, ucs.actions)
    assert cost == ucs.cost <= bfs_cost
    assert len(actions) <= ucs.length
    if stage.group == "G1":
        assert not stage.switches and not stage.bridges
        assert not any("F" in row for row in stage.grid)
    elif stage.group == "G2":
        assert any("F" in row for row in stage.grid)
        assert not stage.switches and not stage.bridges
    elif stage.group == "G3":
        assert stage.switches and stage.bridges
        assert all(s.kind != "split" for s in stage.switches)
        assert not any("F" in row for row in stage.grid)
        assert any(s.bridges_open != states[0].bridges_open for s in states)
    elif stage.group == "G4":
        assert any(s.pose is None for s in states)
        assert not any("F" in row for row in stage.grid)
    else:
        mechanisms = (any("F" in row for row in stage.grid), bool(stage.bridges),
                      any(s.kind == "split" for s in stage.switches))
        assert sum(mechanisms) >= 2


@pytest.mark.parametrize("stage_id", ("g2_02", "g5_03"))
def test_two_routes_trade_one_to_three_extra_moves_for_lower_cost(stage_id):
    stage = load_stage(BENCH / f"{stage_id}.json")
    bfs = reference_bfs(stage)
    assert bfs is not None
    bfs_cost, _ = replay(stage, bfs)
    ucs = run("ucs", stage)
    assert ucs.status == "solved" and ucs.actions != bfs
    assert 1 <= ucs.length - len(bfs) <= 3
    assert ucs.cost < bfs_cost
    assert ucs.cost == ucs.length  # Lời giải an toàn không bước nào chịu phạt F.


def test_switch_coverage_and_mandatory_bridge_in_combined_two_route_stage():
    switches = [s for st in load_stages(BENCH) if st.group == "G3" for s in st.switches]
    assert {s.kind for s in switches} == {"soft", "heavy"}
    assert {s.mode for s in switches} == {"toggle", "permanent"}
    stage = load_stage(BENCH / "g5_03.json")
    actions = reference_bfs(stage)
    assert actions is not None
    _, states = replay(stage, actions)
    assert "entry" not in states[0].bridges_open
    assert any("entry" in s.bridges_open for s in states)
    assert any(s.pose is not None and (0, 3) in get_block_cells(s.pose, s.pos) for s in states)


@pytest.mark.parametrize("stage_id,original", (
    ("g1_02", 1), ("g1_03", 3), ("g1_04", 6), ("g2_03", 4),
    ("g3_03", 5), ("g3_04", 12), ("g4_02", 8), ("g4_03", 9),
    ("g5_01", 10), ("g5_02", 15),
))
def test_original_sources_are_preserved_except_benchmark_id_and_group(stage_id, original):
    actual = json.loads((BENCH / f"{stage_id}.json").read_text(encoding="utf-8"))
    source = json.loads((BENCH.parent / "original" / f"stage_{original:02d}.json").read_text(encoding="utf-8"))
    source.update(id=stage_id, group=actual["group"])
    assert actual == source


@pytest.mark.parametrize("stage_id", IDS)
def test_reference_solution_can_be_played_through_app_controller(stage_id):
    stage = load_stage(BENCH / f"{stage_id}.json")
    actions = reference_bfs(stage)
    assert actions is not None
    controller = GameController([stage])
    keys = {"U": "w", "D": "s", "L": "a", "R": "d"}
    for action in actions:
        if action.cube is not None and action.cube != controller.active_cube:
            assert controller.handle_key("space") == "switch"
        assert controller.handle_key(keys[action.direction.value]) in ("moved", "won")
    assert controller.status == "won"
    assert controller.moves == len(actions)
