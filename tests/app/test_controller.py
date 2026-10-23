"""
Kiểm thử khung ứng dụng chơi tay - Task 4.2
- GameController: lăn khối, thắng, rơi, undo, chơi lại, chuyển màn, phím tắt.
- FakeScene / apply_key: scene nhận đúng sự kiện, vẽ màn bằng ký tự.
- run_text: chơi trong terminal với input giả lập.
- main.select_stages: chọn màn theo id hoặc đường dẫn file.
Không cần Ursina.
"""

from pathlib import Path

import pytest

from bloxorz.gui.controller import GameController
from bloxorz.gui.fake_scene import FakeScene, apply_key, hud_text, run_text
from bloxorz.loader import load_stage, load_stages, parse_stage
from bloxorz.model import Direction, Pose, State
from main import select_stages

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "stages" / "fixtures"
ORIGINAL = ROOT / "stages" / "original"

R, D, L, U = Direction.RIGHT, Direction.DOWN, Direction.LEFT, Direction.UP


def stage(grid, id="t", **extra):
    return parse_stage({"id": id, "group": "G1", "grid": grid, **extra})


@pytest.fixture
def game():
    # "SFF#FFG": 4 lần sang phải là tới đích (nằm qua ô dễ vỡ thì an toàn)
    return GameController([load_stage(FIXTURES / "fragile.json")])


# ---------- GameController ----------

def test_starts_standing_on_start(game):
    assert game.state == State(Pose.STANDING, (0, 0))
    assert game.status == "playing" and game.moves == 0


def test_move_and_win(game):
    assert [game.move(R) for _ in range(4)] == ["moved", "moved", "moved", "won"]
    assert game.state == State(Pose.STANDING, (0, 6))
    assert game.moves == 4
    assert game.move(L) == "ignored"  # đã thắng thì không đi tiếp


def test_fall_keeps_state_and_blocks_moves(game):
    before = game.state
    assert game.move(U) == "fell"
    assert game.status == "fell" and game.state == before and game.moves == 1
    assert game.move(R) == "ignored"


def test_standing_on_fragile_falls():
    g = GameController([stage(["S##FG"])])
    assert g.move(R) == "moved"   # nằm trên (0,1)-(0,2)
    assert g.move(R) == "fell"    # dựng đứng trên ô 'F' -> vỡ


def test_undo_restart_after_fall(game):
    game.move(R)
    game.move(U)
    assert game.status == "fell"
    assert game.undo() and game.status == "playing" and game.moves == 1
    assert game.state == State(Pose.HORIZONTAL, (0, 1))
    assert game.undo() and game.state == State(Pose.STANDING, (0, 0)) and game.moves == 0
    assert not game.undo()
    game.move(R)
    game.restart()
    assert game.state == State(Pose.STANDING, (0, 0)) and game.moves == 0 and game.history == []


def test_initial_bridges_open():
    g = GameController([stage(["S#BBG"], bridges=[{"id": "b1", "cells": [[0, 2], [0, 3]], "initially_open": True}])])
    assert g.state.bridges_open == frozenset({"b1"})


def test_stage_navigation():
    stages = load_stages(FIXTURES)
    g = GameController(stages, index=99)          # kẹp về màn cuối
    assert g.index == len(stages) - 1
    assert not g.next_stage()
    g.move(L)
    assert g.prev_stage() and g.index == len(stages) - 2 and g.moves == 0
    g.load(0)
    assert not g.prev_stage() and g.stage.id == stages[0].id


def test_requires_stages():
    with pytest.raises(ValueError):
        GameController([])


@pytest.mark.parametrize("key, direction", [
    ("d", R), ("right arrow", R), ("a", L), ("left arrow", L),
    ("w", U), ("up arrow", U), ("s", D), ("down arrow", D),
])
def test_direction_keys(key, direction):
    g = GameController([stage(["...", ".#.", "#SG", "...", "..."])])
    expected = GameController([stage(["...", ".#.", "#SG", "...", "..."])])
    expected.move(direction)
    g.handle_key(key)
    assert (g.state, g.status) == (expected.state, expected.status)


def test_command_keys(game):
    game.handle_key("d")
    assert game.handle_key("u") == "undo" and game.moves == 0
    assert game.handle_key("u") is None           # hết để undo
    game.handle_key("d")
    assert game.handle_key("r") == "restart" and game.moves == 0
    assert game.handle_key("n") is None           # chỉ có 1 màn
    assert game.handle_key("p") is None
    assert game.handle_key("space") is None       # phím chưa dùng (tách khối: task 4.4)


# ---------- FakeScene + apply_key ----------

def test_apply_key_sends_scene_events(game):
    scene = FakeScene()
    scene.load_stage(game.stage, game.state)
    for key in "dddd":
        apply_key(game, scene, key)
    kinds = [e[0] for e in scene.events]
    assert kinds == ["load", "move", "move", "move", "move", "win"]
    assert scene.state == game.state

    apply_key(game, scene, "r")
    assert scene.events[-1] == ("load", game.stage.id, game.state)

    apply_key(game, scene, "w")
    assert scene.events[-1][0] == "fall"
    assert apply_key(game, scene, "x") is None    # phím lạ: không có sự kiện mới
    assert scene.events[-1][0] == "fall"


def test_render_draws_tiles_bridges_switches_and_block():
    st = stage(
        ["S#BB#G", "######"],
        bridges=[{"id": "b1", "cells": [[0, 2], [0, 3]]}],
        switches=[
            {"id": "s1", "kind": "soft", "pos": [1, 0], "mode": "toggle", "bridges": ["b1"]},
            {"id": "s2", "kind": "heavy", "pos": [1, 1], "mode": "toggle", "bridges": ["b1"]},
            {"id": "s3", "kind": "split", "pos": [1, 2], "targets": [[1, 4], [1, 5]]},
        ],
    )
    scene = FakeScene()
    assert scene.render() == ""
    scene.load_stage(st, State(Pose.HORIZONTAL, (0, 0)))
    assert scene.render() == "@@--#G\nox*###"
    scene.load_stage(st, State(None, (1, 4), (1, 5), bridges_open=frozenset({"b1"})))
    assert scene.render() == "##==#G\nox*#@@"


def test_hud_text(game):
    assert hud_text(game).startswith("Màn 1/1: fixture_fragile (G1)   Bước: 0")
    game.move(U)
    assert "RƠI" in hud_text(game)
    game.restart()
    for _ in range(4):
        game.move(R)
    assert "HOÀN THÀNH" in hud_text(game)


def test_run_text_plays_until_quit(game):
    inputs = iter(["dd", "dd", "q"])
    out: list[str] = []
    run_text(game, read=lambda _: next(inputs), write=out.append)
    assert game.status == "won" and game.moves == 4
    assert any("HOÀN THÀNH" in line for line in out)


def test_run_text_stops_on_eof(game):
    def read(_):
        raise EOFError
    run_text(game, read=read, write=lambda _: None)


# ---------- main.select_stages ----------

def test_select_stages_by_id_and_file():
    stages, i = select_stages(ORIGINAL, "stage_05")
    assert len(stages) == 33 and stages[i].id == "stage_05"
    stages, i = select_stages(ORIGINAL, None)
    assert i == 0 and stages[0].id == "stage_01"
    stages, i = select_stages(ORIGINAL, str(FIXTURES / "split.json"))
    assert [s.id for s in stages] == ["fixture_split"] and i == 0


def test_select_stages_errors(tmp_path):
    with pytest.raises(SystemExit, match="stage_99"):
        select_stages(ORIGINAL, "stage_99")
    with pytest.raises(SystemExit, match="Không có file màn"):
        select_stages(tmp_path, None)
