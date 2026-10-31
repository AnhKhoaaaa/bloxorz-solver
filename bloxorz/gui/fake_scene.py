# Phụ trách: VT4 - Task 4.2 / 4.4
"""
Mock scene dùng cho việc kiểm thử UI khi không có 3D.

- Scene: giao diện tối thiểu mà app.py gọi tới cảnh vẽ. SceneView 3D (VT3, task 3.1) cần có
  đủ các hàm này để thay thế FakeScene.
- FakeScene: cảnh giả, ghi lại các sự kiện (dùng trong test) và vẽ màn chơi bằng ký tự.
- KeyBuffer: chặn phím khi scene đang diễn hoạt, giữ lại tối đa 1 phím để chạy khi hoạt ảnh xong.
- run_text(): chơi tay ngay trong terminal, không cần đồ họa (python main.py --text).
"""

from __future__ import annotations

from typing import Callable, Protocol

from bloxorz.engine import get_block_cells
from bloxorz.gui.controller import GameController
from bloxorz.model import Action, State
from bloxorz.stage import Stage

# Ký tự khi vẽ bằng chữ
BLOCK = "@"
OTHER_CUBE = "&"  # cube không được chọn khi khối đã tách
BRIDGE_OPEN = "="
BRIDGE_CLOSED = "-"
SWITCH_CHARS = {"soft": "o", "heavy": "x", "split": "*"}

HELP = "W/A/S/D: lăn khối   Space: đổi khối khi tách   R: chơi lại   U: lùi 1 bước   N/P: màn sau/trước   Q: thoát"


class Scene(Protocol):
    def load_stage(self, stage: Stage, state: State) -> None:
        """Vẽ lại toàn bộ màn và đặt khối ở state (gọi khi vào màn, chơi lại, undo)."""

    def on_move(self, old: State, action: Action, new: State) -> None:
        """Khối lăn hợp lệ từ old sang new."""

    def on_fall(self, old: State, action: Action) -> None:
        """Khối lăn từ old theo action và rơi."""

    def on_win(self, state: State) -> None:
        """Khối đứng vào lỗ đích."""

    def set_selected(self, cube: int | None) -> None:
        """Tô sáng cube đang điều khiển khi khối tách (0 = state.pos, 1 = state.cube2); None: bỏ tô sáng.
        load_stage tự bỏ tô sáng."""

    def is_animating(self) -> bool:
        """True khi scene đang bận diễn hoạt (khối đang lăn, rơi, ...); app sẽ giữ phím lại."""


class FakeScene:
    """Cảnh giả: lưu sự kiện vào events và vẽ được màn hiện tại bằng render()."""

    def __init__(self) -> None:
        self.events: list[tuple] = []
        self.stage: Stage | None = None
        self.state: State | None = None
        self.selected: int | None = None
        self.animating = False  # test đặt True để giả lập hoạt ảnh đang chạy

    def is_animating(self) -> bool:
        return self.animating

    def load_stage(self, stage: Stage, state: State) -> None:
        self.stage, self.state = stage, state
        self.selected = None
        self.events.append(("load", stage.id, state))

    def on_move(self, old: State, action: Action, new: State) -> None:
        self.state = new
        self.events.append(("move", old, action, new))

    def on_fall(self, old: State, action: Action) -> None:
        self.events.append(("fall", old, action))

    def on_win(self, state: State) -> None:
        self.events.append(("win", state))

    def set_selected(self, cube: int | None) -> None:
        self.selected = cube
        self.events.append(("selected", cube))

    def render(self) -> str:
        """Lưới ký tự: ô màn chơi, cầu đang mở '=' / đóng '-', công tắc o/x/*, khối '@' (khi tách: cube đang chọn
        '@', cube còn lại '&')."""
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
        for i, (r, c) in enumerate(cells):
            if 0 <= r < len(rows) and 0 <= c < len(rows[r]):
                other = state.pose is None and self.selected is not None and i != self.selected
                rows[r][c] = OTHER_CUBE if other else BLOCK
        return "\n".join("".join(row) for row in rows)


def apply_key(controller: GameController, scene: Scene, key: str) -> str | None:
    """Chuyển 1 phím vào controller rồi báo cho scene. Dùng chung cho app.py và run_text()."""
    old = controller.state
    result = controller.handle_key(key)
    _notify(controller, scene, old, result)
    return result


def apply_action(controller: GameController, scene: Scene, action: Action) -> str:
    """Đi 1 Action có sẵn (bước replay lời giải của solver) rồi báo cho scene như apply_key()."""
    old = controller.state
    result = controller.play(action)
    _notify(controller, scene, old, result)
    return result


def _notify(controller: GameController, scene: Scene, old: State, result: str | None) -> None:
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
    notify_selected(controller, scene, result)


def selected_cube(controller: GameController) -> int | None:
    """Chỉ số cube đang chọn để scene tô sáng; None khi khối chưa tách."""
    return controller.active_cube if controller.is_split else None


def notify_selected(controller: GameController, scene: Scene, result: str | None) -> None:
    """
    Báo scene.set_selected sau 1 việc: đổi khối (Space), mỗi nước đi khi còn tách (kể cả vừa "split", vì số thứ tự
    cube có thể đổi), event "merge" (None), và sau khi vẽ lại màn (restart/undo/đổi màn/"ready") nếu vẫn đang tách.
    """
    if result in ("moved", "won"):
        notify = controller.is_split or controller.last_event == "merge"
    else:
        notify = result in ("switch", "restart", "undo", "next", "prev", "ready") and controller.is_split
    set_selected = getattr(scene, "set_selected", None)
    if notify and set_selected is not None:
        set_selected(selected_cube(controller))


class KeyBuffer:
    """
    Cổng nhận phím cho app: khi scene.is_animating() thì không chạy phím ngay mà giữ lại
    phím mới nhất (tối đa 1); flush() được gọi mỗi frame để chạy phím đó khi hoạt ảnh xong.
    Tránh việc giữ/spam phím làm controller chạy trước hoạt ảnh nhiều bước.
    """

    def __init__(self, controller: GameController, scene: Scene) -> None:
        self.controller = controller
        self.scene = scene
        self.pending: str | None = None

    def press(self, key: str) -> str | None:
        if self.scene.is_animating():
            self.pending = key
            return None
        self.pending = None
        return apply_key(self.controller, self.scene, key)

    def flush(self) -> str | None:
        if self.pending is None or self.scene.is_animating():
            return None
        key, self.pending = self.pending, None
        return apply_key(self.controller, self.scene, key)


def hud_text(controller: GameController) -> str:
    """Dòng trạng thái: tên màn, số bước, cube đang chọn khi tách, thông báo thắng/rơi."""
    stage = controller.stage
    text = f"Màn {controller.index + 1}/{len(controller.stages)}: {stage.id} ({stage.group})   Bước: {controller.moves}"
    if controller.is_split:
        text += f"   Đang điều khiển khối {controller.active_cube + 1}/2 (Space để đổi)"
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
            line = read("> ").lower()
        except EOFError:
            return
        for key in line:
            if key == "q":
                return
            apply_key(controller, scene, "space" if key == " " else key)
