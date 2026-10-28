# Phụ trách: VT4 - Task 4.2 / 4.3
"""
Cửa sổ chính và vòng lặp tương tác ứng dụng.

run(controller) mở cửa sổ Ursina, nhận phím và chuyển cho GameController qua apply_key().
Panel solver (task 4.3, solver_runner.SolverSession) nhận các phím Tab/G/Enter/C trước.
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


def run(controller: GameController, engine: str = "webgl") -> None:
    scene = make_scene()

    # 1. BẢN CHÍNH: Micro-Renderer WebGL Three.js Desktop Native (Tầng 1)
    if engine == "webgl" and hasattr(scene, "run_webgl"):
        try:
            if hasattr(scene, "bind_controller"):
                scene.bind_controller(controller)
            scene.run_webgl(title=f"Bloxorz: Voxel Edition (WebGL 3D) - {controller.stage.id}")
            return
        except Exception as exc:
            print(f"[Cảnh báo] WebGL 3D không khả dụng ({exc}). Đang tự động chuyển sang Fallback Native OpenGL 3.3 Core (v2)...")

    # 2. BẢN DỰ PHÒNG THAY CHO URSINA: Native OpenGL 3.3 Core Profile (v2)
    if engine not in ("text", "ursina") and (hasattr(scene, "run_opengl") or hasattr(scene, "run_native_window")):
        try:
            if hasattr(scene, "bind_controller"):
                scene.bind_controller(controller)
            run_fn = getattr(scene, "run_opengl", None) or getattr(scene, "run_native_window", None)
            run_fn(title=f"Bloxorz: Voxel Edition (OpenGL 3.3) - {controller.stage.id}")
            return
        except Exception as exc:
            print(f"[Cảnh báo] Native OpenGL 3.3 không khả dụng ({exc}). Đang chuyển sang chế độ dự phòng tiếp theo...")

    # 3. Tuỳ chọn kế thừa nếu người dùng truyền rõ --ursina
    if engine == "ursina":
        try:
            from ursina import Entity, Ursina, application, color, time, window
            from bloxorz.gui.solver_runner import SolverSession
            from bloxorz.gui.ui import Hud, SolverPanel

            app = Ursina(title="Bloxorz Solver (Ursina Legacy)", development_mode=False, fullscreen=False, borderless=False)
            window.color = color.rgb32(24, 26, 32)

            u_scene = make_scene()
            hud = Hud()
            panel = SolverPanel()
            session = SolverSession(controller, u_scene)
            u_scene.load_stage(controller.stage, controller.state)

            def refresh() -> None:
                hud.update(controller)
                panel.update(session)

            refresh()
            keys = KeyBuffer(controller, u_scene)

            class KeyInput(Entity):
                def input(self, key: str) -> None:
                    if key == "escape":
                        session.runner.cancel()
                        application.quit()
                    elif session.handle_key(key):
                        keys.pending = None
                        refresh()
                    elif keys.press(key) is not None:
                        refresh()

                def update(self) -> None:
                    changed = session.update(time.dt)
                    if not session.replaying and keys.flush() is not None:
                        changed = True
                    if changed or session.solving:
                        refresh()

            KeyInput()
            app.run()
            return
        except Exception as exc:
            print(f"[Cảnh báo] Ursina không thể khởi chạy ({exc}). Đang chuyển sang chế độ text terminal...")

    # 4. BẢN DỰ PHÒNG CUỐI CÙNG: Terminal text mode (không phụ thuộc bất kỳ thư viện GUI nào)
    from bloxorz.gui.fake_scene import run_text
    run_text(controller)
