# Phụ trách: VT4 - Task 4.2
"""
Cửa sổ chính và vòng lặp tương tác ứng dụng.

run(controller) mở cửa sổ Ursina, nhận phím và chuyển cho GameController qua apply_key().
Cảnh vẽ: dùng SceneView 3D của VT3 (bloxorz/gui/scene/view.py, task 3.1) khi đã có;
trước đó tạm vẽ màn bằng ký tự (TextBoardScene) để vẫn chơi tay được.
"""

from __future__ import annotations

from bloxorz.gui.controller import GameController
from bloxorz.gui.fake_scene import FakeScene, Scene, apply_key
from bloxorz.model import Action, State
from bloxorz.stage import Stage


class TextBoardScene:
    """Scene tạm trong cửa sổ Ursina: vẽ lại lưới ký tự của FakeScene sau mỗi sự kiện."""

    def __init__(self) -> None:
        from ursina import Text

        self.fake = FakeScene()
        self.text = Text(text="", font="VeraMono.ttf", origin=(0, 0), scale=1.6)

    def _redraw(self) -> None:
        self.text.text = self.fake.render()

    def load_stage(self, stage: Stage, state: State) -> None:
        self.fake.load_stage(stage, state)
        self._redraw()

    def on_move(self, old: State, action: Action, new: State) -> None:
        self.fake.on_move(old, action, new)
        self._redraw()

    def on_fall(self, old: State, action: Action) -> None:
        self.fake.on_fall(old, action)

    def on_win(self, state: State) -> None:
        self.fake.on_win(state)


def make_scene() -> Scene:
    try:
        from bloxorz.gui.scene.view import SceneView  # VT3 - task 3.1
    except ImportError:
        return TextBoardScene()
    return SceneView()


def run(controller: GameController) -> None:
    try:
        from ursina import Entity, Ursina, application, color, window
    except ImportError:
        raise SystemExit("Chưa cài Ursina: chạy `pip install -r requirements.txt`, hoặc chơi trong terminal bằng `python main.py --text`")
    from bloxorz.gui.ui import Hud

    app = Ursina(title="Bloxorz Solver", development_mode=False, fullscreen=False, borderless=False)
    window.color = color.rgb32(24, 26, 32)

    scene = make_scene()
    hud = Hud()
    scene.load_stage(controller.stage, controller.state)
    hud.update(controller)

    class KeyInput(Entity):
        def input(self, key: str) -> None:
            if key == "escape":
                application.quit()
            elif apply_key(controller, scene, key) is not None:
                hud.update(controller)

    KeyInput()
    app.run()
