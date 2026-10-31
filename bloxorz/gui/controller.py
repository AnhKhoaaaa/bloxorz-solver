# Phụ trách: VT4 - Task 4.2 / 4.4
"""
Bộ điều khiển phím di chuyển và chuyển khối.

GameController giữ trạng thái 1 ván chơi tay (màn hiện tại, State, số bước, lịch sử để undo)
và gọi engine để lăn khối. Module này thuần logic để test được không cần đồ họa;
app.py (WebGL) và fake_scene.py (chế độ chữ) chỉ chuyển phím vào handle_key().
"""

from __future__ import annotations

from typing import Literal, Sequence

from bloxorz.engine import initial_state, is_goal, step
from bloxorz.model import Action, Direction, Pos, State
from bloxorz.stage import Stage

Status = Literal["playing", "won", "fell"]
Outcome = Literal["moved", "won", "fell", "ignored"]
SplitEvent = Literal["split", "merge"]

# Tên phím theo chuẩn hướng; chế độ chữ dùng chung các chữ cái w/a/s/d
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
    - play(action): như move() nhưng nhận Action của solver (chọn đúng cube khi tách).
    - restart(), undo(), next_stage(), prev_stage(), load(index).
    - Sau khi thắng/rơi, mọi nước đi bị bỏ qua cho tới khi restart/undo/chuyển màn.
    - Khi khối đã tách (state.pose is None): nhớ cube đang chọn theo VỊ TRÍ ô (selected_pos), không theo số
      0/1, vì State luôn sắp 2 cube theo pos < cube2 nên số thứ tự có thể đổi sau mỗi nước.
      - Nước đi sinh event "split": chọn cube ở state.pos.
      - switch_cube() (phím Space): chọn cube còn lại; không tính là 1 nước đi.
      - Phím hướng: lăn cube đang chọn (Action.cube = active_cube); nếu vẫn đang tách thì chọn tiếp
        vị trí mới của cube vừa đi (ô khác vị trí cube đứng yên).
      - Event "merge": selected_pos = None.
      last_event cho biết nước vừa đi có "split" / "merge" hay không.
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
        self.history: list[tuple[State, Pos | None]] = []  # (state, selected_pos) trước mỗi nước đi
        self.last_action: Action | None = None
        self.last_event: SplitEvent | None = None
        self.selected_pos: Pos | None = None

    @property
    def is_split(self) -> bool:
        return self.state.pose is None

    @property
    def active_cube(self) -> int:
        """Chỉ số cube đang chọn trong state hiện tại (0 = state.pos, 1 = state.cube2); 0 khi chưa tách."""
        if not self.is_split:
            return 0
        return 1 if self.selected_pos == self.state.cube2 else 0

    def switch_cube(self) -> bool:
        """Chọn cube còn lại (không tính là 1 nước đi). Trả False nếu khối chưa tách."""
        if not self.is_split:
            return False
        self.selected_pos = self.state.pos if self.active_cube == 1 else self.state.cube2
        return True

    def move(self, direction: Direction) -> Outcome:
        if self.status != "playing":
            return "ignored"
        was_split = self.is_split
        action = Action(direction, cube=self.active_cube if was_split else None)
        # Cube đứng yên trong nước này (chỉ dùng khi đang tách)
        still = (self.state.cube2 if self.active_cube == 0 else self.state.pos) if was_split else None
        self.last_action = action
        self.last_event = None
        self.moves += 1
        new = step(self.state, action, self.stage)
        if new is None:
            # Giữ nguyên state trước khi rơi để scene vẽ hoạt ảnh rơi từ đúng chỗ
            self.status = "fell"
            return "fell"
        self.history.append((self.state, self.selected_pos))
        self.state = new
        if new.pose is None and not was_split:
            self.last_event = "split"
            self.selected_pos = new.pos
        elif new.pose is None:
            # vẫn tách: cube vừa đi là ô khác vị trí cube đứng yên
            self.selected_pos = new.cube2 if new.pos == still else new.pos
        else:
            if was_split:
                self.last_event = "merge"
            self.selected_pos = None
        if is_goal(new, self.stage):
            self.status = "won"
            return "won"
        return "moved"

    def play(self, action: Action) -> Outcome:
        """Đi đúng 1 Action có sẵn (vd. 1 bước trong lời giải của solver), kể cả chỉ số cube khi tách."""
        if self.is_split and action.cube is not None:
            self.selected_pos = self.state.pos if action.cube == 0 else self.state.cube2
        return self.move(action.direction)

    def undo(self) -> bool:
        """Quay lại 1 bước (kể cả ngay sau khi rơi). Trả False nếu không còn gì để undo."""
        if self.status == "fell":
            self.status = "playing"
            self.moves -= 1
            return True
        if not self.history:
            return False
        self.state, self.selected_pos = self.history.pop()
        self.last_event = None
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
