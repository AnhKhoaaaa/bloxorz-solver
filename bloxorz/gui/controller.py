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
}


class GameController:
    """
    Ván chơi tay trên danh sách màn:
    - move(direction): lăn khối 1 bước, trả "moved" | "won" | "fell" | "ignored".
    - restart(), undo(), next_stage(), prev_stage(), load(index).
    - Sau khi thắng/rơi, mọi nước đi bị bỏ qua cho tới khi restart/undo/chuyển màn.
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
        self.history: list[State] = []
        self.last_action: Action | None = None

    def move(self, direction: Direction) -> Outcome:
        if self.status != "playing":
            return "ignored"
        action = Action(direction)
        self.last_action = action
        self.moves += 1
        new = step(self.state, action, self.stage)
        if new is None:
            # Giữ nguyên state trước khi rơi để scene vẽ hoạt ảnh rơi từ đúng chỗ
            self.status = "fell"
            return "fell"
        self.history.append(self.state)
        self.state = new
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
        self.state = self.history.pop()
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
        "moved" | "won" | "fell" | "ignored" (phím hướng), "restart" | "undo" | "next" | "prev",
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
        return command
