"""
Kiểm thử khung ứng dụng chơi tay - Task 4.2
- GameController: lăn khối, thắng, rơi, undo, chơi lại, chuyển màn, phím tắt.
- FakeScene / apply_key: scene nhận đúng sự kiện, vẽ màn bằng ký tự.
- run_text: chơi trong terminal với input giả lập.
- main.select_stages: chọn màn theo id hoặc đường dẫn file.
- Issue #12: chọn cube khi khối tách; #13: KeyBuffer khi scene diễn hoạt; #14: make_scene báo lỗi view.py.
Không cần Ursina.
"""

import sys
import types
from pathlib import Path

import pytest

from bloxorz.gui.controller import GameController
from bloxorz.gui.app import SCENE_MODULE, make_scene
from bloxorz.gui.fake_scene import FakeScene, KeyBuffer, apply_key, banner_text, hud_text, run_text
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
    assert game.handle_key("space") is None       # chưa tách khối thì Space không làm gì


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
    assert "HOÀN THÀNH" not in hud_text(game, show_result=False)


def test_banner_text(game):
    assert banner_text(game) is None
    game.move(U)
    assert banner_text(game)[0] == "RƠI XUỐNG VỰC!"
    game.restart()
    for _ in range(4):
        game.move(R)
    title, sub = banner_text(game)
    assert title == "HOÀN THÀNH!" and sub.startswith("4 bước") and "R để chơi lại" in sub  # màn cuối
    two = GameController([game.stage, game.stage])
    for _ in range(4):
        two.move(R)
    assert "N để sang màn sau" in banner_text(two)[1]


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


# ---------- Issue #12: chọn cube khi khối tách ----------

@pytest.fixture
def split_game():
    g = GameController([stage(["S#####", "######", "#####G"])])
    g.state = State(None, (0, 0), (2, 0))  # giả lập khối đã tách (engine 2.4 chưa có)
    return g


def test_split_move_sends_active_cube(split_game):
    split_game.move(R)
    assert split_game.last_action.cube == 0
    split_game.undo()
    assert split_game.handle_key("space") == "switch" and split_game.active_cube == 1
    split_game.move(R)
    assert split_game.last_action.cube == 1


def test_intact_block_sends_no_cube(game):
    game.move(R)
    assert game.last_action.cube is None
    assert not game.switch_cube() and game.active_cube == 0


def test_switch_cube_resets_on_restart(split_game):
    split_game.switch_cube()
    split_game.restart()
    assert split_game.active_cube == 0 and not split_game.is_split


def test_hud_shows_active_cube(split_game, game):
    assert "Đang điều khiển khối 1/2" in hud_text(split_game)
    split_game.switch_cube()
    assert "Đang điều khiển khối 2/2" in hud_text(split_game)
    assert "Đang điều khiển" not in hud_text(game)


def test_run_text_space_key(split_game):
    inputs = iter([" ", "q"])
    run_text(split_game, read=lambda _: next(inputs), write=lambda _: None)
    assert split_game.active_cube == 1


# ---------- Issue #13: KeyBuffer khi scene đang diễn hoạt ----------

def test_key_buffer_holds_one_key_while_animating(game):
    scene = FakeScene()
    keys = KeyBuffer(game, scene)
    assert keys.press("d") == "moved"
    scene.animating = True
    assert keys.press("d") is None and keys.press("d") is None and keys.press("a") is None
    assert game.moves == 1 and keys.pending == "a"     # chỉ giữ phím mới nhất
    assert keys.flush() is None and game.moves == 1     # vẫn đang diễn hoạt
    scene.animating = False
    assert keys.flush() == "moved" and game.moves == 2
    assert keys.pending is None and keys.flush() is None


def test_fake_scene_not_animating_by_default():
    assert FakeScene().is_animating() is False


# ---------- Issue #14: make_scene không nuốt lỗi của view.py ----------

def test_make_scene_without_scene_view_uses_fallback(monkeypatch, capsys):
    monkeypatch.setitem(sys.modules, SCENE_MODULE, types.ModuleType(SCENE_MODULE))
    assert isinstance(make_scene(fallback=FakeScene), FakeScene)
    assert "chưa có SceneView" in capsys.readouterr().err


def test_make_scene_reports_broken_view(monkeypatch, capsys):
    monkeypatch.setitem(sys.modules, SCENE_MODULE, None)  # import view.py sẽ ném ImportError
    assert isinstance(make_scene(fallback=FakeScene), FakeScene)
    err = capsys.readouterr().err
    assert "[Cảnh báo] Không nạp được" in err and "Traceback" in err


def test_make_scene_uses_scene_view(monkeypatch):
    module = types.ModuleType(SCENE_MODULE)
    module.SceneView = FakeScene
    monkeypatch.setitem(sys.modules, SCENE_MODULE, module)
    assert isinstance(make_scene(fallback=lambda: None), FakeScene)


def test_active_cube_follows_moved_cube_after_reorder():
    # cube 0 ở (0,0), cube 1 ở (0,2): cube 0 đi xuống (1,0) > (0,2) nên State đổi chỗ 2 cube
    g = GameController([stage(["S#####", "######", "#####G"])])
    g.state = State(None, (0, 0), (0, 2))
    assert g.move(D) == "moved"
    assert g.state.pos == (0, 2) and g.state.cube2 == (1, 0)
    assert g.active_cube == 1  # viên vừa đi giờ nằm ở cube2
    g.move(R)
    assert g.last_action.cube == 1 and g.state.cube2 == (1, 1)  # vẫn đi đúng viên đó
    g.undo()
    g.undo()
    assert g.state.pos == (0, 0) and g.active_cube == 0


def test_scene_view_protocol_contract():
    """Kiểm tra SceneView đáp ứng đầy đủ chữ ký phương thức của Scene Protocol (is_animating, load_stage, on_move, on_fall, on_win)."""
    # Import không cần Ursina runtime vì chỉ kiểm tra chữ ký method
    import inspect
    from bloxorz.gui.fake_scene import Scene
    from bloxorz.gui.scene.view import SceneView

    expected_methods = {"is_animating", "load_stage", "on_move", "on_fall", "on_win"}
    for method_name in expected_methods:
        assert hasattr(SceneView, method_name), f"SceneView must have method {method_name}"
        assert callable(getattr(SceneView, method_name))

