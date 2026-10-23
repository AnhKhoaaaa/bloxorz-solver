# Phụ trách: VT4 - Task 4.2
"""
Mock scene dùng cho việc kiểm thử UI khi không có 3D.

- Scene: giao diện tối thiểu mà app.py gọi tới cảnh vẽ. SceneView 3D (VT3, task 3.1) cần có
  đủ các hàm này để thay thế FakeScene.
- FakeScene: cảnh giả, ghi lại các sự kiện (dùng trong test) và vẽ màn chơi bằng ký tự.
- run_text(): chơi tay ngay trong terminal, không cần Ursina (python main.py --text).
"""

from __future__ import annotations

from typing import Callable, Protocol

from bloxorz.engine import get_block_cells
from bloxorz.gui.controller import GameController
from bloxorz.model import Action, State
from bloxorz.stage import Stage

# Ký tự khi vẽ bằng chữ
BLOCK = "@"
BRIDGE_OPEN = "="
BRIDGE_CLOSED = "-"
SWITCH_CHARS = {"soft": "o", "heavy": "x", "split": "*"}

HELP = "W/A/S/D: lăn khối   R: chơi lại   U: lùi 1 bước   N/P: màn sau/trước   Q: thoát"


class Scene(Protocol):
    def load_stage(self, stage: Stage, state: State) -> None:
        """Vẽ lại toàn bộ màn và đặt khối ở state (gọi khi vào màn, chơi lại, undo)."""

    def on_move(self, old: State, action: Action, new: State) -> None:
        """Khối lăn hợp lệ từ old sang new."""

    def on_fall(self, old: State, action: Action) -> None:
        """Khối lăn từ old theo action và rơi."""

    def on_win(self, state: State) -> None:
        """Khối đứng vào lỗ đích."""


class FakeScene:
    """Cảnh giả: lưu sự kiện vào events và vẽ được màn hiện tại bằng render()."""

    def __init__(self) -> None:
        self.events: list[tuple] = []
        self.stage: Stage | None = None
        self.state: State | None = None

    def load_stage(self, stage: Stage, state: State) -> None:
        self.stage, self.state = stage, state
        self.events.append(("load", stage.id, state))

    def on_move(self, old: State, action: Action, new: State) -> None:
        self.state = new
        self.events.append(("move", old, action, new))

    def on_fall(self, old: State, action: Action) -> None:
        self.events.append(("fall", old, action))

    def on_win(self, state: State) -> None:
        self.events.append(("win", state))

    def render(self) -> str:
        """Lưới ký tự: ô màn chơi, cầu đang mở '=' / đóng '-', công tắc o/x/*, khối '@'."""
        if self.stage is None or self.state is None:
            return ""
        stage, state = self.stage, self.state
        rows = [list(row.ljust(stage.cols, ".")) for row in stage.grid]
        for p, bid in stage.bridge_at.items():
            rows[p[0]][p[1]] = BRIDGE_OPEN if bid in state.bridges_open else BRIDGE_CLOSED
        for p, sw in stage.switch_at.items():
            rows[p[0]][p[1]] = SWITCH_CHARS[sw.kind]
        if state.pose is None:
            cells = [state.pos, state.cube2]
        else:
            cells = list(get_block_cells(state.pose, state.pos))
        for r, c in cells:
            if 0 <= r < len(rows) and 0 <= c < len(rows[r]):
                rows[r][c] = BLOCK
        return "\n".join("".join(row) for row in rows)


def apply_key(controller: GameController, scene: Scene, key: str) -> str | None:
    """Chuyển 1 phím vào controller rồi báo cho scene. Dùng chung cho app.py và run_text()."""
    old = controller.state
    result = controller.handle_key(key)
    action = controller.last_action
    if result == "moved":
        scene.on_move(old, action, controller.state)
    elif result == "won":
        scene.on_move(old, action, controller.state)
        scene.on_win(controller.state)
    elif result == "fell":
        scene.on_fall(old, action)
    elif result in ("restart", "undo", "next", "prev"):
        scene.load_stage(controller.stage, controller.state)
    return result


def hud_text(controller: GameController) -> str:
    """Dòng trạng thái: tên màn, số bước, thông báo thắng/rơi."""
    stage = controller.stage
    text = f"Màn {controller.index + 1}/{len(controller.stages)}: {stage.id} ({stage.group})   Bước: {controller.moves}"
    if controller.status == "won":
        text += "   HOÀN THÀNH! Nhấn N để sang màn sau"
    elif controller.status == "fell":
        text += "   RƠI! Nhấn R để chơi lại hoặc U để lùi 1 bước"
    return text


def run_text(
    controller: GameController,
    read: Callable[[str], str] = input,
    write: Callable[[str], None] = print,
) -> None:
    """Chơi tay trong terminal. Mỗi dòng nhập có thể gồm nhiều phím, ví dụ 'ddsw'."""
    scene = FakeScene()
    scene.load_stage(controller.stage, controller.state)
    write(HELP)
    while True:
        write("")
        write(scene.render())
        write(hud_text(controller))
        try:
            line = read("> ").strip().lower()
        except EOFError:
            return
        for key in line:
            if key == "q":
                return
            apply_key(controller, scene, key)
