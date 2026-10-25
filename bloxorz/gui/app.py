# Phụ trách: VT4 - Task 4.2
"""
Cửa sổ chính và vòng lặp tương tác ứng dụng.

run(controller) mở cửa sổ Ursina, nhận phím và chuyển cho GameController qua apply_key().
Cảnh vẽ: dùng SceneView 3D của VT3 (bloxorz/gui/scene/view.py, task 3.1) khi đã có;
trước đó tạm vẽ màn bằng ký tự (TextBoardScene) để vẫn chơi tay được.
"""

from __future__ import annotations

import importlib
import sys
import traceback
from typing import Callable

from bloxorz.gui.controller import GameController
from bloxorz.gui.fake_scene import FakeScene, KeyBuffer, Scene
from bloxorz.model import Action, State
from bloxorz.stage import Stage

SCENE_MODULE = "bloxorz.gui.scene.view"


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

    def is_animating(self) -> bool:
        return False


def make_scene(fallback: Callable[[], Scene] = TextBoardScene) -> Scene:
    """
    Dùng SceneView của VT3 (task 3.1) nếu view.py đã có; nếu chưa có thì dùng cảnh tạm.
    Nếu view.py có lỗi bên trong (import sai, lỗi cú pháp, ...) thì in cảnh báo kèm traceback
    rồi mới dùng cảnh tạm, để lỗi không bị nuốt mất khi đang phát triển SceneView.
    """
    try:
        view = importlib.import_module(SCENE_MODULE)
    except Exception:
        print(f"[Cảnh báo] Không nạp được {SCENE_MODULE}, đang dùng cảnh chữ tạm thời. Chi tiết lỗi:", file=sys.stderr)
        traceback.print_exc()
        return fallback()
    if not hasattr(view, "SceneView"):
        print(f"[Thông báo] {SCENE_MODULE} chưa có SceneView (task 3.1), đang dùng cảnh chữ tạm thời.", file=sys.stderr)
        return fallback()
    return view.SceneView()


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

    keys = KeyBuffer(controller, scene)

    class KeyInput(Entity):
        def input(self, key: str) -> None:
            if key == "escape":
                application.quit()
            elif keys.press(key) is not None:
                hud.update(controller)

        def update(self) -> None:
            # Chạy phím đã giữ lại trong lúc scene diễn hoạt
            if keys.flush() is not None:
                hud.update(controller)

    KeyInput()
    app.run()
