"""
Kiểm thử script đổi màn Quick Bloxorz sang JSON - Task 4.7
- Đổi map Tiled giả lập: dời tọa độ âm, cầu, công tắc, công tắc tách.
- Nhiều nút chồng trên 1 ô thành 1 công tắc có actions; báo lỗi khi mâu thuẫn.
- Mọi file trong stages/original/ đọc được bằng loader.
"""

import json
from dataclasses import replace
from pathlib import Path

import pytest

from bloxorz.loader import load_stage, load_stages, parse_stage, stage_to_dict
from tools.convert_quick_bloxorz import UnsupportedStage, convert, format_stage

ROOT = Path(__file__).resolve().parents[2]
ORIGINAL = ROOT / "stages" / "original"


def tile(oid, row, col, **props):
    obj = {"id": oid, "x": col * 50, "y": row * 50, "width": 50, "height": 50}
    if props:
        obj["properties"] = props
    return obj


def tiled(**layers):
    return {"layers": [{"type": "tilelayer", "name": "Tile Layer 1"}] + [
        {"type": "objectgroup", "name": name, "objects": objs} for name, objs in layers.items()
    ]}


def test_convert_shifts_negative_coordinates_and_maps_tiles():
    data = convert(tiled(
        normal=[tile(1, 0, 0), tile(2, 0, -1), tile(3, -1, 0)],
        weak=[tile(4, 0, 1)],
        goal=[tile(5, 0, 2)],
        border=[tile(6, -2, -2)],
    ), level=4)
    assert data["id"] == "stage_04"
    assert data["group"] == "G2"
    assert data["grid"] == [".#..", "#SFG"]
    assert "bridges" not in data and "switches" not in data


def test_convert_bridges_and_switches():
    data = convert(tiled(
        normal=[tile(1, 0, 0)],
        bridge=[
            tile(2, 0, 2, id="bridgeA", startActivated=False),
            tile(3, 0, 3, id="bridgeA", startActivated=True),  # 1 ô mở => cả cầu mở
        ],
        button=[
            tile(4, 0, 1, activating="bridgeA", hard=False, type="toggle"),
            tile(5, 1, 0, activating="bridgeA", hard=True, type="off"),
        ],
        goal=[tile(6, 0, 4)],
    ), level=2)
    assert data["grid"] == ["S#BBG", "#...."]
    assert data["bridges"] == [{"id": "bridgeA", "cells": [[0, 2], [0, 3]], "initially_open": True}]
    assert data["switches"] == [
        {"id": "s1", "kind": "soft", "pos": [0, 1], "mode": "toggle", "bridges": ["bridgeA"]},
        {"id": "s2", "kind": "heavy", "pos": [1, 0], "mode": "permanent", "set_to": "close", "bridges": ["bridgeA"]},
    ]
    assert data["group"] == "G3"
    parse_stage(data)


def test_convert_splitter_targets_use_object_ids():
    data = convert(tiled(
        normal=[tile(1, 0, 0), tile(2, 2, 0), tile(3, 2, 2)],
        splitter=[tile(4, 0, 1, split1=3, split2=2)],
        goal=[tile(5, 2, 1)],
    ), level=8)
    assert data["switches"] == [{"id": "s1", "kind": "split", "pos": [0, 1], "targets": [[2, 2], [2, 0]]}]
    assert data["group"] == "G4"


def stacked_buttons(*buttons):
    return tiled(
        normal=[tile(1, 0, 0)],
        bridge=[tile(2, 0, 2, id="bridgeA"), tile(3, 0, 3, id="bridgeB")],
        button=[tile(10 + i, 0, 1, **b) for i, b in enumerate(buttons)],
        goal=[tile(6, 0, 4)],
    )


def test_convert_stacked_buttons_become_actions():
    data = convert(stacked_buttons(
        dict(activating="bridgeA", hard=True, type="on"),
        dict(activating="bridgeB", hard=True, type="off"),
    ), level=17)
    assert data["switches"] == [
        {"id": "s1", "kind": "heavy", "pos": [0, 1], "actions": [["bridgeA", "open"], ["bridgeB", "close"]]},
    ]
    sw = parse_stage(data).switch_at[(0, 1)]
    assert sw.actions == (("bridgeA", "open"), ("bridgeB", "close"))
    assert sw.mode is None and sw.bridges == ("bridgeA", "bridgeB")


def test_convert_stacked_buttons_with_same_action_stay_simple():
    data = convert(stacked_buttons(
        dict(activating="bridgeA", hard=False, type="toggle"),
        dict(activating="bridgeB", hard=False, type="toggle"),
    ), level=1)
    assert data["switches"][0] == {
        "id": "s1", "kind": "soft", "pos": [0, 1], "mode": "toggle", "bridges": ["bridgeA", "bridgeB"],
    }


@pytest.mark.parametrize("buttons, message", [
    ((dict(activating="bridgeA", hard=True, type="on"), dict(activating="bridgeB", hard=False, type="off")),
     "mixes soft and heavy"),
    ((dict(activating="bridgeA", hard=True, type="on"), dict(activating="bridgeA", hard=True, type="off")),
     "both opens and closes 'bridgeA'"),
])
def test_convert_rejects_conflicting_buttons(buttons, message):
    with pytest.raises(UnsupportedStage, match=message):
        convert(stacked_buttons(*buttons), level=1)


def test_format_stage_is_valid_json_and_round_trips():
    data = convert(tiled(
        normal=[tile(1, 0, 0)],
        splitter=[tile(2, 0, 1, split1=1, split2=3)],
        goal=[tile(3, 0, 2)],
    ), level=1)
    assert json.loads(format_stage(data)) == data


def test_original_stages_load():
    stages = load_stages(ORIGINAL)
    assert len(stages) == 33
    assert all(s.id == p.stem for s, p in zip(stages, sorted(ORIGINAL.glob("*.json"))))
    assert all(parse_stage(stage_to_dict(s)) == s for s in stages)


def test_original_stage_01_matches_known_layout():
    basic = load_stage(ROOT / "stages" / "fixtures" / "basic.json")
    assert load_stage(ORIGINAL / "stage_01.json") == replace(basic, id="stage_01")
