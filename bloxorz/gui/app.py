# Phụ trách: VT4 - Task 4.2 / 4.3
"""
Cửa sổ chính và điều phối giao diện ứng dụng.
- Mặc định: Micro-Renderer WebGL Three.js Desktop.
- Fallback duy nhất: Terminal Text Mode (run_text).
- Sự kiện người chơi từ WebGL do WebEventRouter xử lý, gắn vào bridge của cảnh qua connect_events():
  - "ready"      : vẽ lại màn hiện tại.
  - "action"     : lăn khối theo hướng UP/DOWN/LEFT/RIGHT; báo scene on_move / on_fall / on_win.
                   "SWITCH" đổi khối đang điều khiển khi khối đã tách (phím Space; đi qua "action" vì kênh
                   pywebview của bridge chỉ chuyển tiếp các sự kiện định sẵn).
  - "undo"       : lùi 1 bước rồi vẽ lại; "restart": chơi lại màn.
  - "next_stage" / "prev_stage": sang màn sau / trước, quay vòng ở 2 đầu danh sách màn.
  - "solve_ai"   : giải màn hiện tại bằng thuật toán payload["algorithm"] (mặc định A*). Có lời giải thì đưa ván
    về đầu màn, đi từng bước qua controller rồi gửi play_solution {"steps", "delay", "solver"} cho WebGL phát
    lại; không có lời giải thì chỉ gửi "solver" để giao diện báo lý do (không giải được / quá thời gian / lỗi).
  Mọi sự kiện trả {"ok": True}; bridge tự gửi kèm các lệnh vẽ mà scene vừa đẩy.
Zero OpenGL & Zero Ursina bloat.
"""

from __future__ import annotations

import importlib
import sys
import traceback
from typing import Any, Callable

from bloxorz import search
from bloxorz.gui.controller import GameController
from bloxorz.gui.fake_scene import FakeScene, Scene, run_text
from bloxorz.gui.solver_runner import WEB_STEP_DELAY_S, solution_steps, solver_info
from bloxorz.model import Action, Direction, State
from bloxorz.stage import Stage

SCENE_MODULE = "bloxorz.gui.scene.view"

DIRECTIONS = {"UP": Direction.UP, "DOWN": Direction.DOWN, "LEFT": Direction.LEFT, "RIGHT": Direction.RIGHT}
SWITCH_ACTION = "SWITCH"  # đổi khối khi tách
DEFAULT_ALGORITHM = "astar"


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


class WebEventRouter:
    """Nhận sự kiện từ WebGL, điều khiển GameController và báo lại cho scene (Scene Protocol + play_solution)."""

    def __init__(self, controller: GameController | None, scene: Any,
                 run_fn: Callable[[str, Stage], Any] = search.run) -> None:
        self.controller = controller
        self.scene = scene
        self.run_fn = run_fn

    def handle(self, event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        controller, scene = self.controller, self.scene
        if not controller:
            return {"ok": True}

        if event_type == "ready":
            scene.load_stage(controller.stage, controller.state)

        elif event_type == "action":
            name = str(payload.get("action", "")).upper()
            direction = DIRECTIONS.get(name)
            if name == SWITCH_ACTION:
                controller.switch_cube()
            elif direction is not None:
                old = controller.state
                outcome = controller.move(direction)
                action = controller.last_action  # Action kèm chỉ số cube khi tách (Scene Protocol)
                if outcome == "fell":
                    scene.on_fall(old, action)
                elif outcome in ("moved", "won"):
                    scene.on_move(old, action, controller.state)
                    if outcome == "won":
                        scene.on_win(controller.state)

        elif event_type == "undo":
            if controller.undo():
                scene.load_stage(controller.stage, controller.state)

        elif event_type == "restart":
            controller.restart()
            scene.load_stage(controller.stage, controller.state)

        elif event_type == "next_stage":
            controller.load((controller.index + 1) % len(controller.stages))
            scene.load_stage(controller.stage, controller.state)

        elif event_type == "prev_stage":
            controller.load((controller.index - 1) % len(controller.stages))
            scene.load_stage(controller.stage, controller.state)

        elif event_type == "solve_ai":
            algorithm = str(payload.get("algorithm", DEFAULT_ALGORITHM)).lower()
            try:
                result = self.run_fn(algorithm, controller.stage)
            except Exception as err:
                print(f"[AI Solver Error]: {err}")
            else:
                self._play_solution(result)

        return {"ok": True}

    def _play_solution(self, result: Any) -> None:
        """Gửi lời giải cho WebGL phát lại; controller đi theo cùng các bước để luôn khớp màn hình."""
        controller, scene = self.controller, self.scene
        bridge = getattr(scene, "bridge", None)
        if bridge is None:  # cảnh không có WebGL (cảnh chữ / test): dùng API play_solution của scene nếu có
            if result.status == "solved" and result.actions and hasattr(scene, "play_solution"):
                scene.play_solution(result.actions, delay=WEB_STEP_DELAY_S)
            return

        steps = []
        if result.status == "solved":
            controller.restart()
            scene.load_stage(controller.stage, controller.state)  # WebGL vẽ lại từ đầu màn trước khi phát
            steps = solution_steps(controller, result.actions, bridge.serialize_move)
        bridge.send_command("play_solution",
                            {"steps": steps, "delay": WEB_STEP_DELAY_S, "solver": solver_info(result)})


def connect_events(scene: object, controller: GameController) -> WebEventRouter | None:
    """
    Gắn WebEventRouter vào bridge của cảnh WebGL, thay cho bộ xử lý nằm trong SceneView.bind_controller:
    điều khiển ván chơi và gọi solver là phần của VT4.
    Cảnh không có bridge (cảnh chữ tạm) thì bỏ qua, trả None.
    """
    bridge = getattr(scene, "bridge", None)
    if bridge is None or not hasattr(bridge, "set_event_handler"):
        return None
    router = WebEventRouter(controller, scene)
    bridge.set_event_handler(router.handle)
    return router


def run(controller: GameController, engine: str = "webgl") -> None:
    """Khởi chạy ứng dụng với Single Engine WebGL Three.js hoặc Terminal Text."""
    if engine == "text":
        run_text(controller)
        return

    try:
        scene = make_scene()
        if hasattr(scene, "bind_controller"):
            scene.bind_controller(controller)  # gán scene.controller (VT3 dùng để đếm bước / số màn)
        connect_events(scene, controller)
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
