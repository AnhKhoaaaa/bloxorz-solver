"""
Kiểm thử SceneView không cần cửa sổ đồ họa - Task 3.2
- Khi khối tách, viên vừa đi lăn tới đúng ô kể cả khi State đổi chỗ pos/cube2.
"""

from types import SimpleNamespace

import pytest

from bloxorz.gui.scene import view as view_module
from bloxorz.gui.scene.view import SceneView
from bloxorz.model import Action, Direction, State


class FakeBlock:
    """Thay BlockView: 2 entity giả, update_from_state đặt cube1 ở state.pos như bản thật."""

    def __init__(self, state):
        self.cube1 = SimpleNamespace(name="A", pos=state.pos)
        self.cube2 = SimpleNamespace(name="B", pos=state.cube2)

    def update_from_state(self, state):
        self.cube1.pos, self.cube2.pos = state.pos, state.cube2


@pytest.fixture
def scene(monkeypatch):
    rolls = []

    def fake_roll(entity, target, on_complete=None):
        rolls.append((entity.name, target))
        on_complete()

    monkeypatch.setattr(view_module, "animate_roll", fake_roll)
    s = SceneView.__new__(SceneView)
    s.board = SimpleNamespace(update_bridges=lambda state: None)
    s._animating = False
    s.rolls = rolls
    return s


@pytest.mark.parametrize("old, action, moved_to", [
    # Không đổi chỗ
    (State(None, (0, 0), (2, 0)), Action(Direction.RIGHT, cube=0), (0, 1)),
    (State(None, (0, 0), (2, 0)), Action(Direction.RIGHT, cube=1), (2, 1)),
    # Cube 0 xuống (1,0) > (0,2) nên trở thành cube2
    (State(None, (0, 0), (0, 2)), Action(Direction.DOWN, cube=0), (1, 0)),
    # Cube 1 lên (0,2) < (1,0) nên trở thành pos
    (State(None, (1, 0), (1, 2)), Action(Direction.UP, cube=1), (0, 2)),
])
def test_split_roll_follows_moved_cube(scene, old, action, moved_to):
    still = old.cube2 if action.cube == 0 else old.pos
    new = State(None, moved_to, still)
    scene.block = FakeBlock(old)
    mover = scene.block.cube1 if action.cube == 0 else scene.block.cube2

    scene.on_move(old, action, new)

    r, c = moved_to
    assert scene.rolls == [(mover.name, (float(c), 0.55, -float(r)))]
    assert mover.pos == moved_to  # entity vừa lăn vẫn nằm ở ô nó lăn tới sau khi cập nhật
    assert not scene.is_animating()
