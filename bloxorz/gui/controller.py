# Phụ trách: VT4 - Task 4.2 / 4.4
"""
Bộ điều khiển phím di chuyển và chuyển khối.

GameController giữ trạng thái 1 ván chơi tay (màn hiện tại, State, số bước, lịch sử để undo)
và gọi engine để lăn khối. Module này KHÔNG import Ursina để test được không cần đồ họa;
app.py (Ursina) và fake_scene.py (chế độ chữ) chỉ chuyển phím vào handle_key().
"""

from __future__ import annotations

from typing import Literal, Sequence

from bloxorz.engine import initial_state, is_goal, step
from bloxorz.model import Action, Direction, State
from bloxorz.stage import Stage

Status = Literal["playing", "won", "fell"]
Outcome = Literal["moved", "won", "fell", "ignored"]

# Tên phím theo Ursina; chế độ chữ dùng chung các chữ cái w/a/s/d
KEY_DIRECTIONS: dict[str, Direction] = {
    "up arrow": Direction.UP, "w": Direction.UP,
    "down arrow": Direction.DOWN, "s": Direction.DOWN,
    "left arrow": Direction.LEFT, "a": Direction.LEFT,
    "right arrow": Direction.RIGHT, "d": Direction.RIGHT,
}
KEY_COMMANDS: dict[str, str] = {
    "r": "restart",
    "u": "undo", "backspace": "undo",
    "n": "next", "page down": "next",
    "p": "prev", "page up": "prev",
    "space": "switch",
}


class GameController:
    """
    Ván chơi tay trên danh sách màn:
    - move(direction): lăn khối 1 bước, trả "moved" | "won" | "fell" | "ignored".
    - restart(), undo(), next_stage(), prev_stage(), load(index).
    - Sau khi thắng/rơi, mọi nước đi bị bỏ qua cho tới khi restart/undo/chuyển màn.
    - Khi khối đã tách (state.pose is None): nước đi điều khiển cube active_cube (0 hoặc 1),
      switch_cube() (phím Space) đổi cube đang chọn.
    """

    def __init__(self, stages: Sequence[Stage], index: int = 0):
        if not stages:
            raise ValueError("need at least one stage")
        self.stages = list(stages)
        self.load(index)

    @property
    def stage(self) -> Stage:
        return self.stages[self.index]

    def load(self, index: int) -> None:
        """Chuyển sang màn thứ index (kẹp trong khoảng hợp lệ) và bắt đầu lại từ đầu."""
        self.index = max(0, min(index, len(self.stages) - 1))
        self.restart()

    def restart(self) -> None:
        self.state: State = initial_state(self.stage)
        self.status: Status = "playing"
        self.moves = 0
        self.history: list[tuple[State, int]] = []  # (state, active_cube) trước mỗi nước đi
        self.last_action: Action | None = None
        self.active_cube = 0

    @property
    def is_split(self) -> bool:
        return self.state.pose is None

    def switch_cube(self) -> bool:
        """Đổi cube đang điều khiển. Trả False nếu khối chưa tách."""
        if not self.is_split:
            return False
        self.active_cube = 1 - self.active_cube
        return True

    def move(self, direction: Direction) -> Outcome:
        if self.status != "playing":
            return "ignored"
        action = Action(direction, cube=self.active_cube if self.is_split else None)
        # Cube đứng yên trong nước này (chỉ dùng khi đang tách)
        still = (self.state.cube2 if self.active_cube == 0 else self.state.pos) if self.is_split else None
        self.last_action = action
        self.moves += 1
        new = step(self.state, action, self.stage)
        if new is None:
            # Giữ nguyên state trước khi rơi để scene vẽ hoạt ảnh rơi từ đúng chỗ
            self.status = "fell"
            return "fell"
        self.history.append((self.state, self.active_cube))
        self.state = new
        if new.pose is None:
            # State luôn chuẩn hóa pos < cube2 nên viên vừa đi có thể bị đổi chỗ sang cube2:
            # chọn lại đúng viên vừa đi để nước sau không "nhảy khối".
            # Vừa tách từ khối nguyên (still is None) thì chọn cube 0.
            self.active_cube = 1 if new.pos == still else 0
        if is_goal(new, self.stage):
            self.status = "won"
            return "won"
        return "moved"

    def undo(self) -> bool:
        """Quay lại 1 bước (kể cả ngay sau khi rơi). Trả False nếu không còn gì để undo."""
        if self.status == "fell":
            self.status = "playing"
            self.moves -= 1
            return True
        if not self.history:
            return False
        self.state, self.active_cube = self.history.pop()
        self.status = "playing"
        self.moves -= 1
        return True

    def next_stage(self) -> bool:
        if self.index + 1 >= len(self.stages):
            return False
        self.load(self.index + 1)
        return True

    def prev_stage(self) -> bool:
        if self.index == 0:
            return False
        self.load(self.index - 1)
        return True

    def handle_key(self, key: str) -> str | None:
        """
        Xử lý 1 phím. Trả về tên việc đã làm để UI cập nhật:
        "moved" | "won" | "fell" | "ignored" (phím hướng), "restart" | "undo" | "next" | "prev" | "switch",
        hoặc None nếu phím không dùng / lệnh không thực hiện được.
        """
        if key in KEY_DIRECTIONS:
            return self.move(KEY_DIRECTIONS[key])
        command = KEY_COMMANDS.get(key)
        if command == "restart":
            self.restart()
        elif command == "undo" and not self.undo():
            return None
        elif command == "next" and not self.next_stage():
            return None
        elif command == "prev" and not self.prev_stage():
            return None
        elif command == "switch" and not self.switch_cube():
            return None
        return command
