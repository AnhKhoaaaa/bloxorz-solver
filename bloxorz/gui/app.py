# Phụ trách: VT4 - Task 4.2 / 4.3
"""
Cửa sổ chính và điều phối giao diện ứng dụng.
- Mặc định: Micro-Renderer WebGL Three.js Desktop.
- Fallback duy nhất: Terminal Text Mode (run_text).
Zero OpenGL & Zero Ursina bloat.
"""

from __future__ import annotations

import importlib
import sys
import traceback
from typing import Callable

from bloxorz.gui.controller import GameController
from bloxorz.gui.fake_scene import FakeScene, Scene, run_text
from bloxorz.model import Action, State
from bloxorz.stage import Stage

SCENE_MODULE = "bloxorz.gui.scene.view"


class TextBoardScene:
    """Scene dự phòng vẽ bằng ký tự khi chưa nạp được SceneView."""

    def __init__(self) -> None:
        self.fake = FakeScene()

    def load_stage(self, stage: Stage, state: State) -> None:
        self.fake.load_stage(stage, state)

    def on_move(self, old: State, action: Action, new: State) -> None:
        self.fake.on_move(old, action, new)

    def on_fall(self, old: State, action: Action) -> None:
        self.fake.on_fall(old, action)

    def on_win(self, state: State) -> None:
        self.fake.on_win(state)

    def is_animating(self) -> bool:
        return False


def make_scene(fallback: Callable[[], Scene] = TextBoardScene) -> Scene:
    """Nạp SceneView của VT3; nếu có lỗi cú pháp hoặc chưa có thì dùng cảnh tạm."""
    try:
        view = importlib.import_module(SCENE_MODULE)
    except Exception:
        print(f"[Cảnh báo] Không nạp được {SCENE_MODULE}, đang dùng cảnh chữ tạm thời. Chi tiết lỗi:", file=sys.stderr)
        traceback.print_exc()
        return fallback()
    if not hasattr(view, "SceneView"):
        print(f"[Thông báo] {SCENE_MODULE} chưa có SceneView, đang dùng cảnh chữ tạm thời.", file=sys.stderr)
        return fallback()
    return view.SceneView()


def run(controller: GameController, engine: str = "webgl") -> None:
    """Khởi chạy ứng dụng với Single Engine WebGL Three.js hoặc Terminal Text."""
    if engine == "text":
        run_text(controller)
        return

    try:
        scene = make_scene()
        if hasattr(scene, "bind_controller"):
            scene.bind_controller(controller)
        if hasattr(scene, "load_stage"):
            scene.load_stage(controller.stage, controller.state)

        if hasattr(scene, "run_webgl"):
            scene.run_webgl(title=f"Bloxorz: Voxel Edition (WebGL 3D) - {controller.stage.id}")
        elif hasattr(scene, "run_window"):
            scene.run_window(title=f"Bloxorz: Voxel Edition (WebGL 3D) - {controller.stage.id}")
        else:
            run_text(controller)
    except Exception as exc:
        print(f"[Cảnh báo] WebGL 3D không khả dụng ({exc}). Tự động chuyển sang Terminal Text Mode...")
        run_text(controller)
