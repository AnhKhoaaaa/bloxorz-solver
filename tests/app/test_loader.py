"""
Kiểm thử loader màn chơi JSON - Task 4.1
- Đọc đúng các màn mẫu trong stages/fixtures/.
- Validator bắt được các lỗi định dạng thường gặp và báo đủ đường dẫn lỗi.
- stage_to_dict -> parse_stage cho lại đúng Stage ban đầu.
"""

import copy
from pathlib import Path

import pytest

from bloxorz.loader import (
    StageFormatError,
    load_stage,
    load_stages,
    parse_stage,
    stage_to_dict,
    validate_stage_data,
)
from bloxorz.stage import Bridge, Switch

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "stages" / "fixtures"
DATA = ROOT / "tests" / "data"

VALID = {
    "id": "t",
    "group": "G2",
    "grid": [
        "S###BB###G",
        "##########",
    ],
    "bridges": [{"id": "b1", "cells": [[0, 4], [0, 5]]}],
    "switches": [
        {"id": "s1", "kind": "soft", "pos": [0, 1], "mode": "toggle", "bridges": ["b1"]},
        {"id": "s2", "kind": "heavy", "pos": [0, 3], "mode": "permanent", "set_to": "close", "bridges": ["b1"]},
        {"id": "s3", "kind": "split", "pos": [1, 5], "targets": [[1, 0], [1, 9]]},
    ],
}


ACTION_SWITCH = {"id": "s4", "kind": "heavy", "pos": [1, 1]}


def with_changes(fn):
    """Bản sao của VALID sau khi áp dụng fn (để mỗi test chỉ làm hỏng 1 chỗ)."""
    data = copy.deepcopy(VALID)
    fn(data)
    return data


def errors_of(fn):
    return validate_stage_data(with_changes(fn))


# ---------- Đọc màn hợp lệ ----------

def test_parse_valid_stage():
    stage = parse_stage(VALID)
    assert stage.id == "t" and stage.group == "G2"
    assert stage.start == (0, 0)
    assert stage.goal == (0, 9)
    assert stage.grid[0] == "####BB###G"  # 'S' được chuẩn hóa thành '#'
    assert stage.bridges == (Bridge("b1", ((0, 4), (0, 5)), False),)
    assert stage.switch_at[(0, 1)] == Switch("s1", "soft", (0, 1), mode="toggle", bridges=("b1",))
    assert stage.switch_at[(0, 3)].set_to == "close"
    assert stage.switch_at[(1, 5)].targets == ((1, 0), (1, 9))
    assert stage.switch_at[(1, 5)].mode is None
    assert stage.bridge_at[(0, 5)] == "b1"


def test_defaults_when_optional_fields_missing():
    stage = parse_stage({"id": "x", "group": "G1", "grid": ["S#G"]})
    assert stage.bridges == () and stage.switches == ()
    soft = parse_stage(with_changes(lambda d: d["switches"][1].pop("set_to"))).switch_at[(0, 3)]
    assert soft.set_to == "open"


def test_actions_switch():
    data = with_changes(lambda d: d["switches"].append(ACTION_SWITCH | {"actions": [["b1", "close"]]}))
    stage = parse_stage(data)
    sw = stage.switch_at[(1, 1)]
    assert sw.actions == (("b1", "close"),) and sw.mode is None and sw.bridges == ("b1",)
    assert stage_to_dict(stage)["switches"][3] == data["switches"][3]
    assert parse_stage(stage_to_dict(stage)) == stage


def test_actions_derived_from_mode():
    stage = parse_stage(VALID)
    assert stage.switch_at[(0, 1)].actions == (("b1", "toggle"),)
    assert stage.switch_at[(0, 3)].actions == (("b1", "close"),)
    assert stage.switch_at[(1, 5)].actions == ()


def test_ragged_rows_allowed():
    stage = parse_stage({"id": "x", "group": "G1", "grid": ["S##", "#", "##G"]})
    assert stage.cell((1, 1)) == "."


@pytest.mark.parametrize("path", sorted(FIXTURES.glob("*.json")), ids=lambda p: p.name)
def test_every_fixture_loads(path):
    stage = load_stage(path)
    assert stage.cell(stage.start) == "#"
    assert stage.cell(stage.goal) == "G"


def test_load_stages_sorted_and_unique():
    stages = load_stages(FIXTURES)
    assert len(stages) == len(list(FIXTURES.glob("*.json"))) >= 5
    assert len({s.id for s in stages}) == len(stages)


def test_round_trip():
    for stage in [parse_stage(VALID), *load_stages(FIXTURES)]:
        assert parse_stage(stage_to_dict(stage)) == stage


# ---------- Bắt lỗi định dạng ----------

@pytest.mark.parametrize("fn, expected", [
    (lambda d: d.pop("id"), "<root>: missing key 'id'"),
    (lambda d: d.update(title="x"), "<root>: unknown key 'title'"),
    (lambda d: d.update(id=""), "id: must be a non-empty string"),
    (lambda d: d.update(group="G6"), "group: must be one of"),
    (lambda d: d.update(grid=[]), "grid: must be a non-empty list of strings"),
    (lambda d: d["grid"].__setitem__(1, "####x#####"), "grid[1][4]: unknown tile 'x'"),
    (lambda d: d["grid"].__setitem__(1, "S#########"), "exactly one 'S'"),
    (lambda d: d["grid"].__setitem__(0, "S###BB####"), "exactly one 'G'"),
    # cầu
    (lambda d: d["bridges"].append({"id": "b1", "cells": [[1, 0]]}), "bridges[1].id: duplicate bridge id 'b1'"),
    (lambda d: d["bridges"][0]["cells"].append([1, 0]), "bridges[0].cells[2]: [1, 0] is '#'"),
    (lambda d: d["bridges"][0]["cells"].append([5, 5]), "bridges[0].cells[2]: [5, 5] is outside the grid"),
    (lambda d: d["bridges"][0]["cells"].append([0, True]), "expected [row, col] of 2 integers"),
    (lambda d: d["bridges"][0]["cells"].pop(), "grid[0][5]: 'B' tile is not part of any bridge"),
    (lambda d: d["bridges"][0].update(cells=[]), "bridges[0].cells: must be a non-empty list"),
    (lambda d: d["bridges"][0].update(initially_open="yes"), "initially_open: must be true or false"),
    # công tắc
    (lambda d: d["switches"][0].update(kind="laser"), "switches[0].kind: must be one of"),
    (lambda d: d["switches"][0].update(id="s2"), "switches[1].id: duplicate switch id 's2'"),
    (lambda d: d["switches"][0].update(pos=[0, 4]), "switches must sit on '#'"),
    (lambda d: d["switches"][0].update(pos=[0, 3]), "switches[1].pos: [0, 3] already has switch 's1'"),
    (lambda d: d["switches"][0].pop("mode"), "switches[0]: missing key 'mode'"),
    (lambda d: d["switches"][0].update(mode="once"), "switches[0].mode: must be one of"),
    (lambda d: d["switches"][0].update(set_to="close"), "set_to: only allowed when mode is 'permanent'"),
    (lambda d: d["switches"][1].update(set_to="shut"), "switches[1].set_to: must be one of"),
    (lambda d: d["switches"][0].update(bridges=[]), "bridges: must be a non-empty list of bridge ids"),
    (lambda d: d["switches"][0].update(bridges=["b9"]), "unknown bridge id 'b9'"),
    (lambda d: d["switches"][0].update(bridges=["b1", "b1"]), "contains duplicate bridge ids"),
    (lambda d: d["switches"][0].update(targets=[[1, 0], [1, 1]]), "switches[0]: unknown key 'targets'"),
    (lambda d: d["switches"][2].update(mode="toggle"), "switches[2]: unknown key 'mode'"),
    (lambda d: d["switches"][2].pop("targets"), "switches[2]: missing key 'targets'"),
    (lambda d: d["switches"][2].update(targets=[[1, 0]]), "must be a list of exactly 2"),
    (lambda d: d["switches"][2].update(targets=[[1, 0], [1, 0]]), "two targets must be different"),
    # công tắc nhiều hành động
    (lambda d: d["switches"][0].update(actions=[["b1", "open"]]), "switches[0].mode: not allowed together with 'actions'"),
    (lambda d: d["switches"][2].update(actions=[["b1", "open"]]), "switches[2]: unknown key 'actions'"),
    (lambda d: d["switches"].append(ACTION_SWITCH | {"actions": []}), "switches[3].actions: must be a non-empty list"),
    (lambda d: d["switches"].append(ACTION_SWITCH | {"actions": [["b1"]]}), "expected [bridge id, action]"),
    (lambda d: d["switches"].append(ACTION_SWITCH | {"actions": [["b9", "open"]]}), "switches[3].actions[0]: unknown bridge id 'b9'"),
    (lambda d: d["switches"].append(ACTION_SWITCH | {"actions": [["b1", "open"], ["b1", "close"]]}), "appears more than once"),
    (lambda d: d["switches"].append(ACTION_SWITCH | {"actions": [["b1", "flip"]]}), "action must be one of"),
])
def test_validator_reports_error(fn, expected):
    errors = errors_of(fn)
    assert any(expected in e for e in errors), errors


def test_root_must_be_object():
    assert validate_stage_data([1, 2]) == ["<root>: expected a JSON object, got list"]


def test_collects_all_errors_and_raises():
    with pytest.raises(StageFormatError) as exc:
        load_stage(DATA / "invalid_stage.json")
    errs = exc.value.errors
    assert len(errs) == 4  # group sai, ô 'B' mồ côi, công tắc ngoài lưới, id cầu lạ
    assert "invalid_stage.json" in str(exc.value)


def test_malformed_json():
    with pytest.raises(StageFormatError, match="invalid JSON"):
        load_stage(DATA / "malformed.json")


def test_duplicate_stage_ids_in_directory():
    with pytest.raises(StageFormatError, match="duplicate stage id 'dup'"):
        load_stages(DATA / "duplicate_ids")
